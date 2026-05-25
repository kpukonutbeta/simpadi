import re
with open('/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/templates/perjalanan/ajukan_form.html', 'r') as f:
    content = f.read()

# Let's find exactly where nominalInput.value is set in updateEstimasi
match = re.search(r'(const isLumpsum.*?)(nominalInput\.value = calculatedValue.*?)(?=})', content, re.DOTALL)
if match:
    print("Found lumpsum override logic.")
