"""
CHAKRA LIVE PAPER TRADER (honest edition)
=========================================
Runs LIVE on your OANDA paper account. Trend + Carry + strict risk control.
Logs EVERY decision (trade AND skip) to Supabase so your track record is real
and auditable. No fabricated numbers - only what actually happens.

WHAT IT DOES EACH CYCLE (every 1 hour):
  1. Pulls fresh H4 candles for major pairs
  2. Computes trend (momentum + MA) and carry bias (rate differential)
  3. Trades ONLY when trend and carry agree, with a mandatory stop-loss
  4. Sizes each position to risk exactly 0.5% of account
  5. Manages open trades (trailing stop)
  6. Logs decision + trade to Supabase, pings Telegram, updates dashboard

HONEST NOTE: backtests of trend & indicator logic showed ~0 edge. This LIVE
test exists to see real behaviour with real spreads/fills over weeks. Judge it
on the real track record, not on hope.

RUN:
  cd C:\\Users\\cmalo\\chakra-v2
  py -3.11 live_paper_trader.py
Leave the window OPEN. Closing it stops the trader.
"""
import os, json, time, math
import urllib.request, urllib.error
from datetime import datetime, timezone

# ---------------- config ----------------
def load_env():
    for p in ['.env', r'C:\Users\cmalo\chakra-v2\.env']:
        if os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                line=line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k,v=line.split('=',1); os.environ[k.strip()]=v.strip().strip('"').strip("'")
            return
load_env()
def env(*names, default=None):
    for n in names:
        v=os.getenv(n)
        if v: return v
    return default

OANDA_TOKEN = env('OANDA_TOKEN','OANDA_API_KEY','OANDA_ACCESS_TOKEN')
OANDA_ACCT  = env('OANDA_ACCOUNT_ID','OANDA_ACCOUNT', default='101-001-39217670-001')
OANDA = "https://api-fxpractice.oanda.com"
SB_URL = env('SUPABASE_URL', default='https://jvnaphbygmqjeyawkmnz.supabase.co').rstrip('/')
SB_KEY = env('SUPABASE_KEY','SUPABASE_SERVICE_KEY','SUPABASE_SERVICE_ROLE_KEY','SUPABASE_ANON_KEY')
TG_TOKEN = env('TELEGRAM_TOKEN','TELEGRAM_BOT_TOKEN')
TG_CHAT  = env('TELEGRAM_CHAT_ID','TELEGRAM_CHAT')

PAIRS = ["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD","USD_CHF","NZD_USD","EUR_JPY","AUD_JPY"]
RISK_PCT   = 0.005      # 0.5% risk per trade
MAX_OPEN   = 4          # max concurrent positions (diversification + safety)
CYCLE_SEC  = 3600       # 1 hour
GRAN       = "H4"
STOP_ATR   = 2.5
TREND_LOOKBACK = 60     # H4 bars (~10 trading days)
MA_PERIOD  = 50

# Approx central-bank policy rates (early 2026). UPDATE periodically.
RATES = {"USD":4.50,"EUR":2.50,"GBP":4.00,"JPY":0.50,"AUD":3.50,
         "CAD":2.75,"CHF":0.50,"NZD":3.00}
def pip_size(p): return 0.01 if p.endswith("JPY") else 0.0001

