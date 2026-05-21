content = open('v15_chakra.py', 'r', encoding='utf-8').read()

checks = [
    ('Futures pairs added', 'SPX500_USD'),
    ('NAS100 added', 'NAS100_USD'),
    ('US30 added', 'US30_USD'),
    ('UK100 added', 'UK100_GBP'),
    ('Oil added', 'BCO_USD'),
    ('60% threshold', '60.0% threshold'),
    ('Max 7 trades', 'self.max_open = 7'),
    ('Tokyo session', 'tokyo = 0 <= hour < 9'),
]

print('=== PAPER-BASED FIXES VERIFICATION ===')
all_ok = True
for name, check in checks:
    status = 'OK' if check in content else 'MISSING'
    if status == 'MISSING': all_ok = False
    print(f'  {status}: {name}')

print(f'\nAll fixes applied: {all_ok}')
