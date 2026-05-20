import os
from dotenv import load_dotenv
load_dotenv()
from oandapyV20 import API
from oandapyV20.endpoints.trades import OpenTrades, TradeClose

token = os.getenv('OANDA_TOKEN', os.getenv('OANDA_ACCESS_TOKEN',''))
account = '101-001-39217670-001'

api = API(access_token=token, environment='practice')
r = OpenTrades(account)
api.request(r)
trades = r.response.get('trades', [])
print(f'Open trades: {len(trades)}')
for t in trades:
    try:
        tc = TradeClose(account, tradeID=t['id'])
        api.request(tc)
        print(f'Closed: {t["id"]} {t["instrument"]}')
    except Exception as e:
        print(f'Error: {e}')
print('All done')
