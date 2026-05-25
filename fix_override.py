with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'r') as f:
    content = f.read()

old_code = """                                const nominalInput = row.querySelector('input[name$="-nominal"]');
                                if (nominalInput) {"""

new_code = """                                const nominalInput = row.querySelector('input[name$="-nominal"]');
                                if (nominalInput && nominalInput.readOnly) {"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'w') as f:
        f.write(content)
    print("Fixed updateEstimasi override!")
else:
    print("Could not find old code.")
