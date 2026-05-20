import re
content = open('v15_chakra.py', 'r', encoding='utf-8').read()
content = re.sub(r'sl_dist = atr \* \d+\.\d+ \* risk_mult', 'sl_dist = atr * 0.8 * risk_mult', content)
open('v15_chakra.py', 'w', encoding='utf-8').write(content)
print('SL fix applied')
