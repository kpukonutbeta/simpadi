# Fitur 05: Manajemen Surat Tugas & Validasi Penugasan (Multi-Role)

## 📝 Deskripsi
Fitur ini adalah gerbang utama aplikasi. Admin (Subbag Keuangan) bertugas mendaftarkan dasar hukum (Surat Tugas), sementara Pegawai yang namanya tercantum dalam surat tersebut bertugas melakukan pengajuan mandiri (Self-Service) untuk rincian perjalanan mereka.

## 🛠️ Fungsi Utama
1. **Pusat Data Surat Tugas:** Admin mengelola database nomor surat, perihal, dan unggahan fisik surat.
2. **Assignment & Restriction:** Admin memetakan pegawai mana saja yang berhak melakukan perjalanan dinas berdasarkan surat tersebut.
3. **Trigger Pengajuan:** Surat tugas yang diunggah akan muncul secara otomatis di dashboard "Tugas Saya" milik pegawai yang bersangkutan.

## 🗄️ Skema Data (Database)

### 1. Table: `surat_tugas` (Supabase/PostgreSQL)
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Primary Key unik. |
| `nomor_surat` | String | Nomor resmi surat tugas. |
| `perihal` | Text | Isi atau maksud penugasan. |
| `tgl_surat` | Date | Tanggal surat diterbitkan. |
| `file_path` | String | URL file PDF asli di Google Drive. |
| `status` | Enum | [Active, Completed, Cancelled] |

### 2. Table: `surat_tugas_pegawai` (Mapping Table)
| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Primary Key. |
| `surat_tugas_id` | UUID (FK) | Referensi ke Surat Tugas. |
| `pegawai_id` | UUID (FK) | Referensi ke User/Pegawai. |

## 🔄 Alur Kerja (Workflow)

### A. Sisi Admin (Otorisasi)
1. Admin (Subbag Keuangan) membuat entitas **Surat Tugas** baru.
2. Admin mengunggah PDF surat dan memilih daftar **Pegawai** yang ditugaskan.
3. Admin menyimpan data. Pada tahap ini, pengajuan biaya belum ada (masih kosong).

### B. Sisi Pegawai (Pengajuan Mandiri)
1. Pegawai login dan melihat daftar Surat Tugas di dashboard mereka.
2. Pegawai mengklik Surat Tugas tersebut untuk **"Ajukan Perjadin"**.
3. Pegawai mengisi detail riil: tanggal keberangkatan, tanggal kepulangan, dan estimasi biaya berdasarkan SBM yang muncul otomatis.
4. Pegawai melengkapi berkas (boarding pass, kuitansi hotel) setelah perjalanan selesai.

### C. Sisi Admin (Verifikasi Akhir)
1. Admin menerima notifikasi bahwa pengajuan dari Pegawai telah lengkap.
2. Admin memverifikasi kesesuaian antara data yang diinput pegawai dengan bukti fisik di Google Drive.
3. Admin mengubah status menjadi **"Approved"** untuk mencetak dokumen pembayaran.

## 🚀 Integrasi Google Apps Script (GAS)
- **Shared Folder:** GAS menyimpan PDF Surat Tugas di folder yang dapat diakses (Read-Only) oleh pegawai yang ditugaskan untuk referensi mereka.
- **Auto-Fill:** Data dari Surat Tugas otomatis mengisi field "Nomor Surat" pada form pengajuan pegawai agar tidak terjadi typo.

## ⚠️ Aturan Bisnis (Business Rules)
- **Pre-Condition:** Pegawai tidak bisa menginput perjalanan dinas jika Admin belum mengupload Surat Tugas yang mencantumkan nama mereka.
- **Unique Submission:** Satu Pegawai hanya bisa membuat **satu rincian pengajuan** untuk **satu Surat Tugas**. Mencegah double claim.
- **Role Isolation:** Pegawai tidak bisa melihat Surat Tugas orang lain yang tidak melibatkan dirinya.
- **Admin Exception:** Jika Admin melakukan perjalanan dinas, ia harus menginput datanya melalui dashboard Pegawai (sebagai pemohon) dan diverifikasi oleh rekan admin lainnya atau atasan.