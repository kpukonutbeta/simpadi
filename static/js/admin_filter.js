document.addEventListener('DOMContentLoaded', function() {
    const suratTugasSelect = document.querySelector('#id_surat_tugas');
    const pegawaiSelect = document.querySelector('#id_pegawai');

    if (suratTugasSelect && pegawaiSelect) {
        suratTugasSelect.addEventListener('change', function() {
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
                if (jbId) {
                    berkas.push({
                        'jenis_berkas_id': parseInt(jbId),
                        'nominal': parseFloat(nominalVal) || 0.0
                    });
                }
            }
        });

        const payload = {
            tanggal_berangkat: tanggalBerangkat,
            tanggal_kembali: tanggalKembali,
            tujuan_provinsi: tujuanProvinsi,
            tidak_menginap: tidakMenginap,
            jenis_transportasi: jenisTransportasi,
            tahun_sbm: tahunSbm,
            pegawai_id: pegawaiId,
            berkas: berkas
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
            const totalEl = document.querySelector('.field-total_dibayarkan div.readonly');

            if (harianEl) harianEl.textContent = formatRupiah(data.uang_harian_riil);
            if (reprEl) reprEl.textContent = formatRupiah(data.uang_representasi_riil);
            if (hotelEl) hotelEl.textContent = formatRupiah(data.biaya_penginapan_riil);
            if (transportEl) transportEl.textContent = formatRupiah(data.biaya_transportasi_riil);
            if (totalEl) totalEl.textContent = formatRupiah(data.total_dibayarkan);
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

    // Delegate listener to capture edits/additions/deletions in the inline berkas rows in Admin
    document.addEventListener('change', function(e) {
        if (e.target.matches('input[name$="-nominal"]') || e.target.matches('select[name$="-jenis_berkas"]') || e.target.matches('input[name$="-DELETE"]')) {
            updateAdminEstimasi();
        }
    });
    document.addEventListener('input', function(e) {
        if (e.target.matches('input[name$="-nominal"]')) {
            updateAdminEstimasi();
        }
    });

    // Thousand separator formatting for nominal inputs
    function formatRupiahInput(value) {
        let digits = value.replace(/\D/g, '');
        if (!digits) return '';
        return parseInt(digits, 10).toLocaleString('id-ID');
    }

    document.addEventListener('input', function(e) {
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

    // Strip dots before form submit in Admin
    const form = document.getElementById('perjalanandinas_form') || document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function() {
            form.querySelectorAll('input[name$="-nominal"]').forEach(input => {
                input.value = input.value.replace(/\./g, '');
            });
        });
    }

    // Run initial estimation on load in Admin
    setTimeout(updateAdminEstimasi, 500);
});
