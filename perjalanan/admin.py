from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe
from .models import (
    PerjalananDinas, BiayaPerjalanan, BerkasPerjalanan, SuratTugas,
    PengaturanNomorSPD, BerkasPerjalananPenginapan, BerkasPerjalananTransportasi, BerkasPerjalananNonNominal
)
from master_data.models import JenisBerkas

class AdminFileWidgetNewTab(AdminFileWidget):
    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        if 'href=' in html and 'target="_blank"' not in html:
            html = html.replace('<a href=', '<a target="_blank" href=')
        return mark_safe(html)

@admin.register(SuratTugas)
class SuratTugasAdmin(admin.ModelAdmin):
    list_display = ('nomor_surat', 'tgl_surat', 'perihal')
    search_fields = ('nomor_surat', 'perihal')
    filter_horizontal = ('pegawai',)
    actions = ['terbitkan_spd_action']

    def terbitkan_spd_action(self, request, queryset):
        # Store selected IDs in session and redirect to custom view
        selected_ids = list(queryset.values_list('id', flat=True))
        # Convert UUIDs to strings for session storage
        selected_ids = [str(uid) for uid in selected_ids]
        request.session['selected_st_ids'] = selected_ids
        return redirect('perjalanan:generate_spd_bulk')
    
    terbitkan_spd_action.short_description = "Terbitkan SPD dari Surat Tugas Terpilih"

class BiayaPerjalananInline(admin.StackedInline):
    model = BiayaPerjalanan
    readonly_fields = ('uang_harian_riil', 'uang_representasi_riil', 'biaya_penginapan_riil', 'biaya_transportasi_riil', 'get_total_dibayarkan', 'get_total_tidak_dibayarkan')
    fields = ('uang_harian_riil', 'uang_representasi_riil', 'biaya_penginapan_riil', 'biaya_transportasi_riil', 'get_total_dibayarkan', 'get_total_tidak_dibayarkan')
    extra = 1
    max_num = 1
    can_delete = False

    def get_total_dibayarkan(self, obj):
        val = obj.total_dibayarkan if obj else 0
        formatted_val = f"Rp {val:,.0f}".replace(",", ".")
        return mark_safe(f'<strong style="color: #0f172a; font-size: 1.1em;">{formatted_val}</strong>')
    get_total_dibayarkan.short_description = "Total Dibayarkan"

    def get_total_tidak_dibayarkan(self, obj):
        val = obj.total_dana_pribadi if obj else 0
        if val > 0:
            formatted_val = f"Rp {val:,.0f}".replace(",", ".")
            return mark_safe(f'<strong style="color: #dc2626; font-size: 1.1em;">{formatted_val}</strong>')
        return "-"
    get_total_tidak_dibayarkan.short_description = "Total Tidak Dibayarkan"

from django.db.models import Q

class BerkasPerjalananPenginapanInline(admin.TabularInline):
    model = BerkasPerjalananPenginapan
    fields = ('jenis_berkas', 'nominal', 'malam_menginap', 'keterangan', 'file', 'is_verified')
    extra = 1
    can_delete = True
    verbose_name = "Berkas Pendukung untuk Penginapan"
    verbose_name_plural = "Berkas Pendukung untuk Penginapan"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            Q(jenis_berkas__kategori_biaya='penginapan') | Q(jenis_berkas__nama__icontains='hotel') | Q(jenis_berkas__nama__icontains='penginapan'),
            jenis_berkas__nominal_biaya=True
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                Q(kategori_biaya='penginapan') | Q(nama__icontains='hotel') | Q(nama__icontains='penginapan'),
                nominal_biaya=True
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'jenis_berkas' and formfield and hasattr(formfield.widget, 'can_delete_related'):
            formfield.widget.can_delete_related = False
        if db_field.name == 'file' and formfield:
            formfield.widget = AdminFileWidgetNewTab(attrs=formfield.widget.attrs)
        return formfield


