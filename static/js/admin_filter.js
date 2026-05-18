document.addEventListener('DOMContentLoaded', function() {
    const suratTugasSelect = document.querySelector('#id_surat_tugas');
    const pegawaiSelect = document.querySelector('#id_pegawai');

    if (suratTugasSelect && pegawaiSelect) {
        suratTugasSelect.addEventListener('change', function() {
            const suratTugasId = this.value;
            if (!suratTugasId) {
                // If no surat tugas selected, maybe clear or reset?
                // For now, we'll leave it as is or could clear it.
                return;
            }

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
                })
                .catch(error => console.error('Error fetching pegawai:', error));
        });

        // Trigger on load if edit mode
        if (suratTugasSelect.value) {
            // We might want to keep the current selection but filter the rest
            // Initial trigger to ensure only assigned ones are visible
            suratTugasSelect.dispatchEvent(new Event('change'));
        }
    }
});
