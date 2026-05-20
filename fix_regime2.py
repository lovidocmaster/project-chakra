content = open('v15_chakra.py', 'r', encoding='utf-8').read()

old = '        log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%} | "\n                 f"Regime:{curr_regime} | News:{news_sent} | COT:{cot_bias} | "\n                 f"TV:{tv_confirmed} | Agents:{len(agreed)}{h4_boost}")\n        # -- Execute trade'

new = '        # Skip RANGING and VOLATILE - only trade TRENDING\n        if curr_regime in ["RANGING", "VOLATILE"]:\n            log.info(f"{pair}: SKIP - regime is {curr_regime} (only TRENDING allowed)")\n            return None\n        log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%} | "\n                 f"Regime:{curr_regime} | News:{news_sent} | COT:{cot_bias} | "\n                 f"TV:{tv_confirmed} | Agents:{len(agreed)}{h4_boost}")\n        # -- Execute trade'

content = content.replace(old, new)

if 'only TRENDING allowed' in content:
    print('SUCCESS - Regime check added')
else:
    print('FAILED - trying line by line')

open('v15_chakra.py', 'w', encoding='utf-8').write(content)
