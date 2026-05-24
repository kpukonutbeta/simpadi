/**
 * rupiah_input.js
 * Formats numeric/decimal admin input fields with thousands separator (dot).
 * Works purely as display formatting - the input value stays as plain digits
 * separated by dots which Django's DecimalField understands via cleaned_data.
 */
(function() {
    'use strict';

    console.log("SIMPADI Rupiah Input JS loaded successfully - Version 5");

    function toRibuan(val) {
        var digits = String(val).replace(/\./g, '').replace(/\D/g, '');
        if (!digits) return '';
        return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    function fromRibuan(val) {
        return String(val).replace(/\./g, '');
    }

    function initRupiahInput(input) {
        if (input.dataset.rupiahInit) return;
        input.dataset.rupiahInit = '1';
        
        console.log("Initializing formatting for input:", input.name || input.id);
        
        try {
            input.type = 'text';
            input.setAttribute('inputmode', 'numeric');
        } catch (e) {
            console.error("Failed to set input type to text:", e);
        }

        // Format initial value
        if (input.value) {
            input.value = toRibuan(input.value);
        }

        input.addEventListener('input', function() {
            var pos = input.selectionStart;
            var prevLen = input.value.length;
            var raw = fromRibuan(input.value);
            var formatted = toRibuan(raw);
            input.value = formatted;
            var newPos = pos + (formatted.length - prevLen);
            try { input.setSelectionRange(newPos, newPos); } catch(e) {}
        });

        input.addEventListener('blur', function() {
            input.value = toRibuan(fromRibuan(input.value));
        });

        // Before form submit: strip dots so Django gets plain integer
        var form = input.closest('form');
        if (form && !form.dataset.rupiahSubmitBound) {
            form.dataset.rupiahSubmitBound = '1';
            form.addEventListener('submit', function() {
                form.querySelectorAll('[data-rupiah-init]').forEach(function(el) {
                    el.value = fromRibuan(el.value);
                });
            });
        }
    }

    var RUPIAH_FIELD_PATTERNS = [
        'uang_harian', 'uang_representasi', 'plafon_penginapan',
        'uang_harian_fullboard',
        'nominal', 'pagu', 'sisa_pagu', 'biaya_taksi', 'taksi'
    ];

    function applyToMatchingInputs() {
        var inputs = document.querySelectorAll('input');
        console.log("Total input elements found on page:", inputs.length);
        inputs.forEach(function(input) {
            var name = (input.name || input.id || '').toLowerCase();
            var match = RUPIAH_FIELD_PATTERNS.some(function(pat) {
                return name.indexOf(pat) !== -1;
            });
            if (match) {
                initRupiahInput(input);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyToMatchingInputs);
    } else {
        applyToMatchingInputs();
    }
})();
