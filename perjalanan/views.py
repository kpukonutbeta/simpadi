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
        'jenis_berkas_fb_dalam': jenis_berkas_fb_dalam
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

    # Parse dates to calculate duration using our robust parser
    durasi = 0
    if tanggal_berangkat_str and tanggal_kembali_str:
        tb = parse_date(tanggal_berangkat_str)
        tk = parse_date(tanggal_kembali_str)
        if tb and tk:
            durasi = (tk - tb).days + 1
            if durasi < 0:
                durasi = 0

    # Fetch StandarBiaya
    tarif_harian = 0.0
    plafon_hotel = 0.0
    tarif_representasi = 0.0
    plafon_transport = 0.0

    if tujuan_provinsi_id and pegawai_obj and tahun_sbm:
        try:
            sbm = StandarBiaya.objects.get(
                provinsi_id=tujuan_provinsi_id,
                golongan=pegawai_obj.golongan,
                tahun=tahun_sbm
            )
            if jenis_perjalanan == 'fullboard_luar':
                tarif_harian = float(getattr(sbm, 'uang_harian_fullboard_luar', 0))
                tarif_representasi = 0.0
            elif jenis_perjalanan == 'fullboard_dalam':
                tarif_harian = float(getattr(sbm, 'uang_harian_fullboard_dalam', 0))
                tarif_representasi = 0.0
            else:
                tarif_harian = float(sbm.uang_harian)
                tarif_representasi = float(sbm.uang_representasi)
            plafon_hotel = float(sbm.plafon_penginapan)
            plafon_transport = float(getattr(sbm, 'plafon_transportasi', 0))
        except StandarBiaya.DoesNotExist:
            pass

    # Sum berkas nominals
    total_hotel_input = 0.0
    total_malam_hotel = 0
    total_malam_lumpsum = 0
    total_malam_fb_luar = 0
    total_malam_fb_dalam = 0
    total_transport_input = 0.0
    
    berkas_list = data.get('berkas', [])
    for b in berkas_list:
        try:
            val_str = str(b.get('nominal') or 0).replace('.', '')
            nominal = float(val_str)
        except (ValueError, TypeError):
            nominal = 0.0
            
        try:
            malam_menginap = int(b.get('malam_menginap') or 0)
        except (ValueError, TypeError):
            malam_menginap = 0
            
        jb_id = b.get('jenis_berkas_id')
        if jb_id:
            try:
                jb = JenisBerkas.objects.get(id=jb_id)
                kategori = jb.kategori_biaya if hasattr(jb, 'kategori_biaya') else 'none'
                
                # Check for penginapan categories
                if kategori == 'penginapan':
                    if jb.nominal_biaya and nominal > 0: # Hotel bill
                        total_hotel_input += nominal
                        total_malam_hotel += malam_menginap if malam_menginap > 0 else 1
                elif kategori == 'penginapan_30':
                    total_malam_lumpsum += malam_menginap if malam_menginap > 0 else 1
                elif kategori == 'penginapan_fb_luar':
                    total_malam_fb_luar += malam_menginap if malam_menginap > 0 else 1
                elif kategori == 'penginapan_fb_dalam':
                    total_malam_fb_dalam += malam_menginap if malam_menginap > 0 else 1
                
                # Check for transportasi category
                elif kategori == 'transportasi':
                    if jenis_transportasi != 'mobil_dinas':
                        if nominal > 0:
                            total_transport_input += nominal
            except JenisBerkas.DoesNotExist:
                pass

    # Calculation
    fb_luar_days = min(total_malam_fb_luar, durasi)
    fb_dalam_days = min(total_malam_fb_dalam, durasi - fb_luar_days)
    normal_days = max(0, durasi - (fb_luar_days + fb_dalam_days))
    
    uang_harian_fb_luar = float(getattr(sbm, 'uang_harian_fullboard_luar', 0)) if sbm else 0.0
    uang_harian_fb_dalam = float(getattr(sbm, 'uang_harian_fullboard_dalam', 0)) if sbm else 0.0
    
    uang_harian_riil = float(
        (fb_luar_days * uang_harian_fb_luar) +
        (fb_dalam_days * uang_harian_fb_dalam) +
        (normal_days * tarif_harian)
    )
    
    if jenis_perjalanan in ['fullboard_luar', 'fullboard_dalam']:
        uang_representasi_riil = 0.0
    else:
        uang_representasi_riil = float(normal_days * tarif_representasi)

    total_malam_perjalanan = max(0, durasi - 1)
    
    # Boundary validation
    over_limit = False
    total_malam_claimed = total_malam_hotel + total_malam_lumpsum + total_malam_fb_luar + total_malam_fb_dalam
    if total_malam_claimed > total_malam_perjalanan:
        over_limit = True
        
    plafon_hotel_limit = plafon_hotel * total_malam_hotel
    biaya_hotel_riil = min(total_hotel_input, plafon_hotel_limit)
    biaya_hotel_lumpsum = 0.30 * plafon_hotel * total_malam_lumpsum
    biaya_penginapan_riil = biaya_hotel_riil + biaya_hotel_lumpsum

    if jenis_transportasi == 'mobil_dinas':
        biaya_transportasi_riil = 0.0
    else:
        if plafon_transport > 0:
            biaya_transportasi_riil = min(total_transport_input, plafon_transport)
        else:
            biaya_transportasi_riil = total_transport_input

    total_dibayarkan = uang_harian_riil + uang_representasi_riil + biaya_penginapan_riil + biaya_transportasi_riil

    # Compute unpaid/unreimbursed amount (total_tidak_dibayarkan)
    penginapan_dana_pribadi = 0.0
    if total_hotel_input > plafon_hotel_limit:
        penginapan_dana_pribadi = total_hotel_input - plafon_hotel_limit

    transportasi_dana_pribadi = 0.0
    if plafon_transport > 0 and total_transport_input > plafon_transport:
        transportasi_dana_pribadi = total_transport_input - plafon_transport

    total_tidak_dibayarkan = penginapan_dana_pribadi + transportasi_dana_pribadi

    return JsonResponse({
        'uang_harian_riil': uang_harian_riil,
        'uang_representasi_riil': uang_representasi_riil,
        'biaya_penginapan_riil': biaya_penginapan_riil,
        'biaya_transportasi_riil': biaya_transportasi_riil,
        'total_dibayarkan': total_dibayarkan,
        'total_tidak_dibayarkan': total_tidak_dibayarkan,
        'durasi_hari': durasi,
        'over_limit': over_limit,
        'plafon_hotel': float(plafon_hotel)
    })
