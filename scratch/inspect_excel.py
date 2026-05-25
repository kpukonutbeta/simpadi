import openpyxl

wb = openpyxl.load_workbook('static/template_documents/rincian_SPD.xlsx')
ws = wb.active

for row in ws.iter_rows(min_row=1, max_row=35):
    row_data = []
    for cell in row:
        val = cell.value
        if val is not None:
            # clean up newlines for printing
            val_str = str(val).replace('\n', '\\n')
            row_data.append(f"[{cell.coordinate}: {val_str}]")
    if row_data:
        print(" ".join(row_data))
