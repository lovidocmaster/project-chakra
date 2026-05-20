lines = open('v15_chakra.py', 'r', encoding='utf-8').readlines()

# Find the problematic injection and fix indentation
for i, line in enumerate(lines):
    if 'Regime router overriding' in line or 'regime-specific strategy' in line:
        print(f'Found at line {i+1}: {repr(line[:50])}')

# Find SIGNAL log line and check surrounding indentation
for i, line in enumerate(lines):
    if 'log.info(f"SIGNAL:' in line and 'Regime:' in (lines[i+1] if i+1<len(lines) else ''):
        print(f'SIGNAL at line {i+1}, indent: {repr(line[:12])}')
        # Show 10 lines before
        for j in range(max(0,i-10), i+3):
            print(f'{j+1}: {repr(lines[j][:80])}')
        break
