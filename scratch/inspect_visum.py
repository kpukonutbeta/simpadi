import openpyxl
import re
from pathlib import Path

file_path = '/Users/muhakbaryasin/Desktop/master/kpukonut/simpadi/static/template_documents/visum_SPD.xlsx'

if not Path(file_path).exists():
    print(f"File not found: {file_path}")
    exit(1)

wb = openpyxl.load_workbook(file_path, data_only=True)
variables = set()

for sheet in wb.worksheets:
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str):
                # Find all {{VAR_NAME}}
                matches = re.findall(r'\{\{([^}]+)\}\}', cell.value)
                for match in matches:
                    variables.add(match)

print("Variables found in visum_SPD.xlsx:")
for v in sorted(variables):
    print(f"- {v}")
