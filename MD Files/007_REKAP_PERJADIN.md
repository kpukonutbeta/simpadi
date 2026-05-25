# Fitur Rekap Perjalanan Dinas (Tabel Preview & Excel Export)

Membuat menu baru **Rekap Perjadin** untuk menampilkan rekapitulasi data perjalanan dinas per pegawai dalam rentang tanggal tertentu, dalam bentuk tabel HTML (preview) dan fitur *Export* ke Excel berdasarkan format `media/Pokok Perjadin.xlsx`.

> [!IMPORTANT]
> Fitur ini diakses khusus untuk Admin. Tampilan awal adalah preview tabel HTML, kemudian admin bisa mendownload Excel jika data dirasa sudah sesuai.

## Proposed Changes

### `simpadi_core/urls.py` & `templates/base.html`
- Menambahkan tautan menu **Rekap Perjadin** di atas menu **Kalender Perjadin** pada sidebar atau list menu utama admin.

### `perjalanan/urls.py`
- Endpoint baru: `path('rekap/', views.rekap_perjadin_view, name='rekap_perjadin')`

### `perjalanan/views.py`
- Fungsi `rekap_perjadin_view`:
  - **Menerima Parameter Filter (GET)**: `pegawai_id`, `start_date`, dan `end_date`.
  - **Query Data**: Mengambil data `PerjalananDinas` berdasarkan filter yang dipilih. (Status default: `APPROVED`).
  - **Format Data Rekapitulasi**: Memproses breakdown biaya dari masing-masing `PerjalananDinas` untuk menghasilkan data tabular (Uang Harian, Transport, Tiket, Penginapan).
  - **Aksi Preview (HTML)**: Mengirim data tersebut ke template untuk dirender menjadi tabel HTML yang format kolomnya mirip Excel.
  - **Aksi Export (Excel)**: Jika ada argumen `?export=excel`, sistem menggunakan *openpyxl* untuk membuka file `media/Pokok Perjadin.xlsx`, menulis data dari hasil filter pada baris ke-8 dan seterusnya, kemudian mengembalikannya sebagai `HttpResponse` attachment (file `.xlsx`).

### `templates/perjalanan/admin_rekap_perjadin.html`
#### [NEW] `templates/perjalanan/admin_rekap_perjadin.html`
- **Filter Section**: Dropdown untuk memilih *Pegawai* (dengan fitur pencarian), dan *Input Date* untuk *Tanggal Awal* & *Tanggal Akhir*. Terdapat tombol "Tampilkan Data".
- **Action Section**: Tombol "Export Excel" (akan muncul jika data tersedia) yang melakukan submit parameter filter saat ini ditambah `export=excel`.
- **Table View**: Tabel lebar yang bisa di-_scroll_ secara horizontal untuk merender semua kolom dari Excel format (No, OPD, Jenis Perjadin, Keperluan, Tanggal Berangkat-Kembali, Uang Harian, Transport, Penginapan, dsb) secara persis. Desain menggunakan style CSS minimalis yang rapi.

## Verification Plan

### Manual Verification
1. Login sebagai Admin.
2. Navigasi ke menu "Rekap Perjadin" di sidebar.
3. Pilih salah satu Pegawai dan set *Tanggal Awal* serta *Tanggal Akhir*.
4. Klik **Tampilkan Data**. Tabel HTML di bawahnya harus termuat dengan rincian biaya yang akurat.
5. Klik **Export Excel**. Unduhan file Excel akan dimulai.
6. Buka file Excel dan verifikasi kesesuaian nilai kolom (Tiket, Penginapan, Harian, dsb) dengan format asli dari `Pokok Perjadin.xlsx`.
