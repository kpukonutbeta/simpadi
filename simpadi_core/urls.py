"""
URL configuration for simpadi_core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('perjalanan/', include('perjalanan.urls')),
    path('', include('core.urls')),
]

# Admin Customization
admin.site.site_header = "SIMPADI [Admin]"
admin.site.site_title = "SIMPADI Admin Portal"
admin.site.index_title = "Selamat Datang di SIMPADI"

# Custom section order in admin sidebar:
# 1. Perjalanan Dinas  2. Master_Data  3. Core  4. Auth
_APP_ORDER = ['perjalanan', 'master_data', 'core', 'auth']

_original_get_app_list = admin.site.__class__.get_app_list

def _ordered_get_app_list(self, request, app_label=None):
    app_list = _original_get_app_list(self, request, app_label)
    for app in app_list:
        if app.get('app_label') == 'perjalanan':
            if not any(m.get('object_name') == 'KalenderPerjadin' for m in app.get('models', [])):
                app['models'].append({
                    'name': 'Kalender Perjadin',
                    'object_name': 'KalenderPerjadin',
                    'admin_url': '/perjalanan/kalender/',
                    'view_only': True,
                })
        for model in app.get('models', []):
            if model.get('object_name') == 'PerjalananDinas':
                model['name'] = 'Manajemen SPD'
        if app.get('app_label') == 'master_data':
            model_order = [
                'Pegawai', 'Provinsi', 'Kota', 'Anggaran', 'JenisBerkas', 'PejabatPenandatangan',
                'DokumenSBM', 'StandarBiaya', 'StandarBiayaTiket'
            ]
            def model_sort_key(model_dict):
                obj_name = model_dict.get('object_name')
                try:
                    return model_order.index(obj_name)
                except ValueError:
                    return len(model_order)
            app['models'] = sorted(app['models'], key=model_sort_key)
    def sort_key(app):
        label = app.get('app_label', '').lower()
        try:
            return _APP_ORDER.index(label)
        except ValueError:
            return len(_APP_ORDER)
    return sorted(app_list, key=sort_key)

admin.site.__class__.get_app_list = _ordered_get_app_list

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
