#!/usr/bin/env python
"""Detailed test for PDF quality and content"""

import os
import sys
import django
import tempfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
sys.path.insert(0, '/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi')
django.setup()

from perjalanan.models import PerjalananDinas
from django.test import RequestFactory
from perjalanan.views import download_rincian_excel
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(is_staff=False).first()
factory = RequestFactory()

print('Detailed PDF Validation Test')
print('=' * 60)

perjadin = PerjalananDinas.objects.first()
if not perjadin:
    print('❌ No PerjalananDinas found')
    sys.exit(1)

print(f'Testing with: ID {perjadin.id} - {perjadin.pegawai.nama}')
print()

request = factory.get(f'/perjalanan/spd/{perjadin.id}/download-rincian/')
request.user = user

response = download_rincian_excel(request, perjadin.id)

print(f'Status Code: {response.status_code}')
print(f'Content-Type: {response.get("Content-Type")}')
print(f'Content-Disposition: {response.get("Content-Disposition")}')
print(f'Content Size: {len(response.content)} bytes')
print()

# Verify PDF signature
pdf_signature = response.content[:5]
print(f'File Signature (hex): {pdf_signature.hex()}')
if pdf_signature.startswith(b'%PDF'):
    print('✅ Valid PDF signature found!')
else:
    print('❌ Invalid PDF signature!')

# Write to temp file for manual inspection
with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
    f.write(response.content)
    temp_path = f.name

print(f'✅ Sample PDF saved to: {temp_path}')
print('   (You can open this file to verify the content looks correct)')
print()

# Check for minimal PDF structure
has_eof = response.content.endswith(b'%%EOF')
has_root = b'/Root' in response.content
has_stream = b'stream' in response.content

print('PDF Structure Check:')
print(f'  EOF Marker: {"✅" if has_eof else "⚠️"}')
print(f'  /Root Object: {"✅" if has_root else "⚠️"}')
print(f'  Stream Content: {"✅" if has_stream else "⚠️"}')
print()

if has_eof and has_root and has_stream:
    print('✅ PDF structure looks valid!')
else:
    print('⚠️  PDF structure may have issues')

print('=' * 60)

