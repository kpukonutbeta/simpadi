import re

with open('static/js/admin_filter.js', 'r') as f:
    lines = f.readlines()

def clean_line(line):
    # Very naive, but just strips out string literals and comments for quick count
    line = re.sub(r'//.*', '', line)
    line = re.sub(r'/\*.*?\*/', '', line)
    line = re.sub(r"'.*?'", '', line)
    line = re.sub(r'".*?"', '', line)
    line = re.sub(r'`.*?`', '', line)
    return line

current_func = None
func_level = 0
global_level = 0

for i, line in enumerate(lines):
    cl = clean_line(line)
    
    # Check if a new function starts (very basic heuristic)
    if 'function ' in cl:
        func_name_match = re.search(r'function\s+(\w+)', cl)
        if func_name_match:
            current_func = func_name_match.group(1)
            func_level = 0
            
    opens = cl.count('{')
    closes = cl.count('}')
    
    global_level += (opens - closes)
    if current_func:
        func_level += (opens - closes)
        if func_level < 0:
            print(f"Function {current_func} dropped below 0 at line {i+1}")
            current_func = None

    if global_level < 0:
        print(f"Global level dropped below 0 at line {i+1}")
        global_level = 0