class BerkasPerjalananTransportasiInline(admin.TabularInline):
    model = BerkasPerjalananTransportasi
    fields = ('jenis_berkas', 'nominal', 'keterangan', 'file', 'is_verified')
    extra = 1
    can_delete = True
    verbose_name = "Berkas Pendukung untuk Transportasi"
    verbose_name_plural = "Berkas Pendukung untuk Transportasi"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            ~Q(jenis_berkas__kategori_biaya='penginapan') & ~Q(jenis_berkas__nama__icontains='hotel') & ~Q(jenis_berkas__nama__icontains='penginapan'),
            jenis_berkas__nominal_biaya=True
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                ~Q(kategori_biaya='penginapan') & ~Q(nama__icontains='hotel') & ~Q(nama__icontains='penginapan'),
                nominal_biaya=True
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'jenis_berkas' and formfield and hasattr(formfield.widget, 'can_delete_related'):
            formfield.widget.can_delete_related = False
        if db_field.name == 'file' and formfield:
            formfield.widget = AdminFileWidgetNewTab(attrs=formfield.widget.attrs)
        return formfield


class BerkasPerjalananNonNominalInline(admin.TabularInline):
    model = BerkasPerjalananNonNominal
    fields = ('jenis_berkas', 'keterangan', 'file', 'is_verified')
    extra = 1
    can_delete = True
    verbose_name = "Berkas Pendukung Tanpa Nominal Biaya"
    verbose_name_plural = "Berkas Pendukung Tanpa Nominal Biaya"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(jenis_berkas__nominal_biaya=False)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(nominal_biaya=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'jenis_berkas' and formfield and hasattr(formfield.widget, 'can_delete_related'):
            formfield.widget.can_delete_related = False
        if db_field.name == 'file' and formfield:
            formfield.widget = AdminFileWidgetNewTab(attrs=formfield.widget.attrs)
        return formfield

@admin.register(PengaturanNomorSPD)
class PengaturanNomorSPDAdmin(admin.ModelAdmin):
    list_display = ('suffix_format', 'prefix_terakhir')
    
    def has_add_permission(self, request):
        # Only allow one configuration record
        if self.model.objects.exists():
            return False
        return True

@admin.register(PerjalananDinas)
class PerjalananDinasAdmin(admin.ModelAdmin):
    list_display = ('nomor_spd', 'surat_tugas', 'pegawai', 'jenis_perjalanan', 'jenis_transportasi', 'status', 'tanggal_berangkat', 'durasi_hari')
    list_filter = ('surat_tugas', 'jenis_perjalanan', 'jenis_transportasi', 'tujuan_provinsi', 'status', 'tahun_sbm', 'tanggal_berangkat')
    search_fields = ('nomor_spd', 'pegawai__nama', 'pegawai__nip', 'surat_tugas__nomor_surat')
    readonly_fields = ('nomor_spd',) # Nomor SPD otomatis, tidak bisa diedit manual
    fields = (
        'nomor_spd', 'surat_tugas', 'pegawai', 'status',
        'tanggal_berangkat', 'tanggal_kembali',
        'tempat_berangkat', 'tempat_tujuan', 'tujuan_provinsi', 'tahun_sbm',
        'maksud_perjalanan',
        'anggaran', 'jenis_perjalanan', 'jenis_transportasi', 'tidak_menginap'
    )
    inlines = [BerkasPerjalananPenginapanInline, BerkasPerjalananTransportasiInline, BerkasPerjalananNonNominalInline, BiayaPerjalananInline]

    class Media:
        js = ('js/admin_filter.js',)

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context.update({
            'show_save_and_add_another': False,
        })
        return super().render_change_form(request, context, add, change, form_url, obj)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Menambahkan informasi tambahan untuk tombol kustom di template admin
        extra_context['show_generate_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def durasi_hari(self, obj):
        return obj.durasi_hari
    durasi_hari.short_description = 'Durasi (Hari)'
