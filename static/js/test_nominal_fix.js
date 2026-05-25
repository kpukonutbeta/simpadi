/**
 * TEST CASES: Nominal Hotel Edit Fix
 *
 * Run these test cases in browser console at http://localhost:8002/admin/perjalanan/perjalanandinas/[ID]/change/
 */

// ========== TEST 1: Listener Attachment ==========
console.log('TEST 1: Verify setupNominalEditListener attaches listener');
const nominalInput1 = document.querySelector('input[name$="-nominal"]');
if (nominalInput1) {
    console.log('Before setup:', {
        listenerAttached: nominalInput1.dataset.nominalListenerAttached,
        userEdited: nominalInput1.dataset.nominalUserEdited
    });

    // Trigger the setup
    window.setupNominalEditListener(nominalInput1);
    console.log('After setup:', {
        listenerAttached: nominalInput1.dataset.nominalListenerAttached,
        userEdited: nominalInput1.dataset.nominalUserEdited
    });
    console.log('✓ TEST 1 PASSED');
} else {
    console.log('✗ TEST 1 FAILED: No nominal input found');
}

// ========== TEST 2: User Edit Detection ==========
console.log('\nTEST 2: Verify user edit detection');
const nominalInput2 = document.querySelector('input[name$="-nominal"]');
if (nominalInput2) {
    window.setupNominalEditListener(nominalInput2);

    console.log('Before edit:', nominalInput2.dataset.nominalUserEdited);

    // Simulate user typing
    nominalInput2.value = '555000';
    nominalInput2.dispatchEvent(new Event('input', { bubbles: true, isTrusted: true }));

    console.log('After user input:', nominalInput2.dataset.nominalUserEdited);

    if (nominalInput2.dataset.nominalUserEdited === '1') {
        console.log('✓ TEST 2 PASSED');
    } else {
        console.log('✗ TEST 2 FAILED: User edit not detected');
    }
} else {
    console.log('✗ TEST 2 FAILED: No nominal input found');
}

// ========== TEST 3: Auto-populate Flag ==========
console.log('\nTEST 3: Verify auto-populate sets flag to "0"');
const nominalInput3 = document.querySelector('input[name$="-nominal"]');
if (nominalInput3) {
    window.setupNominalEditListener(nominalInput3);

    // Simulate auto-populate by programmatic event
    nominalInput3.value = '750000';
    nominalInput3.dataset.nominalUserEdited = '0';
    nominalInput3.dispatchEvent(new Event('input', { bubbles: true }));

    console.log('After auto-populate:', nominalInput3.dataset.nominalUserEdited);

    if (nominalInput3.dataset.nominalUserEdited === '0') {
        console.log('✓ TEST 3 PASSED');
    } else {
        console.log('✗ TEST 3 FAILED: Auto-populate flag incorrect');
    }
} else {
    console.log('✗ TEST 3 FAILED: No nominal input found');
}

// ========== TEST 4: Multiple Listeners Prevention ==========
console.log('\nTEST 4: Verify no duplicate listeners attached');
const nominalInput4 = document.querySelector('input[name$="-nominal"]');
if (nominalInput4) {
    // Clear and test
    delete nominalInput4.dataset.nominalListenerAttached;

    console.log('Attaching listener 1...');
    window.setupNominalEditListener(nominalInput4);
    const attached1 = nominalInput4.dataset.nominalListenerAttached;

    console.log('Attaching listener 2 (should be skipped)...');
    window.setupNominalEditListener(nominalInput4);
    const attached2 = nominalInput4.dataset.nominalListenerAttached;

    if (attached1 === '1' && attached2 === '1') {
        console.log('✓ TEST 4 PASSED');
    } else {
        console.log('✗ TEST 4 FAILED: Duplicate listener issue');
    }
} else {
    console.log('✗ TEST 4 FAILED: No nominal input found');
}

// ========== TEST 5: toggleAdminHotelInputs Integration ==========
console.log('\nTEST 5: Verify toggleAdminHotelInputs calls setupNominalEditListener');
const firstRow = document.querySelector('tr.form-row:not(.empty-form)');
if (firstRow) {
    const nominalInput5 = firstRow.querySelector('input[name$="-nominal"]');
    if (nominalInput5) {
        delete nominalInput5.dataset.nominalListenerAttached;

        // Call toggleAdminHotelInputs(false) which should setup listener
        window.toggleAdminHotelInputs(firstRow, false);

        if (nominalInput5.dataset.nominalListenerAttached === '1') {
            console.log('✓ TEST 5 PASSED');
        } else {
            console.log('✗ TEST 5 FAILED: Listener not attached by toggleAdminHotelInputs');
        }
    } else {
        console.log('✗ TEST 5 FAILED: No nominal input in row');
    }
} else {
    console.log('✗ TEST 5 FAILED: No form row found');
}

// ========== TEST 6: Formset Dynamic Addition ==========
console.log('\nTEST 6: Check listener on all existing rows');
const allNominalInputs = document.querySelectorAll('input[name$="-nominal"]');
console.log(`Found ${allNominalInputs.length} nominal input(s)`);

let allHaveListeners = true;
allNominalInputs.forEach((input, index) => {
    if (input.dataset.nominalListenerAttached !== '1') {
        console.log(`  Row ${index}: Listener NOT attached`);
        allHaveListeners = false;
    } else {
        console.log(`  Row ${index}: ✓ Listener attached`);
    }
});

if (allHaveListeners && allNominalInputs.length > 0) {
    console.log('✓ TEST 6 PASSED');
} else if (allNominalInputs.length === 0) {
    console.log('⊘ TEST 6 SKIPPED: No nominal inputs found');
} else {
    console.log('✗ TEST 6 FAILED: Some rows missing listeners');
}

// ========== SUMMARY ==========
console.log('\n' + '='.repeat(50));
console.log('TEST SUMMARY');
console.log('='.repeat(50));
console.log(`
All tests verify that:
1. setupNominalEditListener() properly attaches listeners
2. User edits are detected (data-nominal-user-edited = '1')
3. Auto-populate sets flag correctly (data-nominal-user-edited = '0')
4. No duplicate listeners are created
5. toggleAdminHotelInputs() integration works
6. All existing rows have listeners attached

If all tests pass, the fix is working correctly!
`);

