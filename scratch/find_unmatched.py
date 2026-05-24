import re

with open('static/js/admin_filter.js', 'r') as f:
    text = f.read()

# very naive JS parser to strip strings/comments
import sys
stack = []
in_str = False
in_comment = False
in_block = False
str_char = ''

i = 0
while i < len(text):
    c = text[i]
    if in_comment:
        if c == '\n': in_comment = False
    elif in_block:
        if c == '*' and i+1 < len(text) and text[i+1] == '/':
            in_block = True
            i += 1
            in_block = False
    elif in_str:
        if c == '\\': i += 1
        elif c == str_char: in_str = False
    else:
        if c == '/' and i+1 < len(text) and text[i+1] == '/':
            in_comment = True
        elif c == '/' and i+1 < len(text) and text[i+1] == '*':
            in_block = True
        elif c in "'\"`":
            in_str = True
            str_char = c
        elif c == '{':
            line = text.count('\n', 0, i) + 1
            stack.append(('{', line))
        elif c == '}':
            if stack and stack[-1][0] == '{':
                stack.pop()
            else:
                line = text.count('\n', 0, i) + 1
                print(f"Unmatched }} at line {line}")
    i += 1

for brace, line in stack:
    print(f"Unmatched {brace} at line {line}")
