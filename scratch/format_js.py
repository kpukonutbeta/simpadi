import sys

def check_js(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
        
    stack = []
    
    in_str = False
    in_comment = False
    in_block = False
    str_char = ''
    
    for i, line in enumerate(lines):
        j = 0
        while j < len(line):
            c = line[j]
            
            if in_comment:
                if c == '\n': in_comment = False
            elif in_block:
                if c == '*' and j+1 < len(line) and line[j+1] == '/':
                    in_block = False
                    j += 1
            elif in_str:
                if c == '\\':
                    j += 1
                elif c == str_char:
                    in_str = False
            else:
                if c == '/' and j+1 < len(line) and line[j+1] == '/':
                    in_comment = True
                    j += 1
                elif c == '/' and j+1 < len(line) and line[j+1] == '*':
                    in_block = True
                    j += 1
                elif c in "'\"`":
                    in_str = True
                    str_char = c
                elif c == '{':
                    stack.append(('{', i+1))
                elif c == '}':
                    if stack and stack[-1][0] == '{':
                        stack.pop()
                    else:
                        print(f"Unmatched }} at line {i+1}")
            j += 1

    for brace, line_num in stack:
        print(f"Unmatched {brace} at line {line_num}")

check_js('static/js/admin_filter.js')
