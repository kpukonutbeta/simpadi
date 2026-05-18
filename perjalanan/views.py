from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from .models import SuratTugas, PerjalananDinas
from .forms import PerjalananDinasForm, BiayaPerjalananFormSet, BerkasPerjalananFormSet
from master_data.models import Provinsi, Anggaran

def get_pegawai_by_surat_tugas(request):
    surat_tugas_id = request.GET.get('surat_tugas_id')
    if not surat_tugas_id:
        return JsonResponse({'pegawai': []})
    
    try:
        surat = SuratTugas.objects.get(id=surat_tugas_id)
        pegawai_list = [
            {'id': p.id, 'nama': f"{p.nama} ({p.nip})"}
            for p in surat.pegawai.all()
        ]
        return JsonResponse({'pegawai': pegawai_list})
    except (SuratTugas.DoesNotExist, ValueError):
        return JsonResponse({'pegawai': []})

@login_required
def ajukan_perjadin(request, surat_tugas_id):
    # Ensure user has a Pegawai profile
    if not hasattr(request.user, 'pegawai_profile'):
        messages.error(request, "Akun Anda belum terhubung dengan data Pegawai.")
        return redirect('core:dashboard')
    
    pegawai = request.user.pegawai_profile
    surat_tugas = get_object_or_404(SuratTugas, id=surat_tugas_id)
    
    # Ensure Pegawai is assigned to this Surat Tugas
    if not surat_tugas.pegawai.filter(id=pegawai.id).exists():
        messages.error(request, "Anda tidak ditugaskan dalam Surat Tugas ini.")
        return redirect('core:dashboard')

    # Check if PerjalananDinas already exists for this ST and Pegawai
    # This enables syncing between Admin-created drafts and Pegawai
    perjadin_instance = PerjalananDinas.objects.filter(
        surat_tugas=surat_tugas, 
        pegawai=pegawai
    ).first()

    # If already approved or completed, don't allow editing via this form
    if perjadin_instance and perjadin_instance.status not in [PerjalananDinas.Status.DRAFT, PerjalananDinas.Status.REJECTED]:
        messages.warning(request, f"SPD ini sudah dalam status {perjadin_instance.get_status_display()} dan tidak dapat diubah lagi.")
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = PerjalananDinasForm(request.POST, instance=perjadin_instance, user=request.user)
        
        # SANGAT PENTING: Tempelkan instance sebelum validasi agar clean() di model tidak error
        form.instance.surat_tugas = surat_tugas
        form.instance.pegawai = pegawai
        
        biaya_formset = BiayaPerjalananFormSet(request.POST, instance=perjadin_instance)
        berkas_formset = BerkasPerjalananFormSet(request.POST, request.FILES, instance=perjadin_instance)

        if form.is_valid() and biaya_formset.is_valid() and berkas_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save main form
                    perjadin = form.save(commit=False)
                    perjadin.surat_tugas = surat_tugas
                    perjadin.pegawai = pegawai
                    
                    # Backend Protection: Jangan biarkan pegawai mengubah anggaran jika sudah ada
                    if not request.user.is_staff and perjadin_instance:
                        perjadin.anggaran = perjadin_instance.anggaran
                        
                    # Keep status as DRAFT if it was new, or keep existing status if it was REJECTED
                    if not perjadin.status:
                        perjadin.status = PerjalananDinas.Status.DRAFT
                    perjadin.save()
                    
                    # Save formsets: berkas_formset first so that BiayaPerjalanan can read the saved berkas nominals
                    berkas_formset.instance = perjadin
                    berkas_formset.save()
                    
                    biaya_formset.instance = perjadin
                    biaya_formset.save()
                    
                messages.success(request, "Data Perjalanan Dinas berhasil disimpan.")
                return redirect('core:dashboard')
            except Exception as e:
                messages.error(request, f"Terjadi kesalahan saat menyimpan: {e}")
        else:
            messages.error(request, "Terdapat kesalahan pada isian form. Silakan periksa kembali.")
    else:
        form = PerjalananDinasForm(instance=perjadin_instance, user=request.user)
        biaya_formset = BiayaPerjalananFormSet(instance=perjadin_instance)
        berkas_formset = BerkasPerjalananFormSet(instance=perjadin_instance)

    from master_data.models import JenisBerkas
    jenis_berkas_nominal = list(JenisBerkas.objects.filter(nominal_biaya=True).values_list('id', flat=True))
    jenis_berkas_wajib = list(JenisBerkas.objects.filter(wajib=True).values_list('id', flat=True))

    context = {
        'surat_tugas': surat_tugas,
        'perjadin': perjadin_instance,
        'form': form,
        'biaya_formset': biaya_formset,
        'berkas_formset': berkas_formset,
        'is_edit': perjadin_instance is not None,
        'jenis_berkas_nominal': jenis_berkas_nominal,
        'jenis_berkas_wajib': jenis_berkas_wajib
    }
    return render(request, 'perjalanan/ajukan_form.html', context)

