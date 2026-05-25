with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'r') as f:
    content = f.read()

# Change 'input' event to 'blur' (change) for the formatRupiahInput listener
old_code = """        document.addEventListener('input', function (e) {
            if (e.target.matches('input.nominal-input-field')) {"""

new_code = """        document.addEventListener('change', function (e) {
            if (e.target.matches('input.nominal-input-field')) {"""

if old_code in content:
    content = content.replace(old_code, new_code)
    
    # We should also remove the cursor positioning logic because it's not needed for 'change'
    # Actually, it's fine to keep it, but it's unnecessary. Let's just leave it, it's harmless on change.
    with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'w') as f:
        f.write(content)
    print("Changed input to change event for nominal formatter!")
else:
    print("Could not find the target code block.")
