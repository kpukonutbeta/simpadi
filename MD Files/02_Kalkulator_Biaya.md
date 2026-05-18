# Fitur 02: Otomasi Perhitungan & Validasi

## Deskripsi
Mesin penghitung otomatis untuk menghilangkan kalkulasi manual oleh staf keuangan.

## Logika Utama
1. **Perhitungan Hari:** Otomatis menghitung selisih tanggal berangkat dan kembali (Durasi = n+1).
2. **Kalkulasi Lumpsum:** `Total Uang Harian = Durasi x Tarif Harian (SBM)`.
3. **Validasi At-Cost:**
    - Jika `Biaya Riil > Plafon SBM`, maka sistem otomatis melakukan *capping* ke nilai maksimal plafon.
    - User tetap bisa input biaya riil, tapi nilai yang "Dapat Dibayarkan" dikunci oleh sistem.
4. **Deteksi Overlap:** Peringatan jika satu NIP memiliki dua perjalanan dinas di tanggal yang bersinggungan.
