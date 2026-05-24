import sys

def check_braces(filename):
    with open(filename, 'r') as f:
        content = f.read()

    level = 0
    in_string = False
    string_char = ''
    in_comment = False
    in_block_comment = False

    for i, char in enumerate(content):
        # Very basic parser, might not be perfect for JS but good enough
        if char == '{': level += 1
        elif char == '}': level -= 1
        
    print(f"Final brace level: {level}")

check_braces('static/js/admin_filter.js')
