function initAdminFilter() {
    const suratTugasSelect = document.querySelector('#id_surat_tugas');
    const pegawaiSelect = document.querySelector('#id_pegawai');

    if (suratTugasSelect && pegawaiSelect) {
        suratTugasSelect.addEventListener('change', function () {
            const suratTugasId = this.value;
            if (!suratTugasId) return;

            fetch(`/perjalanan/api/get-pegawai/?surat_tugas_id=${suratTugasId}`)
                .then(response => response.json())
                .then(data => {
                    const currentPegawaiId = pegawaiSelect.value;
                    pegawaiSelect.innerHTML = '<option value="">---------</option>';

                    data.pegawai.forEach(p => {
                        const option = document.createElement('option');
                        option.value = p.id;
                        option.textContent = p.nama;
                        if (p.id == currentPegawaiId) {
                            option.selected = true;
                        }
                        pegawaiSelect.appendChild(option);
                    });
                    // Trigger estimation update when pegawai list finishes updating
                    updateAdminEstimasi();
                })
                .catch(error => console.error('Error fetching pegawai:', error));
        });

        if (suratTugasSelect.value) {
            suratTugasSelect.dispatchEvent(new Event('change'));
        }
    }

    // Function to calculate and preview costs in real-time in Django Admin
    function updateAdminEstimasi() {
        const tanggalBerangkat = document.querySelector('#id_tanggal_berangkat')?.value;
        const tanggalKembali = document.querySelector('#id_tanggal_kembali')?.value;
        const tujuanProvinsi = document.querySelector('#id_tujuan_provinsi')?.value;
        const tidakMenginapCheckbox = document.querySelector('#id_tidak_menginap');
        const tidakMenginap = tidakMenginapCheckbox ? tidakMenginapCheckbox.checked : false;
        const jenisTransportasi = document.querySelector('#id_jenis_transportasi')?.value;
        const tahunSbm = document.querySelector('#id_tahun_sbm')?.value;
        const pegawaiId = document.querySelector('#id_pegawai')?.value;

        // Gather all berkas inlines from tabular rows
        const berkas = [];
        const rows = document.querySelectorAll('.inline-related tr.form-row:not(.empty-form)');
        rows.forEach(row => {
            const select = row.querySelector('select[name$="-jenis_berkas"]');
            const nominalInput = row.querySelector('input[name$="-nominal"]');
            const deleteInput = row.querySelector('input[name$="-DELETE"]');

            if (deleteInput && deleteInput.checked) return;

            if (select) {
                const jbId = select.value;
                const nominalVal = nominalInput ? nominalInput.value.replace(/\./g, '') : 0;
                const malamInput = row.querySelector('input[name$="-malam_menginap"]');
                const malamVal = malamInput ? parseInt(malamInput.value) || 0 : 0;
                
                let keteranganVal = '';
                if (isTicketPesawat(select)) {
                    const tagHidden = row.querySelector('.admin-ticket-tag-hidden');
                    keteranganVal = tagHidden ? tagHidden.value : '';
                } else if (isPenginapanBerkas(select)) {
                    const tagHidden = row.querySelector('.admin-hotel-tag-hidden');
                    keteranganVal = tagHidden ? tagHidden.value : '';
                }

                if (jbId) {
                    berkas.push({
                        'jenis_berkas_id': parseInt(jbId),
                        'nominal': parseFloat(nominalVal) || 0.0,
                        'malam_menginap': malamVal,
                        'keterangan': keteranganVal
                    });
                }
            }
        });

        const jenisPerjalanan = document.querySelector('#id_jenis_perjalanan')?.value;

        // Gather all harian details from admin inline
        const harian = [];
        const harianGroup = document.querySelector('#harian_details-group');
        if (harianGroup) {
            const harianRows = harianGroup.querySelectorAll('tr.form-row:not(.empty-form)');
            harianRows.forEach((row, index) => {
                const provSelect = row.querySelector('select[name$="-provinsi"]');
                const jenisSelect = row.querySelector('select[name$="-jenis_harian"]');
                const hariKeTd = row.querySelector('.field-hari_ke');
                let hariKe = hariKeTd ? (parseInt(hariKeTd.textContent.trim()) || 0) : (index + 1);
                
                if (provSelect && jenisSelect && hariKe) {
                    harian.push({
                        'hari_ke': hariKe,
                        'provinsi_id': provSelect.value ? parseInt(provSelect.value) : null,
                        'jenis_harian': jenisSelect.value || 'luar_kota'
                    });
                }
            });
        }

        const payload = {
            tanggal_berangkat: tanggalBerangkat,
            tanggal_kembali: tanggalKembali,
            tujuan_provinsi: tujuanProvinsi,
            tidak_menginap: tidakMenginap,
            jenis_transportasi: jenisTransportasi,
            jenis_perjalanan: jenisPerjalanan,
            tahun_sbm: tahunSbm,
            pegawai_id: pegawaiId,
            berkas: berkas,
            harian: harian
        };

        let csrfToken = '';
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) csrfToken = csrfInput.value;

        fetch('/perjalanan/api/hitung-estimasi/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) return;

                const formatRupiah = (val) => {
                    return 'Rp ' + parseFloat(val).toLocaleString('id-ID', {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0
                    });
                };

                // Update DOM readonly elements in BiayaPerjalananInline
                const harianEl = document.querySelector('.field-uang_harian_riil div.readonly');
                const reprEl = document.querySelector('.field-uang_representasi_riil div.readonly');
                const hotelEl = document.querySelector('.field-biaya_penginapan_riil div.readonly');
                const transportEl = document.querySelector('.field-biaya_transportasi_riil div.readonly');
                const totalEl = document.querySelector('.field-get_total_dibayarkan div.readonly');
                const tidakDibayarkanEl = document.querySelector('.field-get_total_tidak_dibayarkan div.readonly');

                if (harianEl) harianEl.textContent = formatRupiah(data.uang_harian_riil);
                if (reprEl) reprEl.textContent = formatRupiah(data.uang_representasi_riil);
                if (hotelEl) hotelEl.textContent = formatRupiah(data.biaya_penginapan_riil);
                if (transportEl) transportEl.textContent = formatRupiah(data.biaya_transportasi_riil);
                if (totalEl) totalEl.innerHTML = `<strong style="color: #0f172a; font-size: 1.1em;">${formatRupiah(data.total_dibayarkan)}</strong>`;
                if (tidakDibayarkanEl) {
                    const unpaidVal = parseFloat(data.total_tidak_dibayarkan) || 0.0;
                    if (unpaidVal > 0) {
                        tidakDibayarkanEl.innerHTML = `<strong style="color: #dc2626; font-size: 1.1em;">${formatRupiah(unpaidVal)}</strong>`;
                    } else {
                        tidakDibayarkanEl.textContent = "-";
                    }
                }
                // Populate lumpsum nominal inputs dynamically for Admin
                const plafonHotel = parseFloat(data.plafon_hotel) || 0;
                const lumpsumNominal = 0.30 * plafonHotel;

                const rows = document.querySelectorAll('.inline-related tr.form-row:not(.empty-form)');
                rows.forEach(row => {
                    const select = row.querySelector('select[name$="-jenis_berkas"]');
                    const nominalInput = row.querySelector('input[name$="-nominal"]');
                    if (select && nominalInput) {
                        const selectText = select.options[select.selectedIndex]?.text || '';
                        if (selectText === 'TIDAK MENGINAP') {
                            nominalInput.readOnly = true;
                            nominalInput.style.backgroundColor = '#f1f5f9';
                            nominalInput.style.cursor = 'not-allowed';

                            const malamInput = row.querySelector('input[name$="-malam_menginap"]');
                            const malamVal = malamInput ? parseInt(malamInput.value) || 0 : 0;
                            const calculatedValue = lumpsumNominal * malamVal;
                            nominalInput.value = calculatedValue.toLocaleString('id-ID', {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            });
                        } else if (selectText.includes('FULLBOARD')) {
                            nominalInput.readOnly = true;
                            nominalInput.style.backgroundColor = '#f1f5f9';
                            nominalInput.style.cursor = 'not-allowed';
                            nominalInput.value = '0';
                        } else {
                            if (nominalInput.readOnly) {
                                nominalInput.readOnly = false;
                                nominalInput.style.backgroundColor = '';
                                nominalInput.style.cursor = '';
                                nominalInput.value = '';
                            }
                        }
                    }
                });
            })
            .catch(err => console.error('Admin estimation error:', err));
    }

    // Bind change/input events to main form inputs for real-time preview in Admin
    const adminInputs = [
        '#id_tanggal_berangkat',
        '#id_tanggal_kembali',
        '#id_tujuan_provinsi',
        '#id_tidak_menginap',
        '#id_jenis_transportasi',
        '#id_jenis_perjalanan',
        '#id_tahun_sbm',
        '#id_pegawai'
    ];
    adminInputs.forEach(sel => {
        const el = document.querySelector(sel);
        if (el) {
            el.addEventListener('change', updateAdminEstimasi);
            el.addEventListener('input', updateAdminEstimasi);
        }
    });

    const jenisPerjalananSelect = document.querySelector('#id_jenis_perjalanan');
    const groupPenginapan = document.querySelector('#berkas-group');

    function checkAdminFullboard() {
        if (!jenisPerjalananSelect) return;
        const val = jenisPerjalananSelect.value;
        if (val === 'fullboard_luar' || val === 'fullboard_dalam') {
            if (groupPenginapan) {
                groupPenginapan.style.display = 'none';
                const rows = groupPenginapan.querySelectorAll('tr.form-row:not(.empty-form)');
                rows.forEach(row => {
                    const deleteInput = row.querySelector('input[name$="-DELETE"]');
                    if (deleteInput) {
                        deleteInput.checked = true;
                    }
                });
            }
        } else {
            if (groupPenginapan) {
                groupPenginapan.style.display = 'block';
            }
        }
    }

    if (jenisPerjalananSelect) {
        jenisPerjalananSelect.addEventListener('change', () => {
            checkAdminFullboard();
        });
        checkAdminFullboard();
    }

    // Delegate listener to capture edits/additions/deletions in the inline berkas or harian rows in Admin
    document.addEventListener('change', function (e) {
        if (e.target.matches('input[name$="-nominal"]') || 
            e.target.matches('select[name$="-jenis_berkas"]') || 
            e.target.matches('input[name$="-DELETE"]') || 
            e.target.matches('input[name$="-malam_menginap"]') ||
            e.target.matches('select[name$="-provinsi"]') ||
            e.target.matches('select[name$="-jenis_harian"]')) {
            updateAdminEstimasi();
        }
    });
    document.addEventListener('input', function (e) {
        if (e.target.matches('input[name$="-nominal"]') || e.target.matches('input[name$="-malam_menginap"]')) {
            updateAdminEstimasi();
        }
    });

    // Thousand separator formatting for nominal inputs
    function formatRupiahInput(value) {
        let digits = value.replace(/\D/g, '');
        if (!digits) return '';
        return parseInt(digits, 10).toLocaleString('id-ID');
    }

    document.addEventListener('input', function (e) {
        if (e.target.matches('input[name$="-nominal"]')) {
            let input = e.target;
            if (input.type === 'number') {
                input.type = 'text';
            }
            let cursorPosition = input.selectionStart;
            let originalLength = input.value.length;

            let formatted = formatRupiahInput(input.value);
            if (input.value !== formatted) {
                input.value = formatted;
                let newLength = formatted.length;
                let diff = newLength - originalLength;
                input.setSelectionRange(cursorPosition + diff, cursorPosition + diff);
            }
        }
    });

    // Format all nominal fields initially
    document.querySelectorAll('input[name$="-nominal"]').forEach(input => {
        if (input.type === 'number') {
            input.type = 'text';
        }
        if (input.value) {
            input.value = formatRupiahInput(input.value);
        }
    });

    // Strip dots and concat ticket tags before form submit in Admin
    const form = document.getElementById('perjalanandinas_form') || document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function (e) {
            let flightCount = 0;
            const rows = document.querySelectorAll('.inline-related tr.form-row:not(.empty-form)');
            rows.forEach(row => {
                const deleteInput = row.querySelector('input[name$="-DELETE"]');
                if (deleteInput && deleteInput.checked) return;

                const select = row.querySelector('select[name$="-jenis_berkas"]');
                if (select && isTicketPesawat(select)) {
                    flightCount++;
                }
            });
            if (flightCount > 2) {
                e.preventDefault();
                alert("Tiket pesawat hanya dapat diinput maksimal 2 kali (untuk pergi dan pulang) sesuai aturan SBM.");
                return false;
            }

            rows.forEach(row => {
                const deleteInput = row.querySelector('input[name$="-DELETE"]');
                if (deleteInput && deleteInput.checked) return;

                const select = row.querySelector('select[name$="-jenis_berkas"]');
                if (select) {
                    if (isTicketPesawat(select)) {
                        const tagHidden = row.querySelector('.admin-ticket-tag-hidden');
                        const descInput = row.querySelector('input[name$="-keterangan"]');
                        if (tagHidden && descInput) {
                            const tagVal = tagHidden.value;
                            const descVal = descInput.value.trim();
                            if (tagVal) {
                                if (descVal) {
                                    descInput.value = `${tagVal} | ${descVal}`;
                                } else {
                                    descInput.value = tagVal;
                                }
                            }
                        }
                    } else if (isPenginapanBerkas(select)) {
                        const tagHidden = row.querySelector('.admin-hotel-tag-hidden');
                        const descInput = row.querySelector('input[name$="-keterangan"]');
                        if (tagHidden && descInput) {
                            const tagVal = tagHidden.value;
                            const descVal = descInput.value.trim();
                            if (tagVal) {
                                if (descVal) {
                                    descInput.value = `${tagVal} | ${descVal}`;
                                } else {
                                    descInput.value = tagVal;
                                }
                            }
                        }
                    }
                }
            });

            form.querySelectorAll('input[name$="-nominal"]').forEach(input => {
                input.value = input.value.replace(/\./g, '');
            });
        });
    }

    // Modal CSS Styles Injection
    const modalStyles = `
        .admin-ticket-modal {
            display: none;
            position: fixed;
            z-index: 99999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(8px);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .admin-ticket-modal-content {
            background-color: white;
            margin: 10% auto;
            border-radius: 0.75rem;
            width: 90%;
            max-width: 450px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        .admin-ticket-modal-header {
            padding: 1rem 1.5rem;
            background: #1e293b;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .admin-ticket-modal-header h2 {
            font-size: 1rem;
            margin: 0;
            font-weight: 700;
            color: white;
            margin: 0;
        }
        .admin-ticket-modal-close {
            color: #94a3b8;
            font-size: 1.25rem;
            font-weight: 300;
            cursor: pointer;
        }
        .admin-ticket-modal-close:hover {
            color: white;
        }
        .admin-ticket-modal-body {
            padding: 1.5rem;
        }
        .admin-ticket-form-group {
            margin-bottom: 1.25rem;
        }
        .admin-ticket-form-group label {
            display: block;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 0.375rem;
            color: #334155;
        }

        .admin-ticket-form-group select {
            width: 100% !important;
            height: 2.2rem !important;
            min-height: 2.2rem !important;
            padding: 0.375rem 2.5rem 0.375rem 0.75rem !important;
            font-size: 0.9rem !important;
            border-radius: 0.375rem !important;
            border: 1px solid #cbd5e1 !important;
            background: #f8fafc url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23475569' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E") no-repeat right 0.75rem center !important;
            background-size: 1rem !important;
            color: #0f172a !important;
            box-sizing: border-box !important;
            -webkit-appearance: none !important;
            -moz-appearance: none !important;
            appearance: none !important;
            line-height: 1.5 !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }
        
        #admin-ticket-asal-select:focus,
        #admin-ticket-tujuan-select:focus,
        #admin-ticket-kelas-select:focus {
            outline: none !important;
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
        }
        .admin-ticket-sbm-preview {
            display: none;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 0.5rem;
            padding: 0.75rem 1rem;
            margin-bottom: 1.5rem;
            align-items: center;
            justify-content: space-between;
        }
        .admin-ticket-sbm-preview span {
            font-size: 0.875rem;
            font-weight: 600;
        }
        .admin-ticket-btn-group {
            display: flex;
            gap: 0.75rem;
        }
        .admin-ticket-btn {
            padding: 0.625rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            border: none;
            flex: 1;
        }
        .admin-ticket-btn-primary {
            background: #2563eb;
            color: white;
        }
        .admin-ticket-btn-primary:disabled {
            background: #94a3b8;
            cursor: not-allowed;
        }
        .admin-ticket-btn-secondary {
            background: #e2e8f0;
            color: #475569;
        }
        .admin-ticket-route-badge {
            display: flex;
            margin-top: 0.375rem;
            align-items: center;
            gap: 0.5rem;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            justify-content: space-between;
            max-width: fit-content;
        }
        .admin-ticket-route-text {
            font-size: 0.75rem;
            color: #1d4ed8;
            font-weight: 600;
        }
        .admin-ticket-route-edit {
            background: none;
            border: none;
            color: #2563eb;
            cursor: pointer;
            padding: 0;
            font-size: 0.75rem;
        }

        /* Adjust padding to prevent overlapping with badge */
        .inline-related tr.form-row.has-ticket-route td,
        .inline-related tr.form-row.has-hotel-route td {
            padding-top: 2.2rem !important;
            position: relative !important;
        }

        /* Styled badge for active ticket route */
        .admin-ticket-route-badge-active {
            position: absolute !important;
            top: 0.4rem !important;
            left: 10px !important;
            margin: 0 !important;
            padding: 2px 6px !important;
            background-color: #eff6ff !important;
            border: 1px solid #bfdbfe !important;
            border-radius: 4px !important;
            color: #1e40af !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
            z-index: 10 !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
            line-height: 1.2 !important;
            height: auto !important;
        }

        /* Edit button styled inside the badge */
        .admin-ticket-route-edit-btn {
            background: none !important;
            border: none !important;
            cursor: pointer !important;
            padding: 2px !important;
            margin-left: 4px !important;
            font-size: 11px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: transform 0.2s !important;
        }
        .admin-ticket-route-edit-btn:hover {
            transform: scale(1.25) !important;
        }
    `;

    let ticketRoutes = [];
    let ticketPesawatIds = [];
    let penginapanBerkasIds = [];
    let activeTicketRow = null;
    let activeHotelRow = null;

    const JENIS_HARIAN_LABELS = {
        'luar_kota': 'Luar Kota',
        'dalam_kota': 'Dalam Kota (> 8 Jam)',
        'diklat': 'Diklat',
        'halfday': 'Rapat/Pertemuan Halfday',
        'fullday': 'Rapat/Pertemuan Fullday',
        'fullboard': 'Rapat/Pertemuan Fullboard',
    };

    function isTicketPesawat(selectElement) {
        if (!selectElement || !selectElement.value) return false;
        const val = parseInt(selectElement.value, 10);
        return !isNaN(val) && ticketPesawatIds.includes(val);
    }

    function isPenginapanBerkas(selectElement) {
        if (!selectElement || !selectElement.value) return false;
        const val = parseInt(selectElement.value, 10);
        return !isNaN(val) && penginapanBerkasIds.includes(val);
    }

    function formatTglIndo(tglStr) {
        if (!tglStr) return '';
        const parts = tglStr.split('-');
        if (parts.length !== 3) return tglStr;
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
        const day = parseInt(parts[2]);
        const month = months[parseInt(parts[1]) - 1];
        const year = parts[0];
        return `${day} ${month} ${year}`;
    }

    function parsePenginapanKeterangan(keteranganVal) {
        if (!keteranganVal) return null;
        const match = keteranganVal.match(/^\[SBM-PENGINAPAN:([^:]+):([^:]+):(\d+):([^:]+):([^\]]+)\](?:\s*\|\s*(.*))?$/);
        if (match) {
            return {
                checkIn: match[1],
                checkOut: match[2],
                nights: parseInt(match[3]),
                provinsiId: match[4],
                provinsiNama: match[5],
                userDesc: match[6] || ""
            };
        }
        return null;
    }

    function countFlightTickets(currentRow = null) {
        let count = 0;
        const rows = document.querySelectorAll('.inline-related tr.form-row:not(.empty-form)');
        rows.forEach(r => {
            if (r === currentRow) return;
            const deleteInput = r.querySelector('input[name$="-DELETE"]');
            if (deleteInput && deleteInput.checked) return;

            const select = r.querySelector('select[name$="-jenis_berkas"]');
            if (select && isTicketPesawat(select)) {
                count++;
            }
        });
        return count;
    }

    function parseTicketKeterangan(keteranganVal) {
        if (!keteranganVal) return null;
        const match = keteranganVal.match(/^\[SBM-TIKET:(\d+)-(\d+)-(\w+):([^:]+):([^\]]+)\](?:\s*\|\s*(.*))?$/);
        if (match) {
            return {
                asalId: match[1],
                tujuanId: match[2],
                kelas: match[3],
                namaAsal: match[4],
                namaTujuan: match[5],
                userDesc: match[6] || ""
            };
        }
        return null;
    }

    function injectAdminTicketModal() {
        if (document.getElementById('adminTicketModal')) return;

        // Inject Styles
        const style = document.createElement('style');
        style.textContent = modalStyles;
        document.head.appendChild(style);

        // Inject HTML
        const modalHtml = `
            <div id="adminTicketModal" class="admin-ticket-modal">
                <div class="admin-ticket-modal-content">
                    <div class="admin-ticket-modal-header">
                        <h2>Pilih Rute & Kelas Penerbangan</h2>
                        <span class="admin-ticket-modal-close" id="admin-close-ticket-modal">&times;</span>
                    </div>
                    <div class="admin-ticket-modal-body">
                        <div class="admin-ticket-form-group">
                            <label>Kota Asal</label>
                            <select id="admin-ticket-asal-select" style="width: 100% !important; height: 2.2rem !important; min-height: 2.2rem !important; padding: 0.375rem 2.5rem 0.375rem 0.75rem !important; font-size: 0.9rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; background: #f8fafc url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23475569' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E&quot;) no-repeat right 0.75rem center !important; background-size: 1rem !important; color: #0f172a !important; box-sizing: border-box !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important; line-height: 1.5 !important; transition: border-color 0.2s, box-shadow 0.2s !important;">
                                <option value="">-- Pilih Kota Asal --</option>
                            </select>
                        </div>
                        <div class="admin-ticket-form-group">
                            <label>Kota Tujuan</label>
                            <select id="admin-ticket-tujuan-select" style="width: 100% !important; height: 2.2rem !important; min-height: 2.2rem !important; padding: 0.375rem 2.5rem 0.375rem 0.75rem !important; font-size: 0.9rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; background: #f8fafc url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23475569' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E&quot;) no-repeat right 0.75rem center !important; background-size: 1rem !important; color: #0f172a !important; box-sizing: border-box !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important; line-height: 1.5 !important; transition: border-color 0.2s, box-shadow 0.2s !important;" disabled>
                                <option value="">-- Pilih Kota Tujuan --</option>
                            </select>
                        </div>
                        <div class="admin-ticket-form-group">
                            <label>Kelas Tiket</label>
                            <select id="admin-ticket-kelas-select" style="width: 100% !important; height: 2.2rem !important; min-height: 2.2rem !important; padding: 0.375rem 2.5rem 0.375rem 0.75rem !important; font-size: 0.9rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; background: #f8fafc url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23475569' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E&quot;) no-repeat right 0.75rem center !important; background-size: 1rem !important; color: #0f172a !important; box-sizing: border-box !important; -webkit-appearance: none !important; -moz-appearance: none !important; appearance: none !important; line-height: 1.5 !important; transition: border-color 0.2s, box-shadow 0.2s !important;" disabled>
                                <option value="">-- Pilih Kelas --</option>
                            </select>
                        </div>
                        <div id="admin-ticket-sbm-preview" class="admin-ticket-sbm-preview">
                            <span style="color: #065f46;">Plafon SBM:</span>
                            <span id="admin-ticket-sbm-amount" style="color: #059669; font-weight: 700;">Rp 0</span>
                        </div>
                        <div class="admin-ticket-btn-group">
                            <button type="button" id="admin-btn-save-ticket" class="admin-ticket-btn admin-ticket-btn-primary" disabled>Simpan Rute</button>
                            <button type="button" id="admin-btn-cancel-ticket" class="admin-ticket-btn admin-ticket-btn-secondary">Batal</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        const div = document.createElement('div');
        div.innerHTML = modalHtml;
        document.body.appendChild(div.firstElementChild);

        // Bind events
        document.getElementById('admin-close-ticket-modal').addEventListener('click', closeAdminTicketModal);
        document.getElementById('admin-btn-cancel-ticket').addEventListener('click', closeAdminTicketModal);

        const asalSelect = document.getElementById('admin-ticket-asal-select');
        const tujuanSelect = document.getElementById('admin-ticket-tujuan-select');
        const kelasSelect = document.getElementById('admin-ticket-kelas-select');

        asalSelect.addEventListener('change', function () {
            populateAdminDestinations(this.value);
        });
        tujuanSelect.addEventListener('change', function () {
            populateAdminClasses(asalSelect.value, this.value);
        });
        kelasSelect.addEventListener('change', function () {
            updateAdminSBMPrice();
        });

        document.getElementById('admin-btn-save-ticket').addEventListener('click', saveAdminTicketRoute);
    }

    function openAdminTicketModal(row) {
        activeTicketRow = row;
        const tagHidden = row.querySelector('.admin-ticket-tag-hidden');
        const tagVal = tagHidden ? tagHidden.value : '';
        const parsed = parseTicketKeterangan(tagVal);

        const asalSelect = document.getElementById('admin-ticket-asal-select');
        const tujuanSelect = document.getElementById('admin-ticket-tujuan-select');
        const kelasSelect = document.getElementById('admin-ticket-kelas-select');
        const sbmPreview = document.getElementById('admin-ticket-sbm-preview');
        const saveBtn = document.getElementById('admin-btn-save-ticket');

        const originMap = new Map();
        ticketRoutes.forEach(r => {
            originMap.set(r.kota_asal_id, r.kota_asal_nama);
        });

        asalSelect.innerHTML = '<option value="">-- Pilih Kota Asal --</option>';
        originMap.forEach((nama, id) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = nama;
            asalSelect.appendChild(opt);
        });

        tujuanSelect.innerHTML = '<option value="">-- Pilih Kota Tujuan --</option>';
        tujuanSelect.disabled = true;
        kelasSelect.innerHTML = '<option value="">-- Pilih Kelas --</option>';
        kelasSelect.disabled = true;
        sbmPreview.style.display = 'none';
        saveBtn.disabled = true;

        if (parsed) {
            asalSelect.value = parsed.asalId;
            populateAdminDestinations(parsed.asalId);
            tujuanSelect.value = parsed.tujuanId;
            populateAdminClasses(parsed.asalId, parsed.tujuanId);
            kelasSelect.value = parsed.kelas;
            updateAdminSBMPrice();
        }

        document.getElementById('adminTicketModal').style.display = 'block';
    }

    function closeAdminTicketModal() {
        document.getElementById('adminTicketModal').style.display = 'none';
        if (activeTicketRow) {
            const tagHidden = activeTicketRow.querySelector('.admin-ticket-tag-hidden');
            const select = activeTicketRow.querySelector('select[name$="-jenis_berkas"]');
            if (select && isTicketPesawat(select) && (!tagHidden || !tagHidden.value)) {
                select.value = "";
                const originalCell = activeTicketRow.querySelector('td.original');
                const pElement = originalCell ? originalCell.querySelector('p') : null;
                if (pElement) {
                    pElement.innerHTML = pElement.dataset.originalText || '';
                }
                updateAdminEstimasi();
            }
        }
        activeTicketRow = null;
    }

    function populateAdminDestinations(originId) {
        const destSelect = document.getElementById('admin-ticket-tujuan-select');
        const kelasSelect = document.getElementById('admin-ticket-kelas-select');
        const sbmPreview = document.getElementById('admin-ticket-sbm-preview');
        const saveBtn = document.getElementById('admin-btn-save-ticket');

        destSelect.innerHTML = '<option value="">-- Pilih Kota Tujuan --</option>';
        kelasSelect.innerHTML = '<option value="">-- Pilih Kelas --</option>';
        kelasSelect.disabled = true;
        sbmPreview.style.display = 'none';
        saveBtn.disabled = true;

        if (!originId) {
            destSelect.disabled = true;
            return;
        }

        const destMap = new Map();
        ticketRoutes.forEach(r => {
            if (r.kota_asal_id == originId) {
                destMap.set(r.kota_tujuan_id, r.kota_tujuan_nama);
            }
        });

        destMap.forEach((nama, id) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = nama;
            destSelect.appendChild(opt);
        });

        destSelect.disabled = false;
    }

    function populateAdminClasses(originId, destId) {
        const kelasSelect = document.getElementById('admin-ticket-kelas-select');
        const sbmPreview = document.getElementById('admin-ticket-sbm-preview');
        const saveBtn = document.getElementById('admin-btn-save-ticket');

        kelasSelect.innerHTML = '<option value="">-- Pilih Kelas --</option>';
        sbmPreview.style.display = 'none';
        saveBtn.disabled = true;

        if (!originId || !destId) {
            kelasSelect.disabled = true;
            return;
        }

        const classes = [];
        ticketRoutes.forEach(r => {
            if (r.kota_asal_id == originId && r.kota_tujuan_id == destId) {
                classes.push({ value: r.kelas, text: r.kelas_display });
            }
        });

        classes.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.value;
            opt.textContent = c.text;
            kelasSelect.appendChild(opt);
        });

        kelasSelect.disabled = false;
    }

    function updateAdminSBMPrice() {
        const asalSelect = document.getElementById('admin-ticket-asal-select');
        const tujuanSelect = document.getElementById('admin-ticket-tujuan-select');
        const kelasSelect = document.getElementById('admin-ticket-kelas-select');
        const sbmPreview = document.getElementById('admin-ticket-sbm-preview');
        const sbmAmount = document.getElementById('admin-ticket-sbm-amount');
        const saveBtn = document.getElementById('admin-btn-save-ticket');

        const originId = asalSelect.value;
        const destId = tujuanSelect.value;
        const kelas = kelasSelect.value;

        if (!originId || !destId || !kelas) {
            sbmPreview.style.display = 'none';
            saveBtn.disabled = true;
            return;
        }

        const route = ticketRoutes.find(r => r.kota_asal_id == originId && r.kota_tujuan_id == destId && r.kelas == kelas);
        if (route) {
            sbmAmount.textContent = 'Rp ' + route.nominal.toLocaleString('id-ID');
            sbmPreview.style.display = 'flex';
            saveBtn.disabled = false;
        } else {
            sbmPreview.style.display = 'none';
            saveBtn.disabled = true;
        }
    }

    function updateAdminRowRouteLayout(row, isActive, originName, destName, kelasName) {
        const originalCell = row.querySelector('td.original');
        if (!originalCell) return;
        let pElement = originalCell.querySelector('p');
        if (!pElement) {
            pElement = document.createElement('p');
            originalCell.appendChild(pElement);
        }

        if (typeof pElement.dataset.originalText === 'undefined') {
            pElement.dataset.originalText = pElement.textContent.trim();
        }

        if (isActive && originName && destName && kelasName) {
            row.classList.add('has-ticket-route');
            pElement.className = 'admin-ticket-route-badge-active';
            pElement.innerHTML = `✈️ ${originName} → ${destName} (${kelasName}) <button type="button" class="admin-ticket-route-edit admin-ticket-route-edit-btn" style="background:none;border:none;cursor:pointer;padding:0;margin-left:5px;" title="Ubah Rute">✏️</button>`;
        } else {
            row.classList.remove('has-ticket-route');
            pElement.className = '';
            pElement.innerHTML = pElement.dataset.originalText || '';
        }
    }

    function saveAdminTicketRoute() {
        if (!activeTicketRow) return;

        const asalSelect = document.getElementById('admin-ticket-asal-select');
        const tujuanSelect = document.getElementById('admin-ticket-tujuan-select');
        const kelasSelect = document.getElementById('admin-ticket-kelas-select');

        const originId = asalSelect.value;
        const destId = tujuanSelect.value;
        const kelas = kelasSelect.value;

        const originName = asalSelect.options[asalSelect.selectedIndex].text;
        const destName = tujuanSelect.options[tujuanSelect.selectedIndex].text;
        const kelasName = kelasSelect.options[kelasSelect.selectedIndex].text;

        const route = ticketRoutes.find(r => r.kota_asal_id == originId && r.kota_tujuan_id == destId && r.kelas == kelas);
        if (!route) return;

        const tagVal = `[SBM-TIKET:${originId}-${destId}-${kelas}:${originName}:${destName}]`;
        const tagHidden = activeTicketRow.querySelector('.admin-ticket-tag-hidden');
        if (tagHidden) tagHidden.value = tagVal;

        updateAdminRowRouteLayout(activeTicketRow, true, originName, destName, kelasName);

        const nominalInput = activeTicketRow.querySelector('input[name$="-nominal"]');
        if (nominalInput) {
            nominalInput.value = route.nominal.toLocaleString('id-ID');
        }

        document.getElementById('adminTicketModal').style.display = 'none';
        activeTicketRow = null;

        updateAdminEstimasi();
    }

    function toggleAdminHotelInputs(row, isBadgeActive) {
        const malamInput = row.querySelector('input[name$="-malam_menginap"]');
        const keteranganInput = row.querySelector('input[name$="-keterangan"]');
        
        if (isBadgeActive) {
            if (malamInput) {
                malamInput.readOnly = true;
                malamInput.style.backgroundColor = '#f1f5f9';
                malamInput.style.cursor = 'not-allowed';
            }
            if (keteranganInput) {
                keteranganInput.readOnly = true;
                keteranganInput.style.backgroundColor = '#f1f5f9';
                keteranganInput.style.cursor = 'not-allowed';
                keteranganInput.removeAttribute('required');
            }
        } else {
            if (malamInput) {
                malamInput.readOnly = false;
                malamInput.style.backgroundColor = '';
                malamInput.style.cursor = '';
            }
            if (keteranganInput) {
                keteranganInput.readOnly = false;
                keteranganInput.style.backgroundColor = '';
                keteranganInput.style.cursor = '';
            }
        }
    }

    function updateAdminRowHotelLayout(row, isActive, provinsiNama, checkIn, checkOut) {
        const originalCell = row.querySelector('td.original') || row.querySelector('td.field-jenis_berkas') || row.querySelector('td:first-child');
        if (!originalCell) return;
        let hElement = originalCell.querySelector('p.hotel-badge');
        if (!hElement) {
            hElement = document.createElement('p');
            hElement.className = 'hotel-badge';
            originalCell.appendChild(hElement);
        }

        if (typeof hElement.dataset.originalText === 'undefined') {
            hElement.dataset.originalText = hElement.textContent.trim();
        }

        if (isActive && provinsiNama && checkIn && checkOut) {
            row.classList.add('has-hotel-route');
            hElement.className = 'hotel-badge admin-ticket-route-badge-active';
            hElement.style.setProperty('background-color', '#ecfdf5', 'important');
            hElement.style.setProperty('border-color', '#a7f3d0', 'important');
            hElement.style.setProperty('color', '#065f46', 'important');
            hElement.style.setProperty('top', '0.4rem', 'important');
            hElement.innerHTML = `🏨 ${provinsiNama} (${formatTglIndo(checkIn)} - ${formatTglIndo(checkOut)}) <button type="button" class="admin-hotel-route-edit admin-ticket-route-edit-btn" style="background:none;border:none;cursor:pointer;padding:0;margin-left:5px;" title="Ubah Akomodasi">✏️</button>`;
        } else {
            row.classList.remove('has-hotel-route');
            hElement.className = 'hotel-badge';
            hElement.innerHTML = '';
        }
    }

    function handleAdminJenisChange(row) {
        const select = row.querySelector('select[name$="-jenis_berkas"]');
        if (!select) return;

        const tagHidden = row.querySelector('.admin-ticket-tag-hidden');
        const hotelTagHidden = row.querySelector('.admin-hotel-tag-hidden');

        if (isTicketPesawat(select)) {
            if (countFlightTickets(row) >= 2) {
                alert("Tiket pesawat hanya dapat diinput maksimal 2 kali (untuk pergi dan pulang) sesuai aturan SBM.");
                select.value = "";
                if (tagHidden) tagHidden.value = '';
                updateAdminRowRouteLayout(row, false);
                updateAdminEstimasi();
                return;
            }
            if (tagHidden && tagHidden.value) {
                const parsed = parseTicketKeterangan(tagHidden.value);
                if (parsed) {
                    const kelasDisplay = parsed.kelas === 'ekonomi' ? 'Ekonomi' : 'Bisnis';
                    updateAdminRowRouteLayout(row, true, parsed.namaAsal, parsed.namaTujuan, kelasDisplay);
                }
            } else {
                openAdminTicketModal(row);
            }
            if (hotelTagHidden) hotelTagHidden.value = '';
            updateAdminRowHotelLayout(row, false);
            toggleAdminHotelInputs(row, false);
        } else if (isPenginapanBerkas(select)) {
            if (hotelTagHidden && hotelTagHidden.value) {
                const parsed = parsePenginapanKeterangan(hotelTagHidden.value);
                if (parsed) {
                    updateAdminRowHotelLayout(row, true, parsed.provinsiNama, parsed.checkIn, parsed.checkOut);
                    toggleAdminHotelInputs(row, true);
                }
            } else {
                openAdminHotelModal(row);
            }
            if (tagHidden) tagHidden.value = '';
            updateAdminRowRouteLayout(row, false);
        } else {
            if (tagHidden) tagHidden.value = '';
            updateAdminRowRouteLayout(row, false);
            if (hotelTagHidden) hotelTagHidden.value = '';
            updateAdminRowHotelLayout(row, false);
            toggleAdminHotelInputs(row, false);
            updateAdminEstimasi();
        }
    }

    function setupAdminRow(row) {
        if (row.classList.contains('ticket-setup-done')) return;
        row.classList.add('ticket-setup-done');

        const select = row.querySelector('select[name$="-jenis_berkas"]');
        if (!select) return;

        const originalCell = row.querySelector('td.original') || row.querySelector('td.field-jenis_berkas') || row.querySelector('td:first-child');
        if (!originalCell) return;

        // Create/get hidden tag input inside originalCell
        let tagHidden = originalCell.querySelector('.admin-ticket-tag-hidden');
        if (!tagHidden) {
            tagHidden = document.createElement('input');
            tagHidden.type = 'hidden';
            tagHidden.className = 'admin-ticket-tag-hidden';
            originalCell.appendChild(tagHidden);
        }

        let hotelTagHidden = originalCell.querySelector('.admin-hotel-tag-hidden');
        if (!hotelTagHidden) {
            hotelTagHidden = document.createElement('input');
            hotelTagHidden.type = 'hidden';
            hotelTagHidden.className = 'admin-hotel-tag-hidden';
            originalCell.appendChild(hotelTagHidden);
        }

        // Get or create p element for ticket route badge
        let pElement = originalCell.querySelector('p.ticket-badge');
        if (!pElement) {
            pElement = document.createElement('p');
            pElement.className = 'ticket-badge';
            originalCell.appendChild(pElement);
        }

        // Get or create p element for hotel route badge
        let hElement = originalCell.querySelector('p.hotel-badge');
        if (!hElement) {
            hElement = document.createElement('p');
            hElement.className = 'hotel-badge';
            originalCell.appendChild(hElement);
        }

        // Store original text if not already stored
        if (typeof pElement.dataset.originalText === 'undefined') {
            pElement.dataset.originalText = pElement.textContent.trim();
        }
        if (typeof hElement.dataset.originalText === 'undefined') {
            hElement.dataset.originalText = hElement.textContent.trim();
        }

        // Load existing tag from keterangan field
        const descInput = row.querySelector('input[name$="-keterangan"]');
        if (descInput) {
            const parsedTicket = parseTicketKeterangan(descInput.value);
            const parsedHotel = parsePenginapanKeterangan(descInput.value);
            if (parsedTicket) {
                const tagVal = `[SBM-TIKET:${parsedTicket.asalId}-${parsedTicket.tujuanId}-${parsedTicket.kelas}:${parsedTicket.namaAsal}:${parsedTicket.namaTujuan}]`;
                tagHidden.value = tagVal;
                descInput.value = parsedTicket.userDesc;

                const kelasDisplay = parsedTicket.kelas === 'ekonomi' ? 'Ekonomi' : 'Bisnis';
                updateAdminRowRouteLayout(row, true, parsedTicket.namaAsal, parsedTicket.namaTujuan, kelasDisplay);
            } else if (parsedHotel) {
                const tagVal = `[SBM-PENGINAPAN:${parsedHotel.checkIn}:${parsedHotel.checkOut}:${parsedHotel.nights}:${parsedHotel.provinsiId}:${parsedHotel.provinsiNama}]`;
                hotelTagHidden.value = tagVal;
                descInput.value = parsedHotel.userDesc;

                updateAdminRowHotelLayout(row, true, parsedHotel.provinsiNama, parsedHotel.checkIn, parsedHotel.checkOut);
                toggleAdminHotelInputs(row, true);
            } else {
                updateAdminRowRouteLayout(row, false);
                updateAdminRowHotelLayout(row, false);
                toggleAdminHotelInputs(row, false);
            }
        } else {
            updateAdminRowRouteLayout(row, false);
            updateAdminRowHotelLayout(row, false);
            toggleAdminHotelInputs(row, false);
        }
    }

    function initializeAdminTicketRows() {
        const rows = document.querySelectorAll('.inline-related tr.form-row:not(.empty-form)');
        rows.forEach(row => {
            setupAdminRow(row);
        });
    }

    function getAdminTransitDays() {
        const harian = [];
        const harianGroup = document.querySelector('#harian_details-group');
        if (harianGroup) {
            const harianRows = harianGroup.querySelectorAll('tr.form-row:not(.empty-form)');
            harianRows.forEach((row, index) => {
                const provSelect = row.querySelector('select[name$="-provinsi"]');
                const jenisSelect = row.querySelector('select[name$="-jenis_harian"]');
                const hariKeTd = row.querySelector('.field-hari_ke');
                const hariKe = hariKeTd ? (parseInt(hariKeTd.textContent.trim()) || 0) : (index + 1);
                const tglInput = row.querySelector('input[name$="-tanggal"]');
                
                if (provSelect && jenisSelect && hariKe && tglInput) {
                    const provOpt = provSelect.options[provSelect.selectedIndex];
                    const provNama = provOpt ? provOpt.text : '';
                    harian.push({
                        hari_ke: hariKe,
                        tanggal: tglInput.value,
                        provinsi_id: provSelect.value,
                        provinsi_nama: provNama,
                        jenis_harian: jenisSelect.value || 'luar_kota'
                    });
                }
            });
        }
        harian.sort((a, b) => a.hari_ke - b.hari_ke);
        return harian;
    }

    function updateAdminHotelNightsPreview() {
        const checkInVal = document.getElementById('admin-hotel-check-in').value;
        const checkOutVal = document.getElementById('admin-hotel-check-out').value;
        const previewEl = document.getElementById('admin-hotel-nights-preview');
        const countEl = document.getElementById('admin-hotel-nights-count');
        
        if (checkInVal && checkOutVal) {
            const checkInDate = new Date(checkInVal);
            const checkOutDate = new Date(checkOutVal);
            const timeDiff = checkOutDate - checkInDate;
            const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
            
            if (daysDiff > 0) {
                countEl.textContent = `${daysDiff} Malam`;
                previewEl.style.display = 'flex';
                return;
            }
        }
        previewEl.style.display = 'none';
    }

    function injectAdminHotelModal() {
        if (document.getElementById('adminHotelModal')) return;

        // Inject HTML
        const modalHtml = `
            <div id="adminHotelModal" class="admin-ticket-modal">
                <div class="admin-ticket-modal-content" style="max-width: 500px;">
                    <div class="admin-ticket-modal-header">
                        <h2>Pilih Segment & Tanggal Menginap</h2>
                        <span class="admin-ticket-modal-close" id="admin-close-hotel-modal">&times;</span>
                    </div>
                    <div class="admin-ticket-modal-body">
                        <div class="admin-ticket-form-group">
                            <label>Provinsi (SBM)</label>
                            <select id="admin-hotel-province-select" style="width: 100% !important; padding: 0.5rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; box-sizing: border-box !important;">
                                <!-- Will be populated dynamically -->
                            </select>
                        </div>
                        <div style="display: flex; gap: 1rem; margin-bottom: 1.25rem;">
                            <div class="admin-ticket-form-group" style="flex: 1;">
                                <label>Tanggal Check-in</label>
                                <input type="date" id="admin-hotel-check-in" style="width: 100% !important; padding: 0.5rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; box-sizing: border-box !important;">
                            </div>
                            <div class="admin-ticket-form-group" style="flex: 1;">
                                <label>Tanggal Check-out</label>
                                <input type="date" id="admin-hotel-check-out" style="width: 100% !important; padding: 0.5rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; box-sizing: border-box !important;">
                            </div>
                        </div>
                        <div id="admin-hotel-nights-preview" style="display: none; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 0.5rem; padding: 0.75rem 1rem; margin-bottom: 1.25rem; align-items: center; justify-content: space-between;">
                            <span style="font-size: 0.875rem; color: #1e3a8a; font-weight: 600;">Jumlah Malam Menginap:</span>
                            <span id="admin-hotel-nights-count" style="font-size: 1.125rem; color: #1d4ed8; font-weight: 700;">0 Malam</span>
                        </div>
                        <div class="admin-ticket-form-group">
                            <label>Nama Hotel / Keterangan Tambahan</label>
                            <input type="text" id="admin-hotel-user-desc" placeholder="Contoh: Hotel Grand Hyatt (Opsional)" style="width: 100% !important; padding: 0.5rem !important; border-radius: 0.375rem !important; border: 1px solid #cbd5e1 !important; box-sizing: border-box !important;">
                        </div>
                        <div class="admin-ticket-btn-group">
                            <button type="button" id="admin-btn-save-hotel" class="admin-ticket-btn admin-ticket-btn-primary">Simpan Akomodasi</button>
                            <button type="button" id="admin-btn-cancel-hotel" class="admin-ticket-btn admin-ticket-btn-secondary">Batal</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        const div = document.createElement('div');
        div.innerHTML = modalHtml;
        document.body.appendChild(div.firstElementChild);

        // Bind events
        document.getElementById('admin-close-hotel-modal').addEventListener('click', closeAdminHotelModal);
        document.getElementById('admin-btn-cancel-hotel').addEventListener('click', closeAdminHotelModal);
        document.getElementById('admin-btn-save-hotel').addEventListener('click', saveAdminHotelRoute);
        
        document.getElementById('admin-hotel-check-in').addEventListener('input', updateAdminHotelNightsPreview);
        document.getElementById('admin-hotel-check-out').addEventListener('input', updateAdminHotelNightsPreview);
    }

    function openAdminHotelModal(row) {
        activeHotelRow = row;
        const tagHidden = row.querySelector('.admin-hotel-tag-hidden');
        const tagVal = tagHidden ? tagHidden.value : '';
        const parsed = parsePenginapanKeterangan(tagVal);

        const provinceSelect = document.getElementById('admin-hotel-province-select');
        provinceSelect.innerHTML = '';

        // Get destination province
        const destProvId = document.querySelector('#id_tujuan_provinsi')?.value;
        const destProvNama = document.querySelector('#id_tujuan_provinsi_nama')?.value || 'Provinsi Utama';
        
        const addedProvinceIds = new Set();
        
        // Add main destination province first
        if (destProvId) {
            const opt = document.createElement('option');
            opt.value = destProvId;
            opt.textContent = destProvNama;
            provinceSelect.appendChild(opt);
            addedProvinceIds.add(destProvId);
        }

        // Get unique provinces from transit rows
        const harian = getAdminTransitDays();
        harian.forEach(day => {
            if (day.provinsi_id && !addedProvinceIds.has(day.provinsi_id)) {
                const opt = document.createElement('option');
                opt.value = day.provinsi_id;
                opt.textContent = day.provinsi_nama;
                provinceSelect.appendChild(opt);
                addedProvinceIds.add(day.provinsi_id);
            }
        });

        // Set min and max limits for date inputs
        const tanggalBerangkat = document.querySelector('#id_tanggal_berangkat')?.value;
        const tanggalKembali = document.querySelector('#id_tanggal_kembali')?.value;
        
        const checkInInput = document.getElementById('admin-hotel-check-in');
        const checkOutInput = document.getElementById('admin-hotel-check-out');

        if (tanggalBerangkat) {
            checkInInput.min = tanggalBerangkat;
            checkOutInput.min = tanggalBerangkat;
        }
        if (tanggalKembali) {
            checkInInput.max = tanggalKembali;
            checkOutInput.max = tanggalKembali;
        }

        // Populate current values
        if (parsed) {
            provinceSelect.value = parsed.provinsiId;
            checkInInput.value = parsed.checkIn;
            checkOutInput.value = parsed.checkOut;
        } else {
            if (destProvId) provinceSelect.value = destProvId;
            checkInInput.value = tanggalBerangkat || '';
            checkOutInput.value = tanggalKembali || '';
        }

        updateAdminHotelNightsPreview();

        const descInput = document.getElementById('admin-hotel-user-desc');
        if (descInput) {
            descInput.value = parsed ? parsed.userDesc : '';
        }

        document.getElementById('adminHotelModal').style.display = 'block';
    }

    function closeAdminHotelModal() {
        document.getElementById('adminHotelModal').style.display = 'none';
        if (activeHotelRow) {
            const tagHidden = activeHotelRow.querySelector('.admin-hotel-tag-hidden');
            const select = activeHotelRow.querySelector('select[name$="-jenis_berkas"]');
            if (select && isPenginapanBerkas(select) && (!tagHidden || !tagHidden.value)) {
                select.value = "";
                updateAdminRowHotelLayout(activeHotelRow, false);
                toggleAdminHotelInputs(activeHotelRow, false);
                updateAdminEstimasi();
            }
        }
        activeHotelRow = null;
    }

    function saveAdminHotelRoute() {
        if (!activeHotelRow) return;

        const checkIn = document.getElementById('admin-hotel-check-in').value;
        const checkOut = document.getElementById('admin-hotel-check-out').value;
        const provSelect = document.getElementById('admin-hotel-province-select');
        const provId = provSelect.value;
        const provNama = provSelect.options[provSelect.selectedIndex]?.text || '';

        if (!provId) {
            alert("Silakan pilih provinsi terlebih dahulu.");
            return;
        }
        if (!checkIn || !checkOut) {
            alert("Silakan isi tanggal check-in dan check-out.");
            return;
        }

        const checkInDate = new Date(checkIn);
        const checkOutDate = new Date(checkOut);
        
        const tanggalBerangkat = document.querySelector('#id_tanggal_berangkat')?.value;
        const tanggalKembali = document.querySelector('#id_tanggal_kembali')?.value;
        
        if (tanggalBerangkat && checkIn < tanggalBerangkat) {
            alert(`Tanggal check-in tidak boleh kurang dari tanggal berangkat (${formatTglIndo(tanggalBerangkat)}).`);
            return;
        }
        if (tanggalKembali && checkOut > tanggalKembali) {
            alert(`Tanggal check-out tidak boleh melebihi tanggal kembali (${formatTglIndo(tanggalKembali)}).`);
            return;
        }
        
        const timeDiff = checkOutDate - checkInDate;
        const nights = Math.ceil(timeDiff / (1000 * 3600 * 24));

        if (nights <= 0) {
            alert("Tanggal check-out harus lebih besar dari tanggal check-in (minimal 1 malam).");
            return;
        }

        const userDescInput = document.getElementById('admin-hotel-user-desc');
        const userDesc = userDescInput ? userDescInput.value.trim() : '';

        const tagVal = `[SBM-PENGINAPAN:${checkIn}:${checkOut}:${nights}:${provId}:${provNama}]`;
        const tagHidden = activeHotelRow.querySelector('.admin-hotel-tag-hidden');
        if (tagHidden) tagHidden.value = tagVal;

        updateAdminRowHotelLayout(activeHotelRow, true, provNama, checkIn, checkOut);

        const malamInput = activeHotelRow.querySelector('input[name$="-malam_menginap"]');
        if (malamInput) {
            malamInput.value = nights;
        }

        const keteranganInput = activeHotelRow.querySelector('input[name$="-keterangan"]');
        if (keteranganInput) {
            keteranganInput.value = userDesc;
        }

        toggleAdminHotelInputs(activeHotelRow, true);

        document.getElementById('adminHotelModal').style.display = 'none';
        activeHotelRow = null;

        updateAdminEstimasi();
    }

    function fetchTicketRoutes() {
        fetch('/perjalanan/api/get-standar-biaya-tiket/')
            .then(res => res.json())
            .then(data => {
                ticketRoutes = data.routes || [];
                ticketPesawatIds = data.ticket_pesawat_ids || [];
                penginapanBerkasIds = data.penginapan_berkas_ids || [];
                initializeAdminTicketRows();
            })
            .catch(err => console.error("Error fetching ticket routes in admin:", err));
    }

    // Initialize Admin Ticket Features
    injectAdminTicketModal();
    injectAdminHotelModal();
    fetchTicketRoutes();

    // Document-level event delegation for select changes & edit button clicks
    document.addEventListener('change', function (e) {
        if (e.target.matches('select[name$="-jenis_berkas"]')) {
            const select = e.target;
            const row = select.closest('tr.form-row');
            if (row) {
                setupAdminRow(row);
                handleAdminJenisChange(row);
            }
        }
    });

    document.addEventListener('click', function (e) {
        const editBtn = e.target.closest('.admin-ticket-route-edit');
        if (editBtn) {
            e.preventDefault();
            const row = editBtn.closest('tr.form-row');
            if (row) {
                setupAdminRow(row);
                openAdminTicketModal(row);
            }
        }

        const editHotelBtn = e.target.closest('.admin-hotel-route-edit');
        if (editHotelBtn) {
            e.preventDefault();
            const row = editHotelBtn.closest('tr.form-row');
            if (row) {
                setupAdminRow(row);
                openAdminHotelModal(row);
            }
        }
    });

    if (window.django && django.jQuery) {
        django.jQuery(document).on('formset:added', function (event, $row, formsetName) {
            let row = null;
            if ($row) {
                if ($row.length) {
                    row = $row[0];
                } else if ($row.nodeType === 1) {
                    row = $row;
                }
            }
            if (row) {
                setupAdminRow(row);
            }
        });
    }

    function setupAdminAccordion() {
        const harianGroup = document.querySelector('#harian_details-group');
        if (!harianGroup) return;

        const h2 = harianGroup.querySelector('h2');
        if (!h2) return;

        // Apply styles to h2 to make it clickable and style it like a premium accordion
        h2.style.cursor = 'pointer';
        h2.style.display = 'flex';
        h2.style.justifyContent = 'space-between';
        h2.style.alignItems = 'center';
        h2.style.userSelect = 'none';

        // Create the chevron indicator
        const chevron = document.createElement('span');
        chevron.style.display = 'inline-block';
        chevron.style.transition = 'transform 0.2s ease';
        chevron.style.fontSize = '0.9rem';
        chevron.style.marginRight = '12px';
        chevron.style.color = '#ffffff';
        chevron.innerHTML = '&#9656;'; // Closed by default: ▶
        h2.appendChild(chevron);

        // Gather all siblings of h2 within the group (these contain the tabular inline formset elements)
        const contentSiblings = [];
        let next = h2.nextElementSibling;
        while (next) {
            contentSiblings.push(next);
            next = next.nextElementSibling;
        }

        // Auto-expand if there are validation errors within the group
        const hasErrors = harianGroup.querySelector('.errors, .errorlist') !== null;
        let isExpanded = hasErrors;

        // Apply initial state (hidden by default unless there are errors)
        contentSiblings.forEach(el => {
            el.style.display = isExpanded ? '' : 'none';
        });
        if (isExpanded) {
            chevron.innerHTML = '&#9662;'; // Open: ▼
        }

        // Hover feedback styles on the header
        h2.style.transition = 'filter 0.2s';
        h2.addEventListener('mouseenter', () => {
            h2.style.filter = 'brightness(1.05)';
        });
        h2.addEventListener('mouseleave', () => {
            h2.style.filter = '';
        });

        // Click handler to toggle expand/collapse state
        h2.addEventListener('click', () => {
            isExpanded = !isExpanded;
            contentSiblings.forEach(el => {
                el.style.display = isExpanded ? '' : 'none';
            });
            chevron.innerHTML = isExpanded ? '&#9662;' : '&#9656;';
        });
    }

    // Initialize Accordion for Uang Harian detail section
    setupAdminAccordion();

    // Run initial estimation on load in Admin
    setTimeout(updateAdminEstimasi, 500);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdminFilter);
} else {
    initAdminFilter();
}
