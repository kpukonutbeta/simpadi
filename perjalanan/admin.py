from django.contrib import admin
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe
from .models import (
    PerjalananDinas, BiayaPerjalanan, BerkasPerjalanan, SuratTugas,
    PengaturanNomorSPD, BerkasPerjalananPenginapan, BerkasPerjalananTransportasi, BerkasPerjalananNonNominal,
    HarianPerjalanan
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(db_field, models.FileField) and formfield:
            formfield.widget = AdminFileWidgetNewTab(attrs=formfield.widget.attrs)
        return formfield

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
    template = 'admin/perjalanan/biaya_inline.html'
    readonly_fields = ('get_rincian_detail',)
    fields = ('get_rincian_detail',)
    extra = 1
    max_num = 1
    can_delete = False

    def get_rincian_detail(self, obj):
        if not obj or not hasattr(obj, 'perjalanan') or not obj.perjalanan:
            return "-"
        try:
            bd = obj.calculate_breakdown()
        except Exception as e:
            return f"Gagal menghitung rincian: {e}"

        def fmt_rp(val):
            return f"Rp {val:,.0f}".replace(",", ".")

        categories = ['uang_harian', 'uang_representasi', 'biaya_penginapan', 'biaya_perjalanan']
        rows_html = []
        for cat_key in categories:
            cat_data = bd['breakdown_categories'].get(cat_key)
            if not cat_data:
                continue
            
            title = cat_data['title']
            items = cat_data.get('items', [])
            subtotal = cat_data.get('subtotal', 0)
            N = len(items)
            
            if N == 0:
                # Placeholder row
                rows_html.append(f"""
                <tr style="border-bottom: 1px solid #cbd5e1;">
                    <td rowspan="2" style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; font-weight: 700; color: #334155; background: #f8fafc; vertical-align: top;">
                        {title}
                    </td>
                    <td style="border: 1px solid #cbd5e1; padding: 0.75rem; text-align: center; color: #94a3b8;">-</td>
                    <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; color: #94a3b8; font-style: italic;">Tidak ada</td>
                    <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; color: #94a3b8;">Rp 0</td>
                    <td style="border: 1px solid #cbd5e1; padding: 0.75rem; text-align: center; color: #94a3b8;">0</td>
                    <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; color: #94a3b8;">Rp 0</td>
                    <td style="border: 1px solid #cbd5e1; padding: 0.5rem; text-align: center;">-</td>
                </tr>
                """)
            else:
                for idx, item in enumerate(items):
                    rowspan_td = ""
                    if idx == 0:
                        rowspan_td = f"""
                        <td rowspan="{N + 1}" style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; font-weight: 700; color: #334155; background: #f8fafc; vertical-align: top;">
                            {title}
                        </td>
                        """
                    
                    file_td = "-"
                    if item.get('file_url'):
                        file_td = f"""
                        <a href="{item['file_url']}" target="_blank" style="display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.35rem 0.75rem; font-size: 0.75rem; font-weight: 600; background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); color: #0369a1; border: 1px solid #7dd3fc; border-radius: 0.375rem; text-decoration: none; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
                            Berkas
                        </a>
                        """
                    
                    rows_html.append(f"""
                    <tr style="border-bottom: 1px solid #cbd5e1;">
                        {rowspan_td}
                        <td style="border: 1px solid #cbd5e1; padding: 0.75rem; text-align: center;">{item['no']}</td>
                        <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem;">{item['keterangan']}</td>
                        <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right;">{fmt_rp(item['harga'])}</td>
                        <td style="border: 1px solid #cbd5e1; padding: 0.75rem; text-align: center;">{item['kuantitas']}</td>
                        <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right;">{fmt_rp(item['total'])}</td>
                        <td style="border: 1px solid #cbd5e1; padding: 0.5rem; text-align: center;">{file_td}</td>
                    </tr>
                    """)
            
            # Subtotal row
            rows_html.append(f"""
            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
                <td colspan="4" style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: #475569;">
                    Subtotal {title}
                </td>
                <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: #0f172a;">
                    {fmt_rp(subtotal)}
                </td>
                <td style="border: 1px solid #cbd5e1; padding: 0.75rem;"></td>
            </tr>
            """)

        total_dibayarkan = bd.get('total_dibayarkan', 0)
        total_tidak_dibayarkan = bd.get('total_dana_pribadi', 0)

        # Append Grand Totals directly inside tbody
        rows_html.append(f"""
        <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
            <td colspan="5" style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: #475569;">
                TOTAL DIBAYARKAN
            </td>
            <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: #0f172a;">
                {fmt_rp(total_dibayarkan)}
            </td>
            <td style="border: 1px solid #cbd5e1; padding: 0.75rem;"></td>
        </tr>
        """)

        unpaid_str = fmt_rp(total_tidak_dibayarkan) if total_tidak_dibayarkan > 0 else "-"
        unpaid_style = "color: red;" if total_tidak_dibayarkan > 0 else ""
        unpaid_label_color = "#dc2626" if total_tidak_dibayarkan > 0 else "#475569"
        unpaid_val_color = "#dc2626" if total_tidak_dibayarkan > 0 else "#0f172a"

        rows_html.append(f"""
        <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; {unpaid_style}">
            <td colspan="5" style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: {unpaid_label_color};">
                TIDAK DIBAYARKAN
            </td>
            <td style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: {unpaid_val_color};">
                {unpaid_str}
            </td>
            <td style="border: 1px solid #cbd5e1; padding: 0.75rem;"></td>
        </tr>
        """)

        rows_str = "".join(rows_html)

        html = f"""
        <div style="overflow-x: auto; margin-bottom: 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <table class="spreadsheet-table" style="width: 100%; border-collapse: collapse; font-size: 13px; border: 1px solid #cbd5e1;">
                <thead>
                    <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: left; font-weight: 700; color: #334155; width: 20%;">Perihal</th>
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem; text-align: center; font-weight: 700; color: #334155; width: 5%;">No</th>
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: left; font-weight: 700; color: #334155; width: 35%;">Keterangan</th>
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: #334155; width: 12%;">Harga</th>
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem; text-align: center; font-weight: 700; color: #334155; width: 8%;">Banyak</th>
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: right; font-weight: 700; color: #334155; width: 12%;">Total</th>
                        <th style="border: 1px solid #cbd5e1; padding: 0.75rem 1rem; text-align: center; font-weight: 700; color: #334155; width: 8%;">Berkas Pendukung</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_str}
                </tbody>
            </table>
        </div>
        """
        return mark_safe(html)
    get_rincian_detail.short_description = "Rincian Detail SBM"

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
            jenis_berkas__kategori_biaya__in=['transportasi', 'transportasi_pesawat']
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                kategori_biaya__in=['transportasi', 'transportasi_pesawat']
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
            jenis_berkas__kategori_biaya__in=[
                'penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam',
                'transportasi', 'transportasi_pesawat'
            ]
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jenis_berkas":
            kwargs["queryset"] = JenisBerkas.objects.filter(
                nominal_biaya=False
            ).exclude(
                kategori_biaya__in=[
                    'penginapan', 'penginapan_30', 'penginapan_fb_luar', 'penginapan_fb_dalam',
                    'transportasi', 'transportasi_pesawat'
                ]
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

from .forms import HarianPerjalananForm

class HarianPerjalananInline(admin.TabularInline):
    model = HarianPerjalanan
    form = HarianPerjalananForm
    extra = 0
    can_delete = False
    fields = ('tanggal_display', 'tanggal', 'provinsi', 'jenis_harian')
    readonly_fields = ('tanggal_display',)
    verbose_name = "Detail Transit Perjalanan Dinas"
    verbose_name_plural = "Detail Transit Perjalanan Dinas"

    def tanggal_display(self, obj):
        if obj and obj.tanggal:
            from django.utils.formats import date_format
            return date_format(obj.tanggal, "d F Y")
        return "-"
    tanggal_display.short_description = "Tanggal"

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
    
    inlines = [
        HarianPerjalananInline,
        BerkasPerjalananPenginapanInline,
        BerkasPerjalananTransportasiInline,
        BerkasPerjalananNonNominalInline,
        BiayaPerjalananInline
    ]

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
        js = ('js/admin_loader.js',)

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
