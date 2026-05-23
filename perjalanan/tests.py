from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
import datetime
import json

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
            uang_harian_fullboard_luar=Decimal("130000"),
            uang_harian_fullboard_dalam=Decimal("90000"),
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
            uang_harian=Decimal("340000"),  # Sultra rate
            uang_harian_fullboard_luar=Decimal("120000"),
            uang_harian_fullboard_dalam=Decimal("80000"),
            plafon_penginapan=Decimal("800000"),
            uang_representasi=Decimal("0"),
            plafon_transportasi=Decimal("300000")
        )

        # Standar Biaya SBM for Jakarta
        self.sbm_jakarta = StandarBiaya.objects.create(
            provinsi=self.provinsi_tujuan,
            golongan="III/a",
            tahun=2024,
            uang_harian=Decimal("370000"),  # Jakarta rate
            uang_harian_fullboard_luar=Decimal("130000"),
            uang_harian_fullboard_dalam=Decimal("90000"),
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
        # Expected total: 370k (Luar Kota) + 148k (Dalam Kota) + 111k (Diklat) + 90k (Halfday) = 719,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("719000"))
        
        # Also test Fullboard (Luar Kota if outside Sultra, else Dalam Kota)
        # Sultra is home (SULAWESI TENGGARA), Jakarta is outside (DKI JAKARTA)
        # So fullboard for Jakarta should be fullboard_luar = 130k
        day4.jenis_harian = HarianPerjalanan.JenisHarian.FULLBOARD
        day4.provinsi = self.provinsi_tujuan  # DKI JAKARTA (luar)
        day4.save()
        
        self.perjadin.biaya.refresh_from_db()
        # Expected total: 370k (Luar Kota) + 148k (Dalam Kota) + 111k (Diklat) + 130k (Fullboard Luar) = 759,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("759000"))
        
        # Fullboard for Sultra (home) should be fullboard_dalam = 80k
        day4.provinsi = self.provinsi_asal  # SULAWESI TENGGARA (home)
        day4.save()
        
        self.perjadin.biaya.refresh_from_db()
        # Expected total: 370k (Luar Kota) + 148k (Dalam Kota) + 111k (Diklat) + 80k (Fullboard Dalam) = 709,000
        self.assertEqual(self.perjadin.biaya.uang_harian_riil, Decimal("709000"))


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
            uang_harian=Decimal("340000"),
            uang_harian_fullboard_luar=Decimal("120000"),
            uang_harian_fullboard_dalam=Decimal("80000"),
            plafon_penginapan=Decimal("800000"),
            uang_representasi=Decimal("0"),
            plafon_transportasi=Decimal("300000")
        )

        # Standar Biaya SBM for Jakarta
        self.sbm_jakarta = StandarBiaya.objects.create(
            provinsi=self.provinsi_tujuan,
            golongan="III/a",
            tahun=2024,
            uang_harian=Decimal("370000"),
            uang_harian_fullboard_luar=Decimal("130000"),
            uang_harian_fullboard_dalam=Decimal("90000"),
            plafon_penginapan=Decimal("1000000"),
            uang_representasi=Decimal("150000"),
            plafon_transportasi=Decimal("500000")
        )

        # Standar Biaya SBM for Jabar (Transit)
        self.sbm_jabar = StandarBiaya.objects.create(
            provinsi=self.provinsi_transit,
            golongan="III/a",
            tahun=2024,
            uang_harian=Decimal("350000"),
            uang_harian_fullboard_luar=Decimal("110000"),
            uang_harian_fullboard_dalam=Decimal("70000"),
            plafon_penginapan=Decimal("600000"),  # Jabar plafon hotel is 600.000 (lower than Jakarta's 1.000.000)
            uang_representasi=Decimal("0"),
            plafon_transportasi=Decimal("400000")
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










