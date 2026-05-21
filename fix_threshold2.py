content = open('v15_chakra.py', 'r', encoding='utf-8').read()

# Fix all regime-specific thresholds to 60% per ATLAS paper
content = content.replace('"TRENDING": {"min_conf":0.60,"risk_mult":1.2,', '"TRENDING": {"min_conf":0.60,"risk_mult":1.2,')
content = content.replace('"RANGING":  {"min_conf":0.70,"risk_mult":0.8,', '"RANGING":  {"min_conf":0.60,"risk_mult":0.8,')
content = content.replace('"VOLATILE": {"min_conf":0.75,"risk_mult":0.5,', '"VOLATILE": {"min_conf":0.65,"risk_mult":0.5,')
content = content.replace('}.get(regime, {"min_conf":0.70,"risk_mult":1.0,', '}.get(regime, {"min_conf":0.60,"risk_mult":1.0,')

open('v15_chakra.py', 'w', encoding='utf-8').write(content)

# Verify
content2 = open('v15_chakra.py', 'r', encoding='utf-8').read()
ranging_ok = '"RANGING":  {"min_conf":0.60' in content2
volatile_ok = '"VOLATILE": {"min_conf":0.65' in content2
print(f'RANGING threshold fixed: {ranging_ok}')
print(f'VOLATILE threshold fixed: {volatile_ok}')
