from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from master_data.models import Pegawai, Provinsi, StandarBiaya, StandarBiayaHarian, Anggaran, JenisBerkas, StandarBiayaTiket
from decimal import Decimal
from datetime import timedelta

import uuid
import os
import re

from django.db.models import Q

def get_eligible_sbm_filter(pegawai):
    q_conditions = Q()
    
    # 1. Direct Golongan match and its Eselon equivalent
    if pegawai.golongan:
        q_conditions |= Q(golongan=pegawai.golongan)
        if pegawai.golongan == 'IV':
            q_conditions |= Q(posisi_jabatan='ES_III')
        elif pegawai.golongan == 'III':
            q_conditions |= Q(posisi_jabatan='ES_IV')
            
    # 2. Direct Eselon match and its Golongan equivalent
    if pegawai.posisi_jabatan and pegawai.posisi_jabatan != 'NON_ESELON':
        q_conditions |= Q(posisi_jabatan=pegawai.posisi_jabatan)
        if pegawai.posisi_jabatan == 'ES_III':
            q_conditions |= Q(golongan='IV')
        elif pegawai.posisi_jabatan == 'ES_IV':
            q_conditions |= Q(golongan='III')
            
    # 3. Fallback: match generic SBM records where both are null or empty
    q_conditions |= Q(golongan__isnull=True, posisi_jabatan__isnull=True)
    q_conditions |= Q(golongan='', posisi_jabatan__isnull=True)
    q_conditions |= Q(golongan__isnull=True, posisi_jabatan='')
    q_conditions |= Q(golongan='', posisi_jabatan='')
    
    return q_conditions

def get_eligible_tiket_filter(pegawai):
    """Filter for StandarBiayaTiket — only uses posisi_jabatan (no golongan) and filters by eligible ticket class."""
    # Determine eligible class based on posisi_jabatan:
    # Eselon I and II get bisnis, all others (ES_III, ES_IV, NON_ESELON) get ekonomi
    if pegawai.posisi_jabatan in ['ES_I', 'ES_II']:
        kelas_filter = Q(kelas='bisnis')
    else:
        kelas_filter = Q(kelas='ekonomi')

    posisi_conditions = Q()
    if pegawai.posisi_jabatan and pegawai.posisi_jabatan != 'NON_ESELON':
        posisi_conditions |= Q(posisi_jabatan=pegawai.posisi_jabatan)

    # Fallback: match generic records where posisi_jabatan is null or empty
    posisi_conditions |= Q(posisi_jabatan__isnull=True)
    posisi_conditions |= Q(posisi_jabatan='')

    return kelas_filter & posisi_conditions

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

