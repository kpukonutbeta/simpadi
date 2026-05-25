# INSTRUKSI: Testing Fix Nominal Hotel

## Ringkasan Perubahan
Perbaikan telah dibuat pada `/static/js/admin_filter.js` untuk mengatasi masalah:
- **Masalah**: User tidak bisa mengedit nominal hotel karena JavaScript terus override nilai dengan auto-calculate dari plafon
- **Solusi**: Tambahkan flag tracking untuk mendeteksi apakah user sudah manual edit nominal

## File yang Diubah
- `/static/js/admin_filter.js` - Ditambahkan 6 modifikasi untuk mencegah nominal override

## Cara Testing

### Setup
1. Pastikan Django server sudah berjalan: `python manage.py runserver 0.0.0.0:8002`
2. Buka browser ke: `http://localhost:8002/admin/perjalanan/perjalanandinas/`
3. Buka existing Perjalanan Dinas atau buat baru untuk testing
4. Scroll ke section "Berkas Pendukung untuk Penginapan"

### Test Scenario 1: Auto-Populate & Manual Edit (CRITICAL)
```
STEP 1: Add Berkas Penginapan
  - Klik "+ Tambah Berkas Penginapan"
  - Pilih jenis berkas: "BILL/INVOICE HOTEL/PENGINAPAN" atau "FULLBOARD LUAR KOTA"
  
STEP 2: Pilih Hotel via Modal
  - Klik button "Ubah Akomodasi" (icon pensil)
  - Modal "Pilih Segment & Tanggal Menginap" akan muncul
  - Isi: Provinsi, Tanggal Check-in, Tanggal Check-out
  - Klik "Simpan Akomodasi"
  
STEP 3: Verifikasi Auto-Populate
  - Lihat field "Nominal Biaya (Rp)"
  - Harus sudah terisi dengan nilai otomatis dari plafon
  - EXPECTED: Nilai = plafon * jumlah_malam
  
STEP 4: USER EDIT (CRITICAL TEST)
  - Klik pada field Nominal Biaya
  - Hapus nilai existing
  - Ketik nilai baru, contoh: "999999"
  - Tekan Tab atau click area lain untuk trigger blur
  
STEP 5: Verifikasi Nilai Tetap
  - EXPECTED: Nilai tetap "999999" (TIDAK di-reset ke auto-calculate)
  - CRITICAL: Jika nilai kembali ke nilai auto-calculate, FIX BELUM BEKERJA
  
✓ TEST PASSED: Nominal bisa diedit dan tetap sesuai input user
✗ TEST FAILED: Nominal di-reset kembali ke nilai auto-calculate
```

### Test Scenario 2: Change Hotel Selection After Manual Edit
```
STEP 1: Ikuti scenario 1 hingga user sudah edit nominal ke "999999"

STEP 2: Ubah Pilihan Hotel
  - Klik button "Ubah Akomodasi" lagi
  - Modal akan muncul dengan data sebelumnya
  - Ubah pilihan (provinsi/tanggal berbeda)
  - Klik "Simpan Akomodasi"
  
STEP 3: Verifikasi Nominal TIDAK Override
  - Lihat field Nominal Biaya
  - EXPECTED: Tetap "999999" (TIDAK berubah ke plafon baru)
  - CRITICAL: Ini membuktikan user-edited flag bekerja
  
✓ TEST PASSED: Nominal tetap user-edited value
✗ TEST FAILED: Nominal berubah ke plafon hotel baru
```

### Test Scenario 3: Fresh Selection (Tidak Ada Manual Edit)
```
STEP 1: Buat Entry Baru
  - Klik "+ Tambah Berkas Penginapan"
  - Pilih jenis berkas
  
STEP 2: Pilih Hotel (Pertama Kali)
  - Klik "Ubah Akomodasi"
  - Isi form dan "Simpan Akomodasi"
  
STEP 3: Ubah Pilihan Hotel (Tanpa Manual Edit)
  - Klik "Ubah Akomodasi" lagi
  - Pilih hotel/provinsi BERBEDA
  - Klik "Simpan Akomodasi"
  
STEP 4: Verifikasi Nominal AUTO-CALCULATE
  - EXPECTED: Nominal berubah ke plafon baru
  - Ini menunjukkan auto-populate masih bekerja saat belum ada manual edit
  
✓ TEST PASSED: Auto-populate bekerja saat belum ada manual edit
✗ TEST FAILED: Nominal tidak berubah (auto-populate rusak)
```

