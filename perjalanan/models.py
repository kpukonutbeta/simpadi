from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from master_data.models import Pegawai, Provinsi, StandarBiaya, Anggaran, JenisBerkas, StandarBiayaTiket
from decimal import Decimal
from datetime import timedelta

import uuid
import os
import re

def parse_tiket_keterangan(keterangan_val):
    if not keterangan_val:
        return None, None, None, None, None, ""
    # Matches with or without user description
    match = re.match(r"^\[SBM-TIKET:(\d+)-(\d+)-(\w+):([^:]+):([^\]]+)\](?:\s*\|\s*(.*))?$", keterangan_val)
    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            match.group(3),
            match.group(4),
            match.group(5),
            match.group(6) or ""
        )
    return None, None, None, None, None, keterangan_val

def upload_surat_tugas_path(instance, filename):
    year = instance.tgl_surat.year if instance.tgl_surat else 2026
    # Replace '/' with '-' to avoid creating nested subdirectories in the filesystem
    cleaned_nomor = instance.nomor_surat.replace('/', '-') if instance.nomor_surat else 'temp'
    return f"surat_tugas/{year}/{cleaned_nomor}.pdf"

class SuratTugas(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Aktif'
        COMPLETED = 'COMPLETED', 'Selesai'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nomor_surat = models.CharField(max_length=100, unique=True, verbose_name="Nomor Surat")
    perihal = models.TextField(verbose_name="Perihal")
    tgl_surat = models.DateField(verbose_name="Tanggal Surat")
    file_path = models.FileField(
        upload_to=upload_surat_tugas_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="File Surat Tugas (PDF)"
    )
    pegawai = models.ManyToManyField(Pegawai, related_name='surat_tugas_set', verbose_name="Pegawai Terdaftar")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="Status")

    # Detail Perjalanan (Relocated from PerjalananDinas)
    tanggal_berangkat = models.DateField(verbose_name="Tanggal Berangkat", null=True, blank=True)
    tanggal_kembali = models.DateField(verbose_name="Tanggal Kembali", null=True, blank=True)
    tempat_berangkat = models.CharField(max_length=255, verbose_name="Tempat Berangkat", default="KPU Kab. Konawe Utara")
    tempat_tujuan = models.CharField(max_length=255, verbose_name="Tempat Tujuan", blank=True, null=True)
    tujuan_provinsi = models.ForeignKey(Provinsi, on_delete=models.PROTECT, verbose_name="Provinsi (SBM)", null=True, blank=True)
    tahun_sbm = models.IntegerField(
        choices=[(2023, '2023 (Tahun Lalu)'), (2024, '2024 (Tahun Ini)')],
        default=2024, 
        verbose_name="Tahun SBM"
    )
    maksud_perjalanan = models.TextField(verbose_name="Maksud Perjalanan", blank=True, null=True)
    anggaran = models.ForeignKey(Anggaran, on_delete=models.PROTECT, verbose_name="Sumber Anggaran", null=True, blank=True)
    
    class JenisPerjalanan(models.TextChoices):
        LUAR_KOTA = 'luar_kota', 'Luar Kota'
        DALAM_KOTA = 'dalam_kota', 'Dalam Kota (> 8 Jam)'
        DIKLAT = 'diklat', 'Diklat'
        
    jenis_perjalanan = models.CharField(
        max_length=20,
        choices=JenisPerjalanan.choices,
        default=JenisPerjalanan.LUAR_KOTA,
        verbose_name="Jenis Perjalanan Dinas"
    )
    
    class JenisTransportasi(models.TextChoices):
        MOBIL_DINAS = 'mobil_dinas', 'Mobil Dinas'
        UMUM = 'umum', 'Transportasi Umum'
        
    jenis_transportasi = models.CharField(
        max_length=20,
        choices=JenisTransportasi.choices,
        default=JenisTransportasi.UMUM,
        verbose_name="Jenis Transportasi"
    )

    def clean(self):
        super().clean()
        if self.tanggal_berangkat and self.tanggal_kembali:
            if self.tanggal_berangkat > self.tanggal_kembali:
                raise ValidationError("Tanggal berangkat tidak boleh setelah tanggal kembali.")
        
        # Enforce that nomor_surat and tgl_surat must be present if a file is being uploaded
        if self.file_path:
            if not self.nomor_surat:
                raise ValidationError({'nomor_surat': 'Nomor surat harus diisi terlebih dahulu sebelum mengunggah file.'})
            if not self.tgl_surat:
                raise ValidationError({'tgl_surat': 'Tanggal surat harus diisi terlebih dahulu sebelum mengunggah file.'})

    def __str__(self):
        return f"{self.nomor_surat} - {self.perihal[:30]}..."

    class Meta:
        verbose_name = "Surat Tugas"
        verbose_name_plural = "Manajemen Surat Tugas"

