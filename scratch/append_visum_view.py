import os

views_file = "/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/perjalanan/views.py"
content_to_append = """
@login_required
def download_visum_excel(request, perjadin_id):
    perjadin = get_object_or_404(PerjalananDinas, id=perjadin_id)
    surat_tugas = perjadin.surat_tugas
    
    months = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
        7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }

    def format_date_indo(date_obj):
        if not date_obj:
            return ""
        return f"{date_obj.day} {months[date_obj.month]} {date_obj.year}"

    ppk = PejabatPenandatangan.objects.filter(jabatan='PPK').first()
    nama_ppk = ppk.nama if ppk else "-"
    nip_ppk = ppk.nip if ppk else "-"

    sekretaris = PejabatPenandatangan.objects.filter(jabatan='SEKRETARIS').first()
    nama_sekretaris = sekretaris.nama if sekretaris else "-"
    nip_sekretaris = sekretaris.nip if sekretaris else "-"

    from core.models import GlobalConfig
    kotakab_opd_config = GlobalConfig.objects.filter(key='KOTAKAB_OPD').first()
    kotakab_opd = kotakab_opd_config.value if kotakab_opd_config else "WANGGUDU"
    
    nama_opd_config = GlobalConfig.objects.filter(key='NAMA_OPD').first()
    nama_opd = nama_opd_config.value if nama_opd_config else "KPU PROVINSI SULAWESI TENGGARA"

    mapping = {
        '{{GLOBAL_KOTAKAB_OPD}}': kotakab_opd,
        '{{GLOBAL_NAMA_OPD}}': nama_opd,
        '{{NAMA_PPK}}': nama_ppk,
        '{{NIP_PPK}}': nip_ppk,
        '{{NAMA_SEKRETARIS}}': nama_sekretaris,
        '{{NIP_SEKRETARIS}}': nip_sekretaris,
        '{{TANGGAL_SPD}}': format_date_indo(perjadin.created_at.date() if perjadin.created_at else None),
    }

    template_path = os.path.join(settings.BASE_DIR, 'static', 'template_documents', 'visum_SPD.xlsx')
    
    import zipfile
    import io

    output_buffer = io.BytesIO()
    
    with zipfile.ZipFile(template_path, 'r') as zin:
        with zipfile.ZipFile(output_buffer, 'w') as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                if item.filename == 'xl/sharedStrings.xml' or item.filename.startswith('xl/worksheets/'):
                    text = content.decode('utf-8')
                    for key, val in mapping.items():
                        text = text.replace(key, str(val))
                    content = text.encode('utf-8')
                zout.writestr(item, content)

    response = HttpResponse(
        output_buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Visum_{perjadin.pegawai.nama}.xlsx"'
    return response
"""

with open(views_file, "a") as f:
    f.write(content_to_append)
