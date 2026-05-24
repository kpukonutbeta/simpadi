import os
import django
import sys

sys.path.append('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from master_data.models import StandarBiaya

print("=== SBM GOLONGAN DISTINCT ===")
for sb in StandarBiaya.objects.values('golongan').distinct():
    print(sb)
