import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from perjalanan.models import PerjalananDinas
from decimal import Decimal

p = PerjalananDinas.objects.get(id=23)
b = p.biaya
print(f"Perjalanan: {p.surat_tugas.jenis_perjalanan}")
print(f"Transit:")
for h in p.harian_details.all():
    print(f"  Hari {h.hari_ke}: {h.jenis_harian} (Provinsi: {h.provinsi})")

breakdown = b.calculate_breakdown()
print("Breakdown Uang Harian:")
for h in breakdown['harian_breakdown']:
    print(f"  Hari {h['hari_ke']}: {h['jenis_harian']} -> Rate: {h['rate']}")

print(f"Total Uang Harian Riil: {breakdown['uang_harian_riil']}")
