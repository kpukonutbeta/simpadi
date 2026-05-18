from django.db import models

class Golongan(models.TextChoices):
    I = 'I', 'Golongan I'
    II = 'II', 'Golongan II'
    III = 'III', 'Golongan III'
    IV = 'IV', 'Golongan IV'

from django.conf import settings

class Pegawai(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pegawai_profile', null=True, blank=True)
    nip = models.CharField(max_length=20, unique=True, verbose_name="NIP")
    nama = models.CharField(max_length=100, verbose_name="Nama Lengkap")
    email = models.EmailField(unique=True, verbose_name="Email", null=True, blank=True)
    golongan = models.CharField(max_length=5, choices=Golongan.choices, verbose_name="Golongan")
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

class StandarBiaya(models.Model):
    provinsi = models.ForeignKey(Provinsi, on_delete=models.CASCADE)
    golongan = models.CharField(max_length=5, choices=Golongan.choices)
    uang_harian = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Uang Harian")
    plafon_penginapan = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Plafon Penginapan")
    uang_representasi = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Uang Representasi")
    plafon_transportasi = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Plafon Transportasi")
    tahun = models.IntegerField(
        choices=[(2023, '2023 (Tahun Lalu)'), (2024, '2024 (Tahun Ini)')],
        default=2024,
        verbose_name="Tahun"
    )

    def __str__(self):
        return f"SBM {self.provinsi} - {self.golongan}"

    class Meta:
        unique_together = ('provinsi', 'golongan', 'tahun')
        verbose_name = "Standar Biaya (SBM)"
        verbose_name_plural = "Standar Biaya (SBM)"

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
        TRANSPORTASI = 'transportasi', 'Biaya Transportasi'
        NONE = 'none', 'Bukan Biaya (Lain-lain)'

    kategori_biaya = models.CharField(
        max_length=20,
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
