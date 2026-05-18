# Fitur 03: Manajemen Berkas & Integrasi Google Drive

## Deskripsi
Mengelola bukti fisik digital dan checklist kelengkapan administrasi.

## Alur Kerja (Django + GAS)
1. **Upload Bukti:** User upload scan tiket/kuitansi di interface Django.
2. **Relay ke GAS:** Django meneruskan file ke Google Apps Script.
3. **Storage:** GAS menyimpan file ke folder spesifik di Google Drive dengan format: `[TAHUN]/[BULAN]/[NIP]_[NAMA]/`.
4. **Link Back:** GAS mengirimkan ID File Drive ke Django untuk disimpan di Supabase.

## Checklist Kelengkapan
- [ ] Surat Tugas
- [ ] SPPD (Telah dicap)
- [ ] Bukti Transport (Tiket/Boarding Pass)
- [ ] Bukti Penginapan (Bill Hotel)
- [ ] Laporan Hasil Perjalanan
