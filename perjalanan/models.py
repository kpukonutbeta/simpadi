from django.db import models
from django.core.exceptions import ValidationError
from master_data.models import Pegawai, Provinsi, StandarBiaya, Anggaran, JenisBerkas
from decimal import Decimal
from datetime import timedelta

import uuid

class SuratTugas(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Aktif'
        COMPLETED = 'COMPLETED', 'Selesai'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nomor_surat = models.CharField(max_length=100, unique=True, verbose_name="Nomor Surat")
    perihal = models.TextField(verbose_name="Perihal")
    tgl_surat = models.DateField(verbose_name="Tanggal Surat")
    file_path = models.URLField(blank=True, null=True, verbose_name="Link File (Drive)")
    pegawai = models.ManyToManyField(Pegawai, related_name='surat_tugas_set', verbose_name="Pegawai Terdaftar")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="Status")

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
    
    tidak_menginap = models.BooleanField(
        default=False,
        verbose_name="Saya tidak menginap di hotel/penginapan"
    )
    
    # Detail Perjalanan (Akan dilengkapi pegawai/admin)
    tempat_berangkat = models.CharField(max_length=255, verbose_name="Tempat Berangkat", default="KPU Kab. Konawe Utara")
    tempat_tujuan = models.CharField(max_length=255, verbose_name="Tempat Tujuan")
    tujuan_provinsi = models.ForeignKey(Provinsi, on_delete=models.PROTECT, verbose_name="Provinsi (SBM)")
    maksud_perjalanan = models.TextField(verbose_name="Maksud Perjalanan")
    tanggal_berangkat = models.DateField(verbose_name="Tanggal Berangkat", null=True, blank=True)
    tanggal_kembali = models.DateField(verbose_name="Tanggal Kembali", null=True, blank=True)
    
    anggaran = models.ForeignKey(Anggaran, on_delete=models.PROTECT, verbose_name="Sumber Anggaran")
    tahun_sbm = models.IntegerField(
        choices=[(2023, '2023 (Tahun Lalu)'), (2024, '2024 (Tahun Ini)')],
        default=2024, 
        verbose_name="Tahun SBM"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # 1. Otomatisasi Nomor SPD jika belum ada
        if not self.nomor_spd:
            from django.db import transaction
            with transaction.atomic():
                config, created = PengaturanNomorSPD.objects.get_or_create(id=1)
                config.prefix_terakhir += 1
                config.save()
                
                self.nomor_spd = f"{config.prefix_terakhir}{config.suffix_format}"

        # 2. Auto-fill tempat_tujuan & maksud from SuratTugas if not set
        if not self.tempat_tujuan:
            self.tempat_tujuan = "Lihat Surat Tugas" 
        if not self.maksud_perjalanan:
            self.maksud_perjalanan = self.surat_tugas.perihal
            
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
                tanggal_berangkat__lte=self.tanggal_kembali,
                tanggal_kembali__gte=self.tanggal_berangkat
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
    uang_harian_riil = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    uang_representasi_riil = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # At-cost components
    biaya_penginapan_riil = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    biaya_transportasi_riil = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Personal expense share (dana pribadi)
    penginapan_dana_pribadi = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Dana Pribadi Penginapan")
    transportasi_dana_pribadi = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Dana Pribadi Transportasi")
    total_dana_pribadi = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Total Dana Pribadi")
    
    # System calculated (locked)
    total_dibayarkan = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=0)

    def save(self, *args, **kwargs):
        # Fetch SBM
        try:
            sbm = StandarBiaya.objects.get(
                provinsi=self.perjalanan.tujuan_provinsi,
                golongan=self.perjalanan.pegawai.golongan,
                tahun=self.perjalanan.tahun_sbm
            )
            tarif_harian = sbm.uang_harian
            plafon_hotel = sbm.plafon_penginapan
            tarif_representasi = sbm.uang_representasi
            plafon_transport = getattr(sbm, 'plafon_transportasi', 0)
        except StandarBiaya.DoesNotExist:
            tarif_harian = 0
            plafon_hotel = 0
            tarif_representasi = 0
            plafon_transport = 0

        # Calculate real hotel and transport from BerkasPerjalanan based on jenis_berkas.kategori_biaya
        total_hotel_input = 0
        total_transport_input = 0
        if self.perjalanan_id:
            for b in BerkasPerjalanan.objects.filter(perjalanan_id=self.perjalanan_id):
                if b.nominal:
                    kategori = b.jenis_berkas.kategori_biaya if (b.jenis_berkas and hasattr(b.jenis_berkas, 'kategori_biaya')) else 'none'
                    if kategori == 'penginapan':
                        if not self.perjalanan.tidak_menginap:
                            total_hotel_input += b.nominal
                    elif kategori == 'transportasi':
                        if self.perjalanan.jenis_transportasi != PerjalananDinas.JenisTransportasi.MOBIL_DINAS:
                            total_transport_input += b.nominal
                    else:
                        nama_berkas = (b.jenis_berkas.nama if b.jenis_berkas else "").upper()
                        if "HOTEL" in nama_berkas or "PENGINAPAN" in nama_berkas:
                            if not self.perjalanan.tidak_menginap:
                                total_hotel_input += b.nominal
                        elif "TIKET" in nama_berkas or "TRANSPORT" in nama_berkas or "TAXI" in nama_berkas or "PESAWAT" in nama_berkas:
                            if self.perjalanan.jenis_transportasi != PerjalananDinas.JenisTransportasi.MOBIL_DINAS:
                                total_transport_input += b.nominal

        # Logic 1: Lumpsum Harian & Representasi (taken from SBM automatically)
        durasi = self.perjalanan.durasi_hari
        self.uang_harian_riil = durasi * tarif_harian
        self.uang_representasi_riil = durasi * tarif_representasi

        # Logic 2: Capping Hotel/Penginapan (At-Cost)
        if self.perjalanan.tidak_menginap:
            self.biaya_penginapan_riil = Decimal('0.30') * plafon_hotel * durasi
            self.penginapan_dana_pribadi = 0
        else:
            plafon_hotel_limit = plafon_hotel * durasi
            if total_hotel_input > plafon_hotel_limit:
                self.biaya_penginapan_riil = plafon_hotel_limit
                self.penginapan_dana_pribadi = total_hotel_input - plafon_hotel_limit
            else:
                self.biaya_penginapan_riil = total_hotel_input
                self.penginapan_dana_pribadi = 0

        # Logic 3: Capping Transportasi (At-Cost)
        if plafon_transport > 0 and total_transport_input > plafon_transport:
            self.biaya_transportasi_riil = plafon_transport
            self.transportasi_dana_pribadi = total_transport_input - plafon_transport
        else:
            self.biaya_transportasi_riil = total_transport_input
            self.transportasi_dana_pribadi = 0

        self.total_dana_pribadi = self.penginapan_dana_pribadi + self.transportasi_dana_pribadi
        self.total_dibayarkan = self.uang_harian_riil + self.uang_representasi_riil + self.biaya_penginapan_riil + self.biaya_transportasi_riil
        
        super().save(*args, **kwargs)

class BerkasPerjalanan(models.Model):
    perjalanan = models.ForeignKey(PerjalananDinas, on_delete=models.CASCADE, related_name='berkas')
    jenis_berkas = models.ForeignKey(JenisBerkas, on_delete=models.PROTECT, verbose_name="Jenis Berkas", null=True, blank=True)
    file = models.FileField(upload_to='perjalanan_dinas/%Y/%m/', blank=True, null=True)
    nominal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Nominal Biaya")
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

    def save(self, *args, **kwargs):
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


class BerkasPerjalananNominal(BerkasPerjalanan):
    class Meta:
        proxy = True
        verbose_name = "Berkas Pendukung dengan Nominal Biaya"
        verbose_name_plural = "Berkas Pendukung dengan Nominal Biaya"


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
