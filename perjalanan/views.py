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
    
    from django.db.models import Q
    jenis_berkas_penginapan = list(JenisBerkas.objects.filter(
        kategori_biaya__in=['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']
    ).values_list('id', flat=True))
    
    jenis_berkas_fb_luar = list(JenisBerkas.objects.filter(
        kategori_biaya='penginapan_fb_luar'
    ).values_list('id', flat=True))
    
    jenis_berkas_fb_dalam = list(JenisBerkas.objects.filter(
        kategori_biaya='penginapan_fb_dalam'
    ).values_list('id', flat=True))

    jenis_berkas_tiket_pesawat = list(JenisBerkas.objects.filter(
        kategori_biaya='transportasi_pesawat'
    ).values_list('id', flat=True))

    jenis_berkas_transportasi = list(JenisBerkas.objects.filter(
        kategori_biaya__in=['transportasi', 'transportasi_pesawat']
    ).values_list('id', flat=True))

    breakdown_initial = None
    if perjadin_instance and hasattr(perjadin_instance, 'biaya') and perjadin_instance.biaya:
        try:
            breakdown_initial = perjadin_instance.biaya.calculate_breakdown()
        except Exception:
            pass

    context = {
        'surat_tugas': surat_tugas,
        'perjadin': perjadin_instance,
        'form': form,
        'biaya_formset': biaya_formset,
        'berkas_formset': berkas_formset,
        'is_edit': perjadin_instance is not None,
        'jenis_berkas_nominal': jenis_berkas_nominal,
        'jenis_berkas_wajib': jenis_berkas_wajib,
        'jenis_berkas_penginapan': jenis_berkas_penginapan,
        'jenis_berkas_fb_luar': jenis_berkas_fb_luar,
        'jenis_berkas_fb_dalam': jenis_berkas_fb_dalam,
        'jenis_berkas_tiket_pesawat': jenis_berkas_tiket_pesawat,
        'jenis_berkas_transportasi': jenis_berkas_transportasi,
        'breakdown_initial': breakdown_initial
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
    history = PerjalananDinas.objects.filter(pegawai=pegawai).order_by('-surat_tugas__tanggal_berangkat', '-created_at')
    
    return render(request, 'perjalanan/riwayat_list.html', {'history': history})


import json
from datetime import datetime
from django.views.decorators.http import require_POST
from master_data.models import StandarBiaya, Pegawai, JenisBerkas

def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    # Try common formats: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

@login_required
@require_POST
def hitung_estimasi_ajax(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    # Retrieve parameters
    tanggal_berangkat_str = data.get('tanggal_berangkat')
    tanggal_kembali_str = data.get('tanggal_kembali')
    tujuan_provinsi_id = data.get('tujuan_provinsi')
    jenis_transportasi = data.get('jenis_transportasi')
    jenis_perjalanan = data.get('jenis_perjalanan')
    tahun_sbm = data.get('tahun_sbm')
    pegawai_id = data.get('pegawai_id')
    
    # If pegawai_id is not passed, use current user's profile
    if not pegawai_id and hasattr(request.user, 'pegawai_profile'):
        pegawai_obj = request.user.pegawai_profile
    elif pegawai_id:
        try:
            pegawai_obj = Pegawai.objects.get(id=pegawai_id)
        except Pegawai.DoesNotExist:
            pegawai_obj = None
    else:
        pegawai_obj = None

    tb = parse_date(tanggal_berangkat_str) if tanggal_berangkat_str else None
    tk = parse_date(tanggal_kembali_str) if tanggal_kembali_str else None
    prov = None
    if tujuan_provinsi_id:
        try:
            prov = Provinsi.objects.get(id=tujuan_provinsi_id)
        except Provinsi.DoesNotExist:
            pass

    from .models import PerjalananDinas, SuratTugas, BiayaPerjalanan

    # Construct mock SuratTugas and PerjalananDinas
    st = SuratTugas(
        tanggal_berangkat=tb,
        tanggal_kembali=tk,
        tujuan_provinsi=prov,
        jenis_perjalanan=jenis_perjalanan,
        jenis_transportasi=jenis_transportasi,
        tahun_sbm=int(tahun_sbm) if tahun_sbm else 2024
    )
    p = PerjalananDinas(
        surat_tugas=st,
        pegawai=pegawai_obj
    )
    b_obj = BiayaPerjalanan(
        perjalanan=p
    )

    berkas_payload = data.get('berkas', [])
    breakdown = b_obj.calculate_breakdown(mock_berkas=berkas_payload)

    # Serialize breakdown_categories for AJAX
    serialized_categories = {}
    for key, category in breakdown['breakdown_categories'].items():
        serialized_items = []
        for item in category['items']:
            serialized_items.append({
                'perihal': item['perihal'],
                'no': item['no'],
                'keterangan': item['keterangan'],
                'harga': float(item['harga']),
                'kuantitas': item['kuantitas'],
                'total': float(item['total']),
                'file_url': item['file_url'],
                'file_name': item['file_name'],
            })
        serialized_categories[key] = {
            'title': category['title'],
            'items': serialized_items,
            'subtotal': float(category['subtotal']),
        }

    # Return JSON with all float/int format for numeric items
    return JsonResponse({
        'uang_harian_riil': float(breakdown['uang_harian_riil']),
        'uang_representasi_riil': float(breakdown['uang_representasi_riil']),
        'biaya_penginapan_riil': float(breakdown['biaya_penginapan_riil']),
        'biaya_transportasi_riil': float(breakdown['biaya_transportasi_riil']),
        'total_dibayarkan': float(breakdown['total_dibayarkan']),
        'total_tidak_dibayarkan': float(breakdown['total_dana_pribadi']),
        'durasi_hari': breakdown['durasi_hari'],
        'over_limit': breakdown['over_limit'],
        'plafon_hotel': float(breakdown['sbm_plafon_hotel']),
        'harian_formula': breakdown['harian_formula'],
        'representasi_formula': breakdown['representasi_formula'],
        'penginapan_formula': breakdown['penginapan_formula'],
        'transport_formula': breakdown['transport_formula'],
        'breakdown_categories': serialized_categories,
    })

@login_required
def get_standar_biaya_tiket_ajax(request):
    from master_data.models import StandarBiayaTiket, JenisBerkas
    tiket_qs = StandarBiayaTiket.objects.select_related('kota_asal', 'kota_tujuan').all()
    data = []
    for t in tiket_qs:
        data.append({
            'id': t.id,
            'kota_asal_id': t.kota_asal.id,
            'kota_asal_nama': t.kota_asal.nama,
            'kota_tujuan_id': t.kota_tujuan.id,
            'kota_tujuan_nama': t.kota_tujuan.nama,
            'kelas': t.kelas,
            'kelas_display': t.get_kelas_display(),
            'nominal': float(t.nominal)
        })
    jenis_berkas_tiket_pesawat = list(JenisBerkas.objects.filter(
        kategori_biaya='transportasi_pesawat'
    ).values_list('id', flat=True))
    return JsonResponse({
        'routes': data,
        'ticket_pesawat_ids': jenis_berkas_tiket_pesawat
    })
