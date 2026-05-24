import re

with open('static/js/admin_filter.js', 'r') as f:
    text = f.read()

# very naive JS parser to strip strings/comments
in_str = False
in_comment = False
in_block = False
str_char = ''

clean_text = list(text)

i = 0
while i < len(text):
    c = text[i]
    if in_comment:
        clean_text[i] = ' '
        if c == '\n': in_comment = False
    elif in_block:
        clean_text[i] = ' '
        if c == '*' and i+1 < len(text) and text[i+1] == '/':
            clean_text[i+1] = ' '
            in_block = False
            i += 1
    elif in_str:
        clean_text[i] = ' '
        if c == '\\': 
            clean_text[i+1] = ' '
            i += 1
        elif c == str_char: in_str = False
    else:
        if c == '/' and i+1 < len(text) and text[i+1] == '/':
            in_comment = True
            clean_text[i] = ' '
            clean_text[i+1] = ' '
            i += 1
        elif c == '/' and i+1 < len(text) and text[i+1] == '*':
            in_block = True
            clean_text[i] = ' '
            clean_text[i+1] = ' '
            i += 1
        elif c in "'\"`":
            in_str = True
            str_char = c
            clean_text[i] = ' '
    i += 1

clean_text = "".join(clean_text)

level = 0
for i, line in enumerate(clean_text.split('\n')):
    prev_level = level
    level += line.count('{') - line.count('}')
    if "function" in text.split('\n')[i] or level != prev_level:
        print(f"L{i+1}: level {prev_level} -> {level} | {text.split(chr(10))[i][:60]}")
