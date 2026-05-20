lines = open('v15_chakra.py', 'r', encoding='utf-8').readlines()

# Fix line 2009 - remove extra indentation
for i, line in enumerate(lines):
    if 'log.info(f"SIGNAL:' in line and i > 2000:
        # Fix this line and next 2 lines indentation
        lines[i] = '        ' + line.lstrip()
        if i+1 < len(lines):
            lines[i+1] = '                 ' + lines[i+1].lstrip()
        if i+2 < len(lines):
            lines[i+2] = '                 ' + lines[i+2].lstrip()
        print(f'Fixed line {i+1}')
        break

open('v15_chakra.py', 'w', encoding='utf-8').writelines(lines)
print('Done')
