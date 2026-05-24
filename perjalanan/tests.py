from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
import datetime
import json

from master_data.models import Pegawai, Provinsi, Kota, StandarBiaya, StandarBiayaHarian, Anggaran, JenisBerkas, StandarBiayaTiket, Golongan, DokumenSBM
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
            plafon_penginapan=Decimal("1000000"),
            uang_representasi=Decimal("150000")
        )

        # Standar Biaya Harian (universal)
        self.sbm_harian = StandarBiayaHarian.objects.create(
            provinsi=self.provinsi_tujuan,
            tahun=2024,
            uang_harian=Decimal("370000"),
            uang_harian_dalam_kota=Decimal("148000"),
            uang_harian_diklat=Decimal("111000")
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
        # Total riil transport = 3,000,000 (tiket capped) + 600,000 (taxi, no plafon cap) = 3,600,000
        # Total dana pribadi transport = 500,000 (tiket over SBM) + 0 = 500,000
        self.assertEqual(self.perjadin.biaya.biaya_transportasi_riil, Decimal("3600000"))
        self.assertEqual(self.perjadin.biaya.transportasi_dana_pribadi, Decimal("500000"))

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

    def test_transport_non_nominal_validation(self):
        # Set nominal_biaya to False on self.jenis_taksi
        self.jenis_taksi.nominal_biaya = False
        self.jenis_taksi.save()

        # Try to clean/save a taksi ticket without nominal
        taksi_ticket = BerkasPerjalanan(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_taksi,
            nominal=None,
            keterangan="Struk Taksi Draft"
        )
        
        # This should NOT raise a ValidationError
        try:
            taksi_ticket.clean()
        except ValidationError as e:
            self.fail(f"ValidationError raised unexpectedly for non-nominal transport document: {e}")

    def test_jenis_berkas_required(self):
        # Try to clean/save a supporting document with jenis_berkas = None
        invalid_berkas = BerkasPerjalanan(
            perjalanan=self.perjadin,
            jenis_berkas=None,
            nominal=Decimal("100000"),
            keterangan="Orphaned supporting document test"
        )
        
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            invalid_berkas.clean()
        
        self.assertIn('jenis_berkas', ctx.exception.message_dict)

    def test_optional_nominal_hotel_calculated(self):
        # Create a JenisBerkas with nominal_biaya = False, kategori_biaya = penginapan
        jenis_hotel_optional = JenisBerkas.objects.create(
            nama="HOTEL OPSIONAL",
            wajib=False,
            nominal_biaya=False,
            kategori_biaya=JenisBerkas.KategoriBiaya.PENGINAPAN
        )
        
        # Create BerkasPerjalanan with nominal and 2 nights
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=jenis_hotel_optional,
            nominal=Decimal("250000"),
            malam_menginap=2,
            keterangan="Hotel Bonte Test"
        )
        
        # Calculate breakdown
        self.perjadin.biaya.refresh_from_db()
        breakdown = self.perjadin.biaya.calculate_breakdown()
        
        # The nominal cost should be calculated even though nominal_biaya is False
        self.assertEqual(self.perjadin.biaya.biaya_penginapan_riil, Decimal("250000"))
        self.assertEqual(breakdown['biaya_penginapan_riil'], Decimal("250000"))


