import re
content = open('v15_chakra.py', 'r', encoding='utf-8').read()

# Fix 1: Add futures pairs (OANDA supports these)
old = 'PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "XAU_USD", "GBP_JPY"]'
new = 'PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD", "XAU_USD", "GBP_JPY", "SPX500_USD", "NAS100_USD", "US30_USD", "UK100_GBP", "BCO_USD"]'
content = content.replace(old, new)

# Fix 2: Confidence threshold to 60% (ATLAS paper: 17-28 trades per window)
content = re.sub(r'(\d+\.\d+)% threshold', lambda m: m.group(0), content)
content = content.replace('< 70.0% threshold', '< 60.0% threshold')
content = content.replace('"< 70.0% threshold"', '"< 60.0% threshold"')

# Fix 3: Max trades from 3 to 7 (one per pair group per ATLAS paper)
content = content.replace('self.max_open = 3', 'self.max_open = 7')

# Fix 4: Session filter - extend to include Tokyo (A3C paper multi-currency)
content = content.replace(
    'london = 7 <= hour < 16\n        new_york = 12 <= hour < 21\n        return london or new_york',
    'tokyo = 0 <= hour < 9\n        london = 7 <= hour < 16\n        new_york = 12 <= hour < 21\n        return tokyo or london or new_york'
)

open('v15_chakra.py', 'w', encoding='utf-8').write(content)
print('Done')
