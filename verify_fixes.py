content = open('v15_chakra.py', 'r', encoding='utf-8').read()

checks = [
    ('HiveMind 3 days', 'days >= 3'),
    ('HiveMind init 4 days', 'timedelta(days=4)'),
    ('Skip RANGING', '"RANGING":0.0'),
    ('Skip VOLATILE', '"VOLATILE":0.0'),
    ('Position size 15K', 'min(units, 15000)'),
    ('SL tight 0.8', 'atr * 0.8 * risk_mult'),
    ('TP wide 2.4', 'atr * 2.4 * risk_mult'),
]

print('=== VERIFICATION ===')
for name, check in checks:
    status = 'OK' if check in content else 'MISSING'
    print(f'{status}: {name}')
