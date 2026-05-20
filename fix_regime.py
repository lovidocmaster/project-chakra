content = open('v15_chakra.py', 'r', encoding='utf-8').read()

# Find where signal is logged and trade executed
# Add regime check before execution
old = '            log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%}'
new = '            # Skip RANGING and VOLATILE markets\n            if curr_regime in ["RANGING", "VOLATILE"]:\n                log.info(f"{pair}: Skipping - regime is {curr_regime}")\n                continue\n            log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%}'

content = content.replace(old, new)

if 'Skipping - regime is' in content:
    print('Regime check added before execution - SUCCESS')
else:
    print('String not found')

open('v15_chakra.py', 'w', encoding='utf-8').write(content)
