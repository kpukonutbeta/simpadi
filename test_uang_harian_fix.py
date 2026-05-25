import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from perjalanan.models import PerjalananDinas

p = PerjalananDinas.objects.get(id=23)

# Update database to match screenshot: Day 1 and 8 are 'luar_kota', Day 2-7 are 'diklat'
for h in p.harian_details.all():
    if h.hari_ke in [1, 8]:
        h.jenis_harian = 'luar_kota'
    else:
        h.jenis_harian = 'diklat'
    h.save()

# Refresh from db and calculate
p.refresh_from_db()
b = p.biaya
breakdown = b.calculate_breakdown()

print("Perjalanan:", p.surat_tugas.jenis_perjalanan)
print("Transit dari DB:")
for h in p.harian_details.all().order_by('hari_ke'):
    print(f"  Hari {h.hari_ke}: {h.jenis_harian}")

print("\nBreakdown Uang Harian:")
for h in breakdown['harian_breakdown']:
    print(f"  Hari {h['hari_ke']}: {h['jenis_harian']} -> Rate: {h['rate']}")

print(f"\nTotal Uang Harian Riil: {breakdown['uang_harian_riil']}")
