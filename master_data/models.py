from django.db import models
from django.core.validators import FileExtensionValidator

class Golongan(models.TextChoices):
    I = 'I', 'Golongan I'
    II = 'II', 'Golongan II'
    III = 'III', 'Golongan III'
    IV = 'IV', 'Golongan IV'
    NON_GOLONGAN = 'NON_GOLONGAN', 'Non Golongan'

class PosisiEselon(models.TextChoices):
    NON_ESELON = 'NON_ESELON', 'Non Posisi Eselon'
    ES_IV = 'ES_IV', 'Eselon IV'
    ES_III = 'ES_III', 'Eselon III'
    ES_II = 'ES_II', 'Eselon II'

from django.conf import settings

class Pegawai(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pegawai_profile', null=True, blank=True)
    nip = models.CharField(max_length=20, unique=True, verbose_name="NIP")
    nama = models.CharField(max_length=100, verbose_name="Nama Lengkap")
    email = models.EmailField(unique=True, verbose_name="Email", null=True, blank=True)
    golongan = models.CharField(max_length=15, choices=Golongan.choices, verbose_name="Golongan")
    posisi_jabatan = models.CharField(
        max_length=15,
        choices=PosisiEselon.choices,
        default=PosisiEselon.NON_ESELON,
        verbose_name="Posisi Jabatan"
    )
    jabatan = models.CharField(max_length=100, verbose_name="Jabatan")

    def __str__(self):
        return f"{self.nama} ({self.nip})"

    class Meta:
        verbose_name = "Pegawai"
        verbose_name_plural = "Data Pegawai"

class Provinsi(models.Model):
    nama = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nama

    class Meta:
        verbose_name = "Provinsi"
        verbose_name_plural = "Data Provinsi"

class Kota(models.Model):
    provinsi = models.ForeignKey(Provinsi, on_delete=models.CASCADE, related_name='kota_set', verbose_name="Provinsi")
    nama = models.CharField(max_length=100, verbose_name="Nama Kota/Kabupaten")

    def __str__(self):
        return self.nama

    class Meta:
        unique_together = ('provinsi', 'nama')
        ordering = ['provinsi__nama', 'nama']
        verbose_name = "Kota/Kabupaten"
        verbose_name_plural = "Data Kota/Kabupaten"

class DokumenSBM(models.Model):
    tahun = models.IntegerField(unique=True, verbose_name="Tahun SBM")
    file_pdf = models.FileField(
        upload_to='sbm_dokumen/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="File PDF SBM"
    )

    class Meta:
        verbose_name = "Tahun Standar Biaya Masukan (SBM)"
        verbose_name_plural = "Tahun Standar Biaya Masukan (SBM)"
        ordering = ['-tahun']

    def __str__(self):
        return f"SBM Tahun {self.tahun}"

class StandarBiayaHarian(models.Model):
    provinsi = models.ForeignKey(Provinsi, on_delete=models.CASCADE)
    tahun = models.IntegerField(default=2024, verbose_name="Tahun")
    uang_harian = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Uang Harian Luar Kota")
    uang_harian_dalam_kota = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Uang Harian Dalam Kota (> 8 Jam)")
    uang_harian_diklat = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Uang Harian Diklat")

    def __str__(self):
        return f"SBM Harian {self.provinsi} - {self.tahun}"

    class Meta:
        unique_together = ('provinsi', 'tahun')
        verbose_name = "Standar Biaya Masukan (SBM) Uang Harian"
        verbose_name_plural = "Standar Biaya Masukan (SBM) Uang Harian"

class StandarBiaya(models.Model):
    provinsi = models.ForeignKey(Provinsi, on_delete=models.CASCADE)
    golongan = models.CharField(max_length=15, choices=Golongan.choices, null=True, blank=True)
    posisi_jabatan = models.CharField(
        max_length=15,
        choices=PosisiEselon.choices,
        null=True,
        blank=True,
        verbose_name="Posisi Jabatan"
    )

    plafon_penginapan = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Plafon Penginapan")
    uang_representasi_luar_kota = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="Representasi Luar Kota",
    )
    uang_representasi_dalam_kota = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="Representasi Dalam Kota (> 8 Jam)",
    )
    biaya_taksi = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Taksi Bandara")
    tahun = models.IntegerField(
        default=2024,
        verbose_name="Tahun"
    )

    def __init__(self, *args, **kwargs):
        legacy_rep = kwargs.pop('uang_representasi', None)
        if legacy_rep is not None and 'uang_representasi_luar_kota' not in kwargs:
            kwargs['uang_representasi_luar_kota'] = legacy_rep
        super().__init__(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if not self.golongan and not self.posisi_jabatan:
            raise ValidationError("Salah satu dari Golongan atau Posisi Jabatan harus diisi.")

    def __str__(self):
        classification = self.golongan or self.posisi_jabatan or "Umum"
        return f"SBM {self.provinsi} - {classification}"

    @property
    def uang_representasi(self):
        return self.uang_representasi_luar_kota

    @uang_representasi.setter
    def uang_representasi(self, value):
        self.uang_representasi_luar_kota = value

    class Meta:
        unique_together = ('provinsi', 'golongan', 'posisi_jabatan', 'tahun')
        verbose_name = "Standar Biaya Masukan (SBM) Golongan/Pejabat Eselon"
        verbose_name_plural = "Standar Biaya Masukan (SBM) Golongan/Pejabat Eselon"

class Anggaran(models.Model):
    kode_dipa = models.CharField(max_length=50, unique=True, verbose_name="Kode DIPA")
    nama_kegiatan = models.CharField(max_length=255, verbose_name="Nama Kegiatan")
    pagu = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="Total Pagu")
    sisa_pagu = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="Sisa Pagu")

    def __str__(self):
        return f"{self.kode_dipa} - {self.nama_kegiatan}"

    class Meta:
        verbose_name = "Anggaran"
        verbose_name_plural = "Data Anggaran"

