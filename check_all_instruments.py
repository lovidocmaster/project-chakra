import os
from dotenv import load_dotenv
load_dotenv()
from oandapyV20 import API
from oandapyV20.endpoints.accounts import AccountInstruments

token = os.getenv('OANDA_TOKEN', os.getenv('OANDA_ACCESS_TOKEN',''))
account = '101-001-39217670-001'
api = API(access_token=token, environment='practice')
r = AccountInstruments(account)
api.request(r)
instruments = r.response.get('instruments', [])
print(f'Total instruments: {len(instruments)}')
print('\nAll instrument types:')
types = set(i['type'] for i in instruments)
for t in sorted(types):
    names = [i['name'] for i in instruments if i['type'] == t]
    print(f'\n{t} ({len(names)}):')
    for n in sorted(names)[:20]:
        print(f'  {n}')