class TransitHarianOverrideTestCase(TestCase):
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

        # Create provinces
        self.provinsi_asal = Provinsi.objects.create(nama="SULAWESI TENGGARA")
        self.provinsi_tujuan = Provinsi.objects.create(nama="DKI JAKARTA")

        # Standar Biaya SBM for Sultra
        self.sbm_sultra = StandarBiaya.objects.create(
            provinsi=self.provinsi_asal,
            golongan="III/a",
            tahun=2024,
            plafon_penginapan=Decimal("800000"),
            uang_representasi=Decimal("0")
        )

        # Standar Biaya SBM for Jakarta
        self.sbm_jakarta = StandarBiaya.objects.create(
            provinsi=self.provinsi_tujuan,
            golongan="III/a",
            tahun=2024,
            plafon_penginapan=Decimal("1000000"),
            uang_representasi=Decimal("150000")
        )

        # Standar Biaya Harian (universal)
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi_asal, tahun=2024,
            uang_harian=Decimal("340000"),
            uang_harian_dalam_kota=Decimal("136000"),
            uang_harian_diklat=Decimal("102000")
        )
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi_tujuan, tahun=2024,
            uang_harian=Decimal("370000"),
            uang_harian_dalam_kota=Decimal("148000"),
            uang_harian_diklat=Decimal("111000")
        )

        # Anggaran
        self.anggaran = Anggaran.objects.create(
            kode_dipa="076.01.2.123456/2026",
            nama_kegiatan="Dukungan Operasional KPU Konawe Utara",
            pagu=Decimal("100000000"),
            sisa_pagu=Decimal("100000000")
        )

        # Surat Tugas (4 days total)
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.surat_tugas = SuratTugas.objects.create(
            nomor_surat="002/ST/KPU-KU/V/2026",
            perihal="Rapat Koordinasi Transit",
            tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25),
            tanggal_kembali=datetime.date(2026, 5, 28),
            tempat_berangkat="Konawe Utara",
            tempat_tujuan="Jakarta",
            tujuan_provinsi=self.provinsi_tujuan,
            tahun_sbm=2024,
            anggaran=self.anggaran,
            jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
            file_path=SimpleUploadedFile("dummy.pdf", b"dummy content")
        )
        self.surat_tugas.pegawai.add(self.pegawai)

        # Perjalanan Dinas (SPD)
        self.perjadin = PerjalananDinas.objects.create(
            surat_tugas=self.surat_tugas,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

    def test_sync_harian_details_creates_correct_rows(self):
        # Durasi is 4 days, check that 4 harian records are created automatically.
        from perjalanan.models import HarianPerjalanan
        harian_list = HarianPerjalanan.objects.filter(perjalanan=self.perjadin).order_by('hari_ke')
        self.assertEqual(harian_list.count(), 4)
        
        # Verify default SBM province is DKI Jakarta
        for record in harian_list:
            self.assertEqual(record.provinsi, self.provinsi_tujuan)
            self.assertEqual(record.jenis_harian, HarianPerjalanan.JenisHarian.LUAR_KOTA)

    def test_transit_override_calculations(self):
        # Default total: 4 days * 370k = 1,480,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("1480000"))

        # Override day 1 to Sulawesi Tenggara
        from perjalanan.models import HarianPerjalanan
        day1_record = HarianPerjalanan.objects.get(perjalanan=self.perjadin, hari_ke=1)
        day1_record.provinsi = self.provinsi_asal  # Sulawesi Tenggara (340k)
        day1_record.save()  # Triggers self.perjalanan.biaya.save()

        self.perjadin.biaya.refresh_from_db()
        # New total should be: 1 day Sultra (340k) + 3 days Jakarta (370k) = 340k + 1,110k = 1,450,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("1450000"))

    def test_ajax_transit_override(self):
        self.client.force_login(self.user)
        url = reverse("perjalanan:hitung_estimasi_ajax")
        
        # Payload with day 1 and 2 overridden to Sulawesi Tenggara, day 3 and 4 default/Jakarta
        payload = {
            "tanggal_berangkat": "2026-05-25",
            "tanggal_kembali": "2026-05-28",
            "tujuan_provinsi": self.provinsi_tujuan.id,
            "jenis_transportasi": "umum",
            "jenis_perjalanan": "luar_kota",
            "tahun_sbm": 2024,
            "pegawai_id": self.pegawai.id,
            "harian": [
                {
                    "hari_ke": 1,
                    "provinsi_id": self.provinsi_asal.id,
                    "jenis_harian": "luar_kota"
                },
                {
                    "hari_ke": 2,
                    "provinsi_id": self.provinsi_asal.id,
                    "jenis_harian": "luar_kota"
                },
                {
                    "hari_ke": 3,
                    "provinsi_id": self.provinsi_tujuan.id,
                    "jenis_harian": "luar_kota"
                },
                {
                    "hari_ke": 4,
                    "provinsi_id": self.provinsi_tujuan.id,
                    "jenis_harian": "luar_kota"
                }
            ]
        }
        
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 2 days * 340k + 2 days * 370k = 680k + 740k = 1,420,000 riil harian
        self.assertEqual(data["uang_harian_riil"], 1420000.0)
        # Check daily breakdown in response
        breakdown_list = data["harian_breakdown"]
        self.assertEqual(len(breakdown_list), 4)
        self.assertEqual(breakdown_list[0]["rate"], 340000.0)
        self.assertEqual(breakdown_list[1]["rate"], 340000.0)
        self.assertEqual(breakdown_list[2]["rate"], 370000.0)
        self.assertEqual(breakdown_list[3]["rate"], 370000.0)

    def test_standard_employee_harian_fields_disabled(self):
        # Log in as a standard user (not staff)
        self.client.force_login(self.user)
        url = reverse("perjalanan:ajukan_perjadin", args=[self.surat_tugas.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check that 'provinsi' and 'jenis_harian' are disabled in the context formset fields
        harian_formset = response.context['harian_formset']
        for form in harian_formset:
            self.assertTrue(form.fields['provinsi'].disabled)
            self.assertTrue(form.fields['jenis_harian'].disabled)

    def test_admin_staff_harian_fields_enabled(self):
        # Make the user staff (admin)
        self.user.is_staff = True
        self.user.save()
        
        self.client.force_login(self.user)
        url = reverse("perjalanan:ajukan_perjadin", args=[self.surat_tugas.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check that 'provinsi' and 'jenis_harian' are NOT disabled
        harian_formset = response.context['harian_formset']
        for form in harian_formset:
            self.assertFalse(form.fields['provinsi'].disabled)
            self.assertFalse(form.fields['jenis_harian'].disabled)

    def test_employee_harian_view_rendering(self):
        # Log in as a standard user
        self.client.force_login(self.user)
        url = reverse("perjalanan:ajukan_perjadin", args=[self.surat_tugas.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify read-only text is present and widgets are wrapped in display: none
        html = response.content.decode('utf-8')
        self.assertIn(self.provinsi_tujuan.nama, html)
        self.assertIn('display: none;', html)
        self.assertIn('Lihat Detail Transit per Hari', html)


    def test_admin_harian_view_rendering(self):
        # Make the user staff (admin)
        self.user.is_staff = True
        self.user.save()
        
        self.client.force_login(self.user)
        url = reverse("perjalanan:ajukan_perjadin", args=[self.surat_tugas.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify Atur Detail Transit button is present
        html = response.content.decode('utf-8')
        self.assertIn('Atur Detail Transit per Hari', html)

    def test_all_new_jenis_harian_choices(self):
        # Let's test the calculations of the new daily allowance choices
        from perjalanan.models import HarianPerjalanan
        
        # 1. Luar Kota (Luar Kota rate, e.g. 370k)
        day1 = HarianPerjalanan.objects.get(perjalanan=self.perjadin, hari_ke=1)
        day1.jenis_harian = HarianPerjalanan.JenisHarian.LUAR_KOTA
        day1.provinsi = self.provinsi_tujuan  # DKI JAKARTA
        day1.save()
        
        # 2. Dalam Kota (> 8 Jam) (40% of SBM, 40% of 370k = 148k)
        day2 = HarianPerjalanan.objects.get(perjalanan=self.perjadin, hari_ke=2)
        day2.jenis_harian = HarianPerjalanan.JenisHarian.DALAM_KOTA
        day2.provinsi = self.provinsi_tujuan
        day2.save()
        
        # 3. Diklat (30% of SBM, 30% of 370k = 111k)
        day3 = HarianPerjalanan.objects.get(perjalanan=self.perjadin, hari_ke=3)
        day3.jenis_harian = HarianPerjalanan.JenisHarian.DIKLAT
        day3.provinsi = self.provinsi_tujuan
        day3.save()
        
        # 4. Rapat/Pertemuan Halfday (Fullboard dalam SBM, e.g. 90k)
        day4 = HarianPerjalanan.objects.get(perjalanan=self.perjadin, hari_ke=4)
        day4.jenis_harian = HarianPerjalanan.JenisHarian.HALFDAY
        day4.provinsi = self.provinsi_tujuan
        day4.save()
        
        self.perjadin.biaya.refresh_from_db()
        # Expected total: 370k (Luar Kota) + 148k (Dalam Kota) + 111k (Diklat) + 0 (Halfday) = 629,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("629000"))
        
        # Also test Fullboard (should be Rp 0 as cost is covered by organizer)
        day4.jenis_harian = HarianPerjalanan.JenisHarian.FULLBOARD
        day4.provinsi = self.provinsi_tujuan  # DKI JAKARTA (luar)
        day4.save()
        
        self.perjadin.biaya.refresh_from_db()
        # Expected total: 370k (Luar Kota) + 148k (Dalam Kota) + 111k (Diklat) + 0 (Fullboard) = 629,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("629000"))
        
        # Fullboard for Sultra (home) should also be Rp 0
        day4.provinsi = self.provinsi_asal  # SULAWESI TENGGARA (home)
        day4.save()
        
        self.perjadin.biaya.refresh_from_db()
        # Expected total: 370k (Luar Kota) + 148k (Dalam Kota) + 111k (Diklat) + 0 (Fullboard) = 629,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("629000"))


class HotelSBMCappingTestCase(TestCase):
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

        # Create provinces
        self.provinsi_asal = Provinsi.objects.create(nama="SULAWESI TENGGARA")
        self.provinsi_tujuan = Provinsi.objects.create(nama="DKI JAKARTA")
        self.provinsi_transit = Provinsi.objects.create(nama="JAWA BARAT")

        # Standar Biaya SBM for Sultra
        self.sbm_sultra = StandarBiaya.objects.create(
            provinsi=self.provinsi_asal,
            golongan="III/a",
            tahun=2024,
            plafon_penginapan=Decimal("800000"),
            uang_representasi=Decimal("0")
        )

        # Standar Biaya SBM for Jakarta
        self.sbm_jakarta = StandarBiaya.objects.create(
            provinsi=self.provinsi_tujuan,
            golongan="III/a",
            tahun=2024,
            plafon_penginapan=Decimal("1000000"),
            uang_representasi=Decimal("150000")
        )

        # Standar Biaya SBM for Jabar (Transit)
        self.sbm_jabar = StandarBiaya.objects.create(
            provinsi=self.provinsi_transit,
            golongan="III/a",
            tahun=2024,
            plafon_penginapan=Decimal("600000"),  # Jabar plafon hotel is 600.000 (lower than Jakarta's 1.000.000)
            uang_representasi=Decimal("0")
        )

        # Standar Biaya Harian (universal)
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi_asal, tahun=2024,
            uang_harian=Decimal("340000"),
            uang_harian_dalam_kota=Decimal("136000"),
            uang_harian_diklat=Decimal("102000")
        )
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi_tujuan, tahun=2024,
            uang_harian=Decimal("370000"),
            uang_harian_dalam_kota=Decimal("148000"),
            uang_harian_diklat=Decimal("111000")
        )
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi_transit, tahun=2024,
            uang_harian=Decimal("350000"),
            uang_harian_dalam_kota=Decimal("140000"),
            uang_harian_diklat=Decimal("105000")
        )

        # Anggaran
        self.anggaran = Anggaran.objects.create(
            kode_dipa="076.01.2.123456/2026",
            nama_kegiatan="Dukungan Operasional KPU Konawe Utara",
            pagu=Decimal("100000000"),
            sisa_pagu=Decimal("100000000")
        )

        # Surat Tugas (4 days total)
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.surat_tugas = SuratTugas.objects.create(
            nomor_surat="003/ST/KPU-KU/V/2026",
            perihal="Rapat Koordinasi Penginapan",
            tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25),
            tanggal_kembali=datetime.date(2026, 5, 28),
            tempat_berangkat="Konawe Utara",
            tempat_tujuan="Jakarta",
            tujuan_provinsi=self.provinsi_tujuan,
            tahun_sbm=2024,
            anggaran=self.anggaran,
            jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
            file_path=SimpleUploadedFile("dummy.pdf", b"dummy content")
        )
        self.surat_tugas.pegawai.add(self.pegawai)

        # Perjalanan Dinas (SPD)
        self.perjadin = PerjalananDinas.objects.create(
            surat_tugas=self.surat_tugas,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

        self.jenis_hotel = JenisBerkas.objects.create(
            nama="KUITANSI HOTEL",
            wajib=False,
            nominal_biaya=True,
            kategori_biaya=JenisBerkas.KategoriBiaya.PENGINAPAN
        )

    def test_auto_calculate_malam_menginap_from_tag(self):
        # Create a BerkasPerjalanan with an SBM-PENGINAPAN tag in keterangan
        # check-in: 2026-05-25, check-out: 2026-05-27 (2 nights)
        tag = f"[SBM-PENGINAPAN:2026-05-25:2026-05-27:2:{self.provinsi_transit.id}:{self.provinsi_transit.nama}] | Hotel Bandung"
        
        berkas = BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_hotel,
            nominal=Decimal("1500000"),
            keterangan=tag
        )
        
        # Verify that malam_menginap is automatically computed to 2
        self.assertEqual(berkas.malam_menginap, 2)

    def test_per_document_capping_jabar_sbm(self):
        # Plafon hotel in Jabar is 600.000/night.
        # Plafon hotel in Jakarta is 1.000.000/night.
        # We submit a hotel bill in Jabar for 2 nights with nominal 1.500.000 (750.000/night).
        # It should cap at 2 * 600.000 = 1.200.000, and 300.000 should be personal expense (dana pribadi).
        tag = f"[SBM-PENGINAPAN:2026-05-25:2026-05-27:2:{self.provinsi_transit.id}:{self.provinsi_transit.nama}] | Hotel Bandung"
        
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_hotel,
            nominal=Decimal("1500000"),
            keterangan=tag
        )

        self.perjadin.biaya.refresh_from_db()
        breakdown = self.perjadin.biaya.calculate_breakdown()
        
        self.assertEqual(self.perjadin.biaya.biaya_penginapan_riil, Decimal("1200000"))
        self.assertEqual(self.perjadin.biaya.penginapan_dana_pribadi, Decimal("300000"))
        self.assertEqual(breakdown['biaya_penginapan_riil'], Decimal("1200000"))
        self.assertEqual(breakdown['penginapan_dana_pribadi'], Decimal("300000"))

    def test_per_document_no_tag_fallback_to_destination(self):
        # We submit a hotel bill without any tag for 2 nights with nominal 2.500.000.
        # Since no tag is present, it falls back to the trip destination province SBM (Jakarta, 1.000.000/night).
        # Capping should be 2 * 1.000.000 = 2.000.000, and 500.000 should be personal expense (dana pribadi).
        BerkasPerjalanan.objects.create(
            perjalanan=self.perjadin,
            jenis_berkas=self.jenis_hotel,
            nominal=Decimal("2500000"),
            malam_menginap=2,
            keterangan="Hotel Jakarta No Tag"
        )

        self.perjadin.biaya.refresh_from_db()
        breakdown = self.perjadin.biaya.calculate_breakdown()
        
        self.assertEqual(self.perjadin.biaya.biaya_penginapan_riil, Decimal("2000000"))
        self.assertEqual(self.perjadin.biaya.penginapan_dana_pribadi, Decimal("500000"))


class BulkGenerateSPDTestCase(TestCase):
    def setUp(self):
        # Create a user and make them a superuser so staff_member_required and admin page views are satisfied
        self.user = User.objects.create_superuser(email="admin@kpu.go.id", username="adminuser", password="password123")
        self.client.force_login(self.user)

        # Create Pegawai
        self.pegawai1 = Pegawai.objects.create(
            nip="199001012015011001",
            nama="Ahmad Yani",
            email="test1@kpu.go.id",
            golongan="III/a",
            jabatan="Staf Teknis"
        )
        self.pegawai2 = Pegawai.objects.create(
            nip="199001012015011002",
            nama="Budi Santoso",
            email="test2@kpu.go.id",
            golongan="III/b",
            jabatan="Fungsional"
        )

        self.provinsi = Provinsi.objects.create(nama="DKI JAKARTA")
        self.anggaran = Anggaran.objects.create(
            kode_dipa="076.01.2.123456/2026",
            nama_kegiatan="Kegiatan Test",
            pagu=Decimal("100000000"),
            sisa_pagu=Decimal("100000000")
        )

        # Config nomor SPD
        from perjalanan.models import PengaturanNomorSPD
        self.config, _ = PengaturanNomorSPD.objects.get_or_create(
            id=1,
            defaults={'prefix_terakhir': 0, 'suffix_format': '/SPD/KPU-KU/V/2026'}
        )

        # Surat Tugas 1
        self.st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/KPU-KU/V/2026",
            perihal="Perjalanan Dinas A",
            tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25),
            tanggal_kembali=datetime.date(2026, 5, 28),
            tempat_berangkat="Konawe Utara",
            tempat_tujuan="Jakarta",
            tujuan_provinsi=self.provinsi,
            tahun_sbm=2024,
            anggaran=self.anggaran,
            jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        self.st1.pegawai.add(self.pegawai1, self.pegawai2)

        # Surat Tugas 2
        self.st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/KPU-KU/V/2026",
            perihal="Perjalanan Dinas B",
            tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25),
            tanggal_kembali=datetime.date(2026, 5, 28),
            tempat_berangkat="Konawe Utara",
            tempat_tujuan="Jakarta",
            tujuan_provinsi=self.provinsi,
            tahun_sbm=2024,
            anggaran=self.anggaran,
            jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        self.st2.pegawai.add(self.pegawai1)

    def test_generate_spd_bulk_success_and_skips_existing(self):
        # 1. First run: generate bulk for st1 and st2 (should create 3 PerjalananDinas)
        session = self.client.session
        session['selected_st_ids'] = [str(self.st1.id), str(self.st2.id)]
        session.save()

        url = reverse('perjalanan:generate_spd_bulk')
        response = self.client.post(url)
        
        # Verify success redirect to perjalanan admin list
        self.assertRedirects(response, '/admin/perjalanan/perjalanandinas/')
        
        # Verify PerjalananDinas instances created: st1 (2 pegawais) + st2 (1 pegawai) = 3 SPDs
        self.assertEqual(PerjalananDinas.objects.count(), 3)
        self.assertEqual(PerjalananDinas.objects.filter(surat_tugas=self.st1).count(), 2)
        self.assertEqual(PerjalananDinas.objects.filter(surat_tugas=self.st2).count(), 1)

        # 2. Second run: try generating bulk again when they already exist
        # It should skip gracefully without any errors
        session = self.client.session
        session['selected_st_ids'] = [str(self.st1.id), str(self.st2.id)]
        session.save()

        response = self.client.post(url)
        self.assertRedirects(response, '/admin/perjalanan/perjalanandinas/')
        
        # Count should remain 3, none should be added, skipped should work gracefully
        self.assertEqual(PerjalananDinas.objects.count(), 3)

    def test_nomor_spd_collision_resolution(self):
        # Set up a situation where the next prefix generated by config (which is 1)
        # already exists as a PerjalananDinas nomor_spd.
        collision_no = "1/SPD/KPU-KU/V/2026"
        PerjalananDinas.objects.create(
            surat_tugas=self.st1,
            pegawai=self.pegawai1,
            nomor_spd=collision_no,
            status=PerjalananDinas.Status.DRAFT
        )

        # Now, create a new PerjalananDinas without nomor_spd.
        # It should increment past 1 (since 1 is taken) and auto-assign 2.
        p2 = PerjalananDinas.objects.create(
            surat_tugas=self.st1,
            pegawai=self.pegawai2,
            status=PerjalananDinas.Status.DRAFT
        )

        self.assertEqual(p2.nomor_spd, "2/SPD/KPU-KU/V/2026")
        self.assertEqual(PerjalananDinas.objects.filter(nomor_spd="2/SPD/KPU-KU/V/2026").count(), 1)


class PerjalananKalenderTestCase(TestCase):
    def setUp(self):
        # Create normal employee user
        self.user = User.objects.create_user(email="pegawai@kpu.go.id", username="pegawaiuser", password="password123")
        self.pegawai = Pegawai.objects.create(
            nip="199501012019011001",
            nama="Bambang Pamungkas",
            email="pegawai@kpu.go.id",
            golongan="III/a",
            jabatan="Fungsional Umum",
            user=self.user
        )
        self.client.force_login(self.user)

        self.provinsi = Provinsi.objects.create(nama="DKI JAKARTA")
        self.anggaran = Anggaran.objects.create(
            kode_dipa="076.01.2.123456/2026",
            nama_kegiatan="Kegiatan Test",
            pagu=Decimal("100000000"),
            sisa_pagu=Decimal("100000000")
        )

        # Config nomor SPD
        from perjalanan.models import PengaturanNomorSPD
        PengaturanNomorSPD.objects.get_or_create(
            id=1,
            defaults={'prefix_terakhir': 0, 'suffix_format': '/SPD/KPU-KU/V/2026'}
        )

    def test_kalender_perjadin_render_no_trips(self):
        url = reverse('perjalanan:kalender_perjadin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kalender Perjalanan Dinas")
        self.assertFalse(response.context['has_overlaps'])
        self.assertEqual(len(response.context['overlaps']), 0)

    def test_kalender_perjadin_with_non_overlapping_trips(self):
        # Trip 1: May 1 to May 3
        st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/2026", perihal="Rakornas", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 3),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st1.pegawai.add(self.pegawai)
        PerjalananDinas.objects.create(surat_tugas=st1, pegawai=self.pegawai, status=PerjalananDinas.Status.APPROVED)

        # Trip 2: May 5 to May 7
        st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/2026", perihal="Bimtek", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 5), tanggal_kembali=datetime.date(2026, 5, 7),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st2.pegawai.add(self.pegawai)
        PerjalananDinas.objects.create(surat_tugas=st2, pegawai=self.pegawai, status=PerjalananDinas.Status.PENDING)

        url = reverse('perjalanan:kalender_perjadin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['has_overlaps'])
        
        # Verify serialized JSON contains both trips
        trips_data = json.loads(response.context['trips_json'])
        self.assertEqual(len(trips_data), 2)
        self.assertFalse(trips_data[0]['has_overlap'])
        self.assertFalse(trips_data[1]['has_overlap'])

    def test_kalender_perjadin_with_overlapping_trips(self):
        # Trip 1: May 1 to May 5
        st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/2026", perihal="Rakornas", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 5),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st1.pegawai.add(self.pegawai)
        PerjalananDinas.objects.create(surat_tugas=st1, pegawai=self.pegawai, status=PerjalananDinas.Status.APPROVED)

        # Trip 2: May 4 to May 7 (overlaps on May 4 & 5)
        st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/2026", perihal="Bimtek", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 4), tanggal_kembali=datetime.date(2026, 5, 7),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st2.pegawai.add(self.pegawai)
        PerjalananDinas.objects.create(surat_tugas=st2, pegawai=self.pegawai, status=PerjalananDinas.Status.PENDING)

        url = reverse('perjalanan:kalender_perjadin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_overlaps'])
        self.assertEqual(len(response.context['overlaps']), 1)
        
        # Verify serialized JSON has overlap flag as true for both trips
        trips_data = json.loads(response.context['trips_json'])
        self.assertEqual(len(trips_data), 2)
        self.assertTrue(trips_data[0]['has_overlap'])
        self.assertTrue(trips_data[1]['has_overlap'])

    def test_admin_kalender_sees_all_pegawais(self):
        # Create admin user
        admin_user = User.objects.create_superuser(email="admin@kpu.go.id", username="adminuser", password="password123")
        self.client.force_login(admin_user)

        # Create Pegawai 2
        user2 = User.objects.create_user(email="pegawai2@kpu.go.id", username="pegawai2user", password="password123")
        pegawai2 = Pegawai.objects.create(
            nip="199501012019011002",
            nama="Christian Gonzales",
            email="pegawai2@kpu.go.id",
            golongan="III/b",
            jabatan="Fungsional Umum",
            user=user2
        )

        # Trip for Pegawai 1 (self.pegawai): May 1 to May 3
        st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/2026", perihal="Rakornas", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 3),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st1.pegawai.add(self.pegawai)
        PerjalananDinas.objects.create(surat_tugas=st1, pegawai=self.pegawai, status=PerjalananDinas.Status.APPROVED)

        # Trip for Pegawai 2: May 1 to May 3 (same dates, but different pegawai)
        st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/2026", perihal="Bimtek", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 3),
            tempat_berangkat="Kendari", tempat_tujuan="Surabaya", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st2.pegawai.add(pegawai2)
        PerjalananDinas.objects.create(surat_tugas=st2, pegawai=pegawai2, status=PerjalananDinas.Status.PENDING)

        url = reverse('perjalanan:kalender_perjadin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Admin should see both trips
        trips_data = json.loads(response.context['trips_json'])
        self.assertEqual(len(trips_data), 2)
        self.assertTrue(any(t['pegawai_nama'] == self.pegawai.nama for t in trips_data))
        self.assertTrue(any(t['pegawai_nama'] == pegawai2.nama for t in trips_data))

    def test_admin_kalender_overlap_detection_per_pegawai(self):
        # Create admin user
        admin_user = User.objects.create_superuser(email="admin@kpu.go.id", username="adminuser", password="password123")
        self.client.force_login(admin_user)

        # Create Pegawai 2
        user2 = User.objects.create_user(email="pegawai2@kpu.go.id", username="pegawai2user", password="password123")
        pegawai2 = Pegawai.objects.create(
            nip="199501012019011002",
            nama="Christian Gonzales",
            email="pegawai2@kpu.go.id",
            golongan="III/b",
            jabatan="Fungsional Umum",
            user=user2
        )

        # Pegawai 1 Trip 1: May 1 to May 5
        st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/2026", perihal="Rakornas", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 5),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st1.pegawai.add(self.pegawai)
        pd1 = PerjalananDinas.objects.create(surat_tugas=st1, pegawai=self.pegawai, status=PerjalananDinas.Status.APPROVED)

        # Pegawai 1 Trip 2 (overlaps with Trip 1): May 4 to May 7
        st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/2026", perihal="Bimtek", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 4), tanggal_kembali=datetime.date(2026, 5, 7),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st2.pegawai.add(self.pegawai)
        pd2 = PerjalananDinas.objects.create(surat_tugas=st2, pegawai=self.pegawai, status=PerjalananDinas.Status.PENDING)

        # Pegawai 2 Trip (overlaps in DATE with Pegawai 1's trips, but different pegawai): May 3 to May 6
        st3 = SuratTugas.objects.create(
            nomor_surat="003/ST/2026", perihal="Kunjungan Kerja", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 3), tanggal_kembali=datetime.date(2026, 5, 6),
            tempat_berangkat="Kendari", tempat_tujuan="Surabaya", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st3.pegawai.add(pegawai2)
        pd3 = PerjalananDinas.objects.create(surat_tugas=st3, pegawai=pegawai2, status=PerjalananDinas.Status.APPROVED)

        url = reverse('perjalanan:kalender_perjadin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # There should only be 1 overlap recorded (between pd1 and pd2 for Pegawai 1)
        self.assertTrue(response.context['has_overlaps'])
        self.assertEqual(len(response.context['overlaps']), 1)
        overlap = response.context['overlaps'][0]
        self.assertEqual(overlap['pegawai_nama'], self.pegawai.nama)
        
        # Verify serialized JSON
        trips_data = {t['id']: t for t in json.loads(response.context['trips_json'])}
        self.assertTrue(trips_data[pd1.id]['has_overlap'])
        self.assertTrue(trips_data[pd2.id]['has_overlap'])
        self.assertFalse(trips_data[pd3.id]['has_overlap'])

    def test_resolusi_konflik_admin_success(self):
        # Create admin user
        admin_user = User.objects.create_superuser(email="admin@kpu.go.id", username="adminuser", password="password123")
        self.client.force_login(admin_user)

        # Setup StandarBiaya for calculation
        StandarBiaya.objects.get_or_create(
            provinsi=self.provinsi,
            golongan=self.pegawai.golongan,
            tahun=2024,
            defaults={'plafon_penginapan': Decimal('500000')}
        )
        StandarBiayaHarian.objects.get_or_create(
            provinsi=self.provinsi,
            tahun=2024,
            defaults={'uang_harian': Decimal('400000'), 'uang_harian_dalam_kota': Decimal('160000'), 'uang_harian_diklat': Decimal('120000')}
        )

        # Setup JenisBerkas
        jb_hotel, _ = JenisBerkas.objects.get_or_create(
            nama="Kuitansi Hotel Test",
            defaults={'wajib': False, 'nominal_biaya': True, 'kategori_biaya': 'penginapan'}
        )
        jb_tiket, _ = JenisBerkas.objects.get_or_create(
            nama="Tiket Pesawat Test",
            defaults={'wajib': False, 'nominal_biaya': True, 'kategori_biaya': 'transportasi_pesawat'}
        )

        # Trip A (pd1): May 1 to May 3
        st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/2026", perihal="Rakornas", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 3),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st1.pegawai.add(self.pegawai)
        pd1 = PerjalananDinas.objects.create(surat_tugas=st1, pegawai=self.pegawai, status=PerjalananDinas.Status.APPROVED)

        # Trip B (pd2): May 2 to May 4 (overlaps on May 2 & 3)
        st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/2026", perihal="Bimtek", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 2), tanggal_kembali=datetime.date(2026, 5, 4),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st2.pegawai.add(self.pegawai)
        pd2 = PerjalananDinas.objects.create(surat_tugas=st2, pegawai=self.pegawai, status=PerjalananDinas.Status.PENDING)

        # Create biaya perjalanan
        biaya1, _ = BiayaPerjalanan.objects.get_or_create(perjalanan=pd1)
        biaya2, _ = BiayaPerjalanan.objects.get_or_create(perjalanan=pd2)

        # Verify initial state of harian_details
        pd1.sync_harian_details()
        pd2.sync_harian_details()
        biaya1.save()
        biaya2.save()

        # Create hotel bill for Trip B (pd2): 2 nights covering May 2 and May 3 (unpaid dates)
        BerkasPerjalanan.objects.create(
            perjalanan=pd2,
            jenis_berkas=jb_hotel,
            nominal=Decimal('1000000'),
            malam_menginap=2,
            keterangan=f"[SBM-PENGINAPAN:2026-05-02:2026-05-04:2:{self.provinsi.id}:{self.provinsi.nama}] | Hotel Trip B"
        )

        # Create plane ticket for Trip B (pd2): date May 2 in description
        BerkasPerjalanan.objects.create(
            perjalanan=pd2,
            jenis_berkas=jb_tiket,
            nominal=Decimal('1500000'),
            keterangan="[SBM-TIKET:1-2-ekonomi:Kendari:Jakarta] | Tiket Pergi 2026-05-02"
        )

        # Re-save/calculate after attaching files
        pd2.biaya.save()

        # Verify initial costs: Both trips initially calculate 3 days of uang harian (3 * 400.000 = 1.200.000)
        # Trip B has hotel (1.000.000) and ticket (1.500.000)
        self.assertEqual(pd1.biaya.uang_harian_riil, Decimal('1200000'))
        self.assertEqual(pd2.biaya.uang_harian_riil, Decimal('1200000'))
        self.assertEqual(pd2.biaya.biaya_penginapan_riil, Decimal('1000000'))
        self.assertEqual(pd2.biaya.biaya_transportasi_riil, Decimal('1500000'))

        # Admin resolves conflict: choosing Trip A (pd1) for May 2 & 3
        url = reverse('perjalanan:resolusi_konflik')
        post_data = {
            'pegawai_id': self.pegawai.id,
            'chosen_2026-05-02': pd1.id,
            'chosen_2026-05-03': pd1.id,
        }
        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse('perjalanan:kalender_perjadin'))

        # Verify Trip A still has normal rates
        harian_a2 = pd1.harian_details.get(tanggal=datetime.date(2026, 5, 2))
        harian_a3 = pd1.harian_details.get(tanggal=datetime.date(2026, 5, 3))
        self.assertEqual(harian_a2.jenis_harian, 'luar_kota')
        self.assertEqual(harian_a3.jenis_harian, 'luar_kota')

        # Verify Trip B has tidak_dibayai on May 2 & 3
        harian_b2 = pd2.harian_details.get(tanggal=datetime.date(2026, 5, 2))
        harian_b3 = pd2.harian_details.get(tanggal=datetime.date(2026, 5, 3))
        harian_b4 = pd2.harian_details.get(tanggal=datetime.date(2026, 5, 4))
        self.assertEqual(harian_b2.jenis_harian, 'tidak_dibayai')
        self.assertEqual(harian_b3.jenis_harian, 'tidak_dibayai')
        self.assertEqual(harian_b4.jenis_harian, 'luar_kota') # May 4 was not part of the overlap

        # Verify costs are recalculated
        # Trip A should remain 1.200.000 harian
        pd1.biaya.refresh_from_db()
        self.assertEqual(pd1.biaya.uang_harian_riil, Decimal('1200000'))

        # Trip B should only be financed for May 4 (1 day = 400.000)
        # Trip B's hotel (May 2 & 3) is fully unfinanced/cancelled -> 0
        # Trip B's plane ticket (May 2) is fully unfinanced/cancelled -> 0
        pd2.biaya.refresh_from_db()
        self.assertEqual(pd2.biaya.uang_harian_riil, Decimal('400000'))
        self.assertEqual(pd2.biaya.biaya_penginapan_riil, Decimal('0'))
        self.assertEqual(pd2.biaya.biaya_transportasi_riil, Decimal('0'))

        # Verify cancellation text is appended to description in breakdown
        bd = pd2.biaya.calculate_breakdown()
        # Hotel bill description check
        hotel_desc = bd['breakdown_categories']['biaya_penginapan']['items'][0]['keterangan']
        self.assertIn("[DIBATALKAN 2 MALAM KARENA BENTROK]", hotel_desc)
        # Ticket description check
        ticket_desc = bd['breakdown_categories']['biaya_perjalanan']['items'][0]['keterangan']
        self.assertIn("[DIBATALKAN KARENA BENTROK]", ticket_desc)

    def test_resolusi_konflik_employee_forbidden(self):
        # Log in as normal employee user
        self.client.force_login(self.user)

        url = reverse('perjalanan:resolusi_konflik')
        post_data = {
            'pegawai_id': self.pegawai.id,
            'chosen_2026-05-02': 'some-id',
        }
        response = self.client.post(url, post_data)
        # Should redirect to login / admin login since they aren't staff
        self.assertEqual(response.status_code, 302)

    def test_calendar_daily_overlap_properties(self):
        # Create admin user
        admin_user = User.objects.create_superuser(email="admin@kpu.go.id", username="adminuser", password="password123")
        self.client.force_login(admin_user)

        # Trip A (pd1): May 1 to May 3
        st1 = SuratTugas.objects.create(
            nomor_surat="001/ST/2026", perihal="Rakornas", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 1), tanggal_kembali=datetime.date(2026, 5, 3),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st1.pegawai.add(self.pegawai)
        pd1 = PerjalananDinas.objects.create(surat_tugas=st1, pegawai=self.pegawai, status=PerjalananDinas.Status.APPROVED)

        # Trip B (pd2): May 2 to May 4 (overlaps on May 2 & 3)
        st2 = SuratTugas.objects.create(
            nomor_surat="002/ST/2026", perihal="Bimtek", tgl_surat=datetime.date(2026, 4, 30),
            tanggal_berangkat=datetime.date(2026, 5, 2), tanggal_kembali=datetime.date(2026, 5, 4),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2024, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM
        )
        st2.pegawai.add(self.pegawai)
        pd2 = PerjalananDinas.objects.create(surat_tugas=st2, pegawai=self.pegawai, status=PerjalananDinas.Status.PENDING)

        pd1.sync_harian_details()
        pd2.sync_harian_details()

        # Step 1: Before resolution (unresolved clash)
        url = reverse('perjalanan:kalender_perjadin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        trips_data = {t['id']: t for t in json.loads(response.context['trips_json'])}
        
        # Verify both trips have 'dates_info'
        self.assertIn('dates_info', trips_data[pd1.id])
        self.assertIn('dates_info', trips_data[pd2.id])
        self.assertEqual(trips_data[pd1.id]['pegawai_id'], str(self.pegawai.id))
        self.assertEqual(trips_data[pd2.id]['pegawai_id'], str(self.pegawai.id))
        
        # On May 1: pd1 has no overlap
        self.assertFalse(trips_data[pd1.id]['dates_info']['2026-05-01']['is_overlap'])
        self.assertFalse(trips_data[pd1.id]['dates_info']['2026-05-01']['is_unresolved_clash'])

        # On May 2 (unresolved): both pd1 and pd2 must show overlap/unresolved
        self.assertTrue(trips_data[pd1.id]['dates_info']['2026-05-02']['is_overlap'])
        self.assertTrue(trips_data[pd1.id]['dates_info']['2026-05-02']['is_unresolved_clash'])
        self.assertTrue(trips_data[pd2.id]['dates_info']['2026-05-02']['is_overlap'])
        self.assertTrue(trips_data[pd2.id]['dates_info']['2026-05-02']['is_unresolved_clash'])

        # Step 2: Resolve conflict choosing pd1 for May 2 & 3
        # Which sets pd2 to tidak_dibayai on May 2 & 3
        resolusi_url = reverse('perjalanan:resolusi_konflik')
        post_data = {
            'pegawai_id': self.pegawai.id,
            'chosen_2026-05-02': pd1.id,
            'chosen_2026-05-03': pd1.id,
        }
        self.client.post(resolusi_url, post_data)

        # Refresh from calendar view
        response = self.client.get(url)
        trips_data = {t['id']: t for t in json.loads(response.context['trips_json'])}

        # After resolution:
        # On May 2:
        # pd1 (financed) should NOT show overlap warning
        self.assertFalse(trips_data[pd1.id]['dates_info']['2026-05-02']['is_overlap'])
        self.assertFalse(trips_data[pd1.id]['dates_info']['2026-05-02']['is_unresolved_clash'])
        
        # pd2 (tidak_dibayai) MUST show overlap warning
        self.assertTrue(trips_data[pd2.id]['dates_info']['2026-05-02']['is_overlap'])
        # but the clash is resolved, so it's not unresolved
        self.assertFalse(trips_data[pd2.id]['dates_info']['2026-05-02']['is_unresolved_clash'])

        # On May 4 (outside conflict date for pd2): normal
        self.assertFalse(trips_data[pd2.id]['dates_info']['2026-05-04']['is_overlap'])


class DynamicSBMTestCase(TestCase):
    def setUp(self):
        # Create standard setup
        self.provinsi = Provinsi.objects.create(nama="Provinsi Sulawesi Tenggara")
        self.anggaran = Anggaran.objects.create(
            kode_dipa="001", nama_kegiatan="DIPA KPU", pagu=Decimal("50000000"), sisa_pagu=Decimal("50000000")
        )
        self.user = User.objects.create_user(email="pegawai@kpu.go.id", username="pegawai", password="password123")
        self.pegawai = Pegawai.objects.create(
            user=self.user, nip="12345", nama="Muhammad Akbar Yasin", email="pegawai@kpu.go.id",
            golongan=Golongan.III, jabatan="Staf"
        )
        # Create custom mock SBM PDF file
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.pdf_file = SimpleUploadedFile("sbm_2025.pdf", b"pdf content", content_type="application/pdf")
        self.sbm_doc = DokumenSBM.objects.create(
            tahun=2025,
            file_pdf=self.pdf_file
        )

    def tearDown(self):
        if self.sbm_doc.file_pdf:
            self.sbm_doc.file_pdf.delete(save=False)

    def test_create_standar_biaya_with_dynamic_year(self):
        # Admin can create StandarBiaya for year 2025 (which is not hardcoded)
        sb = StandarBiaya.objects.create(
            provinsi=self.provinsi,
            golongan=Golongan.III,
            plafon_penginapan=Decimal('550000'),
            tahun=2025
        )
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi, tahun=2025,
            uang_harian=Decimal('430000'),
            uang_harian_dalam_kota=Decimal('172000'),
            uang_harian_diklat=Decimal('129000')
        )
        self.assertEqual(sb.tahun, 2025)

    def test_surat_tugas_with_dynamic_year_and_pdf_context(self):
        # Admin creates SuratTugas for year 2025
        from django.core.files.uploadedfile import SimpleUploadedFile
        dummy_st_file = SimpleUploadedFile("dummy_st.pdf", b"dummy st content", content_type="application/pdf")
        st = SuratTugas.objects.create(
            nomor_surat="100/ST/2026", perihal="Bimtek Pilkada", tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25), tanggal_kembali=datetime.date(2026, 5, 27),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2025, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
            file_path=dummy_st_file
        )
        st.pegawai.add(self.pegawai)

        # Log in as the employee assigned to this ST
        self.client.force_login(self.user)

        # Get the ajukan form
        url = reverse('perjalanan:ajukan_perjadin', args=[st.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify sbm_dokumen is in context
        self.assertIn('sbm_dokumen', response.context)
        self.assertEqual(response.context['sbm_dokumen'], self.sbm_doc)
        self.assertContains(response, self.sbm_doc.file_pdf.url)

    def test_ticket_sbm_by_year(self):
        # Authenticate client
        self.client.force_login(self.user)
        # Create Kota asal and tujuan
        from master_data.models import Kota
        kota_kdi = Kota.objects.create(provinsi=self.provinsi, nama="Kendari")
        kota_jkt = Kota.objects.create(provinsi=self.provinsi, nama="Jakarta")

        # Create ticket SBM for year 2024
        sbm_2024 = StandarBiayaTiket.objects.create(
            kota_asal=kota_kdi,
            kota_tujuan=kota_jkt,
            kelas=StandarBiayaTiket.KelasTiket.EKONOMI,
            nominal=Decimal('3000000'),
            tahun=2024
        )

        # Create ticket SBM for year 2025
        sbm_2025 = StandarBiayaTiket.objects.create(
            kota_asal=kota_kdi,
            kota_tujuan=kota_jkt,
            kelas=StandarBiayaTiket.KelasTiket.EKONOMI,
            nominal=Decimal('4000000'),
            tahun=2025
        )

        # Test AJAX filter for SBM year 2024
        url = reverse('perjalanan:get_standar_biaya_tiket_ajax')
        response = self.client.get(f"{url}?tahun_sbm=2024")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        routes = data.get('routes', [])
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]['nominal'], 3000000.0)

        # Test AJAX filter for SBM year 2025
        response = self.client.get(f"{url}?tahun_sbm=2025")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        routes = data.get('routes', [])
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]['nominal'], 4000000.0)

    def test_favorable_sbm_selection_case_1(self):
        # Case 1: Pegawai has Golongan IV and Eselon IV (PosisiEselon.ES_IV).
        # We set up two SBM records with different plafon_penginapan.
        # It should select the one with higher plafon_penginapan (Golongan IV).
        # Uang harian is now universal (same for all golongan/eselon).
        
        # 1. Update test pegawai to Golongan IV and Eselon IV
        from master_data.models import PosisiEselon
        self.pegawai.golongan = Golongan.IV
        self.pegawai.posisi_jabatan = PosisiEselon.ES_IV
        self.pegawai.save()

        # 2. Create universal harian rate for year 2025
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi, tahun=2025,
            uang_harian=Decimal('500000'),
            uang_harian_dalam_kota=Decimal('200000'),
            uang_harian_diklat=Decimal('150000')
        )

        # 3. Create the two SBM rates for year 2025 (different plafon_penginapan)
        # Higher plafon for Golongan IV
        sbm_higher = StandarBiaya.objects.create(
            provinsi=self.provinsi,
            golongan=Golongan.IV,
            posisi_jabatan=None,
            plafon_penginapan=Decimal('1200000'),
            tahun=2025
        )
        # Lower plafon for ES_IV
        sbm_lower = StandarBiaya.objects.create(
            provinsi=self.provinsi,
            golongan=None,
            posisi_jabatan=PosisiEselon.ES_IV,
            plafon_penginapan=Decimal('800000'),
            tahun=2025
        )

        # 4. Create Perjalanan Dinas for this pegawai
        from django.core.files.uploadedfile import SimpleUploadedFile
        st = SuratTugas.objects.create(
            nomor_surat="200/ST/2026", perihal="Kunjungan Kerja", tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25), tanggal_kembali=datetime.date(2026, 5, 27),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2025, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
            file_path=SimpleUploadedFile("dummy_st_1.pdf", b"dummy content")
        )
        st.pegawai.add(self.pegawai)

        perjadin = PerjalananDinas.objects.create(
            surat_tugas=st,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

        # 5. Verify: uang harian is universal (3 days * 500k = 1,500,000)
        self.assertEqual(perjadin.biaya.uang_harian_riil, Decimal('1500000'))
        
        # Verify plafon hotel picks the more favorable (higher) one
        breakdown = perjadin.biaya.calculate_breakdown()
        self.assertEqual(breakdown['sbm_plafon_hotel'], Decimal('1200000'))

    def test_favorable_sbm_selection_case_2(self):
        # Case 2: Pegawai has Golongan III and Eselon III (PosisiEselon.ES_III).
        # Eselon III has higher plafon_penginapan than Golongan III.
        # It should select the Eselon III record (higher plafon).
        
        # 1. Update test pegawai to Golongan III and Eselon III
        from master_data.models import PosisiEselon
        self.pegawai.golongan = Golongan.III
        self.pegawai.posisi_jabatan = PosisiEselon.ES_III
        self.pegawai.save()

        # 2. Create universal harian rate for year 2025
        StandarBiayaHarian.objects.create(
            provinsi=self.provinsi, tahun=2025,
            uang_harian=Decimal('500000'),
            uang_harian_dalam_kota=Decimal('200000'),
            uang_harian_diklat=Decimal('150000')
        )

        # 3. Create the two SBM rates for year 2025
        # Higher plafon for Eselon III
        sbm_higher = StandarBiaya.objects.create(
            provinsi=self.provinsi,
            golongan=None,
            posisi_jabatan=PosisiEselon.ES_III,
            plafon_penginapan=Decimal('1200000'),
            tahun=2025
        )
        # Lower plafon for Golongan III
        sbm_lower = StandarBiaya.objects.create(
            provinsi=self.provinsi,
            golongan=Golongan.III,
            posisi_jabatan=None,
            plafon_penginapan=Decimal('800000'),
            tahun=2025
        )

        # 4. Create Perjalanan Dinas for this pegawai
        from django.core.files.uploadedfile import SimpleUploadedFile
        st = SuratTugas.objects.create(
            nomor_surat="300/ST/2026", perihal="Bimbingan Teknis", tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25), tanggal_kembali=datetime.date(2026, 5, 27),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2025, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
            file_path=SimpleUploadedFile("dummy_st_2.pdf", b"dummy content")
        )
        st.pegawai.add(self.pegawai)

        perjadin = PerjalananDinas.objects.create(
            surat_tugas=st,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

        # 5. Verify: uang harian is universal (3 days * 500k = 1,500,000)
        self.assertEqual(perjadin.biaya.uang_harian_riil, Decimal('1500000'))
        
        # Verify plafon hotel picks the more favorable (higher) one
        breakdown = perjadin.biaya.calculate_breakdown()
        self.assertEqual(breakdown['sbm_plafon_hotel'], Decimal('1200000'))

    def test_tiket_sbm_favorable_selection_by_classification(self):
        # Setup route destinations
        from master_data.models import Kota, PosisiEselon
        kota_kdi = Kota.objects.create(provinsi=self.provinsi, nama="Kendari")
        kota_jkt = Kota.objects.create(provinsi=self.provinsi, nama="Jakarta")

        # 1. Update test pegawai to Golongan IV and Eselon IV (PosisiEselon.ES_IV)
        self.pegawai.golongan = Golongan.IV
        self.pegawai.posisi_jabatan = PosisiEselon.ES_IV
        self.pegawai.save()

        # 2. Create StandarBiayaTiket records:
        # Fallback (no classification)
        sbm_fallback = StandarBiayaTiket.objects.create(
            kota_asal=kota_kdi, kota_tujuan=kota_jkt, kelas=StandarBiayaTiket.KelasTiket.EKONOMI,
            posisi_jabatan=None, nominal=Decimal('3000000'), tahun=2025
        )
        # Specific lower rate for Eselon IV
        sbm_lower = StandarBiayaTiket.objects.create(
            kota_asal=kota_kdi, kota_tujuan=kota_jkt, kelas=StandarBiayaTiket.KelasTiket.EKONOMI,
            posisi_jabatan=PosisiEselon.ES_IV, nominal=Decimal('4000000'), tahun=2025
        )

        # 3. Test AJAX endpoint filters to the single highest / most favorable route
        self.client.force_login(self.user)
        url = reverse('perjalanan:get_standar_biaya_tiket_ajax')
        response = self.client.get(f"{url}?tahun_sbm=2025&pegawai_id={self.pegawai.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        routes = data.get('routes', [])
        self.assertEqual(len(routes), 1)
        # Should pick Rp 4.000.000 (ES_IV specific, more favorable than fallback)
        self.assertEqual(routes[0]['nominal'], 4000000.0)

        # 4. Test calculate_breakdown on BiayaPerjalanan matches the Rp 5.000.000 limit
        from django.core.files.uploadedfile import SimpleUploadedFile
        st = SuratTugas.objects.create(
            nomor_surat="400/ST/2026", perihal="Bimtek Tiket", tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25), tanggal_kembali=datetime.date(2026, 5, 27),
            tempat_berangkat="Kendari", tempat_tujuan="Jakarta", tujuan_provinsi=self.provinsi,
            tahun_sbm=2025, anggaran=self.anggaran, jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
            file_path=SimpleUploadedFile("dummy_st_3.pdf", b"dummy content")
        )
        st.pegawai.add(self.pegawai)

        perjadin = PerjalananDinas.objects.create(
            surat_tugas=st,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

        # Create travel ticket bill with high nominal (e.g. 6 million)
        from master_data.models import JenisBerkas
        from perjalanan.models import BerkasPerjalanan
        jenis_tiket = JenisBerkas.objects.create(nama="TIKET PESAWAT", kategori_biaya='transportasi_pesawat', nominal_biaya=True)
        
        # We need to construct a description with metadata: [SBM-TIKET:kota_asal_id-kota_tujuan_id-kelas:nama_asal:nama_tujuan]
        keterangan = f"[SBM-TIKET:{kota_kdi.id}-{kota_jkt.id}-ekonomi:Kendari:Jakarta]"
        
        berkas = BerkasPerjalanan.objects.create(
            perjalanan=perjadin,
            jenis_berkas=jenis_tiket,
            nominal=Decimal('6000000'),
            keterangan=keterangan,
            file=SimpleUploadedFile("tiket.pdf", b"pdf content")
        )

        # Recalculate and verify: ticket real cost capped at Rp 5.000.000, 1.000.000 is personal expense
        breakdown = perjadin.biaya.calculate_breakdown()
        self.assertEqual(breakdown['biaya_transportasi_riil'], Decimal('4000000'))
        self.assertEqual(breakdown['transportasi_dana_pribadi'], Decimal('2000000'))

    def test_tiket_sbm_class_eligibility_by_eselon(self):
        from master_data.models import PosisiEselon
        from perjalanan.models import get_eligible_tiket_filter

        # 1. Non Eselon
        self.pegawai.posisi_jabatan = PosisiEselon.NON_ESELON
        self.pegawai.save()
        filt_non_es = get_eligible_tiket_filter(self.pegawai)
        self.assertIn("('kelas', 'ekonomi')", str(filt_non_es))
        self.assertNotIn("('kelas', 'bisnis')", str(filt_non_es))

        # 2. Eselon IV
        self.pegawai.posisi_jabatan = PosisiEselon.ES_IV
        self.pegawai.save()
        filt_es_iv = get_eligible_tiket_filter(self.pegawai)
        self.assertIn("('kelas', 'ekonomi')", str(filt_es_iv))
        self.assertNotIn("('kelas', 'bisnis')", str(filt_es_iv))

        # 3. Eselon III
        self.pegawai.posisi_jabatan = PosisiEselon.ES_III
        self.pegawai.save()
        filt_es_iii = get_eligible_tiket_filter(self.pegawai)
        self.assertIn("('kelas', 'ekonomi')", str(filt_es_iii))
        self.assertNotIn("('kelas', 'bisnis')", str(filt_es_iii))

        # 4. Eselon II
        self.pegawai.posisi_jabatan = PosisiEselon.ES_II
        self.pegawai.save()
        filt_es_ii = get_eligible_tiket_filter(self.pegawai)
        self.assertIn("('kelas', 'bisnis')", str(filt_es_ii))
        self.assertNotIn("('kelas', 'ekonomi')", str(filt_es_ii))


class AjukanPerjadinBerkasDraftSaveTestCase(TiketPesawatTestCase):
    def test_save_draft_persists_new_berkas_row(self):
        self.client.force_login(self.user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        surat_tugas = SuratTugas.objects.create(
            nomor_surat="999/ST/KPU-KU/V/2026",
            perihal="Uji Simpan Draft Berkas",
            tgl_surat=datetime.date(2026, 5, 20),
            tanggal_berangkat=datetime.date(2026, 5, 25),
            tanggal_kembali=datetime.date(2026, 5, 28),
            tempat_berangkat="Konawe Utara",
            tempat_tujuan="Jakarta",
            tujuan_provinsi=self.provinsi_tujuan,
            tahun_sbm=2024,
            anggaran=self.anggaran,
            jenis_perjalanan=SuratTugas.JenisPerjalanan.LUAR_KOTA,
            jenis_transportasi=SuratTugas.JenisTransportasi.UMUM,
        )
        surat_tugas.file_path.save(
            "surat_tugas_uji.pdf",
            SimpleUploadedFile("surat_tugas_uji.pdf", b"dummy content", content_type="application/pdf"),
            save=True,
        )
        surat_tugas.pegawai.add(self.pegawai)
        perjadin = PerjalananDinas.objects.create(
            surat_tugas=surat_tugas,
            pegawai=self.pegawai,
            status=PerjalananDinas.Status.DRAFT
        )

        url = reverse('perjalanan:ajukan_perjadin', args=[surat_tugas.id])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        berkas_formset = response.context['berkas_formset']
        biaya_formset = response.context['biaya_formset']
        harian_formset = response.context['harian_formset']

        berkas_prefix = berkas_formset.prefix
        biaya_prefix = biaya_formset.prefix
        harian_prefix = harian_formset.prefix

        payload = {
            f'{berkas_prefix}-TOTAL_FORMS': '1',
            f'{berkas_prefix}-INITIAL_FORMS': '0',
            f'{berkas_prefix}-MIN_NUM_FORMS': '0',
            f'{berkas_prefix}-MAX_NUM_FORMS': '1000',
            f'{berkas_prefix}-0-jenis_berkas': str(self.jenis_taksi.id),
            f'{berkas_prefix}-0-nominal': '8000',
            f'{berkas_prefix}-0-keterangan': 'STRUK PARKIR',
            f'{berkas_prefix}-0-malam_menginap': '1',
            f'{biaya_prefix}-TOTAL_FORMS': str(biaya_formset.total_form_count()),
            f'{biaya_prefix}-INITIAL_FORMS': str(biaya_formset.initial_form_count()),
            f'{biaya_prefix}-MIN_NUM_FORMS': '0',
            f'{biaya_prefix}-MAX_NUM_FORMS': '1',
            f'{harian_prefix}-TOTAL_FORMS': str(harian_formset.total_form_count()),
            f'{harian_prefix}-INITIAL_FORMS': str(harian_formset.initial_form_count()),
            f'{harian_prefix}-MIN_NUM_FORMS': '0',
            f'{harian_prefix}-MAX_NUM_FORMS': '1000',
            'action': 'save',
        }

        if biaya_formset.forms and biaya_formset.forms[0].instance.pk:
            payload[f'{biaya_prefix}-0-id'] = str(biaya_formset.forms[0].instance.pk)

        for idx, form in enumerate(harian_formset.forms):
            payload[f'{harian_prefix}-{idx}-id'] = str(form.instance.pk)
            payload[f'{harian_prefix}-{idx}-hari_ke'] = str(form.instance.hari_ke)
            payload[f'{harian_prefix}-{idx}-tanggal'] = form.instance.tanggal.isoformat()
            payload[f'{harian_prefix}-{idx}-provinsi'] = str(form.instance.provinsi_id)
            payload[f'{harian_prefix}-{idx}-jenis_harian'] = form.instance.jenis_harian

        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 302)

        berkas = BerkasPerjalanan.objects.filter(perjalanan=perjadin)
        self.assertEqual(berkas.count(), 1)
        self.assertEqual(berkas.first().nominal, Decimal('8000'))
        self.assertEqual(berkas.first().keterangan, 'STRUK PARKIR')