class JenisBerkas(models.Model):
    nama = models.CharField(max_length=100, unique=True, verbose_name="Nama Jenis Berkas")
    wajib = models.BooleanField(default=False, verbose_name="Wajib Diunggah?")
    nominal_biaya = models.BooleanField(default=False, verbose_name="Menyertakan Nominal Biaya?")
    
    class KategoriBiaya(models.TextChoices):
        PENGINAPAN = 'penginapan', 'Biaya Penginapan'
        PENGINAPAN_30 = 'penginapan_30', 'Biaya Penginapan 30%'
        PENGINAPAN_FB_LUAR = 'penginapan_fb_luar', 'Biaya Penginapan Fullboard Luar Kota'
        PENGINAPAN_FB_DALAM = 'penginapan_fb_dalam', 'Biaya Penginapan Fullboard Dalam Kota'
        TRANSPORTASI = 'transportasi', 'Biaya Transportasi'
        TRANSPORTASI_PESAWAT = 'transportasi_pesawat', 'Biaya Transportasi Tiket Pesawat'
        NONE = 'none', 'Bukan Biaya (Lain-lain)'

    kategori_biaya = models.CharField(
        max_length=30,
        choices=KategoriBiaya.choices,
        default=KategoriBiaya.NONE,
        verbose_name="Kategori Biaya"
    )

    def save(self, *args, **kwargs):
        self.nama = self.nama.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nama

    class Meta:
        verbose_name = "Jenis Berkas"
        verbose_name_plural = "Jenis Berkas"

class PejabatPenandatangan(models.Model):
    class Jabatan(models.TextChoices):
        SEKRETARIS = 'SEKRETARIS', 'Sekretaris'
        PPK = 'PPK', 'Pejabat Pembuat Komitmen (PPK)'

    nama = models.CharField(max_length=150, verbose_name="Nama Lengkap")
    nip = models.CharField(max_length=30, verbose_name="NIP")
    jabatan = models.CharField(max_length=50, choices=Jabatan.choices, verbose_name="Jabatan")
    aktif = models.BooleanField(default=True, verbose_name="Status Aktif")

    def save(self, *args, **kwargs):
        if self.aktif:
            # Set all other signers with the same jabatan to inactive
            PejabatPenandatangan.objects.filter(jabatan=self.jabatan, aktif=True).exclude(pk=self.pk).update(aktif=False)
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Aktif" if self.aktif else "Tidak Aktif"
        return f"{self.get_jabatan_display()} - {self.nama} ({status})"

    class Meta:
        verbose_name = "Pejabat Penandatangan"
        verbose_name_plural = "Pejabat Penandatangan"

class StandarBiayaTiket(models.Model):
    class KelasTiket(models.TextChoices):
        BISNIS = 'bisnis', 'Bisnis'
        EKONOMI = 'ekonomi', 'Ekonomi'

    kota_asal = models.ForeignKey(
        Kota,
        on_delete=models.PROTECT,
        related_name='tiket_asal_set',
        verbose_name="Kota Asal"
    )
    kota_tujuan = models.ForeignKey(
        Kota,
        on_delete=models.PROTECT,
        related_name='tiket_tujuan_set',
        verbose_name="Kota Tujuan"
    )
    kelas = models.CharField(
        max_length=10,
        choices=KelasTiket.choices,
        verbose_name="Kelas Tiket"
    )
    posisi_jabatan = models.CharField(
        max_length=15,
        choices=PosisiEselon.choices,
        null=True,
        blank=True,
        verbose_name="Posisi Jabatan"
    )
    nominal = models.DecimalField(
        max_digits=14,
        decimal_places=0,
        verbose_name="Nominal Biaya (PP)"
    )
    tahun = models.IntegerField(
        default=2024,
        verbose_name="Tahun"
    )

    def __str__(self):
        class_str = ""
        if self.posisi_jabatan:
            class_str += f" - {self.get_posisi_jabatan_display()}"
        return f"{self.kota_asal} → {self.kota_tujuan} ({self.get_kelas_display()}){class_str} - {self.tahun}"

    class Meta:
        unique_together = ('kota_asal', 'kota_tujuan', 'kelas', 'posisi_jabatan', 'tahun')
        ordering = ['kota_asal__nama', 'kota_tujuan__nama', 'kelas', 'posisi_jabatan', 'tahun']
        verbose_name = "Standar Biaya Masukan (SBM) Tiket Pesawat Dalam Negeri"
        verbose_name_plural = "Standar Biaya Masukan (SBM) Tiket Pesawat Dalam Negeri"
