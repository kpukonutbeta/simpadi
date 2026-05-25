import os
import django
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from django.test import Client
from perjalanan.models import PerjalananDinas

c = Client(); from django.contrib.auth import get_user_model; c.force_login(get_user_model().objects.first())
p = PerjalananDinas.objects.get(id=23)

payload = {
    'tanggal_berangkat': p.surat_tugas.tanggal_berangkat.isoformat(),
    'tanggal_kembali': p.surat_tugas.tanggal_kembali.isoformat(),
    'tujuan_provinsi': p.surat_tugas.tujuan_provinsi.id,
    'jenis_perjalanan': p.surat_tugas.jenis_perjalanan,
    'jenis_transportasi': p.surat_tugas.jenis_transportasi,
    'tahun_sbm': p.surat_tugas.tahun_sbm,
    'pegawai_id': p.pegawai.id,
    'harian': [
        {'hari_ke': 1, 'provinsi_id': p.surat_tugas.tujuan_provinsi.id, 'jenis_harian': 'luar_kota'},
        {'hari_ke': 2, 'provinsi_id': p.surat_tugas.tujuan_provinsi.id, 'jenis_harian': 'diklat'},
        {'hari_ke': 3, 'provinsi_id': p.surat_tugas.tujuan_provinsi.id, 'jenis_harian': 'diklat'},
    ]
}

response = c.post('/perjalanan/api/hitung-estimasi/', data=json.dumps(payload), content_type='application/json')
print("Status:", response.status_code)
data = response.json()
print("Uang Harian:", data.get('uang_harian_riil'))
for item in data.get('breakdown_categories', {}).get('lumpsum_harian', {}).get('items', []):
    print(" ", item['perihal'], "->", item['harga'], "x", item['kuantitas'])
