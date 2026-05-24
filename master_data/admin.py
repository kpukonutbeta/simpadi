from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Pegawai, Provinsi, Kota, StandarBiaya, StandarBiayaHarian, Anggaran, JenisBerkas, PejabatPenandatangan, StandarBiayaTiket, DokumenSBM
from core.models import User
from django import forms
from django.forms import TextInput
from decimal import Decimal
import re


class RupiahInput(TextInput):
    """Text input that renders values with dot thousand separators.

    It also adds inline input handlers so formatting still works even if the
    external static JS is not loaded for some reason.
    """

    def __init__(self, attrs=None):
        base_attrs = {
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'class': 'rupiah',
            'data-rupiah': '1',
            'oninput': "this.value=this.value.replace(/\\./g,'').replace(/\\D/g,'').replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');",
            'onblur': "this.value=this.value.replace(/\\./g,'').replace(/\\D/g,'').replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');",
        }
        if attrs:
            base_attrs.update(attrs)
        super().__init__(base_attrs)

    def format_value(self, value):
        if value in (None, ''):
            return ''
        digits = re.sub(r'\D', '', str(value))
        if not digits:
            return ''
        return f"{int(digits):,}".replace(',', '.')

@admin.register(JenisBerkas)
class JenisBerkasAdmin(admin.ModelAdmin):
    list_display = ('nama', 'wajib', 'nominal_biaya', 'kategori_biaya')
    list_filter = ('wajib', 'nominal_biaya', 'kategori_biaya')
    search_fields = ('nama',)
    actions = ['set_wajib_true', 'set_wajib_false', 'set_nominal_true', 'set_nominal_false']

    def set_wajib_true(self, request, queryset):
        updated = queryset.update(wajib=True)
        self.message_user(request, f"{updated} jenis berkas berhasil diubah menjadi Wajib Diunggah.")
    set_wajib_true.short_description = "Setel Terpilih: Wajib Diunggah"

    def set_wajib_false(self, request, queryset):
        updated = queryset.update(wajib=False)
        self.message_user(request, f"{updated} jenis berkas berhasil diubah menjadi Tidak Wajib Diunggah.")
    set_wajib_false.short_description = "Setel Terpilih: Tidak Wajib Diunggah"

    def set_nominal_true(self, request, queryset):
        updated = queryset.update(nominal_biaya=True)
        self.message_user(request, f"{updated} jenis berkas berhasil diubah menjadi Menyertakan Nominal Biaya.")
    set_nominal_true.short_description = "Setel Terpilih: Menyertakan Nominal Biaya"

    def set_nominal_false(self, request, queryset):
        updated = queryset.update(nominal_biaya=False)
        self.message_user(request, f"{updated} jenis berkas berhasil diubah menjadi Tidak Menyertakan Nominal Biaya.")
    set_nominal_false.short_description = "Setel Terpilih: Tidak Menyertakan Nominal Biaya"

@admin.register(PejabatPenandatangan)
class PejabatPenandatanganAdmin(admin.ModelAdmin):
    list_display = ('jabatan', 'nama', 'nip', 'aktif')
    list_filter = ('jabatan', 'aktif')
    search_fields = ('nama', 'nip')

class PegawaiForm(forms.ModelForm):
    password_input = forms.CharField(
        label="Password Login",
        required=False,
        widget=forms.PasswordInput,
        help_text="Kosongkan jika tidak ingin mengubah password"
    )

    class Meta:
        model = Pegawai
        fields = ('nip', 'nama', 'email', 'golongan', 'posisi_jabatan', 'jabatan')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['password_input'].required = True
            self.fields['password_input'].help_text = "Password untuk akun login baru"

@admin.register(Pegawai)
class PegawaiAdmin(admin.ModelAdmin):
    form = PegawaiForm
    list_display = ('nip', 'nama', 'email', 'golongan', 'posisi_jabatan', 'jabatan', 'has_user_account')
    search_fields = ('nip', 'nama', 'email')
    list_filter = ('golongan', 'posisi_jabatan')
    
    def has_user_account(self, obj):
        return obj.user is not None
    has_user_account.boolean = True
    has_user_account.short_description = "Akun Login"

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get('password_input')
        if not obj.user and obj.email:
            # Create user account
            user, created = User.objects.get_or_create(
                email=obj.email,
                defaults={'username': obj.email.split('@')[0]}
            )
            if password:
                user.set_password(password)
                user.save()
            obj.user = user
        elif obj.user and password:
            obj.user.set_password(password)
            obj.user.save()
            
        super().save_model(request, obj, form, change)