def parse_penginapan_keterangan(keterangan_val):
    if not keterangan_val:
        return None, None, None, None, None, ""
    match = re.match(r"^\[SBM-PENGINAPAN:([^:]+):([^:]+):(\d+):([^:]+):([^\]]+)\](?:\s*\|\s*(.*))?$", keterangan_val)
    if match:
        return (
            match.group(1),
            match.group(2),
            int(match.group(3)),
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

    def sync_harian_details(self):
        durasi = self.durasi_hari
        if durasi <= 0:
            self.harian_details.all().delete()
            return

        # Fetch current details
        existing = {h.hari_ke: h for h in self.harian_details.all()}
        
        # We want to create/keep records up to durasi
        for i in range(1, durasi + 1):
            tgl = self.tanggal_berangkat + timedelta(days=i - 1) if self.tanggal_berangkat else None
            if i in existing:
                h = existing[i]
                # Update date if changed
                if h.tanggal != tgl:
                    h.tanggal = tgl
                    h.save()
            else:
                HarianPerjalanan.objects.create(
                    perjalanan=self,
                    hari_ke=i,
                    tanggal=tgl,
                    provinsi=self.tujuan_provinsi,
                    jenis_harian='luar_kota'
                )
        
        # Delete extra days if durasi was reduced
        self.harian_details.filter(hari_ke__gt=durasi).delete()

    @property
    def history_timeline(self):
        history = list(self.status_history.all().order_by('created_at'))
        if not history:
            class VirtualHistory:
                def __init__(self, status, get_status_display, created_at):
                    self.status = status
                    self._status_display = get_status_display
                    self.created_at = created_at
                def get_status_display(self):
                    return self._status_display

            history = [
                VirtualHistory(self.Status.DRAFT, 'Draft', self.created_at)
            ]
            if self.status != self.Status.DRAFT:
                history.append(
                    VirtualHistory(self.status, self.get_status_display(), self.updated_at)
                )
        return history

    def save(self, *args, **kwargs):
        status_changed = False
        if not self.pk:
            status_changed = True
        else:
            try:
                original = PerjalananDinas.objects.get(pk=self.pk)
                if original.status != self.status:
                    status_changed = True
            except PerjalananDinas.DoesNotExist:
                status_changed = True

        # 1. Otomatisasi Nomor SPD jika belum ada
        if not self.nomor_spd:
            from django.db import transaction
            with transaction.atomic():
                config, created = PengaturanNomorSPD.objects.get_or_create(id=1)
                while True:
                    config.prefix_terakhir += 1
                    candidate = f"{config.prefix_terakhir}{config.suffix_format}"
                    if not PerjalananDinas.objects.filter(nomor_spd=candidate).exists():
                        self.nomor_spd = candidate
                        break
                config.save()
            
        super().save(*args, **kwargs)
        self.sync_harian_details()
        if hasattr(self, 'biaya'):
            self.biaya.save()

        # Log status history if changed
        if status_changed:
            StatusHistoryPerjalanan.objects.create(perjalanan=self, status=self.status)

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

    def __str__(self):
        return f"{self.nomor_spd or 'No SPD'} - {self.pegawai.nama}"

class StatusHistoryPerjalanan(models.Model):
    perjalanan = models.ForeignKey(PerjalananDinas, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=PerjalananDinas.Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Riwayat Status Perjalanan"
        verbose_name_plural = "Riwayat Status Perjalanan"

    def __str__(self):
        return f"{self.perjalanan.nomor_spd or 'SPD'} - {self.get_status_display()} ({self.created_at})"


class HarianPerjalanan(models.Model):
    class JenisHarian(models.TextChoices):
        LUAR_KOTA = 'luar_kota', 'Luar Kota'
        DALAM_KOTA = 'dalam_kota', 'Dalam Kota (> 8 Jam)'
        DIKLAT = 'diklat', 'Diklat'
        HALFDAY = 'halfday', 'Rapat/Pertemuan Halfday'
        FULLDAY = 'fullday', 'Rapat/Pertemuan Fullday'
        FULLBOARD = 'fullboard', 'Rapat/Pertemuan Fullboard'
        TIDAK_DIBAYAI = 'tidak_dibayai', 'Tidak Dibiayai (Bentrok)'

    perjalanan = models.ForeignKey(PerjalananDinas, on_delete=models.CASCADE, related_name='harian_details')
    hari_ke = models.PositiveIntegerField(verbose_name="Hari Ke")
    tanggal = models.DateField(verbose_name="Tanggal")
    provinsi = models.ForeignKey(Provinsi, on_delete=models.PROTECT, verbose_name="Provinsi")
    jenis_harian = models.CharField(max_length=20, choices=JenisHarian.choices, default=JenisHarian.LUAR_KOTA, verbose_name="Jenis Perjalanan Dinas")

    class Meta:
        ordering = ['hari_ke']
        unique_together = ('perjalanan', 'hari_ke')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self.perjalanan, 'biaya'):
            self.perjalanan.biaya.save()

    def delete(self, *args, **kwargs):
        perjalanan = self.perjalanan
        super().delete(*args, **kwargs)
        if hasattr(perjalanan, 'biaya'):
            perjalanan.biaya.save()

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

    def calculate_breakdown(self, mock_berkas=None, mock_harian=None):
        # Helper to find the most favorable SBM based on Eselon and Golongan
        def find_favorable_sbm(prov_id):
            if not prov_id:
                return None
            pegawai = self.perjalanan.pegawai
            q_filter = get_eligible_sbm_filter(pegawai)
            sbms = StandarBiaya.objects.filter(
                q_filter,
                provinsi_id=prov_id,
                tahun=self.perjalanan.tahun_sbm
            ).order_by('-plafon_penginapan')
            return sbms.first()

        # Helper to find SBM Harian (universal, no golongan/eselon)
        sbm_harian_cache = {}
        def find_sbm_harian(prov_id):
            if not prov_id:
                return None
            if prov_id not in sbm_harian_cache:
                sbm_harian_cache[prov_id] = StandarBiayaHarian.objects.filter(
                    provinsi_id=prov_id,
                    tahun=self.perjalanan.tahun_sbm
                ).first()
            return sbm_harian_cache[prov_id]

        # Fetch SBM
        tujuan_prov_id = self.perjalanan.tujuan_provinsi.id if self.perjalanan.tujuan_provinsi else None
        sbm = find_favorable_sbm(tujuan_prov_id)
        sbm_harian = find_sbm_harian(tujuan_prov_id)
        if sbm:
            plafon_hotel = sbm.plafon_penginapan
        else:
            plafon_hotel = Decimal('0')
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
                    if nominal:
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
                    if nominal:
                        asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(keterangan)
                        if asal_id and tujuan_id and kelas:
                            if self.perjalanan.jenis_transportasi != SuratTugas.JenisTransportasi.MOBIL_DINAS:
                                sbm_tikets = StandarBiayaTiket.objects.filter(
                                    get_eligible_tiket_filter(self.perjalanan.pegawai),
                                    kota_asal_id=asal_id,
                                    kota_tujuan_id=tujuan_id,
                                    kelas=kelas,
                                    tahun=self.perjalanan.tahun_sbm
                                ).order_by('-nominal')
                                sbm_tiket = sbm_tikets.first()
                                plafon_tiket = sbm_tiket.nominal if sbm_tiket else None
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
                        if nominal:
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
                        if nominal:
                            asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(keterangan)
                            if asal_id and tujuan_id and kelas:
                                if self.perjalanan.jenis_transportasi != SuratTugas.JenisTransportasi.MOBIL_DINAS:
                                    sbm_tikets = StandarBiayaTiket.objects.filter(
                                        get_eligible_tiket_filter(self.perjalanan.pegawai),
                                        kota_asal_id=asal_id,
                                        kota_tujuan_id=tujuan_id,
                                        kelas=kelas,
                                        tahun=self.perjalanan.tahun_sbm
                                    ).order_by('-nominal')
                                    sbm_tiket = sbm_tikets.first()
                                    plafon_tiket = sbm_tiket.nominal if sbm_tiket else None
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

        # Process overlap cancellations for hotel and transport bills
        from datetime import datetime
        unpaid_dates = set()
        if self.perjalanan_id:
            unpaid_dates = set(
                self.perjalanan.harian_details.filter(jenis_harian='tidak_dibayai').values_list('tanggal', flat=True)
            )
        if mock_harian:
            for item in mock_harian:
                if item.get('jenis_harian') == 'tidak_dibayai':
                    hk = int(item.get('hari_ke') or 0)
                    if hk and self.perjalanan.tanggal_berangkat:
                        unpaid_dates.add(self.perjalanan.tanggal_berangkat + timedelta(days=hk - 1))

        # Helper to parse dates from string
        def get_date_from_string(s):
            if not s:
                return None
            m1 = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
            if m1:
                try:
                    return datetime.strptime(m1.group(0), '%Y-%m-%d').date()
                except ValueError:
                    pass
            m2 = re.search(r"\b(\d{2})-(\d{2})-(\d{4})\b", s)
            if m2:
                try:
                    return datetime.strptime(m2.group(0), '%d-%m-%Y').date()
                except ValueError:
                    pass
            m3 = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", s)
            if m3:
                try:
                    return datetime.strptime(m3.group(0), '%d/%m/%Y').date()
                except ValueError:
                    pass
            return None

        # Adjust hotel/penginapan bills
        def adjust_hotel_bill(bill):
            if not bill['keterangan'] or not bill['keterangan'].startswith('[SBM-PENGINAPAN:'):
                return
            c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(bill['keterangan'])
            if not c_in or not c_out:
                return
            try:
                start_dt = datetime.strptime(c_in, '%Y-%m-%d').date()
                end_dt = datetime.strptime(c_out, '%Y-%m-%d').date()
            except Exception:
                return
            
            total_nights = (end_dt - start_dt).days
            if total_nights <= 0:
                return
            
            unpaid_count = 0
            curr = start_dt
            while curr < end_dt:
                if curr in unpaid_dates:
                    unpaid_count += 1
                curr += timedelta(days=1)
                
            if unpaid_count > 0:
                financed_nights = max(0, total_nights - unpaid_count)
                orig_nominal = bill['nominal']
                bill['nominal'] = Decimal(str(orig_nominal * financed_nights / total_nights)).quantize(Decimal('1'))
                bill['malam'] = financed_nights
                # Add cancellation note to keterangan
                bill['keterangan'] = bill['keterangan'] + f" [DIBATALKAN {unpaid_count} MALAM KARENA BENTROK]"

        for b in hotel_bills: adjust_hotel_bill(b)
        for b in lumpsum_bills: adjust_hotel_bill(b)
        for b in fb_luar_bills: adjust_hotel_bill(b)
        for b in fb_dalam_bills: adjust_hotel_bill(b)

        # Recalculate hotel/penginapan sums from adjusted lists
        total_hotel_input = sum(b['nominal'] for b in hotel_bills)
        total_malam_hotel = sum(b['malam'] for b in hotel_bills)
        total_malam_lumpsum = sum(b['malam'] for b in lumpsum_bills)
        total_malam_fb_luar = sum(b['malam'] for b in fb_luar_bills)
        total_malam_fb_dalam = sum(b['malam'] for b in fb_dalam_bills)

        # Adjust flight tickets
        for idx, ft in enumerate(flight_tickets_details):
            tgl_ticket = get_date_from_string(ft.get('route_str') or '') or get_date_from_string(ft.get('file_name') or '')
            if not tgl_ticket:
                # Fallback based on sequence
                if len(flight_tickets_details) == 1:
                    tgl_ticket = self.perjalanan.tanggal_berangkat
                elif len(flight_tickets_details) == 2:
                    if idx == 0:
                        tgl_ticket = self.perjalanan.tanggal_berangkat
                    else:
                        tgl_ticket = self.perjalanan.tanggal_kembali
                        
            if tgl_ticket and tgl_ticket in unpaid_dates:
                ft['nominal'] = Decimal('0')
                ft['route_str'] = ft.get('route_str', '') + " [DIBATALKAN KARENA BENTROK]"

        # Adjust non-flight transports
        for nt in non_flight_transports:
            tgl_ticket = get_date_from_string(nt.get('keterangan') or '') or get_date_from_string(nt.get('file_name') or '')
            if not tgl_ticket:
                k_lower = (nt.get('keterangan') or '').lower()
                if 'berangkat' in k_lower or 'pergi' in k_lower:
                    tgl_ticket = self.perjalanan.tanggal_berangkat
                elif 'kembali' in k_lower or 'pulang' in k_lower:
                    tgl_ticket = self.perjalanan.tanggal_kembali
                    
            if tgl_ticket and tgl_ticket in unpaid_dates:
                nt['nominal'] = Decimal('0')
                nt['keterangan'] = nt.get('keterangan', '') + " [DIBATALKAN KARENA BENTROK]"

        # Recalculate non-plane transport sum
        total_transport_non_pesawat_input = sum(b['nominal'] for b in non_flight_transports)

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

        # Logic 1: Lumpsum Harian & Representasi (day-by-day lookup with overrides)
        durasi = self.perjalanan.durasi_hari

        mock_harian_map = {}
        if mock_harian:
            for item in mock_harian:
                hk = int(item.get('hari_ke') or 0)
                if hk:
                    mock_harian_map[hk] = item

        db_harian_map = {}
        if not mock_harian and self.perjalanan_id:
            db_harian_map = {h.hari_ke: h for h in self.perjalanan.harian_details.all()}

        sbm_cache = {}
        def get_sbm_for_province(prov_id):
            if prov_id not in sbm_cache:
                sbm_cache[prov_id] = find_favorable_sbm(prov_id)
            return sbm_cache[prov_id]

        provinsi_cache = {}
        def get_provinsi(prov_id):
            if prov_id not in provinsi_cache:
                try:
                    provinsi_cache[prov_id] = Provinsi.objects.get(id=prov_id)
                except Provinsi.DoesNotExist:
                    provinsi_cache[prov_id] = self.perjalanan.tujuan_provinsi
            return provinsi_cache[prov_id]

        def get_representasi_info(sbm_obj, jenis_harian):
            if not sbm_obj:
                return Decimal('0'), ''
            if jenis_harian == 'luar_kota':
                return getattr(sbm_obj, 'uang_representasi_luar_kota', Decimal('0')), 'Luar Kota'
            if jenis_harian == 'dalam_kota':
                return getattr(sbm_obj, 'uang_representasi_dalam_kota', Decimal('0')), 'Dalam Kota (> 8 Jam)'
            return Decimal('0'), ''

        harian_breakdown = []
        uang_harian_riil = Decimal('0')
        uang_representasi_riil = Decimal('0')

        for i in range(1, durasi + 1):
            tgl = self.perjalanan.tanggal_berangkat + timedelta(days=i - 1) if self.perjalanan.tanggal_berangkat else None
            if i in mock_harian_map:
                prov_id = mock_harian_map[i].get('provinsi_id')
                jenis_harian = mock_harian_map[i].get('jenis_harian', 'luar_kota') or 'luar_kota'
            elif i in db_harian_map:
                prov_id = db_harian_map[i].provinsi_id
                jenis_harian = db_harian_map[i].jenis_harian
            else:
                prov_id = self.perjalanan.tujuan_provinsi.id if self.perjalanan.tujuan_provinsi else None
                jenis_harian = 'luar_kota'

            if not prov_id:
                prov_id = self.perjalanan.tujuan_provinsi.id if self.perjalanan.tujuan_provinsi else None

            prov_obj = get_provinsi(prov_id)
            sbm_day = get_sbm_for_province(prov_id)
            sbm_harian_day = find_sbm_harian(prov_id)

            if sbm_harian_day:
                if jenis_harian == 'tidak_dibayai':
                    rate = Decimal('0')
                elif jenis_harian == 'luar_kota':
                    rate = sbm_harian_day.uang_harian
                elif jenis_harian == 'dalam_kota':
                    rate = sbm_harian_day.uang_harian_dalam_kota
                elif jenis_harian == 'diklat':
                    rate = sbm_harian_day.uang_harian_diklat
                elif jenis_harian in ['halfday', 'fullday', 'fullboard']:
                    rate = Decimal('0')
                else:
                    rate = sbm_harian_day.uang_harian
            else:
                rate = Decimal('0')

            if sbm_day:
                rep_expected_rate, rep_label = get_representasi_info(sbm_day, jenis_harian)
                if jenis_harian == 'tidak_dibayai':
                    rep_rate = Decimal('0')
                elif self.perjalanan.jenis_perjalanan in ['fullboard_luar', 'fullboard_dalam']:
                    rep_rate = Decimal('0')
                elif jenis_harian in ['luar_kota', 'dalam_kota']:
                    rep_rate = rep_expected_rate
                else:
                    rep_rate = Decimal('0')
            else:
                rep_rate = Decimal('0')
                rep_expected_rate = Decimal('0')
                rep_label = ''

            uang_harian_riil += rate
            uang_representasi_riil += rep_rate

            harian_breakdown.append({
                'hari_ke': i,
                'tanggal': tgl,
                'provinsi_id': prov_id,
                'provinsi_obj': prov_obj,
                'provinsi_nama': prov_obj.nama if prov_obj else "",
                'jenis_harian': jenis_harian,
                'rate': rate,
                'representasi': rep_rate,
                'representasi_expected': rep_expected_rate,
                'representasi_label': rep_label,
            })

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
            
        biaya_hotel_riil = Decimal('0')
        biaya_hotel_lumpsum = Decimal('0')
        penginapan_dana_pribadi = Decimal('0')

        doc_sbm_cache = {}
        def get_sbm_for_doc(prov_id):
            if not prov_id:
                prov_id = self.perjalanan.tujuan_provinsi.id if self.perjalanan.tujuan_provinsi else None
            if not prov_id:
                return None
            if prov_id not in doc_sbm_cache:
                doc_sbm_cache[prov_id] = find_favorable_sbm(prov_id)
            return doc_sbm_cache[prov_id]

        for hb in hotel_bills:
            doc_prov_id = None
            if hb['keterangan'] and hb['keterangan'].startswith('[SBM-PENGINAPAN:'):
                c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(hb['keterangan'])
                if p_id:
                    doc_prov_id = p_id
            doc_sbm = get_sbm_for_doc(doc_prov_id)
            doc_plafon_hotel = doc_sbm.plafon_penginapan if doc_sbm else Decimal('0')
            doc_ceil = doc_plafon_hotel * hb['malam']
            biaya_hotel_riil += min(hb['nominal'], doc_ceil)
            penginapan_dana_pribadi += max(Decimal('0'), hb['nominal'] - doc_ceil)

        for lb in lumpsum_bills:
            doc_prov_id = None
            if lb['keterangan'] and lb['keterangan'].startswith('[SBM-PENGINAPAN:'):
                c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(lb['keterangan'])
                if p_id:
                    doc_prov_id = p_id
            doc_sbm = get_sbm_for_doc(doc_prov_id)
            doc_plafon_hotel = doc_sbm.plafon_penginapan if doc_sbm else Decimal('0')
            biaya_hotel_lumpsum += Decimal('0.30') * doc_plafon_hotel * lb['malam']

        biaya_penginapan_riil = biaya_hotel_riil + biaya_hotel_lumpsum

        # Logic 3: Capping Transportasi (At-Cost)
        if plafon_transport > 0 and total_transport_non_pesawat_input > plafon_transport:
            biaya_non_pesawat_riil = plafon_transport
            non_pesawat_dana_pribadi = total_transport_non_pesawat_input - plafon_transport
        else:
            biaya_non_pesawat_riil = total_transport_non_pesawat_input
            non_pesawat_dana_pribadi = Decimal('0')

        if self.perjalanan.jenis_transportasi == SuratTugas.JenisTransportasi.MOBIL_DINAS:
            biaya_transportasi_riil = biaya_non_pesawat_riil
            transportasi_dana_pribadi = non_pesawat_dana_pribadi
        else:
            biaya_transportasi_riil = biaya_non_pesawat_riil + total_tiket_pesawat_riil
            transportasi_dana_pribadi = non_pesawat_dana_pribadi + tiket_pesawat_dana_pribadi

        total_dana_pribadi = penginapan_dana_pribadi + transportasi_dana_pribadi
        total_dibayarkan = uang_harian_riil + uang_representasi_riil + biaya_penginapan_riil + biaya_transportasi_riil

        def fmt_rp(val):
            return f"Rp {val:,.0f}".replace(",", ".")

        JENIS_HARIAN_LABELS = {
            'luar_kota': 'Luar Kota',
            'dalam_kota': 'Dalam Kota (> 8 Jam)',
            'diklat': 'Diklat',
            'halfday': 'Rapat/Pertemuan Halfday',
            'fullday': 'Rapat/Pertemuan Fullday',
            'fullboard': 'Rapat/Pertemuan Fullboard',
            'tidak_dibayai': 'Tidak Dibiayai (Bentrok)',
        }

        # Group days by (provinsi_nama, jenis_harian, rate) to build a beautiful formula string
        harian_groups = {}
        for day_info in harian_breakdown:
            key = (day_info['provinsi_nama'], day_info['jenis_harian'], day_info['rate'])
            harian_groups[key] = harian_groups.get(key, 0) + 1

        harian_formulas = []
        for (prov_nama, jh, rate), qty in sorted(harian_groups.items(), key=lambda x: x[0][0]):
            jh_label = JENIS_HARIAN_LABELS.get(jh, jh)
            harian_formulas.append(f"{qty} Hari x {fmt_rp(rate)} ({prov_nama} - {jh_label})")
        harian_formula_str = " + ".join(harian_formulas) if harian_formulas else "0 Hari"

        # Group representasi by (provinsi_nama, representasi_rate)
        repr_groups = {}
        for day_info in harian_breakdown:
            if day_info['representasi'] > 0:
                key = (day_info['provinsi_nama'], day_info['representasi_label'], day_info['representasi'])
                repr_groups[key] = repr_groups.get(key, 0) + 1

        representasi_formulas = []
        for (prov_nama, rep_label, rate), qty in sorted(repr_groups.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            label_txt = f"{rep_label} - " if rep_label else ""
            representasi_formulas.append(f"{qty} Hari x {fmt_rp(rate)} ({label_txt}{prov_nama})")

        if not representasi_formulas:
            if self.perjalanan.jenis_perjalanan in ['fullboard_luar', 'fullboard_dalam']:
                representasi_formula_str = "Tidak ada representasi (Jenis: Fullboard)"
            else:
                representasi_formula_str = "0 Hari"
        else:
            representasi_formula_str = " + ".join(representasi_formulas)

        penginapan_formulas = []
        if total_malam_hotel > 0:
            if penginapan_dana_pribadi > 0:
                over_str = f" (Kelebihan {fmt_rp(penginapan_dana_pribadi)} ditanggung sendiri)"
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
        harian_item_groups = {}
        for day_info in harian_breakdown:
            key = (day_info['provinsi_obj'], day_info['jenis_harian'], day_info['rate'])
            harian_item_groups[key] = harian_item_groups.get(key, 0) + 1

        for (prov_obj, jh, rate), qty in sorted(harian_item_groups.items(), key=lambda x: x[0][0].nama if (x[0][0] and hasattr(x[0][0], 'nama')) else ""):
            jh_label = JENIS_HARIAN_LABELS.get(jh, jh)
            item_keterangan = f"Uang Harian {jh_label} ({prov_obj.nama if prov_obj else ''})"
            if jh == 'tidak_dibayai':
                item_keterangan += " [DIBATALKAN KARENA BENTROK]"
            uang_harian_items.append({
                'perihal': 'Uang Harian Riil',
                'no': 0,
                'keterangan': item_keterangan,
                'harga': rate,
                'kuantitas': f"{qty} (hari)",
                'total': qty * rate,
                'file_url': None,
                'file_name': None
            })

        # 2. Uang Representasi Items
        repr_item_groups = {}
        for day_info in harian_breakdown:
            if day_info['representasi'] > 0:
                key = (day_info['provinsi_obj'], day_info['representasi'])
                repr_item_groups[key] = repr_item_groups.get(key, 0) + 1

        for (prov_obj, rate), qty in sorted(repr_item_groups.items(), key=lambda x: x[0][0].nama if (x[0][0] and hasattr(x[0][0], 'nama')) else ""):
            uang_representasi_items.append({
                'perihal': 'Uang Representasi Riil',
                'no': 0,
                'keterangan': f"Uang Representasi ({prov_obj.nama if prov_obj else ''})",
                'harga': rate,
                'kuantitas': f"{qty} (hari)",
                'total': qty * rate,
                'file_url': None,
                'file_name': None
            })

        # Add cancelled representasi row if applicable
        cancelled_repr_qty = 0
        for day_info in harian_breakdown:
            if day_info['jenis_harian'] == 'tidak_dibayai' and day_info.get('representasi_expected', Decimal('0')) > 0:
                cancelled_repr_qty += 1
        if cancelled_repr_qty > 0:
            uang_representasi_items.append({
                'perihal': 'Uang Representasi Riil',
                'no': 0,
                'keterangan': f"Uang Representasi ({self.perjalanan.tujuan_provinsi.nama if self.perjalanan.tujuan_provinsi else ''}) [DIBATALKAN KARENA BENTROK]",
                'harga': Decimal('0'),
                'kuantitas': f"{cancelled_repr_qty} (hari)",
                'total': Decimal('0'),
                'file_url': None,
                'file_name': None
            })

        # 3. Biaya Penginapan Items
        from datetime import datetime
        for hb in hotel_bills:
            doc_prov_id = None
            clean_keterangan = hb['keterangan']
            p_nama = ""
            if hb['keterangan'] and hb['keterangan'].startswith('[SBM-PENGINAPAN:'):
                c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(hb['keterangan'])
                if p_id:
                    doc_prov_id = p_id
                try:
                    cin_f = datetime.strptime(c_in, '%Y-%m-%d').strftime('%d/%m/%Y')
                    cout_f = datetime.strptime(c_out, '%Y-%m-%d').strftime('%d/%m/%Y')
                    clean_keterangan = f"Hotel {p_nama} ({cin_f} - {cout_f})"
                    if u_desc:
                        clean_keterangan += f" | {u_desc}"
                except Exception:
                    clean_keterangan = u_desc or f"Hotel {p_nama}"
            
            doc_sbm = get_sbm_for_doc(doc_prov_id)
            doc_plafon_hotel = doc_sbm.plafon_penginapan if doc_sbm else Decimal('0')
            doc_ceil = doc_plafon_hotel * hb['malam']
            covered = min(hb['nominal'], doc_ceil)
            unit_price = covered / hb['malam'] if hb['malam'] > 0 else covered
            
            biaya_penginapan_items.append({
                'perihal': 'Biaya Penginapan Riil',
                'no': 0,
                'keterangan': clean_keterangan or 'Hotel',
                'harga': unit_price,
                'kuantitas': f"{hb['malam']} (Malam)",
                'total': covered,
                'file_url': hb['file_url'],
                'file_name': hb['file_name']
            })

        for lb in lumpsum_bills:
            doc_prov_id = None
            clean_keterangan = lb['keterangan']
            p_nama = ""
            if lb['keterangan'] and lb['keterangan'].startswith('[SBM-PENGINAPAN:'):
                c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(lb['keterangan'])
                if p_id:
                    doc_prov_id = p_id
                try:
                    cin_f = datetime.strptime(c_in, '%Y-%m-%d').strftime('%d/%m/%Y')
                    cout_f = datetime.strptime(c_out, '%Y-%m-%d').strftime('%d/%m/%Y')
                    clean_keterangan = f"Lumpsum Penginapan {p_nama} ({cin_f} - {cout_f})"
                    if u_desc:
                        clean_keterangan += f" | {u_desc}"
                except Exception:
                    clean_keterangan = u_desc or f"Lumpsum Penginapan {p_nama}"
            
            doc_sbm = get_sbm_for_doc(doc_prov_id)
            doc_plafon_hotel = doc_sbm.plafon_penginapan if doc_sbm else Decimal('0')
            lumpsum_rate = Decimal('0.30') * doc_plafon_hotel
            total_lumpsum = lumpsum_rate * lb['malam']
            
            biaya_penginapan_items.append({
                'perihal': 'Lumpsum Penginapan (30%)',
                'no': 0,
                'keterangan': clean_keterangan or 'Lumpsum',
                'harga': lumpsum_rate,
                'kuantitas': f"{lb['malam']} (Malam)",
                'total': total_lumpsum,
                'file_url': lb['file_url'],
                'file_name': lb['file_name']
            })

        for fb in fb_luar_bills:
            clean_keterangan = fb['keterangan']
            if fb['keterangan'] and fb['keterangan'].startswith('[SBM-PENGINAPAN:'):
                c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(fb['keterangan'])
                try:
                    cin_f = datetime.strptime(c_in, '%Y-%m-%d').strftime('%d/%m/%Y')
                    cout_f = datetime.strptime(c_out, '%Y-%m-%d').strftime('%d/%m/%Y')
                    clean_keterangan = f"Fullboard Luar {p_nama} ({cin_f} - {cout_f})"
                    if u_desc:
                        clean_keterangan += f" | {u_desc}"
                except Exception:
                    clean_keterangan = u_desc or f"Fullboard Luar {p_nama}"
            biaya_penginapan_items.append({
                'perihal': 'Fullboard Luar Kota (Akomodasi)',
                'no': 0,
                'keterangan': clean_keterangan,
                'harga': Decimal('0'),
                'kuantitas': f"{fb['malam']} (Malam)",
                'total': Decimal('0'),
                'file_url': fb['file_url'],
                'file_name': fb['file_name']
            })

        for fb in fb_dalam_bills:
            clean_keterangan = fb['keterangan']
            if fb['keterangan'] and fb['keterangan'].startswith('[SBM-PENGINAPAN:'):
                c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(fb['keterangan'])
                try:
                    cin_f = datetime.strptime(c_in, '%Y-%m-%d').strftime('%d/%m/%Y')
                    cout_f = datetime.strptime(c_out, '%Y-%m-%d').strftime('%d/%m/%Y')
                    clean_keterangan = f"Fullboard Dalam {p_nama} ({cin_f} - {cout_f})"
                    if u_desc:
                        clean_keterangan += f" | {u_desc}"
                except Exception:
                    clean_keterangan = u_desc or f"Fullboard Dalam {p_nama}"
            biaya_penginapan_items.append({
                'perihal': 'Fullboard Dalam Kota (Akomodasi)',
                'no': 0,
                'keterangan': clean_keterangan,
                'harga': Decimal('0'),
                'kuantitas': f"{fb['malam']} (Malam)",
                'total': Decimal('0'),
                'file_url': fb['file_url'],
                'file_name': fb['file_name']
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
            'sbm_uang_harian': sbm_harian.uang_harian if sbm_harian else Decimal('0'),
            'sbm_uang_representasi_luar_kota': sbm.uang_representasi_luar_kota if sbm else Decimal('0'),
            'sbm_uang_representasi_dalam_kota': sbm.uang_representasi_dalam_kota if sbm else Decimal('0'),
            'sbm_uang_representasi': sbm.uang_representasi_luar_kota if sbm else Decimal('0'),
            'sbm_plafon_hotel': plafon_hotel,
            'sbm_plafon_transport': plafon_transport,
            
            # Detailed breakdown strings/details
            'harian_formula': harian_formula_str,
            'representasi_formula': representasi_formula_str,
            'penginapan_formula': penginapan_formula_str,
            'transport_formula': transport_formula_str,
            'harian_breakdown': harian_breakdown,

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
        # Auto-calculate malam_menginap from SBM-PENGINAPAN tag if present
        if self.keterangan and self.keterangan.startswith('[SBM-PENGINAPAN:'):
            c_in, c_out, malam, p_id, p_nama, u_desc = parse_penginapan_keterangan(self.keterangan)
            if c_in and c_out:
                from datetime import datetime
                try:
                    d_in = datetime.strptime(c_in, '%Y-%m-%d').date()
                    d_out = datetime.strptime(c_out, '%Y-%m-%d').date()
                    self.malam_menginap = max(0, (d_out - d_in).days)
                except Exception:
                    pass

        super().clean()
        # 0. Pastikan jenis berkas dipilih
        if not self.jenis_berkas:
            raise ValidationError({
                'jenis_berkas': "Jenis berkas wajib dipilih."
            })
            
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
