with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'r') as f:
    content = f.read()

old_code = """        document.addEventListener('change', function (e) {
            if (e.target.matches('input.nominal-input-field')) {"""

new_code = """        document.addEventListener('input', function (e) {
            if (e.target.matches('input.nominal-input-field')) {"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'w') as f:
        f.write(content)
    print("Reverted to input event!")
else:
    print("Could not find the target code block.")