@admin.register(Provinsi)
class ProvinsiAdmin(admin.ModelAdmin):
    list_display = ('nama',)
    search_fields = ('nama',)

@admin.register(Kota)
class KotaAdmin(admin.ModelAdmin):
    list_display = ('nama', 'provinsi')
    list_filter = ('provinsi',)
    search_fields = ('nama', 'provinsi__nama')
    ordering = ('provinsi__nama', 'nama')


class StandarBiayaForm(forms.ModelForm):
    """Custom form for StandarBiaya that displays formatted rupiah but
    stores numeric values. Uses CharField widgets for input display and
    converts to Decimal on clean.
    """
    plafon_penginapan = forms.CharField(widget=RupiahInput(), required=True)
    biaya_taksi = forms.CharField(widget=RupiahInput(), required=True)
    uang_representasi = forms.CharField(widget=RupiahInput(), required=True)

    class Meta:
        model = StandarBiaya
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def clean(self):
        cleaned = super().clean()
        # Convert formatted string with dots into Decimal values
        for fname in ('plafon_penginapan', 'biaya_taksi', 'uang_representasi'):
            raw = cleaned.get(fname)
            if raw is None:
                continue
            # remove any non-digit characters (dots, spaces, etc.)
            digits = re.sub(r"\D", "", str(raw))
            if digits == "":
                cleaned[fname] = Decimal(0)
            else:
                cleaned[fname] = Decimal(digits)
        return cleaned


# --- Forms for other admin classes to display formatted rupiah ---
class StandarBiayaHarianForm(forms.ModelForm):
    uang_harian = forms.CharField(widget=RupiahInput(), required=True)
    uang_harian_dalam_kota = forms.CharField(widget=RupiahInput(), required=True)
    uang_harian_diklat = forms.CharField(widget=RupiahInput(), required=True)

    class Meta:
        model = StandarBiayaHarian
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def clean(self):
        cleaned = super().clean()
        for fname in ('uang_harian', 'uang_harian_dalam_kota', 'uang_harian_diklat'):
            raw = cleaned.get(fname)
            if raw is None:
                continue
            digits = re.sub(r"\D", "", str(raw))
            cleaned[fname] = Decimal(digits) if digits != "" else Decimal(0)
        return cleaned


class AnggaranForm(forms.ModelForm):
    pagu = forms.CharField(widget=RupiahInput(), required=True)
    sisa_pagu = forms.CharField(widget=RupiahInput(), required=True)

    class Meta:
        model = Anggaran
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def clean(self):
        cleaned = super().clean()
        for fname in ('pagu', 'sisa_pagu'):
            raw = cleaned.get(fname)
            if raw is None:
                continue
            digits = re.sub(r"\D", "", str(raw))
            cleaned[fname] = Decimal(digits) if digits != "" else Decimal(0)
        return cleaned


class StandarBiayaTiketForm(forms.ModelForm):
    nominal = forms.CharField(widget=RupiahInput(), required=True)

    class Meta:
        model = StandarBiayaTiket
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        raw = cleaned.get('nominal')
        if raw is not None:
            digits = re.sub(r"\D", "", str(raw))
            cleaned['nominal'] = Decimal(digits) if digits != "" else Decimal(0)
        return cleaned

@admin.register(StandarBiaya)
class StandarBiayaAdmin(admin.ModelAdmin):
    list_display = (
        'provinsi', 'golongan', 'posisi_jabatan', 'tahun',
        'fmt_plafon_penginapan', 'fmt_biaya_taksi', 'fmt_uang_representasi'
    )
    list_filter = ('provinsi', 'golongan', 'posisi_jabatan', 'tahun')
    fields = ('provinsi', 'tahun', 'golongan', 'posisi_jabatan', 'plafon_penginapan', 'biaya_taksi', 'uang_representasi')
    form = StandarBiayaForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'tahun':
            from .models import DokumenSBM
            docs = DokumenSBM.objects.all().order_by('-tahun')
            if docs.exists():
                choices = [(doc.tahun, str(doc.tahun)) for doc in docs]
                kwargs['widget'] = forms.Select(choices=choices)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @staticmethod
    def _rupiah(val):
        return f"Rp{val:,.0f}".replace(',', '.')


    def fmt_plafon_penginapan(self, obj): return self._rupiah(obj.plafon_penginapan)
    fmt_plafon_penginapan.short_description = "Plafon Penginapan"
    fmt_plafon_penginapan.admin_order_field = 'plafon_penginapan'


    def fmt_biaya_taksi(self, obj): return self._rupiah(obj.biaya_taksi)
    fmt_biaya_taksi.short_description = "Taksi Bandara"
    fmt_biaya_taksi.admin_order_field = 'biaya_taksi'

    def fmt_uang_representasi(self, obj): return self._rupiah(obj.uang_representasi)
    fmt_uang_representasi.short_description = "Uang Representasi"
    fmt_uang_representasi.admin_order_field = 'uang_representasi'

    class Media:
        js = ('js/rupiah_input.js?v=6',)

