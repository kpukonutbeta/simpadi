import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpadi_core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

c = Client()
c.force_login(get_user_model().objects.first())

response = c.get('/admin/perjalanan/perjalanandinas/23/change/')
with open('admin_page.html', 'w') as f:
    f.write(response.content.decode('utf-8'))
