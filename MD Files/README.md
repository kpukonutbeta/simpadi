# Sistem Informasi Perjalanan Dinas (SIMPADI)

Sistem otomasi administrasi perjalanan dinas untuk meningkatkan akurasi perhitungan biaya dan manajemen berkas.

## 🏛️ Arsitektur Teknologi
- **Backend Utama:** Python Django
- **Database:** Supabase (PostgreSQL)
- **Engine Tambahan:** Google Apps Script (GAS)
- **Penyimpanan Berkas:** Google Drive & Supabase Storage
- **Pelaporan:** Google Spreadsheet

## 📂 Struktur Fitur (Dokumentasi Terpisah)
1. [Master Data & Standar Biaya](features/01_master_data.md) - Fondasi tarif SBM/SSH.
2. [Otomasi Perhitungan & Validasi](features/02_kalkulator_biaya.md) - Logika anti-salah hitung.
3. [Manajemen Berkas & Checklist](features/03_manajemen_berkas.md) - Integrasi Google Drive & GAS.
4. [Reporting & Output Dokumen](features/04_pelaporan.md) - Export Spreadsheet & PDF.
5. [Manajemen Surat Tugas](features/05_Manajemen_Surat_Tugas.md) - Pengelolaan surat tugas dan validasi penugasan.
6. [Sistem Autentikasi & Role](features/00_user_auth.md) - Pengaturan hak akses Admin dan Pegawai.

## 🔄 Alur Integrasi Django-GAS
1. Django mengirimkan JSON data transaksi ke Web App GAS.
2. GAS memproses template Google Docs/Sheets.
3. GAS menyimpan file ke Drive dan mengembalikan link ke Django/Supabase.