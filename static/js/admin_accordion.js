document.addEventListener('DOMContentLoaded', function() {
    const inlineGroups = document.querySelectorAll('.inline-group .tabular');
    
    // Cek status SPD
    let isNotDraft = false;
    const statusSelect = document.querySelector('#id_status');
    const statusReadonly = document.querySelector('.field-status .readonly');
    
    if (statusSelect) {
        if (statusSelect.value && statusSelect.value.toUpperCase() !== 'DRAFT') {
            isNotDraft = true;
        }
    } else if (statusReadonly) {
        if (statusReadonly.textContent.trim().toUpperCase() !== 'DRAFT') {
            isNotDraft = true;
        }
    }
    
    inlineGroups.forEach(function(tabularDiv) {
        const fieldset = tabularDiv.querySelector('fieldset');
        if (!fieldset) return;
        
        const h2 = fieldset.querySelector('h2');
        if (!h2) return;
        
        const titleText = h2.textContent.trim().toLowerCase();
        
        const targetSections = [
            'detail transit perjalanan dinas',
            'berkas pendukung untuk penginapan',
            'berkas pendukung untuk transportasi',
            'berkas pendukung tanpa nominal biaya'
        ];
        
        const isTargetSection = targetSections.some(sec => titleText.includes(sec));
        
        if (isTargetSection) {
            h2.style.cursor = 'pointer';
            h2.style.display = 'flex';
            h2.style.justifyContent = 'space-between';
            h2.style.alignItems = 'center';
            h2.style.userSelect = 'none';
            
            const arrow = document.createElement('span');
            arrow.innerHTML = '&#9660;'; // Down arrow
            arrow.style.transition = 'transform 0.2s ease';
            arrow.style.fontSize = '1.2em';
            h2.appendChild(arrow);
            
            const toggleAccordion = function() {
                const isCollapsed = tabularDiv.classList.toggle('custom-collapsed');
                
                const children = fieldset.children;
                for (let i = 0; i < children.length; i++) {
                    const child = children[i];
                    if (child.tagName.toLowerCase() !== 'h2') {
                        child.style.display = isCollapsed ? 'none' : '';
                    }
                }
                
                arrow.style.transform = isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)';
            };
            
            h2.addEventListener('click', toggleAccordion);
            
            // Logika default tertutup/terbuka berdasarkan status
            if (isNotDraft) {
                toggleAccordion(); // Jika bukan draft, semua tertutup
            } else {
                if (titleText.includes('detail transit perjalanan dinas')) {
                    toggleAccordion(); // Jika draft, hanya Detail Transit yang tertutup
                }
            }
        }
    });
});