@staff_member_required
def generate_spd_bulk(request):
    selected_ids = request.session.get('selected_st_ids', [])
    if not selected_ids:
        messages.warning(request, "Tidak ada Surat Tugas yang dipilih.")
        return redirect('/admin/perjalanan/surattugas/')
    
    surat_tugas_list = SuratTugas.objects.filter(id__in=selected_ids)
    
    # Get default suffix from new config model
    from .models import PengaturanNomorSPD
    config, _ = PengaturanNomorSPD.objects.get_or_create(id=1)
    default_suffix = config.suffix_format

    if request.method == 'POST':
        provinsi_id = request.POST.get('provinsi')
        anggaran_id = request.POST.get('anggaran')
        
        provinsi = get_object_or_404(Provinsi, id=provinsi_id)
        anggaran = get_object_or_404(Anggaran, id=anggaran_id)
        
        count_created = 0
        try:
            with transaction.atomic():
                for st in surat_tugas_list:
                    for pgw in st.pegawai.all():
                        # Check if SPD already exists for this pair
                        if not PerjalananDinas.objects.filter(surat_tugas=st, pegawai=pgw).exists():
                            # Note: nomor_spd will be generated automatically in .save()
                            PerjalananDinas.objects.create(
                                surat_tugas=st,
                                pegawai=pgw,
                                status=PerjalananDinas.Status.DRAFT,
                                tujuan_provinsi=provinsi,
                                anggaran=anggaran,
                                maksud_perjalanan=st.perihal,
                                tempat_tujuan="Konawe Utara" # Default
                            )
                            count_created += 1
                            
            messages.success(request, f"Berhasil menerbitkan {count_created} SPD baru dengan nomor otomatis.")
            del request.session['selected_st_ids']
            return redirect('/admin/perjalanan/perjalanandinas/')
        except Exception as e:
            messages.error(request, f"Gagal menerbitkan SPD: {e}")

    context = {
        'surat_tugas_list': surat_tugas_list,
        'default_suffix': default_suffix,
        'provinsi_list': Provinsi.objects.all(),
        'anggaran_list': Anggaran.objects.all(),
    }
    return render(request, 'perjalanan/admin_generate_spd.html', context)

@login_required
def riwayat_perjadin(request):
    if not hasattr(request.user, 'pegawai_profile'):
        messages.error(request, "Akun Anda belum terhubung dengan data Pegawai.")
        return redirect('core:dashboard')
    
    pegawai = request.user.pegawai_profile
    # Filter only those that are NOT in DRAFT (or include DRAFT if you want full history)
    # Usually history includes everything the user has done.
    history = PerjalananDinas.objects.filter(pegawai=pegawai).order_by('-tanggal_berangkat', '-created_at')
    
    return render(request, 'perjalanan/riwayat_list.html', {'history': history})