### Test Scenario 4: Tiket Pesawat (Bonus)
```
STEP 1: Buat Berkas Tiket
  - Klik "+ Tambah Berkas Transportasi"
  - Pilih jenis berkas: "TIKET PESAWAT ROUND TRIP" (atau variant lain)
  
STEP 2: Pilih Rute
  - Klik "Ubah Rute"
  - Pilih Kota Asal, Kota Tujuan, Kelas
  - Klik "Simpan Rute"
  
STEP 3: Verifikasi Auto-Populate Nominal Tiket
  - Nominal Biaya harus terisi otomatis
  
STEP 4: Edit Nominal Tiket
  - Ubah nominal ke nilai custom
  
STEP 5: Pilih Rute Berbeda
  - Nominal HARUS TETAP nilai custom (tidak di-reset)
  
✓ TEST PASSED: Tiket nominal juga tidak di-override
✗ TEST FAILED: Tiket nominal di-reset
```

### Test Scenario 5: Dinamis Row Addition
```
STEP 1: Dalam section "Berkas Pendukung untuk Penginapan"
  - Sudah ada beberapa row
  - Klik "Tambah Berkas Penginapan" (add another)
  
STEP 2: New Row Ditambahkan
  - Pilih hotel untuk row baru
  - Edit nominal di row baru
  
STEP 3: Verifikasi Dinamis Row
  - Nominal di row baru juga tidak boleh di-override
  
✓ TEST PASSED: Dinamis rows juga dilindungi
✗ TEST FAILED: Dinamis row nominal tidak terlindungi
```

## Debug di Browser Console

Jika ada issue, buka Dev Tools (F12) dan jalankan:

```javascript
// COPY PASTE semua kode ini ke console

// Test 1: Cek apakah listener sudah attach
const nominalInputs = document.querySelectorAll('input[name$="-nominal"]');
console.log(`Total nominal inputs: ${nominalInputs.length}`);

nominalInputs.forEach((input, idx) => {
    console.log(`[${idx}]`, {
        id: input.id,
        value: input.value,
        listenerAttached: input.dataset.nominalListenerAttached,
        userEdited: input.dataset.nominalUserEdited,
        readOnly: input.readOnly
    });
});

// Test 2: Manual attach listener ke first input
if (nominalInputs[0]) {
    console.log('\nManually testing listener on first input...');
    const inp = nominalInputs[0];
    
    console.log('Before manual edit:', inp.dataset.nominalUserEdited);
    
    inp.value = '777777';
    inp.dispatchEvent(new Event('input', { bubbles: true }));
    
    console.log('After manual edit:', inp.dataset.nominalUserEdited);
}
```

## Hal-hal yang Perlu Diperhatikan

### ✓ Yang Harus Bekerja
- [x] Auto-populate nominal saat hotel pertama kali dipilih
- [x] User bisa edit nominal setelah auto-populate
- [x] Nominal tidak berubah ketika user edit
- [x] Saat hotel berubah dan user sudah manual edit, nominal TETAP
- [x] Saat hotel berubah dan user BELUM manual edit, nominal AUTO-UPDATE
- [x] Fitur bekerja untuk tiket pesawat juga
- [x] Fitur bekerja untuk row yang dynamis ditambahkan
- [x] No console errors atau warnings baru

### ✗ Tanda-tanda Issue
- [ ] Nominal reset ke auto-value saat user mengetik
- [ ] "Cannot read property 'dataset'" error di console
- [ ] Nominal field menjadi disabled/readonly setelah edit
- [ ] Auto-populate tidak bekerja sama sekali
- [ ] Multiple listeners attached (event triggered multiple times)

## Rollback Instruction (Jika Ada Problem)

Jika ada problem yang tidak bisa diperbaiki:

```bash
# Revert ke versi sebelumnya (jika ada git)
git checkout -- static/js/admin_filter.js

# Atau manual restore backup (jika ada)
cp static/js/admin_filter.js.backup static/js/admin_filter.js

# Refresh browser cache
# Hard refresh: Ctrl+Shift+R (Windows/Linux) atau Cmd+Shift+R (Mac)
```

## Reporting Issue

Jika test FAILED, please provide:
1. Browser & version (Chrome, Firefox, Safari, etc)
2. Django version: `python manage.py --version`
3. Exact step yang fail
4. Console error messages (screenshot atau copy paste)
5. Value yang diperoleh vs expected value

## Success Criteria

✓ FIX BERHASIL jika:
- User bisa mengedit nominal setelah auto-populate
- Nilai tetap sesuai input user (tidak di-reset)
- Auto-populate masih bekerja pada first-time selection
- No console errors
- No regression pada fitur lain

