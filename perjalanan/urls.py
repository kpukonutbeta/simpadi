from django.urls import path
from . import views

app_name = 'perjalanan'

urlpatterns = [
    path('api/get-pegawai/', views.get_pegawai_by_surat_tugas, name='get_pegawai_ajax'),
    path('api/hitung-estimasi/', views.hitung_estimasi_ajax, name='hitung_estimasi_ajax'),
    path('ajukan/<uuid:surat_tugas_id>/', views.ajukan_perjadin, name='ajukan_perjadin'),
    path('generate-spd-bulk/', views.generate_spd_bulk, name='generate_spd_bulk'),
    path('riwayat/', views.riwayat_perjadin, name='riwayat_perjadin'),
]
