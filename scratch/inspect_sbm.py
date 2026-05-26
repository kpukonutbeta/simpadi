import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from master_data.models import StandarBiaya

print("Standar Biaya for Golongan III:")
for sbm in StandarBiaya.objects.filter(golongan='III'):
    print(f"ID: {sbm.id}, Golongan: {sbm.golongan}, Posisi: {sbm.posisi_jabatan}, Plafon: {sbm.plafon_penginapan}, Tahun: {sbm.tahun}")

print("\nStandar Biaya for Posisi Jabatan ES_III:")
for sbm in StandarBiaya.objects.filter(posisi_jabatan='ES_III'):
    print(f"ID: {sbm.id}, Golongan: {sbm.golongan}, Posisi: {sbm.posisi_jabatan}, Plafon: {sbm.plafon_penginapan}, Tahun: {sbm.tahun}")