class PengaturanNomorSPD(models.Model):
    prefix_terakhir = models.IntegerField(default=0, verbose_name="Nomor Terakhir (Angka)")
    suffix_format = models.CharField(
        max_length=100, 
        default="/PPK-PROV.026/VII/2026", 
        verbose_name="Format Suffix (Belakang Nomor)"
    )
    
    class Meta:
        verbose_name = "Konfigurasi Nomor SPD"
        verbose_name_plural = "Konfigurasi Nomor SPD"

    def __str__(self):
        return f"Format: [Angka]{self.suffix_format} (Terakhir: {self.prefix_terakhir})"

class PerjalananDinas(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING = 'PENDING', 'Menunggu Verifikasi'
        APPROVED = 'APPROVED', 'Disetujui'
        REJECTED = 'REJECTED', 'Ditolak'
        PROCESSED = 'PROCESSED', 'Selesai Diproses'

    surat_tugas = models.ForeignKey(SuratTugas, on_delete=models.PROTECT, verbose_name="Surat Tugas")
    pegawai = models.ForeignKey(Pegawai, on_delete=models.CASCADE, verbose_name="Pegawai")
    nomor_spd = models.CharField(max_length=100, unique=True, verbose_name="Nomor SPD", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="Status")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def jenis_perjalanan(self):
        return self.surat_tugas.jenis_perjalanan

    @property
    def jenis_transportasi(self):
        return self.surat_tugas.jenis_transportasi

    @property
    def tempat_berangkat(self):
        return self.surat_tugas.tempat_berangkat

    @property
    def tempat_tujuan(self):
        return self.surat_tugas.tempat_tujuan

    @property
    def tujuan_provinsi(self):
        return self.surat_tugas.tujuan_provinsi

    @property
    def maksud_perjalanan(self):
        return self.surat_tugas.maksud_perjalanan or self.surat_tugas.perihal

    @property
    def tanggal_berangkat(self):
        return self.surat_tugas.tanggal_berangkat

    @property
    def tanggal_kembali(self):
        return self.surat_tugas.tanggal_kembali

    @property
    def anggaran(self):
        return self.surat_tugas.anggaran

    @property
    def tahun_sbm(self):
        return self.surat_tugas.tahun_sbm

    def save(self, *args, **kwargs):
        # 1. Otomatisasi Nomor SPD jika belum ada
        if not self.nomor_spd:
            from django.db import transaction
            with transaction.atomic():
                config, created = PengaturanNomorSPD.objects.get_or_create(id=1)
                config.prefix_terakhir += 1
                config.save()
                
                self.nomor_spd = f"{config.prefix_terakhir}{config.suffix_format}"
            
        super().save(*args, **kwargs)
        if hasattr(self, 'biaya'):
            self.biaya.save()

    @property
    def durasi_hari(self):
        if self.tanggal_berangkat and self.tanggal_kembali:
            delta = self.tanggal_kembali - self.tanggal_berangkat
            return delta.days + 1
        return 0

    def clean(self):
        # Validation logic remains similar...
        try:
            if hasattr(self, 'surat_tugas') and hasattr(self, 'pegawai') and self.surat_tugas and self.pegawai:
                if not self.surat_tugas.pegawai.filter(pk=self.pegawai.pk).exists():
                    raise ValidationError(f"Pegawai {self.pegawai.nama} tidak terdaftar dalam Surat Tugas {self.surat_tugas.nomor_surat}.")
        except:
            pass

        if self.tanggal_berangkat and self.tanggal_kembali:
            if self.tanggal_berangkat > self.tanggal_kembali:
                raise ValidationError("Tanggal berangkat tidak boleh setelah tanggal kembali.")
        
        if hasattr(self, 'pegawai') and self.pegawai and self.tanggal_berangkat and self.tanggal_kembali:
            overlapping = PerjalananDinas.objects.filter(
                pegawai=self.pegawai,
                surat_tugas__tanggal_berangkat__lte=self.tanggal_kembali,
                surat_tugas__tanggal_kembali__gte=self.tanggal_berangkat
            ).exclude(pk=self.pk)
            
            if overlapping.exists():
                raise ValidationError(f"Pegawai sudah memiliki jadwal perjalanan dinas lain pada rentang tanggal ini.")

    def __str__(self):
        return f"{self.nomor_spd or 'No SPD'} - {self.pegawai.nama}"

    class Meta:
        verbose_name = "Manajemen SPD"
        verbose_name_plural = "Manajemen SPD"

class BiayaPerjalanan(models.Model):
    perjalanan = models.OneToOneField(PerjalananDinas, on_delete=models.CASCADE, related_name='biaya')
    
    # Lumpsum components
    uang_harian_riil = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    uang_representasi_riil = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # At-cost components
    biaya_penginapan_riil = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    biaya_transportasi_riil = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # Personal expense share (dana pribadi)
    penginapan_dana_pribadi = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Dana Pribadi Penginapan")
    transportasi_dana_pribadi = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Dana Pribadi Transportasi")
    total_dana_pribadi = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name="Total Dana Pribadi")
    
    # System calculated (locked)
    total_dibayarkan = models.DecimalField(max_digits=15, decimal_places=0, editable=False, default=0)

    def calculate_breakdown(self, mock_berkas=None):
        # Fetch SBM
        try:
            sbm = StandarBiaya.objects.get(
                provinsi=self.perjalanan.tujuan_provinsi,
                golongan=self.perjalanan.pegawai.golongan,
                tahun=self.perjalanan.tahun_sbm
            )
            if self.perjalanan.jenis_perjalanan == 'fullboard_luar':
                tarif_harian = getattr(sbm, 'uang_harian_fullboard_luar', Decimal('0'))
            elif self.perjalanan.jenis_perjalanan == 'fullboard_dalam':
                tarif_harian = getattr(sbm, 'uang_harian_fullboard_dalam', Decimal('0'))
            else:
                tarif_harian = sbm.uang_harian
            plafon_hotel = sbm.plafon_penginapan
            tarif_representasi = sbm.uang_representasi
            plafon_transport = getattr(sbm, 'plafon_transportasi', Decimal('0'))
        except StandarBiaya.DoesNotExist:
            tarif_harian = Decimal('0')
            plafon_hotel = Decimal('0')
            tarif_representasi = Decimal('0')
            plafon_transport = Decimal('0')

        # Calculate real hotel and transport from BerkasPerjalanan based on jenis_berkas.kategori_biaya
        total_hotel_input = Decimal('0')
        total_malam_hotel = 0
        total_malam_lumpsum = 0
        total_malam_fb_luar = 0
        total_malam_fb_dalam = 0
        
        # Penjumlahan biaya transportasi terpisah
        total_transport_non_pesawat_input = Decimal('0')
        total_tiket_pesawat_riil = Decimal('0')
        tiket_pesawat_dana_pribadi = Decimal('0')

        # Collect and classify bills
        hotel_bills = []
        lumpsum_bills = []
        fb_luar_bills = []
        fb_dalam_bills = []
        flight_tickets_details = []
        non_flight_transports = []

        # Helper to retrieve file url and name
        def get_file_info(db_id=None, db_file=None):
            if db_file:
                return db_file.url, os.path.basename(db_file.name)
            if db_id:
                try:
                    db_berkas = BerkasPerjalanan.objects.get(id=db_id)
                    if db_berkas.file:
                        return db_berkas.file.url, os.path.basename(db_berkas.file.name)
                except Exception:
                    pass
            return None, None

        if mock_berkas is not None:
            for b in mock_berkas:
                jb_id = b.get('jenis_berkas_id')
                if not jb_id:
                    continue
                try:
                    jenis = JenisBerkas.objects.get(id=jb_id)
                except JenisBerkas.DoesNotExist:
                    continue
                kategori = jenis.kategori_biaya
                nominal = Decimal(str(b.get('nominal') or 0))
                malam_menginap = int(b.get('malam_menginap') or 0)
                keterangan = b.get('keterangan') or ""
                b_id = b.get('id')
                file_url, file_name = get_file_info(db_id=b_id)

                if kategori == 'penginapan':
                    if jenis.nominal_biaya and nominal:
                        m = malam_menginap if malam_menginap > 0 else 1
                        total_hotel_input += nominal
                        total_malam_hotel += m
                        hotel_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                elif kategori == 'penginapan_30':
                    m = malam_menginap if malam_menginap > 0 else 1
                    total_malam_lumpsum += m
                    lumpsum_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                elif kategori == 'penginapan_fb_luar':
                    m = malam_menginap if malam_menginap > 0 else 1
                    total_malam_fb_luar += m
                    fb_luar_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                elif kategori == 'penginapan_fb_dalam':
                    m = malam_menginap if malam_menginap > 0 else 1
                    total_malam_fb_dalam += m
                    fb_dalam_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                elif kategori in ['transportasi', 'transportasi_pesawat']:
                    if self.perjalanan.jenis_transportasi != SuratTugas.JenisTransportasi.MOBIL_DINAS:
                        if nominal:
                            asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(keterangan)
                            if asal_id and tujuan_id and kelas:
                                try:
                                    sbm_tiket = StandarBiayaTiket.objects.get(
                                        kota_asal_id=asal_id,
                                        kota_tujuan_id=tujuan_id,
                                        kelas=kelas
                                    )
                                    plafon_tiket = sbm_tiket.nominal
                                except StandarBiayaTiket.DoesNotExist:
                                    plafon_tiket = None
                                flight_tickets_details.append({
                                    'nominal': nominal,
                                    'plafon': plafon_tiket,
                                    'route_str': f"Tiket Pesawat {nama_asal} - {nama_tujuan} - {kelas.capitalize()} (PP)",
                                    'file_url': file_url,
                                    'file_name': file_name
                                })
                            else:
                                total_transport_non_pesawat_input += nominal
                                non_flight_transports.append({'nominal': nominal, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
        else:
            if self.perjalanan_id:
                for b in BerkasPerjalanan.objects.filter(perjalanan_id=self.perjalanan_id):
                    jenis = b.jenis_berkas
                    if not jenis:
                        continue
                    kategori = jenis.kategori_biaya
                    nominal = b.nominal or Decimal('0')
                    malam_menginap = b.malam_menginap
                    keterangan = b.keterangan
                    file_url, file_name = get_file_info(db_file=b.file)

                    if kategori == 'penginapan':
                        if jenis.nominal_biaya and nominal:
                            m = malam_menginap if (malam_menginap is not None and malam_menginap > 0) else 1
                            total_hotel_input += nominal
                            total_malam_hotel += m
                            hotel_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                    elif kategori == 'penginapan_30':
                        m = malam_menginap if (malam_menginap is not None and malam_menginap > 0) else 1
                        total_malam_lumpsum += m
                        lumpsum_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                    elif kategori == 'penginapan_fb_luar':
                        m = malam_menginap if (malam_menginap is not None and malam_menginap > 0) else 1
                        total_malam_fb_luar += m
                        fb_luar_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                    elif kategori == 'penginapan_fb_dalam':
                        m = malam_menginap if (malam_menginap is not None and malam_menginap > 0) else 1
                        total_malam_fb_dalam += m
                        fb_dalam_bills.append({'nominal': nominal, 'malam': m, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})
                    elif kategori in ['transportasi', 'transportasi_pesawat']:
                        if self.perjalanan.jenis_transportasi != SuratTugas.JenisTransportasi.MOBIL_DINAS:
                            if nominal:
                                asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(keterangan)
                                if asal_id and tujuan_id and kelas:
                                    try:
                                        sbm_tiket = StandarBiayaTiket.objects.get(
                                            kota_asal_id=asal_id,
                                            kota_tujuan_id=tujuan_id,
                                            kelas=kelas
                                        )
                                        plafon_tiket = sbm_tiket.nominal
                                    except StandarBiayaTiket.DoesNotExist:
                                        plafon_tiket = None
                                    flight_tickets_details.append({
                                        'nominal': nominal,
                                        'plafon': plafon_tiket,
                                        'route_str': f"Tiket Pesawat {nama_asal} - {nama_tujuan} - {kelas.capitalize()} (PP)",
                                        'file_url': file_url,
                                        'file_name': file_name
                                    })
                                else:
                                    total_transport_non_pesawat_input += nominal
                                    non_flight_transports.append({'nominal': nominal, 'keterangan': keterangan or jenis.nama, 'file_url': file_url, 'file_name': file_name})

        total_tiket_pesawat_nominal = Decimal('0')
        max_plafon_tiket = Decimal('0')
        if flight_tickets_details:
            total_tiket_pesawat_nominal = sum(ft['nominal'] for ft in flight_tickets_details)
            plafon_list = [ft['plafon'] for ft in flight_tickets_details if ft['plafon'] is not None]
            if plafon_list:
                max_plafon_tiket = max(plafon_list)
                total_tiket_pesawat_riil = min(total_tiket_pesawat_nominal, max_plafon_tiket)
                tiket_pesawat_dana_pribadi = max(Decimal('0'), total_tiket_pesawat_nominal - max_plafon_tiket)
            else:
                total_tiket_pesawat_riil = total_tiket_pesawat_nominal
                tiket_pesawat_dana_pribadi = Decimal('0')

        # Logic 1: Lumpsum Harian & Representasi (taken from SBM automatically)
        durasi = self.perjalanan.durasi_hari
        
        # Calculate mixed fullboard days
        fb_luar_days = min(total_malam_fb_luar, durasi)
        fb_dalam_days = min(total_malam_fb_dalam, durasi - fb_luar_days)
        normal_days = max(0, durasi - (fb_luar_days + fb_dalam_days))
        
        uang_harian_fb_luar = getattr(sbm, 'uang_harian_fullboard_luar', Decimal('0')) if sbm else Decimal('0')
        uang_harian_fb_dalam = getattr(sbm, 'uang_harian_fullboard_dalam', Decimal('0')) if sbm else Decimal('0')
        
        uang_harian_riil = (fb_luar_days * uang_harian_fb_luar) + \
                            (fb_dalam_days * uang_harian_fb_dalam) + \
                            (normal_days * tarif_harian)
                            
        if self.perjalanan.jenis_perjalanan in ['fullboard_luar', 'fullboard_dalam']:
            uang_representasi_riil = Decimal('0')
        else:
            uang_representasi_riil = normal_days * tarif_representasi

        # Logic 2: Capping Hotel/Penginapan (Partial 30%)
        total_malam_perjalanan = max(0, durasi - 1)
        total_malam_claimed = total_malam_hotel + total_malam_lumpsum + total_malam_fb_luar + total_malam_fb_dalam
        
        over_limit = total_malam_claimed > total_malam_perjalanan
        over_limit_msg = ""
        if over_limit:
            over_limit_msg = (
                f"Total klaim penginapan ({total_malam_hotel} malam hotel + {total_malam_lumpsum} malam lumpsum + "
                f"{total_malam_fb_luar} malam FB luar + {total_malam_fb_dalam} malam FB dalam = {total_malam_claimed} malam) "
                f"melebihi batas malam perjalanan ({total_malam_perjalanan} malam)."
            )
            
        plafon_hotel_limit = plafon_hotel * total_malam_hotel
        biaya_hotel_riil = min(total_hotel_input, plafon_hotel_limit)
        
        biaya_hotel_lumpsum = Decimal('0.30') * plafon_hotel * total_malam_lumpsum
        biaya_penginapan_riil = biaya_hotel_riil + biaya_hotel_lumpsum
        
        penginapan_dana_pribadi = max(Decimal('0'), total_hotel_input - plafon_hotel_limit)

        # Logic 3: Capping Transportasi (At-Cost)
        if self.perjalanan.jenis_transportasi == SuratTugas.JenisTransportasi.MOBIL_DINAS:
            biaya_transportasi_riil = Decimal('0')
            transportasi_dana_pribadi = Decimal('0')
            biaya_non_pesawat_riil = Decimal('0')
            non_pesawat_dana_pribadi = Decimal('0')
        else:
            if plafon_transport > 0 and total_transport_non_pesawat_input > plafon_transport:
                biaya_non_pesawat_riil = plafon_transport
                non_pesawat_dana_pribadi = total_transport_non_pesawat_input - plafon_transport
            else:
                biaya_non_pesawat_riil = total_transport_non_pesawat_input
                non_pesawat_dana_pribadi = Decimal('0')

            biaya_transportasi_riil = biaya_non_pesawat_riil + total_tiket_pesawat_riil
            transportasi_dana_pribadi = non_pesawat_dana_pribadi + tiket_pesawat_dana_pribadi

        total_dana_pribadi = penginapan_dana_pribadi + transportasi_dana_pribadi
        total_dibayarkan = uang_harian_riil + uang_representasi_riil + biaya_penginapan_riil + biaya_transportasi_riil

        def fmt_rp(val):
            return f"Rp {val:,.0f}".replace(",", ".")

        harian_formulas = []
        if normal_days > 0:
            harian_formulas.append(f"{normal_days} Hari x {fmt_rp(tarif_harian)} (Tarif Normal)")
        if fb_luar_days > 0:
            harian_formulas.append(f"{fb_luar_days} Hari x {fmt_rp(uang_harian_fb_luar)} (Fullboard Luar)")
        if fb_dalam_days > 0:
            harian_formulas.append(f"{fb_dalam_days} Hari x {fmt_rp(uang_harian_fb_dalam)} (Fullboard Dalam)")
        harian_formula_str = " + ".join(harian_formulas) if harian_formulas else "0 Hari"

        if uang_representasi_riil > 0:
            representasi_formula_str = f"{normal_days} Hari x {fmt_rp(tarif_representasi)}"
        else:
            if self.perjalanan.jenis_perjalanan in ['fullboard_luar', 'fullboard_dalam']:
                representasi_formula_str = "Tidak ada representasi (Jenis: Fullboard)"
            else:
                representasi_formula_str = "0 Hari"

        penginapan_formulas = []
        if total_malam_hotel > 0:
            if total_hotel_input > plafon_hotel_limit:
                over_str = f" (Kelebihan {fmt_rp(total_hotel_input - plafon_hotel_limit)} ditanggung sendiri)"
            else:
                over_str = ""
            penginapan_formulas.append(
                f"Hotel Riil: {total_malam_hotel} Malam (Maks {fmt_rp(plafon_hotel)}/Malam) | Total Input: {fmt_rp(total_hotel_input)} → Dicover: {fmt_rp(biaya_hotel_riil)}{over_str}"
            )
        if total_malam_lumpsum > 0:
            penginapan_formulas.append(
                f"Lumpsum (30% SBM): {total_malam_lumpsum} Malam x {fmt_rp(Decimal('0.30') * plafon_hotel)} = {fmt_rp(biaya_hotel_lumpsum)}"
            )
        if total_malam_fb_luar > 0:
            penginapan_formulas.append(f"Fullboard Luar: {total_malam_fb_luar} Malam (Akomodasi ditanggung penyelenggara)")
        if total_malam_fb_dalam > 0:
            penginapan_formulas.append(f"Fullboard Dalam: {total_malam_fb_dalam} Malam (Akomodasi ditanggung penyelenggara)")
        penginapan_formula_str = " dan ".join(penginapan_formulas) if penginapan_formulas else "Tidak ada klaim penginapan"

        if self.perjalanan.jenis_transportasi == SuratTugas.JenisTransportasi.MOBIL_DINAS:
            transport_formula_str = "Mobil Dinas (Biaya 0)"
        else:
            transport_formulas = []
            if total_transport_non_pesawat_input > 0:
                if non_pesawat_dana_pribadi > 0:
                    over_str = f" (Kelebihan {fmt_rp(non_pesawat_dana_pribadi)} melebihi Plafon SBM {fmt_rp(plafon_transport)} ditanggung sendiri)"
                else:
                    over_str = ""
                transport_formulas.append(
                    f"Transportasi Darat/Riil: Input {fmt_rp(total_transport_non_pesawat_input)} → Dicover: {fmt_rp(biaya_non_pesawat_riil)}{over_str}"
                )
            if flight_tickets_details:
                ticket_details = []
                for ft in flight_tickets_details:
                    ticket_details.append(f"{ft['route_str']}: {fmt_rp(ft['nominal'])}")
                if tiket_pesawat_dana_pribadi > 0:
                    over_str = f" (Total melebihi Plafon 1x PP SBM {fmt_rp(max_plafon_tiket)}, kelebihan {fmt_rp(tiket_pesawat_dana_pribadi)} ditanggung sendiri)"
                else:
                    over_str = ""
                transport_formulas.append(
                    f"Tiket Pesawat ({', '.join(ticket_details)}) | Total Input: {fmt_rp(total_tiket_pesawat_nominal)} → Dicover: {fmt_rp(total_tiket_pesawat_riil)}{over_str}"
                )
            transport_formula_str = " dan ".join(transport_formulas) if transport_formulas else "Tidak ada klaim transportasi"

        # Build spreadsheet itemizations
        uang_harian_items = []
        uang_representasi_items = []
        biaya_penginapan_items = []
        biaya_perjalanan_items = []

        # 1. Uang Harian Items
        if normal_days > 0:
            uang_harian_items.append({
                'perihal': 'Uang Harian Riil',
                'no': 0,
                'keterangan': 'Uang Harian Normal',
                'harga': tarif_harian,
                'kuantitas': f"{normal_days} (hari)",
                'total': normal_days * tarif_harian,
                'file_url': None,
                'file_name': None
            })
        if fb_luar_days > 0:
            uang_harian_items.append({
                'perihal': 'Uang Harian Riil',
                'no': 0,
                'keterangan': 'Uang Harian Fullboard',
                'harga': uang_harian_fb_luar,
                'kuantitas': f"{fb_luar_days} (hari)",
                'total': fb_luar_days * uang_harian_fb_luar,
                'file_url': None,
                'file_name': None
            })
        if fb_dalam_days > 0:
            uang_harian_items.append({
                'perihal': 'Uang Harian Riil',
                'no': 0,
                'keterangan': 'Uang Harian Fullboard',
                'harga': uang_harian_fb_dalam,
                'kuantitas': f"{fb_dalam_days} (hari)",
                'total': fb_dalam_days * uang_harian_fb_dalam,
                'file_url': None,
                'file_name': None
            })

        # 2. Uang Representasi Items
        if normal_days > 0:
            gol_str = self.perjalanan.pegawai.golongan if (self.perjalanan and self.perjalanan.pegawai) else ""
            keterangan_repr = f"Uang Representasi (Gol. {gol_str.split('/')[0]})" if gol_str else "Uang Representasi"
            uang_representasi_items.append({
                'perihal': 'Uang Representasi Riil',
                'no': 0,
                'keterangan': keterangan_repr,
                'harga': tarif_representasi,
                'kuantitas': f"{normal_days} (hari)",
                'total': normal_days * tarif_representasi,
                'file_url': None,
                'file_name': None
            })

        # 3. Biaya Penginapan Items
        # Sequential hotel capping
        rem_hotel_plafon = plafon_hotel * total_malam_hotel
        for hb in hotel_bills:
            covered = min(hb['nominal'], rem_hotel_plafon)
            rem_hotel_plafon = max(Decimal('0'), rem_hotel_plafon - covered)
            unit_price = covered / hb['malam'] if hb['malam'] > 0 else covered
            biaya_penginapan_items.append({
                'perihal': 'Biaya Penginapan Riil',
                'no': 0,
                'keterangan': hb['keterangan'] or 'Hotel',
                'harga': unit_price,
                'kuantitas': f"{hb['malam']} (Malam)",
                'total': covered,
                'file_url': hb['file_url'],
                'file_name': hb['file_name']
            })

        for lb in lumpsum_bills:
            covered = Decimal('0.30') * plafon_hotel * lb['malam']
            biaya_penginapan_items.append({
                'perihal': 'Biaya Penginapan Riil',
                'no': 0,
                'keterangan': lb['keterangan'] or 'Biaya Penginapan Lumpsum',
                'harga': Decimal('0.30') * plafon_hotel,
                'kuantitas': f"{lb['malam']} (Malam)",
                'total': covered,
                'file_url': lb['file_url'],
                'file_name': lb['file_name']
            })

        for fb_luar in fb_luar_bills:
            biaya_penginapan_items.append({
                'perihal': 'Biaya Penginapan Riil',
                'no': 0,
                'keterangan': fb_luar['keterangan'] or 'Biaya Penginapan Fullboard',
                'harga': Decimal('0'),
                'kuantitas': f"{fb_luar['malam']} (Malam)",
                'total': Decimal('0'),
                'file_url': fb_luar['file_url'],
                'file_name': fb_luar['file_name']
            })

        for fb_dalam in fb_dalam_bills:
            biaya_penginapan_items.append({
                'perihal': 'Biaya Penginapan Riil',
                'no': 0,
                'keterangan': fb_dalam['keterangan'] or 'Biaya Penginapan Fullboard',
                'harga': Decimal('0'),
                'kuantitas': f"{fb_dalam['malam']} (Malam)",
                'total': Decimal('0'),
                'file_url': fb_dalam['file_url'],
                'file_name': fb_dalam['file_name']
            })

        # 4. Biaya Perjalanan Items
        # Sequential plane ticket capping
        rem_flight_plafon = max_plafon_tiket if (flight_tickets_details and max_plafon_tiket > 0) else None
        for ft in flight_tickets_details:
            if rem_flight_plafon is not None:
                covered = min(ft['nominal'], rem_flight_plafon)
                rem_flight_plafon = max(Decimal('0'), rem_flight_plafon - covered)
            else:
                covered = ft['nominal']
            biaya_perjalanan_items.append({
                'perihal': 'Biaya Perjalanan Riil',
                'no': 0,
                'keterangan': ft['route_str'],
                'harga': ft['nominal'],
                'kuantitas': '1',
                'total': covered,
                'file_url': ft['file_url'],
                'file_name': ft['file_name']
            })

        # Sequential non-plane transport capping
        rem_trans_plafon = plafon_transport if plafon_transport > 0 else None
        for nt in non_flight_transports:
            if rem_trans_plafon is not None:
                covered = min(nt['nominal'], rem_trans_plafon)
                rem_trans_plafon = max(Decimal('0'), rem_trans_plafon - covered)
            else:
                covered = nt['nominal']
            biaya_perjalanan_items.append({
                'perihal': 'Biaya Perjalanan Riil',
                'no': 0,
                'keterangan': nt['keterangan'],
                'harga': nt['nominal'],
                'kuantitas': '1',
                'total': covered,
                'file_url': nt['file_url'],
                'file_name': nt['file_name']
            })

        # Sequence-number all items sequentially
        idx = 1
        for item in uang_harian_items:
            item['no'] = idx
            idx += 1
        for item in uang_representasi_items:
            item['no'] = idx
            idx += 1
        for item in biaya_penginapan_items:
            item['no'] = idx
            idx += 1
        for item in biaya_perjalanan_items:
            item['no'] = idx
            idx += 1

        subtotal_harian = sum(item['total'] for item in uang_harian_items)
        subtotal_representasi = sum(item['total'] for item in uang_representasi_items)
        subtotal_penginapan = sum(item['total'] for item in biaya_penginapan_items)
        subtotal_perjalanan = sum(item['total'] for item in biaya_perjalanan_items)

        return {
            'uang_harian_riil': uang_harian_riil,
            'uang_representasi_riil': uang_representasi_riil,
            'biaya_penginapan_riil': biaya_penginapan_riil,
            'biaya_transportasi_riil': biaya_transportasi_riil,
            'penginapan_dana_pribadi': penginapan_dana_pribadi,
            'transportasi_dana_pribadi': transportasi_dana_pribadi,
            'total_dana_pribadi': total_dana_pribadi,
            'total_tidak_dibayarkan': total_dana_pribadi,
            'total_dibayarkan': total_dibayarkan,
            'durasi_hari': durasi,
            'over_limit': over_limit,
            'over_limit_msg': over_limit_msg,
            
            # SBM values for UI info
            'sbm_uang_harian': tarif_harian,
            'sbm_uang_representasi': tarif_representasi,
            'sbm_plafon_hotel': plafon_hotel,
            'sbm_plafon_transport': plafon_transport,
            
            # Detailed breakdown strings/details
            'harian_formula': harian_formula_str,
            'representasi_formula': representasi_formula_str,
            'penginapan_formula': penginapan_formula_str,
            'transport_formula': transport_formula_str,

            # Categorized items for spreadsheet views
            'breakdown_categories': {
                'uang_harian': {
                    'title': 'Uang Harian Riil',
                    'items': uang_harian_items,
                    'subtotal': subtotal_harian,
                },
                'uang_representasi': {
                    'title': 'Uang Representasi Riil',
                    'items': uang_representasi_items,
                    'subtotal': subtotal_representasi,
                },
                'biaya_penginapan': {
                    'title': 'Biaya Penginapan Riil',
                    'items': biaya_penginapan_items,
                    'subtotal': subtotal_penginapan,
                },
                'biaya_perjalanan': {
                    'title': 'Biaya Perjalanan Riil',
                    'items': biaya_perjalanan_items,
                    'subtotal': subtotal_perjalanan,
                }
            }
        }

    def save(self, *args, **kwargs):
        breakdown = self.calculate_breakdown()
        
        self.uang_harian_riil = breakdown['uang_harian_riil']
        self.uang_representasi_riil = breakdown['uang_representasi_riil']
        self.biaya_penginapan_riil = breakdown['biaya_penginapan_riil']
        self.biaya_transportasi_riil = breakdown['biaya_transportasi_riil']
        self.penginapan_dana_pribadi = breakdown['penginapan_dana_pribadi']
        self.transportasi_dana_pribadi = breakdown['transportasi_dana_pribadi']
        self.total_dana_pribadi = breakdown['total_dana_pribadi']
        self.total_dibayarkan = breakdown['total_dibayarkan']
        
        if breakdown['over_limit']:
            raise ValidationError(breakdown['over_limit_msg'])
            
        super().save(*args, **kwargs)

    @property
    def total_tidak_dibayarkan(self):
        return self.total_dana_pribadi

class BerkasPerjalanan(models.Model):
    perjalanan = models.ForeignKey(PerjalananDinas, on_delete=models.CASCADE, related_name='berkas')
    jenis_berkas = models.ForeignKey(JenisBerkas, on_delete=models.PROTECT, verbose_name="Jenis Berkas", null=True, blank=True)
    file = models.FileField(upload_to='perjalanan_dinas/%Y/%m/', blank=True, null=True)
    malam_menginap = models.IntegerField(null=True, blank=True, verbose_name="Malam Menginap")
    nominal = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="Nominal Biaya")
    keterangan = models.CharField(max_length=255, blank=True, null=True, verbose_name="Keterangan")
    
    is_verified = models.BooleanField(default=False, verbose_name="Verifikasi?")
    
    def clean(self):
        super().clean()
        # 1. Pastikan file terisi jika jenis berkas wajib diunggah
        if self.jenis_berkas and self.jenis_berkas.wajib:
            if not self.file:
                raise ValidationError({
                    'file': "Wajib mengunggah file untuk jenis berkas ini."
                })

        # 2. Pastikan nominal terisi jika jenis berkas mewajibkan
        if self.jenis_berkas and self.jenis_berkas.nominal_biaya:
            if self.nominal is None or self.nominal <= 0:
                raise ValidationError({
                    'nominal': f"Nominal biaya wajib diisi untuk berkas jenis {self.jenis_berkas.nama}."
                })

        # 3. Tiket pesawat hanya boleh diinput maksimal 2 kali
        is_flight_ticket = False
        if self.jenis_berkas:
            if self.jenis_berkas.kategori_biaya == 'transportasi_pesawat':
                is_flight_ticket = True
            elif self.jenis_berkas.kategori_biaya == 'transportasi' and self.keterangan:
                asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(self.keterangan)
                if asal_id and tujuan_id and kelas:
                    is_flight_ticket = True

        if is_flight_ticket:
            other_tickets = BerkasPerjalanan.objects.filter(
                perjalanan=self.perjalanan
            )
            if self.pk:
                other_tickets = other_tickets.exclude(pk=self.pk)
            
            flight_ticket_count = 0
            for ot in other_tickets:
                if ot.jenis_berkas:
                    if ot.jenis_berkas.kategori_biaya == 'transportasi_pesawat':
                        flight_ticket_count += 1
                    elif ot.jenis_berkas.kategori_biaya == 'transportasi' and ot.keterangan:
                        o_asal_id, o_tujuan_id, o_kelas, o_nama_asal, o_nama_tujuan, o_user_desc = parse_tiket_keterangan(ot.keterangan)
                        if o_asal_id and o_tujuan_id and o_kelas:
                            flight_ticket_count += 1
            
            if flight_ticket_count >= 2:
                raise ValidationError(
                    "Tiket pesawat hanya dapat diinput maksimal 2 kali (untuk pergi dan pulang) sesuai aturan SBM."
                )

    def save(self, *args, **kwargs):
        if self.jenis_berkas and self.jenis_berkas.kategori_biaya in ['penginapan_fb_luar', 'penginapan_fb_dalam']:
            self.nominal = 0
        self.full_clean()
        super().save(*args, **kwargs)
        if hasattr(self.perjalanan, 'biaya'):
            self.perjalanan.biaya.save()

    def delete(self, *args, **kwargs):
        perjalanan = self.perjalanan
        super().delete(*args, **kwargs)
        if hasattr(perjalanan, 'biaya'):
            perjalanan.biaya.save()

    def __str__(self):
        return f"{self.jenis_berkas.nama if self.jenis_berkas else 'Berkas'} - {self.perjalanan}"


class BerkasPerjalananPenginapan(BerkasPerjalanan):
    class Meta:
        proxy = True
        verbose_name = "Berkas Pendukung untuk Penginapan"
        verbose_name_plural = "Berkas Pendukung untuk Penginapan"


class BerkasPerjalananTransportasi(BerkasPerjalanan):
    class Meta:
        proxy = True
        verbose_name = "Berkas Pendukung untuk Transportasi"
        verbose_name_plural = "Berkas Pendukung untuk Transportasi"


class BerkasPerjalananNonNominal(BerkasPerjalanan):
    class Meta:
        proxy = True
        verbose_name = "Berkas Pendukung Tanpa Nominal Biaya"
        verbose_name_plural = "Berkas Pendukung Tanpa Nominal Biaya"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=PerjalananDinas)
def create_biaya_perjalanan(sender, instance, created, **kwargs):
    if created:
        BiayaPerjalanan.objects.get_or_create(perjalanan=instance)
