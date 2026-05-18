# Fitur 01: Master Data & Standar Biaya

## Deskripsi
Mengelola data dasar yang menjadi acuan perhitungan agar tidak terjadi kesalahan input tarif.

## Komponen Data
- **Data Pegawai:** NIP, Nama, Golongan (I-IV), Jabatan.
- **Tabel SBM (Standar Biaya Masukan):**
    - Tarif Uang Harian per Provinsi.
    - Plafon Biaya Penginapan per Golongan/Provinsi.
    - Tarif Uang Representasi (untuk Pejabat).
- **Data Anggaran:** Kode akun DIPA dan sisa pagu.

## Aturan Bisnis
- Tarif hotel otomatis terkunci berdasarkan kombinasi **Golongan Pegawai** + **Provinsi Tujuan**.
- Perubahan tarif SBM dilakukan melalui modul admin dan langsung berdampak pada pengajuan baru.
