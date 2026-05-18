# Fitur 00: Sistem Autentikasi & Manajemen Role

## 👤 Konsep User & Role
Sistem menggunakan model User tunggal yang memiliki atribut peran. Seorang Admin secara otomatis adalah Pegawai, namun memiliki hak akses tambahan ke modul verifikasi dan master data.

### 1. Role: Pegawai (User)
- **Akses:** Dashboard Pribadi.
- **Fitur:**
    - Melihat daftar Surat Tugas di mana namanya tercantum.
    - Mengajukan rincian biaya perjalanan dinas berdasarkan Surat Tugas tersebut.
    - Mengunggah bukti berkas (Tiket, Hotel, Laporan) via GAS/Drive.
    - Memantau status verifikasi (Draft, Pending, Approved, Rejected).

### 2. Role: Admin (Subbag Keuangan/Verifikator)
- **Akses:** Dashboard Admin + Dashboard Pegawai.
- **Fitur:**
    - Kelola Master Data (SBM, Pegawai, Anggaran/DIPA).
    - Kelola Surat Tugas (Upload & Assign Pegawai).
    - Verifikasi pengajuan biaya dari Pegawai (Checklist kelengkapan & Akurasi hitung).
    - Cetak dokumen resmi (SPPD, Rincian Riil) setelah status 'Approved'.

## 🔑 Logika "Admin sebagai Pegawai"
Dalam Django, kita menggunakan `AbstractUser` dengan flag `is_staff` untuk Admin. 
- Jika `is_staff = True`: User dapat masuk ke menu manajemen keuangan.
- Saat Admin tersebut melakukan perjalanan dinas, ia masuk ke menu **"Pengajuan Saya"** sebagai Pegawai biasa untuk menginput datanya sendiri. Hal ini memastikan alur audit tetap konsisten (Admin tidak memverifikasi datanya sendiri jika memungkinkan, atau minimal ada jejak rekamnya).

## 🔒 Security & Constraints
- **Self-Service:** Pegawai hanya bisa melihat dan mengedit data perjalanan dinas milik mereka sendiri (`filter(pegawai=request.user)`).
- **Read-Only:** Setelah status pengajuan menjadi 'Approved' atau 'Processed', Pegawai tidak dapat lagi mengubah data/berkas kecuali Admin membuka kunci (Unlock).
- **Validation:** Pegawai hanya bisa memilih Surat Tugas yang aktif dan di mana nama mereka terdaftar di dalamnya.