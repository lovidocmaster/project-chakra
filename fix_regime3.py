lines = open('v15_chakra.py', 'r', encoding='utf-8').readlines()

# Find the SIGNAL log line
for i, line in enumerate(lines):
    if 'log.info(f"SIGNAL:' in line and 'Regime:' in lines[i+1] if i+1 < len(lines) else False:
        # Insert regime check before this line
        indent = '        '
        check = [
            indent + '# Skip RANGING/VOLATILE - only trade TRENDING markets\n',
            indent + 'if curr_regime in ["RANGING", "VOLATILE"]:\n',
            indent + '    log.info(f"{pair}: SKIP - regime={curr_regime} not TRENDING")\n',
            indent + '    return None\n',
        ]
        lines = lines[:i] + check + lines[i:]
        print(f'Inserted regime check at line {i+1}')
        break

open('v15_chakra.py', 'w', encoding='utf-8').writelines(lines)
print('Done')
