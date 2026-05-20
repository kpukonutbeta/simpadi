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
    list_display = ('nomor_surat', 'tgl_surat', 'perihal', 'tanggal_berangkat', 'tanggal_kembali', 'tempat_tujuan')
    search_fields = ('nomor_surat', 'perihal', 'tempat_tujuan')
    filter_horizontal = ('pegawai',)
    actions = ['terbitkan_spd_action']
    fieldsets = (
        (None, {
            'fields': ('nomor_surat', 'perihal', 'tgl_surat', 'file_path', 'pegawai', 'status')
        }),
        ('Pengaturan Perjalanan Dinas dari Surat Tugas', {
            'fields': (
                'tanggal_berangkat', 'tanggal_kembali', 'tempat_berangkat', 'tempat_tujuan',
                'tujuan_provinsi', 'tahun_sbm', 'maksud_perjalanan', 'anggaran',
                'jenis_perjalanan', 'jenis_transportasi'
            )
        }),
    )

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
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

class BerkasPenginapanInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        total_malam_hotel = 0
        total_malam_lumpsum = 0
        total_malam_fb_luar = 0
        total_malam_fb_dalam = 0
        
        parent = self.instance
        durasi = parent.durasi_hari
        if parent.jenis_perjalanan in ['fullboard_luar', 'fullboard_dalam']:
            total_malam_perjalanan = 0
        else:
            total_malam_perjalanan = max(0, durasi - 1)
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.is_valid():
                continue
                
            jenis_berkas = form.cleaned_data.get('jenis_berkas')
            if jenis_berkas:
                kategori = jenis_berkas.kategori_biaya
                if kategori in ['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']:
                    malam = form.cleaned_data.get('malam_menginap') or 1
                    if kategori == 'penginapan' and jenis_berkas.nominal_biaya:
                        total_malam_hotel += malam
                    elif kategori == 'penginapan_30':
                        total_malam_lumpsum += malam
                    elif kategori == 'penginapan_fb_luar':
                        total_malam_fb_luar += malam
                    elif kategori == 'penginapan_fb_dalam':
                        total_malam_fb_dalam += malam
                        
        total_malam_claimed = total_malam_hotel + total_malam_lumpsum + total_malam_fb_luar + total_malam_fb_dalam
        if total_malam_claimed > total_malam_perjalanan:
            raise ValidationError(
                f"Total klaim penginapan ({total_malam_hotel} malam hotel + {total_malam_lumpsum} malam lumpsum + "
                f"{total_malam_fb_luar} malam FB luar + {total_malam_fb_dalam} malam FB dalam = {total_malam_claimed} malam) "
                f"melebihi batas malam perjalanan ({total_malam_perjalanan} malam)."
            )

