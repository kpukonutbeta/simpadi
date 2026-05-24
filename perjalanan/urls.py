from django.urls import path
from . import views

app_name = 'perjalanan'

urlpatterns = [
    path('api/get-pegawai/', views.get_pegawai_by_surat_tugas, name='get_pegawai_ajax'),
    path('api/hitung-estimasi/', views.hitung_estimasi_ajax, name='hitung_estimasi_ajax'),
    path('api/get-standar-biaya-tiket/', views.get_standar_biaya_tiket_ajax, name='get_standar_biaya_tiket_ajax'),
    path('api/get-plafon-penginapan/', views.get_standar_biaya_penginapan_ajax, name='get_standar_biaya_penginapan_ajax'),
    path('ajukan/<uuid:surat_tugas_id>/', views.ajukan_perjadin, name='ajukan_perjadin'),
    path('generate-spd-bulk/', views.generate_spd_bulk, name='generate_spd_bulk'),
    path('riwayat/', views.riwayat_perjadin, name='riwayat_perjadin'),
    path('kalender/', views.kalender_perjadin, name='kalender_perjadin'),
    path('resolusi-konflik/', views.resolusi_konflik, name='resolusi_konflik'),
    path('spd/<int:perjadin_id>/download-excel/', views.download_spd_excel, name='download_spd_excel'),
    path('spd/<int:perjadin_id>/download-rincian/', views.download_rincian_excel, name='download_rincian_excel'),
    path('spd/<int:perjadin_id>/download-kwitansi/', views.download_kwitansi_excel, name='download_kwitansi_excel'),
]
