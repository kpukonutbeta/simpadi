level = 0
with open('static/js/admin_filter.js', 'r') as f:
    content = f.read()

# clean JS
in_str = False
in_comment = False
in_block = False
str_char = ''
clean = list(content)
for i in range(len(content)):
    c = content[i]
    if in_comment:
        clean[i] = ' '
        if c == '\n': in_comment = False
    elif in_block:
        clean[i] = ' '
        if c == '*' and i+1 < len(content) and content[i+1] == '/':
            clean[i+1] = ' '
            in_block = False
    elif in_str:
        clean[i] = ' '
        if c == '\\': clean[i+1] = ' '
        elif c == str_char: in_str = False
    else:
        if c == '/' and i+1 < len(content) and content[i+1] == '/':
            in_comment = True
            clean[i] = ' '
            clean[i+1] = ' '
        elif c == '/' and i+1 < len(content) and content[i+1] == '*':
            in_block = True
            clean[i] = ' '
            clean[i+1] = ' '
        elif c in "'\"`":
            in_str = True
            str_char = c
            clean[i] = ' '

clean = "".join(clean)
level = 0
for i, line in enumerate(clean.split('\n')):
    level += line.count('{') - line.count('}')
    if level == 0 and i > 0:
        print(f"Level dropped to 0 at line {i+1}")
        break
