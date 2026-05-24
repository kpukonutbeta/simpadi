with open('static/js/admin_filter.js', 'r') as f:
    lines = f.readlines()

level = 0
for i, line in enumerate(lines):
    # strip comments for accurate counting (simple check)
    clean_line = line.split('//')[0]
    for char in clean_line:
        if char == '{': level += 1
        elif char == '}': level -= 1
    
    if level < 0:
        print(f"Error at line {i+1}: level dropped below 0")
        break

print(f"Final level: {level}")