class BerkasPerjalananPenginapanInline(admin.TabularInline):
    model = BerkasPerjalananPenginapan
    formset = BerkasPenginapanInlineFormSet
    fields = ('jenis_berkas', 'nominal', 'malam_menginap', 'keterangan', 'file', 'is_verified')
    extra = 1
    can_delete = True
    verbose_name = "Berkas Pendukung untuk Penginapan"
    verbose_name_plural = "Berkas Pendukung untuk Penginapan"

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            jenis_berkas__kategori_biaya__in=['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                kategori_biaya__in=['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']
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
            jenis_berkas__kategori_biaya='transportasi',
            jenis_berkas__nominal_biaya=True
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                kategori_biaya='transportasi',
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
        return super().get_queryset(request).filter(
            jenis_berkas__nominal_biaya=False
        ).exclude(
            jenis_berkas__kategori_biaya__in=['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                nominal_biaya=False
            ).exclude(
                kategori_biaya__in=['penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam']
            )
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
    list_filter = ('surat_tugas', 'surat_tugas__jenis_perjalanan', 'surat_tugas__jenis_transportasi', 'surat_tugas__tujuan_provinsi', 'status', 'surat_tugas__tahun_sbm', 'surat_tugas__tanggal_berangkat')
    search_fields = ('nomor_spd', 'pegawai__nama', 'pegawai__nip', 'surat_tugas__nomor_surat')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('nomor_spd', 'surat_tugas', 'pegawai', 'get_detail_perjalanan_table')
        return ('nomor_spd',)
    
    def get_fieldsets(self, request, obj=None):
        if obj:
            return (
                ('Informasi Utama SPD', {
                    'fields': ('nomor_spd', 'surat_tugas', 'pegawai', 'status')
                }),
                ('Rincian Perjalanan Dinas', {
                    'fields': ('get_detail_perjalanan_table',),
                }),
            )
        return (
            (None, {
                'fields': ('nomor_spd', 'surat_tugas', 'pegawai', 'status')
            }),
        )
    
    inlines = [BerkasPerjalananPenginapanInline, BerkasPerjalananTransportasiInline, BerkasPerjalananNonNominalInline, BiayaPerjalananInline]

    def get_detail_perjalanan_table(self, obj):
        if not obj or not obj.surat_tugas:
            return "-"
        
        st = obj.surat_tugas
        tgl_berangkat = st.tanggal_berangkat.strftime('%d-%m-%Y') if st.tanggal_berangkat else '-'
        tgl_kembali = st.tanggal_kembali.strftime('%d-%m-%Y') if st.tanggal_kembali else '-'
        prov_nama = st.tujuan_provinsi.nama if st.tujuan_provinsi else '-'
        jenis_perjadin = st.get_jenis_perjalanan_display() if st.jenis_perjalanan else '-'
        jenis_trans = st.get_jenis_transportasi_display() if st.jenis_transportasi else '-'
        maksud_perjadin = st.maksud_perjalanan or '-'
        kode_dipa = st.anggaran.kode_dipa if st.anggaran else '-'
        nama_kegiatan = st.anggaran.nama_kegiatan if st.anggaran else '-'
        
        html = f"""
        <style>
            .field-get_detail_perjalanan_table label {{
                display: none !important;
            }}
            .field-get_detail_perjalanan_table .readonly {{
                display: block !important;
                margin-left: 0 !important;
                float: none !important;
                width: 100% !important;
                padding-left: 0 !important;
            }}
        </style>
        <table style="width: 100%; border-collapse: collapse; margin-top: 5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; width: 20%; background: #f8fafc; border-right: 1px solid #e2e8f0;">Tanggal Berangkat</td>
                <td style="padding: 10px 14px; color: #1e293b; width: 30%; border-right: 1px solid #e2e8f0;">{tgl_berangkat}</td>
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; width: 20%; background: #f8fafc; border-right: 1px solid #e2e8f0;">Tanggal Kembali</td>
                <td style="padding: 10px 14px; color: #1e293b; width: 30%;">{tgl_kembali}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Tempat Berangkat</td>
                <td style="padding: 10px 14px; color: #1e293b; border-right: 1px solid #e2e8f0;">{st.tempat_berangkat or '-'}</td>
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Tempat Tujuan</td>
                <td style="padding: 10px 14px; color: #1e293b;">{st.tempat_tujuan or '-'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Provinsi (SBM)</td>
                <td style="padding: 10px 14px; color: #1e293b; border-right: 1px solid #e2e8f0;">{prov_nama}</td>
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Tahun SBM</td>
                <td style="padding: 10px 14px; color: #1e293b;">{st.tahun_sbm or '-'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Jenis Perjalanan Dinas</td>
                <td style="padding: 10px 14px; color: #1e293b; border-right: 1px solid #e2e8f0;">{jenis_perjadin}</td>
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Jenis Transportasi</td>
                <td style="padding: 10px 14px; color: #1e293b;">{jenis_trans}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Maksud Perjalanan</td>
                <td colspan="3" style="padding: 10px 14px; color: #1e293b;">{maksud_perjadin}</td>
            </tr>
            <tr>
                <td style="padding: 10px 14px; font-weight: 700; color: #475569; background: #f8fafc; border-right: 1px solid #e2e8f0;">Sumber Anggaran</td>
                <td colspan="3" style="padding: 10px 14px; color: #1e293b;">
                    <strong>{kode_dipa}</strong> - {nama_kegiatan}
                </td>
            </tr>
        </table>
        """
        return mark_safe(html)
    get_detail_perjalanan_table.short_description = "Rincian Perjalanan Dinas"

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
