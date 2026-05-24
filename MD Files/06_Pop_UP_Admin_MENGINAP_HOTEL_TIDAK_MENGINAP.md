tidak terjadi apa-apa saat saya pilih jenis berkas penginapan. kita fokus bikin implementasi lagi yang baru tanpa lihat history git yang sudah lalu. terlalu lambat.

kita mulai dengan admin dahulu.

pada intinya jenis berkas pendukung penginapan apapun yang dipilih akan memicu pop up hotel.  

pilih SBM provinsi , provinsi SBM hanya mencakup provinsi yang ada di detail transit.

ada inputan tanggal checkin dan ada tanggal checkout lalu ada inputan teks keterangan yang bisa diisi dengan nama hotel.

ada tombol simpan dan tombol batal.

saat disimpan, nominal akan otomatis terisi dengan plafon dari hotel sesuai dengan provinsi, golongan dan posisi jabatan pegawai di data Standar Biaya Masukan (SBM) Golongan/Pejabat Eselon.

inputan teks keterangan yang ada di pop up sebelumnya akan otomatis mengisi kolom keterangan di form agar bisa terbaca oleh user admin. sementara data provinsi SBM, tanggal checkin, tanggal Checkout disimpan dalam format tertentu di hidden input text. kedua input text baik keterangan yang tampil maupun yang hidden akan disimpan sebagai satu keteranga (concat dengan format tertentu) yang nanti pada saat diload bisa dengan mudah diparsing lagi.

Provinsi SBM tanggal checkin dan checkout terlihat sebagai tampilan label di atas inputan select jenis berkas