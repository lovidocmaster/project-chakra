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
# Filter for indices and commodities
futures = [i['name'] for i in instruments if i['type'] in ['CFD', 'METAL'] or 
           any(x in i['name'] for x in ['SPX', 'NAS', 'US30', 'UK100', 'XAU', 'BCO', 'WTICO', 'CORN', 'SOYBEAN'])]
print('Available futures/indices/metals:')
for f in sorted(futures):
    print(f'  {f}')