@admin.register(StandarBiayaHarian)
class StandarBiayaHarianAdmin(admin.ModelAdmin):
    list_display = ('provinsi', 'tahun', 'fmt_uang_harian', 'fmt_dalam_kota', 'fmt_diklat')
    list_filter = ('provinsi', 'tahun')
    form = StandarBiayaHarianForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'tahun':
            from .models import DokumenSBM
            docs = DokumenSBM.objects.all().order_by('-tahun')
            if docs.exists():
                choices = [(doc.tahun, str(doc.tahun)) for doc in docs]
                kwargs['widget'] = forms.Select(choices=choices)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @staticmethod
    def _rupiah(val):
        return f"Rp{val:,.0f}".replace(',', '.')

    def fmt_uang_harian(self, obj): return self._rupiah(obj.uang_harian)
    fmt_uang_harian.short_description = "Luar Kota"
    fmt_uang_harian.admin_order_field = 'uang_harian'

    def fmt_dalam_kota(self, obj): return self._rupiah(obj.uang_harian_dalam_kota)
    fmt_dalam_kota.short_description = "Dalam Kota (> 8 Jam)"
    fmt_dalam_kota.admin_order_field = 'uang_harian_dalam_kota'

    def fmt_diklat(self, obj): return self._rupiah(obj.uang_harian_diklat)
    fmt_diklat.short_description = "Diklat"
    fmt_diklat.admin_order_field = 'uang_harian_diklat'

    class Media:
        js = ('js/rupiah_input.js?v=6',)
@admin.register(Anggaran)
class AnggaranAdmin(admin.ModelAdmin):
    list_display = ('kode_dipa', 'nama_kegiatan', 'fmt_pagu', 'fmt_sisa_pagu')
    search_fields = ('kode_dipa', 'nama_kegiatan')
    form = AnggaranForm

    @staticmethod
    def _rupiah(val):
        return f"Rp{val:,.0f}".replace(',', '.')

    def fmt_pagu(self, obj): return self._rupiah(obj.pagu)
    fmt_pagu.short_description = "Total Pagu"
    fmt_pagu.admin_order_field = 'pagu'

    def fmt_sisa_pagu(self, obj): return self._rupiah(obj.sisa_pagu)
    fmt_sisa_pagu.short_description = "Sisa Pagu"
    fmt_sisa_pagu.admin_order_field = 'sisa_pagu'

    class Media:
        js = ('js/rupiah_input.js?v=6',)


@admin.register(StandarBiayaTiket)
class StandarBiayaTiketAdmin(admin.ModelAdmin):
    list_display = ('kota_asal', 'kota_tujuan', 'kelas', 'posisi_jabatan', 'tahun', 'nominal_rupiah')
    list_filter = ('tahun', 'kelas', 'posisi_jabatan', 'kota_asal__provinsi')
    search_fields = ('kota_asal__nama', 'kota_tujuan__nama')
    ordering = ('kota_asal__nama', 'kota_tujuan__nama', 'kelas', 'posisi_jabatan', 'tahun')
    autocomplete_fields = ('kota_asal', 'kota_tujuan')
    form = StandarBiayaTiketForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'tahun':
            from .models import DokumenSBM
            docs = DokumenSBM.objects.all().order_by('-tahun')
            if docs.exists():
                choices = [(doc.tahun, str(doc.tahun)) for doc in docs]
                kwargs['widget'] = forms.Select(choices=choices)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def nominal_rupiah(self, obj):
        return f"Rp{obj.nominal:,.0f}".replace(',', '.')
    nominal_rupiah.short_description = "Nominal Biaya (PP)"
    nominal_rupiah.admin_order_field = 'nominal'

    class Media:
        js = ('js/rupiah_input.js?v=6',)


@admin.register(DokumenSBM)
class DokumenSBMAdmin(admin.ModelAdmin):
    list_display = ('tahun', 'file_pdf_link')
    search_fields = ('tahun',)

    def file_pdf_link(self, obj):
        if obj.file_pdf:
            return mark_safe(f'<a href="{obj.file_pdf.url}" target="_blank">Unduh PDF (SBM {obj.tahun})</a>')
        return "-"
    file_pdf_link.short_description = "File PDF SBM"
