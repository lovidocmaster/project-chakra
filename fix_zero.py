content = open('v15_chakra.py', 'r', encoding='utf-8').read()

# Find the calculate method and add skip check after risk_mult
old = '        # SL/TP based on ATR\n        sl_dist = atr * 0.8 * risk_mult'
new = '        # Skip RANGING/VOLATILE markets\n        if risk_mult == 0.0:\n            return {"entry":price,"sl":price*0.99,"tp":price*1.01,"units":1000,"risk_usd":0,"sl_pips":0,"tp_pips":0}\n        # SL/TP based on ATR\n        sl_dist = max(atr * 0.8 * risk_mult, 0.0001)'
content = content.replace(old, new)

if 'Skip RANGING' in content:
    print('Fix applied successfully')
else:
    print('String not found - trying alternative')
    # Direct fix - just prevent division by zero
    old2 = 'units    = int(risk_usd / (sl_dist * pip_val))'
    new2 = 'units    = int(risk_usd / max(sl_dist * pip_val, 0.0001))'
    content = content.replace(old2, new2)
    print('Alternative fix applied')

open('v15_chakra.py', 'w', encoding='utf-8').write(content)