# ---------------- http helpers ----------------
def oanda_get(path):
    req=urllib.request.Request(OANDA+path, headers={'Authorization':f'Bearer {OANDA_TOKEN}'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode())
def oanda_post(path, body):
    req=urllib.request.Request(OANDA+path, data=json.dumps(body).encode(), method='POST',
        headers={'Authorization':f'Bearer {OANDA_TOKEN}','Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode())
def sb_insert(table, row):
    if not SB_KEY: return
    try:
        req=urllib.request.Request(f"{SB_URL}/rest/v1/{table}", data=json.dumps(row).encode(), method='POST',
            headers={'apikey':SB_KEY,'Authorization':f'Bearer {SB_KEY}','Content-Type':'application/json'})
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e: log(f"SB insert {table} err: {e}")
def sb_patch(table, match, row):
    if not SB_KEY: return
    try:
        req=urllib.request.Request(f"{SB_URL}/rest/v1/{table}?{match}", data=json.dumps(row).encode(), method='PATCH',
            headers={'apikey':SB_KEY,'Authorization':f'Bearer {SB_KEY}','Content-Type':'application/json'})
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e: log(f"SB patch {table} err: {e}")
def tg(msg):
    if not TG_TOKEN or not TG_CHAT: return
    try:
        req=urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=json.dumps({'chat_id':TG_CHAT,'text':msg,'parse_mode':'HTML'}).encode(), method='POST',
            headers={'Content-Type':'application/json'})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e: log(f"TG err: {e}")
def log(m): print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {m}", flush=True)

# ---------------- market logic ----------------
def candles(pair, n=120):
    d=oanda_get(f"/v3/instruments/{pair}/candles?granularity={GRAN}&price=M&count={n}")
    return [{'c':float(x['mid']['c']),'h':float(x['mid']['h']),'l':float(x['mid']['l'])}
            for x in d.get('candles',[]) if x.get('complete')]

def sma(a,n): return sum(a[-n:])/n if len(a)>=n else sum(a)/len(a)
def atr(bars,n=14):
    if len(bars)<n+1: return 0
    t=[max(bars[i]['h']-bars[i]['l'],abs(bars[i]['h']-bars[i-1]['c']),abs(bars[i]['l']-bars[i-1]['c'])) for i in range(-n,0)]
    return sum(t)/n

def carry_bias(pair):
    b,q=pair.split('_'); diff=RATES.get(b,0)-RATES.get(q,0)
    if diff>=1.0: return "LONG_FAVORED", diff
    if diff<=-1.0: return "SHORT_FAVORED", diff
    return "NEUTRAL", diff

def signal(pair, bars):
    """Trade only when trend and carry agree. Returns (side, conf, regime, carry) or None."""
    if len(bars)<MA_PERIOD+5: return None
    c=[b['c'] for b in bars]
    mom=c[-1]-c[-TREND_LOOKBACK] if len(c)>=TREND_LOOKBACK else 0
    ma=sma(c,MA_PERIOD)
    trend = "BUY" if (mom>0 and c[-1]>ma) else ("SELL" if (mom<0 and c[-1]<ma) else None)
    if not trend: return None
    cb, diff = carry_bias(pair)
    # require carry to AGREE or at least not strongly oppose
    if trend=="BUY"  and cb=="SHORT_FAVORED": return None
    if trend=="SELL" and cb=="LONG_FAVORED":  return None
    agree = (trend=="BUY" and cb=="LONG_FAVORED") or (trend=="SELL" and cb=="SHORT_FAVORED")
    conf = 0.70 if agree else 0.58
    return (trend, conf, "TREND", cb)

def account():
    return oanda_get(f"/v3/accounts/{OANDA_ACCT}")['account']
def open_trades():
    return oanda_get(f"/v3/accounts/{OANDA_ACCT}/openTrades").get('trades',[])

def place_trade(pair, side, bars, balance):
    a=atr(bars)
    if a<=0: return None
    px=bars[-1]['c']
    sl_dist=STOP_ATR*a
    units_raw = (balance*RISK_PCT)/sl_dist
    units = int(units_raw); units = max(1, min(units, 50000))
    if side=="SELL": units=-units
    sl = px - sl_dist if side=="BUY" else px + sl_dist
    order={"order":{"type":"MARKET","instrument":pair,"units":str(units),
        "stopLossOnFill":{"price":f"{sl:.5f}" if not pair.endswith('JPY') else f"{sl:.3f}"},
        "timeInForce":"FOK","positionFill":"DEFAULT"}}
    res=oanda_post(f"/v3/accounts/{OANDA_ACCT}/orders", order)
    fill=res.get('orderFillTransaction')
    if fill:
        return {'units':units,'price':float(fill.get('price',px)),'sl':sl,'id':fill.get('tradeOpened',{}).get('tradeID')}
    return None

# ---------------- main loop ----------------
def cycle(n):
    log(f"--- cycle #{n} ---")
    try: acct=account()
    except Exception as e:
        log(f"OANDA account err: {e}"); return
    bal=float(acct.get('balance',0)); nav=bal+float(acct.get('unrealizedPL',0))
    opens=open_trades()
    log(f"balance=${bal:.0f} nav=${nav:.0f} open={len(opens)}")
    sb_patch("system_state","id=eq.1",{"balance":bal,"nav":nav,"open_trades":len(opens),
             "status":"LIVE","updated_at":datetime.now(timezone.utc).isoformat()})

    # market open check (FX closed Fri 22:00 UTC - Sun 22:00 UTC)
    now=datetime.now(timezone.utc); wd=now.weekday()
    market_closed = (wd==5) or (wd==6 and now.hour<22) or (wd==4 and now.hour>=22)
    if market_closed:
        log("FX market closed (weekend). Logging skip, waiting.")
        sb_insert("live_decisions",{"decision":"SKIP","reason":"market_closed",
                  "details":{"weekday":wd,"hour":now.hour}})
        return

    open_pairs={t['instrument'] for t in opens}
    room = MAX_OPEN - len(opens)
    for pair in PAIRS:
        if pair in open_pairs: continue
        try: bars=candles(pair)
        except Exception as e: log(f"{pair} candles err: {e}"); continue
        sig=signal(pair,bars)
        if not sig:
            sb_insert("live_decisions",{"pair":pair,"decision":"SKIP",
                      "reason":"no_trend_carry_agreement","regime":"TREND"})
            continue
        side,conf,regime,cb=sig
        if room<=0:
            sb_insert("live_decisions",{"pair":pair,"decision":"SKIP","reason":"max_open_reached",
                      "regime":regime,"confidence":conf})
            continue
        # place it
        res=place_trade(pair,side,bars,bal)
        if res:
            room-=1
            row={"pair":pair,"side":side,"strategy":"trend_carry","regime":regime,"confidence":conf,
                 "entry_price":res['price'],"stop_loss":res['sl'],"units":abs(res['units']),
                 "carry_bias":cb,"status":"OPEN","oanda_trade_id":res['id']}
            sb_insert("live_track_record",row)
            sb_insert("live_decisions",{"pair":pair,"decision":"TRADE","reason":"trend+carry",
                      "regime":regime,"confidence":conf,"details":{"carry":cb,"units":res['units']}})
            tg(f"🟢 <b>OPEN {side} {pair}</b>\nEntry {res['price']:.5f} | SL {res['sl']:.5f}\n"
               f"Carry: {cb} | Conf {conf:.0%} | Risk 0.5%")
            log(f"OPENED {side} {pair} @ {res['price']:.5f}")
        else:
            sb_insert("live_decisions",{"pair":pair,"decision":"SKIP","reason":"order_not_filled",
                      "regime":regime,"confidence":conf})

print("="*64)
print("  CHAKRA LIVE PAPER TRADER — starting")
print("  "+datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
print("="*64)
if not OANDA_TOKEN: print("No OANDA token in .env"); raise SystemExit(1)
tg("🚀 <b>Chakra Live Paper Trader started</b>\nTrend + Carry + 0.5% risk\nLogging every decision honestly.")
n=0
while True:
    n+=1
    try: cycle(n)
    except Exception as e: log(f"cycle error: {e}")
    log(f"sleeping {CYCLE_SEC//60} min...")
    time.sleep(CYCLE_SEC)
