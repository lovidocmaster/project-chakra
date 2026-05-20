content = open('v15_chakra.py', 'r', encoding='utf-8').read()

# Fix RANGING market filter
old = '{"TRENDING":1.2,"RANGING":0.8,"VOLATILE":0.5}'
new = '{"TRENDING":1.0,"RANGING":0.0,"VOLATILE":0.0}'
content = content.replace(old, new)

# Verify
if '{"TRENDING":1.0,"RANGING":0.0,"VOLATILE":0.0}' in content:
    print('RANGING fix applied')
else:
    print('RANGING fix NOT applied - checking...')
    # Try alternative
    import re
    content = re.sub(r'"RANGING":\s*0\.\d+', '"RANGING":0.0', content)
    content = re.sub(r'"VOLATILE":\s*0\.\d+', '"VOLATILE":0.0', content)
    content = re.sub(r'"TRENDING":\s*1\.\d+', '"TRENDING":1.0', content)
    print('Applied via regex')

open('v15_chakra.py', 'w', encoding='utf-8').write(content)
print('Done')
