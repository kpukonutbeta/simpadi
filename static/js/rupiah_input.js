/**
 * rupiah_input.js
 * Formats numeric/decimal admin input fields with thousands separator (dot).
 * Works purely as display formatting - the input value stays as plain digits
 * separated by dots which Django's DecimalField understands via cleaned_data.
 */
(function() {
    'use strict';

    console.log('SIMPADI Rupiah Input JS loaded successfully - Version 6');

    var RUPIAH_FIELD_PATTERNS = [
        'uang_harian', 'uang_representasi', 'plafon_penginapan',
        'uang_harian_fullboard',
        'nominal', 'pagu', 'sisa_pagu', 'biaya_taksi', 'taksi'
    ];

    function toRibuan(val) {
        var digits = String(val).replace(/\./g, '').replace(/\D/g, '');
        if (!digits) return '';
        return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    }

    function fromRibuan(val) {
        return String(val).replace(/\./g, '');
    }

    function isRupiahInput(input) {
        if (!input || input.tagName !== 'INPUT') return false;
        var name = (input.name || input.id || '').toLowerCase();
        return Boolean(
            (typeof input.dataset.rupiah !== 'undefined') ||
            input.hasAttribute('data-rupiah') ||
            (input.classList && input.classList.contains('rupiah')) ||
            RUPIAH_FIELD_PATTERNS.some(function(pat) { return name.indexOf(pat) !== -1; })
        );
    }

    function normalizeInput(input) {
        if (!isRupiahInput(input)) return;

        try {
            input.type = 'text';
            input.setAttribute('inputmode', 'numeric');
            input.setAttribute('autocomplete', 'off');
        } catch (e) {
            console.error('Failed to set rupiah input attrs:', e);
        }

        if (input.dataset.rupiahInit !== '1') {
            input.dataset.rupiahInit = '1';
            if (input.value) {
                input.value = toRibuan(input.value);
            }
        }
    }

    function formatInput(input) {
        if (!isRupiahInput(input)) return;
        var raw = fromRibuan(input.value);
        var formatted = toRibuan(raw);
        if (input.value !== formatted) {
            input.value = formatted;
        }
    }

    function stripAllRupiahValues(root) {
        (root || document).querySelectorAll('input').forEach(function(input) {
            if (isRupiahInput(input)) {
                input.value = fromRibuan(input.value);
            }
        });
    }

    function bindDelegatedEvents() {
        document.addEventListener('input', function(e) {
            if (isRupiahInput(e.target)) {
                formatInput(e.target);
            }
        }, true);

        document.addEventListener('blur', function(e) {
            if (isRupiahInput(e.target)) {
                formatInput(e.target);
            }
        }, true);

        document.addEventListener('focus', function(e) {
            if (isRupiahInput(e.target)) {
                normalizeInput(e.target);
            }
        }, true);

        document.addEventListener('submit', function(e) {
            stripAllRupiahValues(e.target);
        }, true);
    }

    function initAllRupiahInputs() {
        document.querySelectorAll('input').forEach(function(input) {
            normalizeInput(input);
        });
    }

    function boot() {
        initAllRupiahInputs();
        bindDelegatedEvents();

        // Fallback pass in case Django admin or related widgets render a bit later.
        setTimeout(initAllRupiahInputs, 150);
        setTimeout(initAllRupiahInputs, 600);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
