from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
import datetime

from master_data.models import Pegawai, Provinsi, Kota, StandarBiaya, Anggaran, JenisBerkas, StandarBiayaTiket
from perjalanan.models import PerjalananDinas, SuratTugas, BiayaPerjalanan, BerkasPerjalanan, parse_tiket_keterangan

User = get_user_model()

class TiketPesawatTestCase(TestCase):
    def setUp(self):
        # Create user & pegawai
        self.user = User.objects.create_user(email="test@kpu.go.id", username="testuser", password="password123")
        self.pegawai = Pegawai.objects.create(
            nip="199001012015011001",
            nama="Ahmad Yani",
            email="test@kpu.go.id",
            golongan="III/a",
            jabatan="Staf Teknis",
            user=self.user
        )

        # Create master data
        self.provinsi_asal = Provinsi.objects.create(nama="SULAWESI TENGGARA")
        self.provinsi_tujuan = Provinsi.objects.create(nama="DKI JAKARTA")
        
        self.kota_asal = Kota.objects.create(nama="KENDARI", provinsi=self.provinsi_asal)
        self.kota_tujuan = Kota.objects.create(nama="JAKARTA", provinsi=self.provinsi_tujuan)

        # Standar Biaya Tiket SBM
        self.sbm_tiket = StandarBiayaTiket.objects.create(
            kota_asal=self.kota_asal,
            kota_tujuan=self.kota_tujuan,
            kelas=StandarBiayaTiket.KelasTiket.EKONOMI,
            nominal=Decimal("3000000") # 3,000,000 IDR
        )

        # Standar Biaya Harian/Penginapan/Transportasi
        self.sbm = StandarBiaya.objects.create(
            provinsi=self.provinsi_tujuan,
            golongan="III/a",
            tahun=2024,
            uang_harian=Decimal("370000"),
            plafon_penginapan=Decimal("1000000"),
            uang_representasi=Decimal("150000"),
            plafon_transportasi=Decimal("500000")
        )

        # Anggaran
        self.anggaran = Anggaran.objects.create(
            kode_dipa="076.01.2.123456/2026",
            nama_kegiatan="Dukungan Operasional KPU Konawe Utara",
            pagu=Decimal("100000000"),
            sisa_pagu=Decimal("100000000")
        )

        # Jenis Berkas
        self.jenis_tiket = JenisBerkas.objects.create(
            nama="TIKET PESAWAT",
            wajib=False,
            nominal_biaya=True,
            kategori_biaya=JenisBerkas.KategoriBiaya.TRANSPORTASI_PESAWAT
        )

        self.jenis_taksi = JenisBerkas.objects.create(
            nama="STRUK TAKSI",
            wajib=False,
            nominal_biaya=True,
            kategori_biaya=JenisBerkas.KategoriBiaya.TRANSPORTASI
        )

        # Surat Tugas
        self.surat_tugas = SuratTugas.objects.create(
            nomor_surat="001/ST/KPU-KU/V/2026",
            perihal="Rapat Koordinasi Nasional",
            tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25),
            tanggal_kembali=datetime.date(2026, 5, 28),
            tempat_berangkat="Konawe Utara",
            tempat_tujuan="Jakarta",
            tujuan_provinsi=self.provinsi_tujuan,
            tahun_sbm=2024,
            anggaran=self.anggaran,
            jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        self.surat_tugas.pegawai.add(self.pegawai)

        # Perjalanan Dinas (SPD)
        self.perjadin = PerjalananDinas.objects.create(
            surat_tugas=self.surat_tugas,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

    def test_parse_tiket_keterangan(self):
        # Test helper parsing function
        # Format: [SBM-TIKET:asal_id-tujuan_id-kelas:NamaAsal:NamaTujuan] | Keterangan bebas
        valid_tag = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:Kendari:Jakarta] | Tiket Dinas Pertama"
        asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(valid_tag)
        
        self.assertEqual(asal_id, self.kota_asal.id)
        self.assertEqual(tujuan_id, self.kota_tujuan.id)
        self.assertEqual(kelas, "ekonomi")
        self.assertEqual(nama_asal, "Kendari")
        self.assertEqual(nama_tujuan, "Jakarta")
        self.assertEqual(user_desc, "Tiket Dinas Pertama")

        # Test without description
        tag_no_desc = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:Kendari:Jakarta]"
        asal_id, tujuan_id, kelas, nama_asal, nama_tujuan, user_desc = parse_tiket_keterangan(tag_no_desc)
        self.assertEqual(user_desc, "")

        # Test invalid tags
        self.assertEqual(parse_tiket_keterangan("Bukan tiket"), (None, None, None, None, None, "Bukan tiket"))
        self.assertEqual(parse_tiket_keterangan(None), (None, None, None, None, None, ""))

    def test_biaya_perjalanan_save_capping_under_sbm(self):
        # Ticket cost: 2,500,000 (SBM limit is 3,000,000)
        # Should be covered entirely by the system (0 dana pribadi)
        tag = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pergi"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("2500000"),
            keterangan=tag
        )

        self.perjadin.biaya.refresh_from_db()
        # Transport cost = 2,500,000
        # Dana pribadi = 0
        self.assertEqual(self.perjadin.biaya.biaya_transportasi_riil, Decimal("2500000"))
        self.assertEqual(self.perjadin.biaya.transportasi_dana_pribadi, Decimal("0"))

    def test_biaya_perjalanan_save_capping_over_sbm(self):
        # Ticket cost: 3,500,000 (SBM limit is 3,000,000)
        # 3,000,000 should be covered, 500,000 should go to dana pribadi
        tag = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pergi"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3500000"),
            keterangan=tag
        )

        self.perjadin.biaya.refresh_from_db()
        self.assertEqual(self.perjadin.biaya.biaya_transportasi_riil, Decimal("3000000"))
        self.assertEqual(self.perjadin.biaya.transportasi_dana_pribadi, Decimal("500000"))

    def test_biaya_perjalanan_mixed_transport(self):
        # Plane Ticket: 3,500,000 (SBM: 3,000,000 -> 3,000,000 riil, 500,000 dana pribadi)
        # Taxi structure: 600,000 (Plafon transport: 500,000 -> 500,000 riil, 100,000 dana pribadi)
        tag = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pergi"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3500000"),
            keterangan=tag
        )
        
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_taksi,
            nominal=Decimal("600000"),
            keterangan="Taksi bandara"
        )

        self.perjadin.biaya.refresh_from_db()
        # Total riil transport = 3,000,000 + 500,000 = 3,500,000
        # Total dana pribadi transport = 500,000 + 100,000 = 600,000
        self.assertEqual(self.perjadin.biaya.biaya_transportasi_riil, Decimal("3500000"))
        self.assertEqual(self.perjadin.biaya.transportasi_dana_pribadi, Decimal("600000"))

    def test_api_get_standar_biaya_tiket(self):
        self.client.force_login(self.user)
        url = reverse("perjalanan:get_standar_biaya_tiket_ajax")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("routes", data)
        self.assertEqual(len(data["routes"]), 1)
        self.assertEqual(data["routes"][0]["kota_asal_nama"], "KENDARI")
        self.assertEqual(data["routes"][0]["nominal"], 3000000.0)

    def test_api_hitung_estimasi_ajax(self):
        self.client.force_login(self.user)
        url = reverse("perjalanan:hitung_estimasi_ajax")
        
        # Test estimating with 3,500,000 ticket
        tag = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA]"
        payload = {
            "tanggal_berangkat": "2026-05-25",
            "tanggal_kembali": "2026-05-28",
            "tujuan_provinsi": self.provinsi_tujuan.id,
            "jenis_transportasi": "umum",
            "jenis_perjalanan": "luar_kota",
            "tahun_sbm": 2024,
            "pegawai_id": self.pegawai.id,
            "berkas": [
                {
                    "jenis_berkas_id": self.jenis_tiket.id,
                    "nominal": 3500000,
                    "keterangan": tag
                }
            ]
        }
        
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 3,000,000 riil transport + 4 days * (370k harian + 150k representasi) = 3,000,000 + 2,080,000 = 5,080,000
        self.assertEqual(data["biaya_transportasi_riil"], 3000000.0)
        self.assertEqual(data["total_tidak_dibayarkan"], 500000.0)
        self.assertEqual(data["total_dibayarkan"], 5080000.0)

    def test_biaya_perjalanan_two_tickets_capped(self):
        # Ticket 1 cost: 3,500,000
        # Ticket 2 cost: 3,500,000
        # SBM limit is 3,000,000
        # Total cost is 7,000,000. The approved amount should be capped at 3,000,000 (the max SBM rate of the route).
        # The remaining 4,000,000 should go to dana pribadi.
        tag = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pergi"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3500000"),
            keterangan=tag
        )

        tag2 = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pulang"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3500000"),
            keterangan=tag2
        )

        self.perjadin.biaya.refresh_from_db()
        self.assertEqual(self.perjadin.biaya.biaya_transportasi_riil, Decimal("3000000"))
        self.assertEqual(self.perjadin.biaya.transportasi_dana_pribadi, Decimal("4000000"))

    def test_validation_limit_max_two_flight_tickets(self):
        # We can add 2 flight tickets
        tag1 = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pergi"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3000000"),
            keterangan=tag1
        )

        tag2 = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pulang"
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3000000"),
            keterangan=tag2
        )

        # Attempting to add a 3rd flight ticket should raise a ValidationError in clean()
        tag3 = f"[SBM-TIKET:{self.kota_asal.id}-{self.kota_tujuan.id}-ekonomi:KENDARI:JAKARTA] | Pergi Lagi"
        third_ticket = BerkasPerjalanan(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_tiket,
            nominal=Decimal("3000000"),
            keterangan=tag3
        )
        
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            third_ticket.clean()

