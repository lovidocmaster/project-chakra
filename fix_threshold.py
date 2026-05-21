import re
content = open('v15_chakra.py', 'r', encoding='utf-8').read()

# Find and fix threshold - try multiple patterns
content = re.sub(r'< (\d+\.\d+)% threshold', '< 60.0% threshold', content)
content = re.sub(r'(\d+\.\d+) < CONF', '0.60 < CONF', content)
content = re.sub(r'final_conf < 0\.\d+', 'final_conf < 0.60', content)
content = re.sub(r'conf < 0\.\d+', 'conf < 0.60', content)

open('v15_chakra.py', 'w', encoding='utf-8').write(content)
print('Done')
