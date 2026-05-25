import re
with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'r') as f:
    content = f.read()

# Add debounce variables
if 'let estimasiTimeout = null;' not in content:
    content = content.replace(
        'function updateEstimasi() {',
        'let estimasiTimeout = null;\n    function updateEstimasi() {\n        if (estimasiTimeout) clearTimeout(estimasiTimeout);\n        estimasiTimeout = setTimeout(doUpdateEstimasi, 500);\n    }\n\n    function doUpdateEstimasi() {'
    )

with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'w') as f:
    f.write(content)
print("Debounce added!")
