"""
V8 ULTIMATE TRADING SYSTEM - COMPLETE 120 AGENTS
All Data Sources | Self-Evolving | OANDA Execution | Full AI
SMC + ICT + Wyckoff + Intermarket + Volume + ML + LLM + Risk
Fear&Greed + COT + Economic Calendar + Google Trends + MyFxBook
"""

import numpy as np
import pandas as pd
import json
import time
import requests
import warnings
import os
import threading
import io
import base64
from datetime import datetime, timedelta
from collections import deque, defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

# ============================================================
# COMPLETE CONFIGURATION - ALL KEYS
# ============================================================
CONFIG = {
    # AI
    'ANTHROPIC_API_KEY':  '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',
    # Broker
    'OANDA_API_KEY':      '500c5382d32fcc8a3a58b0ea0507c083-64e0d997e301a20caa3270a846d33402',
    'OANDA_ACCOUNT_ID':   '101-001-39217670-001',
    'OANDA_URL':          'https://api-fxpractice.oanda.com',
    # Data
    'FRED_API_KEY':       '0d5051e1563e45866badf276454ce1ec',
    'NEWS_API_KEY':       '00ce3b995b134bf98265358f98b9d41e',
    'ALPHA_VANTAGE_KEY':  'T7TQAX2SMD7RTNXN',
    'MASSIVE_KEY':        'zATWYvrh7FNOXfR95eIRcI40XxDaDtzY',
    # Alerts
    'TELEGRAM_TOKEN':     '8635098808:AAG07lR1RTnImndoCbnIEEXn8mGrIzR0nOc',
    'TELEGRAM_CHAT_ID':   '757855988',
    # Database
    'SUPABASE_URL':       'https://jvnaphbygmqjeyawkmnz.supabase.co',
    'SUPABASE_KEY':       'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2bmFwaGJ5Z21xamV5YXdrbW56Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ3NDI2NzcsImV4cCI6MjA2MDMxODY3N30.Suz0H3jrDn89vzCLCPPFlbo3oVYcqVbn7d_OtB3zLR0',
    # Trading
    'INITIAL_CAPITAL':    10000,
    'RISK_PER_TRADE':     0.01,
    'MAX_POSITIONS':      5,
    'MIN_VOTES':          6,
    'VOTE_THRESHOLD':     0.60,
    'MAX_DRAWDOWN':       0.10,
    'BREAKEVEN_R':        1.0,
    'PARTIAL_CLOSE_R':    1.0,
    'AUTO_EXECUTE':       False,
}

# ============================================================
# MARKETS - 40 INSTRUMENTS
# ============================================================
MARKETS = {
    # Forex Majors
    'EURUSD': {'type':'forex','pip':0.0001,'pusd':10.0,'yahoo':'EURUSD=X','oanda':'EUR_USD','psych':[1.05,1.10,1.15,1.20]},
    'USDJPY': {'type':'forex','pip':0.01,  'pusd':9.0, 'yahoo':'USDJPY=X','oanda':'USD_JPY','psych':[145,150,155,160]},
    'GBPUSD': {'type':'forex','pip':0.0001,'pusd':10.0,'yahoo':'GBPUSD=X','oanda':'GBP_USD','psych':[1.25,1.30,1.35,1.40]},
    'AUDUSD': {'type':'forex','pip':0.0001,'pusd':10.0,'yahoo':'AUDUSD=X','oanda':'AUD_USD','psych':[0.60,0.65,0.70,0.75]},
    'USDCAD': {'type':'forex','pip':0.0001,'pusd':7.5, 'yahoo':'USDCAD=X','oanda':'USD_CAD','psych':[1.30,1.35,1.40,1.45]},
    'NZDUSD': {'type':'forex','pip':0.0001,'pusd':10.0,'yahoo':'NZDUSD=X','oanda':'NZD_USD','psych':[0.58,0.60,0.62,0.65]},
    'USDCHF': {'type':'forex','pip':0.0001,'pusd':11.0,'yahoo':'USDCHF=X','oanda':'USD_CHF','psych':[0.88,0.90,0.92,0.95]},
    # Forex Crosses
    'EURJPY': {'type':'forex','pip':0.01,  'pusd':9.0, 'yahoo':'EURJPY=X','oanda':'EUR_JPY','psych':[155,160,165,170]},
    'GBPJPY': {'type':'forex','pip':0.01,  'pusd':9.0, 'yahoo':'GBPJPY=X','oanda':'GBP_JPY','psych':[185,190,195,200]},
    'EURGBP': {'type':'forex','pip':0.0001,'pusd':12.5,'yahoo':'EURGBP=X','oanda':'EUR_GBP','psych':[0.83,0.85,0.87,0.90]},
    'AUDJPY': {'type':'forex','pip':0.01,  'pusd':9.0, 'yahoo':'AUDJPY=X','oanda':'AUD_JPY','psych':[90,95,100,105]},
    'AUDCAD': {'type':'forex','pip':0.0001,'pusd':7.5, 'yahoo':'AUDCAD=X','oanda':'AUD_CAD','psych':[0.88,0.90,0.92,0.95]},
    'EURCAD': {'type':'forex','pip':0.0001,'pusd':7.5, 'yahoo':'EURCAD=X','oanda':'EUR_CAD','psych':[1.45,1.50,1.55,1.60]},
    'GBPCAD': {'type':'forex','pip':0.0001,'pusd':7.5, 'yahoo':'GBPCAD=X','oanda':'GBP_CAD','psych':[1.70,1.75,1.80,1.85]},
    # Metals
    'XAUUSD': {'type':'metal','pip':0.1,   'pusd':1.0, 'yahoo':'GC=F',    'oanda':'XAU_USD','psych':[2000,2100,2200,2300]},
    'XAGUSD': {'type':'metal','pip':0.01,  'pusd':5.0, 'yahoo':'SI=F',    'oanda':'XAG_USD','psych':[25,30,35,40]},
    # Commodities
    'USOIL':  {'type':'commodity','pip':0.01,'pusd':1.0,'yahoo':'CL=F',   'oanda':'BCO_USD','psych':[70,75,80,85,90]},
    'NGAS':   {'type':'commodity','pip':0.001,'pusd':1.0,'yahoo':'NG=F',  'oanda':'NATGAS_USD','psych':[2,3,4,5]},
    # Indices
    'US500':  {'type':'index','pip':0.25,  'pusd':12.5,'yahoo':'^GSPC',   'oanda':'SPX500_USD','psych':[5000,5200,5400,5600]},
    'US30':   {'type':'index','pip':1.0,   'pusd':5.0, 'yahoo':'^DJI',    'oanda':'US30_USD','psych':[40000,41000,42000,43000]},
    'USTEC':  {'type':'index','pip':0.25,  'pusd':5.0, 'yahoo':'^NDX',    'oanda':'NAS100_USD','psych':[18000,19000,20000,21000]},
    'GER40':  {'type':'index','pip':1.0,   'pusd':1.0, 'yahoo':'^GDAXI',  'oanda':'DE30_EUR','psych':[17000,18000,19000,20000]},
    'UK100':  {'type':'index','pip':1.0,   'pusd':1.0, 'yahoo':'^FTSE',   'oanda':'UK100_GBP','psych':[7500,8000,8500,9000]},
    # Crypto
    'BTCUSD': {'type':'crypto','pip':1.0,  'pusd':1.0, 'yahoo':'BTC-USD', 'oanda':'BTC_USD','psych':[90000,95000,100000,105000]},
    'ETHUSD': {'type':'crypto','pip':0.1,  'pusd':1.0, 'yahoo':'ETH-USD', 'oanda':'ETH_USD','psych':[3000,3500,4000,4500]},
}

TRADING_PAIRS = list(MARKETS.keys())

# Global state
signals_store = []
agent_weights_store = {}
system_status = {'running':False,'last_run':None,'capital':CONFIG['INITIAL_CAPITAL']}

# ============================================================
# HELPERS
# ============================================================
def rsi(p, n=14):
    d = np.diff(p)
    g = pd.Series(np.where(d>0,d,0)).ewm(span=n).mean().values
    l = pd.Series(np.where(d<0,-d,0)).ewm(span=n).mean().values
    return np.concatenate([[50], 100-100/(1+g/(l+1e-10))])

def ema(p, n):
    return pd.Series(p).ewm(span=n,adjust=False).mean().values

def atr(h, l, c, n=14):
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    return np.concatenate([[tr[0]], pd.Series(tr).ewm(span=n).mean().values])

def swh(h, w=5):
    return [(i,h[i]) for i in range(w,len(h)-w) if h[i]==max(h[i-w:i+w+1])]

def swl(l, w=5):
    return [(i,l[i]) for i in range(w,len(l)-w) if l[i]==min(l[i-w:i+w+1])]

def safe_df(df):
    if df is None: return False
    if not isinstance(df, pd.DataFrame): return False
    return not df.empty and len(df) >= 20

# ============================================================
# DATA LOADER - ALL SOURCES
# ============================================================
class DataLoader:
    _cache = {}
    _ct = {}

    @classmethod
    def ohlcv(cls, symbol, period='365d', interval='1h'):
        k = f"{symbol}_{interval}"
        if k in cls._cache and time.time()-cls._ct.get(k,0)<300:
            return cls._cache[k]
        try:
            import yfinance as yf
            yahoo = MARKETS[symbol]['yahoo']
            df = yf.download(yahoo, period=period, interval=interval, progress=False, auto_adjust=True)
            if df.empty: return None
            df.columns = [c.lower() if isinstance(c,str) else c[0].lower() for c in df.columns]
            needed = [c for c in ['open','high','low','close','volume'] if c in df.columns]
            df = df[needed].dropna()
            if 'volume' not in df.columns: df['volume'] = 1000
            cls._cache[k] = df
            cls._ct[k] = time.time()
            return df
        except: return None

    @classmethod
    def multi_tf(cls, symbol):
        df4 = cls.ohlcv(symbol, '180d', '4h')
        if not safe_df(df4):
            df4 = cls.ohlcv(symbol, '180d', '1h')
        return {
            '1h': cls.ohlcv(symbol, '60d', '1h'),
            '4h': df4,
            '1d': cls.ohlcv(symbol, '365d', '1d'),
        }

    @classmethod
    def vix(cls):
        try:
            import yfinance as yf
            df = yf.download('^VIX', period='5d', interval='1d', progress=False, auto_adjust=True)
            return float(df['Close'].iloc[-1]) if not df.empty else 20.0
        except: return 20.0

    @classmethod
    def dxy(cls):
        try:
            import yfinance as yf
            df = yf.download('DX-Y.NYB', period='5d', interval='1d', progress=False, auto_adjust=True)
            return float(df['Close'].iloc[-1]) if not df.empty else 104.0
        except: return 104.0

    @classmethod
    def gold(cls):
        try:
            import yfinance as yf
            df = yf.download('GC=F', period='5d', interval='1d', progress=False, auto_adjust=True)
            return float(df['Close'].iloc[-1]) if not df.empty else 2000.0
        except: return 2000.0

    @classmethod
    def fear_greed(cls):
        """CNN Fear and Greed Index - no API key needed"""
        try:
            r = requests.get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata', timeout=10,
                headers={'User-Agent':'Mozilla/5.0'})
            if r.status_code == 200:
                data = r.json()
                score = data.get('fear_and_greed', {}).get('score', 50)
                rating = data.get('fear_and_greed', {}).get('rating', 'neutral')
                return {'score': float(score), 'rating': rating}
        except: pass
        return {'score': 50.0, 'rating': 'neutral'}

    @classmethod
    def myfxbook_sentiment(cls):
        """MyFxBook community sentiment - no API key needed"""
        try:
            r = requests.get('https://www.myfxbook.com/api/get-community-outlook.json',
                params={'session': ''}, timeout=10,
                headers={'User-Agent':'Mozilla/5.0'})
            if r.status_code == 200:
                data = r.json()
                symbols = data.get('symbols', [])
                sentiment = {}
                for s in symbols:
                    name = s.get('name', '').replace('/', '')
                    long_pct = float(s.get('longsPercentage', 50))
                    sentiment[name] = long_pct / 100.0
                return sentiment
        except: pass
        return {}

    @classmethod
    def fred_data(cls):
        try:
            from fredapi import Fred
            fred = Fred(api_key=CONFIG['FRED_API_KEY'])
            data = {}
            for sid, name in [('DFF','fed_rate'),('T10Y2Y','yield_curve'),('VIXCLS','vix_fred'),('DTWEXBGS','trade_usd')]:
                try: data[name] = float(fred.get_series(sid, limit=3).dropna().iloc[-1])
                except: data[name] = 0.0
            return data
        except: return {'fed_rate':5.25,'yield_curve':0.5,'vix_fred':20.0,'trade_usd':104.0}

    @classmethod
    def cot_data(cls):
        """CFTC Commitment of Traders - free government data"""
        try:
            r = requests.get('https://www.cftc.gov/dea/newcot/f_disagg.txt', timeout=20)
            if r.status_code == 200:
                cot = {}
                for line in r.text.split('\n')[:100]:
                    parts = line.split(',')
                    if len(parts) > 10:
                        name = parts[0].strip().replace('"','').upper()
                        try:
                            lg = int(parts[8].strip().replace('"',''))
                            sh = int(parts[9].strip().replace('"',''))
                            total = lg + sh
                            if total > 0:
                                if 'EURO FX' in name: cot['EURUSD'] = (lg-sh)/total
                                elif 'JAPANESE YEN' in name: cot['USDJPY'] = -(lg-sh)/total
                                elif 'BRITISH POUND' in name: cot['GBPUSD'] = (lg-sh)/total
                                elif 'AUSTRALIAN DOLLAR' in name: cot['AUDUSD'] = (lg-sh)/total
                                elif 'GOLD' in name: cot['XAUUSD'] = (lg-sh)/total
                        except: pass
                return cot
        except: pass
        return {}

    @classmethod
    def economic_calendar(cls):
        """Get upcoming economic events"""
        try:
            r = requests.get('https://nfs.faireconomy.media/ff_calendar_thisweek.json', timeout=10)
            if r.status_code == 200:
                events = r.json()
                upcoming = []
                now = datetime.utcnow()
                for ev in events:
                    try:
                        ev_time = datetime.strptime(ev.get('date',''), '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
                        diff = (ev_time - now).total_seconds() / 60
                        if -30 < diff < 120 and ev.get('impact') in ['High', 'Medium']:
                            upcoming.append({
                                'title': ev.get('title',''),
                                'impact': ev.get('impact',''),
                                'currency': ev.get('country',''),
                                'minutes': diff
                            })
                    except: pass
                return upcoming
        except: pass
        return []

    @classmethod
    def google_trends(cls, keyword):
        """Google Trends for currency interest"""
        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl='en-US', tz=360)
            pt.build_payload([keyword], timeframe='now 7-d')
            df = pt.interest_over_time()
            if not df.empty:
                recent = df[keyword].values[-5:]
                trend = (recent[-1] - recent[0]) / (recent[0] + 1e-10)
                return trend
        except: pass
        return 0.0

    @classmethod
    def news_sentiment(cls, symbol):
        try:
            from newsapi import NewsApiClient
            api = NewsApiClient(api_key=CONFIG['NEWS_API_KEY'])
            cur = symbol[:3]
            arts = api.get_everything(q=f'{cur} forex currency', language='en', page_size=5, sort_by='publishedAt')
            pos = ['bullish','rally','rise','gain','surge','strong','up','positive']
            neg = ['bearish','fall','drop','weak','decline','down','crash','negative']
            score = 0
            for a in arts.get('articles',[]):
                txt = (a.get('title','') + ' ' + a.get('description','')).lower()
                score += sum(1 for w in pos if w in txt) - sum(1 for w in neg if w in txt)
            return score / max(len(arts.get('articles',[])),1) / 5.0
        except: return 0.0

loader = DataLoader()

# ============================================================
# BASE AGENT
# ============================================================
class Agent:
    def __init__(self, name, weight=1.0):
        self.name = name
        self.weight = weight
        self.correct = 0
        self.total = 0
        agent_weights_store[name] = weight

    def analyze(self, df, symbol, ctx=None):
        return {'signal':0,'confidence':0.0,'reason':'base'}

    def learn(self, correct):
        self.total += 1
        if correct: self.correct += 1
        if self.total >= 10:
            acc = self.correct / self.total
            self.weight = max(0.3, min(2.5, 0.3 + acc * 1.7))
            agent_weights_store[self.name] = self.weight

# ============================================================
# LAYER 1 — MARKET STRUCTURE (8 agents)
# ============================================================
class BOS_CHOCHAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            sh,sl = swh(h[-100:]),swl(l[-100:])
            if len(sh)<2 or len(sl)<2: return {'signal':0,'confidence':0.3,'reason':'No structure'}
            lsh,psh = sh[-1][1],sh[-2][1]
            lsl,psl = sl[-1][1],sl[-2][1]
            cur = c[-1]
            if cur>lsh and lsh>psh: return {'signal':1,'confidence':0.88,'reason':f'Bullish BOS {lsh:.5f}'}
            if cur<lsl and lsl<psl: return {'signal':-1,'confidence':0.88,'reason':f'Bearish BOS {lsl:.5f}'}
            if cur>lsh and lsh<psh: return {'signal':1,'confidence':0.78,'reason':'Bullish CHOCH'}
            if cur<lsl and lsl>psl: return {'signal':-1,'confidence':0.78,'reason':'Bearish CHOCH'}
            return {'signal':0,'confidence':0.4,'reason':'Structure intact'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class LiquiditySweepAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            a = np.mean(atr(h,l,c)[-14:])
            kh,kl = np.max(h[-25:-5]),np.min(l[-25:-5])
            rh,rl = np.max(h[-3:]),np.min(l[-3:])
            cur = c[-1]
            if rl<kl and cur>kl+a*0.3: return {'signal':1,'confidence':0.90,'reason':f'Bull sweep {kl:.5f}'}
            if rh>kh and cur<kh-a*0.3: return {'signal':-1,'confidence':0.90,'reason':f'Bear sweep {kh:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No sweep'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class OrderBlockAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            o,h,l,c = df['open'].values,df['high'].values,df['low'].values,df['close'].values
            a = np.mean(atr(h,l,c)[-14:])
            cur = c[-1]
            for i in range(len(c)-10,len(c)-2):
                if i<5: continue
                if c[i]<o[i] and len(h)>i+5 and np.max(h[i+1:i+6])>h[i]+a*1.5:
                    ob_h,ob_l = max(o[i],c[i]),min(o[i],c[i])
                    if ob_l<=cur<=ob_h+a*0.5: return {'signal':1,'confidence':0.85,'reason':f'Bull OB {ob_l:.5f}'}
                if c[i]>o[i] and len(l)>i+5 and np.min(l[i+1:i+6])<l[i]-a*1.5:
                    ob_h,ob_l = max(o[i],c[i]),min(o[i],c[i])
                    if ob_l-a*0.5<=cur<=ob_h: return {'signal':-1,'confidence':0.85,'reason':f'Bear OB {ob_h:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No OB'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class FairValueGapAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            cur = c[-1]
            for i in range(len(c)-30,len(c)-2):
                if i<2: continue
                if l[i+1]>h[i-1] and h[i-1]<=cur<=l[i+1]:
                    return {'signal':1,'confidence':0.80,'reason':f'Bull FVG {h[i-1]:.5f}'}
                if h[i+1]<l[i-1] and h[i+1]<=cur<=l[i-1]:
                    return {'signal':-1,'confidence':0.80,'reason':f'Bear FVG {l[i-1]:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No FVG'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PremiumDiscountAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            rh,rl = np.max(h[-100:]),np.min(l[-100:])
            rng = rh-rl
            if rng==0: return {'signal':0,'confidence':0.3,'reason':'No range'}
            pos = (c[-1]-rl)/rng
            if pos<0.25: return {'signal':1,'confidence':0.80,'reason':f'Deep discount {pos:.1%}'}
            if pos<0.40: return {'signal':1,'confidence':0.58,'reason':f'Discount {pos:.1%}'}
            if pos>0.75: return {'signal':-1,'confidence':0.80,'reason':f'Deep premium {pos:.1%}'}
            if pos>0.60: return {'signal':-1,'confidence':0.58,'reason':f'Premium {pos:.1%}'}
            return {'signal':0,'confidence':0.4,'reason':f'Equilibrium {pos:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BreakerBlockAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            sh,sl = swh(h[-80:]),swl(l[-80:])
            if len(sh)<3 or len(sl)<3: return {'signal':0,'confidence':0.3,'reason':'No breaker'}
            cur = c[-1]
            a = np.mean(atr(h,l,c)[-14:])
            last_sh = sh[-1][1]
            last_sl = sl[-1][1]
            if cur>last_sh and c[-10]<last_sh:
                return {'signal':1,'confidence':0.75,'reason':f'Breaker block bull {last_sh:.5f}'}
            if cur<last_sl and c[-10]>last_sl:
                return {'signal':-1,'confidence':0.75,'reason':f'Breaker block bear {last_sl:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No breaker'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class InducementAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            sh,sl = swh(h[-50:]),swl(l[-50:])
            if len(sh)<2 or len(sl)<2: return {'signal':0,'confidence':0.3,'reason':'No inducement'}
            a = np.mean(atr(h,l,c)[-14:])
            cur = c[-1]
            if cur>sh[-2][1]+a*0.5 and c[-2]<sh[-2][1]:
                return {'signal':-1,'confidence':0.72,'reason':f'Inducement above {sh[-2][1]:.5f}'}
            if cur<sl[-2][1]-a*0.5 and c[-2]>sl[-2][1]:
                return {'signal':1,'confidence':0.72,'reason':f'Inducement below {sl[-2][1]:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No inducement'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MitigationBlockAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            o,h,l,c = df['open'].values,df['high'].values,df['low'].values,df['close'].values
            a = np.mean(atr(h,l,c)[-14:])
            cur = c[-1]
            for i in range(len(c)-50,len(c)-10):
                if i<5: continue
                if c[i]<o[i]:
                    mb_h,mb_l = max(o[i],c[i]),min(o[i],c[i])
                    if mb_l<=cur<=mb_h:
                        return {'signal':1,'confidence':0.70,'reason':f'Mitigation bull {mb_l:.5f}'}
                if c[i]>o[i]:
                    mb_h,mb_l = max(o[i],c[i]),min(o[i],c[i])
                    if mb_l<=cur<=mb_h:
                        return {'signal':-1,'confidence':0.70,'reason':f'Mitigation bear {mb_h:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No mitigation'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 2 — ICT CONCEPTS (8 agents)
# ============================================================
class KillzoneAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h = datetime.utcnow().hour
            if h==13: return {'signal':1,'confidence':0.90,'reason':'NY-London overlap peak'}
            if 8<=h<=10: return {'signal':1,'confidence':0.75,'reason':f'London killzone {h}:00'}
            if 13<=h<=16: return {'signal':1,'confidence':0.72,'reason':f'NY killzone {h}:00'}
            if 2<=h<=4: return {'signal':1,'confidence':0.65,'reason':f'Tokyo killzone {h}:00'}
            if 0<=h<=6: return {'signal':0,'confidence':0.55,'reason':'Asian low vol'}
            return {'signal':0,'confidence':0.4,'reason':f'Off-session {h}:00'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class OTEAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            rh,rl = np.max(h[-20:]),np.min(l[-20:])
            rng = rh-rl
            if rng==0: return {'signal':0,'confidence':0.3,'reason':'No range'}
            if c[-20]<c[-1]:
                ret = (rh-c[-1])/rng
                if 0.62<=ret<=0.79: return {'signal':1,'confidence':0.85,'reason':f'Bull OTE {ret:.1%}'}
            if c[-20]>c[-1]:
                ret = (c[-1]-rl)/rng
                if 0.62<=ret<=0.79: return {'signal':-1,'confidence':0.85,'reason':f'Bear OTE {ret:.1%}'}
            return {'signal':0,'confidence':0.3,'reason':'Not at OTE'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SilverBulletAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            ny = (datetime.utcnow().hour-4)%24
            if ny in [3,10,14]:
                c,h,l = df['close'].values,df['high'].values,df['low'].values
                a = np.mean(atr(h,l,c)[-14:])
                mv = c[-1]-c[-6]
                if mv>a*0.5: return {'signal':1,'confidence':0.78,'reason':f'SB bull {ny}:00 NY'}
                if mv<-a*0.5: return {'signal':-1,'confidence':0.78,'reason':f'SB bear {ny}:00 NY'}
            return {'signal':0,'confidence':0.3,'reason':'No silver bullet'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MidnightOpenAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            ny = (datetime.utcnow().hour-4)%24
            c = df['close'].values
            mo = c[-ny-1] if ny<len(c) else c[0]
            cur = c[-1]
            if cur>mo*1.001: return {'signal':1,'confidence':0.65,'reason':f'Above midnight open {mo:.5f}'}
            if cur<mo*0.999: return {'signal':-1,'confidence':0.65,'reason':f'Below midnight open {mo:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'At midnight open'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class AsianRangeAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            hour = datetime.utcnow().hour
            ah,al = np.max(h[-10:]),np.min(l[-10:])
            a = np.mean(atr(h,l,c)[-14:])
            if hour>=8:
                if c[-1]>ah+a*0.2: return {'signal':1,'confidence':0.74,'reason':f'Asian breakout {ah:.5f}'}
                if c[-1]<al-a*0.2: return {'signal':-1,'confidence':0.74,'reason':f'Asian breakdown {al:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'Within Asian range'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PowerOf3Agent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,h,l = df['close'].values,df['high'].values,df['low'].values
            hour = datetime.utcnow().hour
            dop = c[-24] if len(c)>24 else c[0]
            cur = c[-1]
            if 8<=hour<=10:
                if cur>dop: return {'signal':1,'confidence':0.68,'reason':'Po3 accumulation bull'}
                return {'signal':-1,'confidence':0.68,'reason':'Po3 accumulation bear'}
            return {'signal':0,'confidence':0.4,'reason':'Po3 waiting'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WeeklyOpenAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            wo = c[-5*24] if len(c)>120 else c[0]
            cur = c[-1]
            if cur>wo*1.005: return {'signal':1,'confidence':0.65,'reason':f'Above weekly open {wo:.5f}'}
            if cur<wo*0.995: return {'signal':-1,'confidence':0.65,'reason':f'Below weekly open {wo:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'Near weekly open'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class GapFillAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,o = df['close'].values,df['open'].values
            gap = o[-1]-c[-2]
            gp = abs(gap)/c[-2]
            if gp>0.002:
                if gap>0: return {'signal':-1,'confidence':0.72,'reason':f'Gap up {gp:.3%} fill expected'}
                return {'signal':1,'confidence':0.72,'reason':f'Gap down {gp:.3%} fill expected'}
            return {'signal':0,'confidence':0.35,'reason':'No gap'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 3 — WYCKOFF (6 agents)
# ============================================================
class WyckoffPhaseAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,h,l,v = df['close'].values,df['high'].values,df['low'].values,df['volume'].values
            rng = np.max(h[-50:])-np.min(l[-50:])
            avg = np.mean(c[-50:])
            rp = rng/avg
            if rp<0.02:
                vt = np.mean(v[-10:])/(np.mean(v[-50:-10])+1e-10)
                pos = (c[-1]-np.min(l[-50:]))/(rng+1e-10)
                if vt>1.2 and pos<0.4: return {'signal':1,'confidence':0.72,'reason':'Wyckoff accumulation'}
                if vt>1.2 and pos>0.6: return {'signal':-1,'confidence':0.72,'reason':'Wyckoff distribution'}
            ret = np.diff(c[-20:])
            if np.sum(ret>0)>14: return {'signal':1,'confidence':0.65,'reason':'Wyckoff markup'}
            if np.sum(ret<0)>14: return {'signal':-1,'confidence':0.65,'reason':'Wyckoff markdown'}
            return {'signal':0,'confidence':0.4,'reason':f'Wyckoff range {rp:.2%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SpringUpthrustAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            sup = np.min(l[-50:-5]) if len(l)>55 else np.min(l[:-5])
            res = np.max(h[-50:-5]) if len(h)>55 else np.max(h[:-5])
            a = np.mean(atr(h,l,c)[-14:])
            if l[-2]<sup and c[-1]>sup+a*0.3: return {'signal':1,'confidence':0.90,'reason':f'Spring {sup:.5f}'}
            if h[-2]>res and c[-1]<res-a*0.3: return {'signal':-1,'confidence':0.90,'reason':f'Upthrust {res:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No spring/upthrust'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WyckoffVolumeAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v = df['close'].values,df['volume'].values
            pu = c[-1]>c[-2]
            vu = v[-1]>np.mean(v[-20:])
            if pu and vu: return {'signal':1,'confidence':0.70,'reason':'High vol bull - institutions buying'}
            if not pu and vu: return {'signal':-1,'confidence':0.70,'reason':'High vol bear - institutions selling'}
            if pu and not vu: return {'signal':-1,'confidence':0.55,'reason':'Low vol rally - weak'}
            return {'signal':1,'confidence':0.55,'reason':'Low vol decline - weak'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class AccumulationAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v,h,l = df['close'].values,df['volume'].values,df['high'].values,df['low'].values
            rng50 = np.max(h[-50:])-np.min(l[-50:])
            avg50 = np.mean(c[-50:])
            if rng50/avg50 < 0.015:
                if c[-1]<avg50 and v[-1]>np.mean(v[-20:]):
                    return {'signal':1,'confidence':0.72,'reason':'Accumulation zone with volume'}
            return {'signal':0,'confidence':0.4,'reason':'Not in accumulation'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class DistributionAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v,h,l = df['close'].values,df['volume'].values,df['high'].values,df['low'].values
            rng50 = np.max(h[-50:])-np.min(l[-50:])
            avg50 = np.mean(c[-50:])
            if rng50/avg50 < 0.015:
                if c[-1]>avg50 and v[-1]>np.mean(v[-20:]):
                    return {'signal':-1,'confidence':0.72,'reason':'Distribution zone with volume'}
            return {'signal':0,'confidence':0.4,'reason':'Not in distribution'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CompositeManAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v = df['close'].values,df['volume'].values
            bv = sum(v[i] for i in range(len(c)-20,len(c)) if c[i]>c[i-1])
            sv = sum(v[i] for i in range(len(c)-20,len(c)) if c[i]<c[i-1])
            delta = (bv-sv)/(bv+sv+1e-10)
            if delta>0.3: return {'signal':1,'confidence':0.70,'reason':f'Composite Man buying delta={delta:.2f}'}
            if delta<-0.3: return {'signal':-1,'confidence':0.70,'reason':f'Composite Man selling delta={delta:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'CM neutral delta={delta:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 4 — TECHNICAL (15 agents)
# ============================================================
class MomentumAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            r = rsi(c)
            m = ema(c,12)-ema(c,26)
            sig = ema(m,9)
            s,reasons = 0,[]
            if r[-1]<30: s+=1; reasons.append(f'RSI OS {r[-1]:.0f}')
            elif r[-1]>70: s-=1; reasons.append(f'RSI OB {r[-1]:.0f}')
            if m[-1]>sig[-1] and m[-2]<=sig[-2]: s+=1; reasons.append('MACD bull X')
            elif m[-1]<sig[-1] and m[-2]>=sig[-2]: s-=1; reasons.append('MACD bear X')
            return {'signal':int(np.sign(s)),'confidence':min(abs(s)*0.35+0.25,0.85),'reason':' | '.join(reasons) or 'Neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class TrendStrengthAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ma20,ma50 = ema(c,20),ema(c,50)
            ma200 = ema(c,200) if len(c)>200 else ema(c,50)
            s,reasons = 0,[]
            if c[-1]>ma20[-1]>ma50[-1]: s+=2; reasons.append('Price>MA20>MA50 bull')
            elif c[-1]<ma20[-1]<ma50[-1]: s-=2; reasons.append('Price<MA20<MA50 bear')
            if len(c)>200:
                if c[-1]>ma200[-1]: s+=1; reasons.append('Above MA200')
                else: s-=1; reasons.append('Below MA200')
            return {'signal':int(np.sign(s)),'confidence':min(abs(s)*0.2+0.3,0.85),'reason':' | '.join(reasons)}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SupportResistanceAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            rh,rl = np.max(h[-50:]),np.min(l[-50:])
            rng = rh-rl
            if rng==0: return {'signal':0,'confidence':0.3,'reason':'Flat'}
            pos = (c[-1]-rl)/rng
            if pos<0.15: return {'signal':1,'confidence':0.78,'reason':f'Strong support {rl:.5f}'}
            if pos>0.85: return {'signal':-1,'confidence':0.78,'reason':f'Strong resistance {rh:.5f}'}
            return {'signal':0,'confidence':0.35,'reason':f'Mid range {pos:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BollingerAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ma = ema(c,20)
            std = pd.Series(c).rolling(20).std().values
            up,dn = ma+2*std,ma-2*std
            cur = c[-1]
            if cur<dn[-1]: return {'signal':1,'confidence':0.74,'reason':f'Below BB lower {dn[-1]:.5f}'}
            if cur>up[-1]: return {'signal':-1,'confidence':0.74,'reason':f'Above BB upper {up[-1]:.5f}'}
            if cur>ma[-1]: return {'signal':1,'confidence':0.50,'reason':'Above BB mid'}
            return {'signal':-1,'confidence':0.50,'reason':'Below BB mid'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MeanReversionAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values[-100:]
            z = (c[-1]-np.mean(c))/(np.std(c)+1e-10)
            if z<-2.5: return {'signal':1,'confidence':0.85,'reason':f'Z={z:.2f} extreme OS'}
            if z>2.5: return {'signal':-1,'confidence':0.85,'reason':f'Z={z:.2f} extreme OB'}
            if z<-1.5: return {'signal':1,'confidence':0.65,'reason':f'Z={z:.2f} OS'}
            if z>1.5: return {'signal':-1,'confidence':0.65,'reason':f'Z={z:.2f} OB'}
            return {'signal':0,'confidence':0.35,'reason':f'Z={z:.2f} neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BreakoutAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            kh,kl = np.max(h[-21:-1]),np.min(l[-21:-1])
            a = np.mean(atr(h,l,c)[-14:])
            if c[-1]>kh+a*0.1: return {'signal':1,'confidence':0.78,'reason':f'20p breakout {kh:.5f}'}
            if c[-1]<kl-a*0.1: return {'signal':-1,'confidence':0.78,'reason':f'20p breakdown {kl:.5f}'}
            return {'signal':0,'confidence':0.35,'reason':'No breakout'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CandlestickAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            o,h,l,c = df['open'].values[-5:],df['high'].values[-5:],df['low'].values[-5:],df['close'].values[-5:]
            body = abs(c[-1]-o[-1])
            uw = h[-1]-max(c[-1],o[-1])
            lw = min(c[-1],o[-1])-l[-1]
            if lw>body*2 and uw<body*0.5: return {'signal':1,'confidence':0.70,'reason':'Hammer'}
            if uw>body*2 and lw<body*0.5: return {'signal':-1,'confidence':0.70,'reason':'Shooting star'}
            if c[-1]>o[-1] and c[-2]<o[-2] and c[-1]>o[-2] and o[-1]<c[-2]: return {'signal':1,'confidence':0.74,'reason':'Bull engulf'}
            if c[-1]<o[-1] and c[-2]>o[-2] and c[-1]<o[-2] and o[-1]>c[-2]: return {'signal':-1,'confidence':0.74,'reason':'Bear engulf'}
            if all(c[-i]>o[-i] for i in [1,2,3]): return {'signal':1,'confidence':0.68,'reason':'3 white soldiers'}
            if all(c[-i]<o[-i] for i in [1,2,3]): return {'signal':-1,'confidence':0.68,'reason':'3 black crows'}
            return {'signal':0,'confidence':0.3,'reason':'No pattern'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class StochasticAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            lo = pd.Series(l).rolling(14).min().values
            hi = pd.Series(h).rolling(14).max().values
            k = 100*(c-lo)/(hi-lo+1e-10)
            d = pd.Series(k).rolling(3).mean().values
            if k[-1]<20 and d[-1]<20: return {'signal':1,'confidence':0.72,'reason':f'Stoch OS K={k[-1]:.0f}'}
            if k[-1]>80 and d[-1]>80: return {'signal':-1,'confidence':0.72,'reason':f'Stoch OB K={k[-1]:.0f}'}
            if k[-1]>d[-1] and k[-2]<=d[-2]: return {'signal':1,'confidence':0.62,'reason':'Stoch bull X'}
            if k[-1]<d[-1] and k[-2]>=d[-2]: return {'signal':-1,'confidence':0.62,'reason':'Stoch bear X'}
            return {'signal':0,'confidence':0.35,'reason':f'Stoch neutral {k[-1]:.0f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class ElliottWaveAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values[-50:]
            sh = swh(c)
            sl = swl(c)
            if len(sh)<3 or len(sl)<3: return {'signal':0,'confidence':0.3,'reason':'No waves'}
            if sh[-1][1]>sh[-2][1]>sh[-3][1] and sl[-1][1]>sl[-2][1]:
                return {'signal':1,'confidence':0.70,'reason':'Elliott wave 3 bullish'}
            if sh[-1][1]<sh[-2][1]<sh[-3][1] and sl[-1][1]<sl[-2][1]:
                return {'signal':-1,'confidence':0.70,'reason':'Elliott wave 3 bearish'}
            return {'signal':0,'confidence':0.4,'reason':'Elliott wave unclear'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class ADXTrendAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            a = atr(h,l,c)
            dm_plus = np.maximum(h[1:]-h[:-1], 0)
            dm_minus = np.maximum(l[:-1]-l[1:], 0)
            dmp = pd.Series(dm_plus).ewm(span=14).mean().values
            dmm = pd.Series(dm_minus).ewm(span=14).mean().values
            atr14 = pd.Series(a[1:]).ewm(span=14).mean().values
            dip = 100*dmp/(atr14+1e-10)
            dim = 100*dmm/(atr14+1e-10)
            dx = 100*abs(dip-dim)/(dip+dim+1e-10)
            adx = pd.Series(dx).ewm(span=14).mean().values
            if adx[-1]>25 and dip[-1]>dim[-1]: return {'signal':1,'confidence':0.72,'reason':f'ADX {adx[-1]:.0f} bull trend'}
            if adx[-1]>25 and dim[-1]>dip[-1]: return {'signal':-1,'confidence':0.72,'reason':f'ADX {adx[-1]:.0f} bear trend'}
            return {'signal':0,'confidence':0.4,'reason':f'ADX {adx[-1]:.0f} no trend'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CCIAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            tp = (h+l+c)/3
            ma = pd.Series(tp).rolling(20).mean().values
            md = pd.Series(tp).rolling(20).apply(lambda x: np.mean(np.abs(x-x.mean()))).values
            cci = (tp-ma)/(0.015*md+1e-10)
            if cci[-1]<-100: return {'signal':1,'confidence':0.70,'reason':f'CCI OS {cci[-1]:.0f}'}
            if cci[-1]>100: return {'signal':-1,'confidence':0.70,'reason':f'CCI OB {cci[-1]:.0f}'}
            return {'signal':0,'confidence':0.35,'reason':f'CCI neutral {cci[-1]:.0f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WilliamsRAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            hi = pd.Series(h).rolling(14).max().values
            lo = pd.Series(l).rolling(14).min().values
            wr = -100*(hi-c)/(hi-lo+1e-10)
            if wr[-1]<-80: return {'signal':1,'confidence':0.68,'reason':f'WR OS {wr[-1]:.0f}'}
            if wr[-1]>-20: return {'signal':-1,'confidence':0.68,'reason':f'WR OB {wr[-1]:.0f}'}
            return {'signal':0,'confidence':0.35,'reason':f'WR neutral {wr[-1]:.0f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class ParabolicSARAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            af,max_af = 0.02,0.2
            bull = c[1]>c[0]
            sar = l[0] if bull else h[0]
            ep = h[0] if bull else l[0]
            sars = [sar]
            for i in range(1,len(c)):
                if bull:
                    if h[i]>ep: ep=h[i]; af=min(af+0.02,max_af)
                    sar = min(sar+af*(ep-sar), l[i-1])
                    if c[i]<sar: bull=False; sar=ep; ep=l[i]; af=0.02
                else:
                    if l[i]<ep: ep=l[i]; af=min(af+0.02,max_af)
                    sar = max(sar+af*(ep-sar), h[i-1])
                    if c[i]>sar: bull=True; sar=ep; ep=h[i]; af=0.02
                sars.append(sar)
            if bull: return {'signal':1,'confidence':0.65,'reason':f'PSAR bull {sars[-1]:.5f}'}
            return {'signal':-1,'confidence':0.65,'reason':f'PSAR bear {sars[-1]:.5f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VolatilityRegimeAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            cv = np.std(ret[-20:])*np.sqrt(252)
            hv = np.std(ret[-100:])*np.sqrt(252)
            ratio = cv/(hv+1e-10)
            if ratio<0.7: return {'signal':1,'confidence':0.65,'reason':f'Low vol {cv:.3f} breakout likely'}
            if ratio>1.8: return {'signal':0,'confidence':0.68,'reason':f'High vol {cv:.3f} reduce size'}
            return {'signal':0,'confidence':0.4,'reason':f'Normal vol {cv:.3f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 5 — VOLUME AND FLOW (8 agents)
# ============================================================
class VWAPAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c,v = df['high'].values,df['low'].values,df['close'].values,df['volume'].values
            tp = (h+l+c)/3
            vwap = np.cumsum(tp*v)/(np.cumsum(v)+1e-10)
            a = np.mean(atr(h,l,c)[-14:])
            dev = (c[-1]-vwap[-1])/(a+1e-10)
            if dev<-2: return {'signal':1,'confidence':0.74,'reason':f'{dev:.1f}x below VWAP'}
            if dev>2: return {'signal':-1,'confidence':0.74,'reason':f'{dev:.1f}x above VWAP'}
            if c[-1]>vwap[-1]: return {'signal':1,'confidence':0.55,'reason':'Above VWAP'}
            return {'signal':-1,'confidence':0.55,'reason':'Below VWAP'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class DarkPoolAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v = df['close'].values,df['volume'].values
            av = np.mean(v[-50:])
            lv = v[-1]>av*2.5
            pm = abs(c[-1]-c[-2])/c[-2]
            if lv and pm<0.001:
                if c[-1]>c[-2]: return {'signal':1,'confidence':0.78,'reason':'Dark pool accumulation'}
                return {'signal':-1,'confidence':0.78,'reason':'Dark pool distribution'}
            if lv and pm>0.003:
                if c[-1]>c[-2]: return {'signal':1,'confidence':0.72,'reason':'Institutional buying'}
                return {'signal':-1,'confidence':0.72,'reason':'Institutional selling'}
            return {'signal':0,'confidence':0.35,'reason':'Normal volume'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SmartMoneyAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v = df['close'].values,df['volume'].values
            bv = sum(v[i] for i in range(len(c)-20,len(c)) if i>0 and c[i]>c[i-1])
            sv = sum(v[i] for i in range(len(c)-20,len(c)) if i>0 and c[i]<c[i-1])
            d = (bv-sv)/(bv+sv+1e-10)
            if d>0.3: return {'signal':1,'confidence':0.72,'reason':f'Smart money bull delta={d:.2f}'}
            if d<-0.3: return {'signal':-1,'confidence':0.72,'reason':f'Smart money bear delta={d:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Neutral delta={d:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VolumeProfileAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v,h,l = df['close'].values,df['volume'].values,df['high'].values,df['low'].values
            prices = np.linspace(np.min(l[-100:]),np.max(h[-100:]),50)
            vp = np.zeros(50)
            for i in range(len(c)-100,len(c)):
                if i<0: continue
                idx = np.argmin(abs(prices-c[i]))
                vp[idx] += v[i]
            poc_idx = np.argmax(vp)
            poc = prices[poc_idx]
            cur = c[-1]
            a = np.mean(atr(h,l,c)[-14:])
            if abs(cur-poc)<a*0.5:
                return {'signal':0,'confidence':0.60,'reason':f'At POC {poc:.5f} expect bounce'}
            if cur<poc: return {'signal':1,'confidence':0.65,'reason':f'Below POC {poc:.5f} likely return'}
            return {'signal':-1,'confidence':0.65,'reason':f'Above POC {poc:.5f} likely return'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class OrderFlowAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v,h,l = df['close'].values,df['volume'].values,df['high'].values,df['low'].values
            buy_press = []
            sell_press = []
            for i in range(max(0,len(c)-20),len(c)):
                if i==0: continue
                hl = h[i]-l[i]+1e-10
                buy_press.append(v[i]*(c[i]-l[i])/hl)
                sell_press.append(v[i]*(h[i]-c[i])/hl)
            if not buy_press: return {'signal':0,'confidence':0.4,'reason':'No flow'}
            bp = sum(buy_press)
            sp = sum(sell_press)
            ratio = bp/(sp+1e-10)
            if ratio>1.5: return {'signal':1,'confidence':0.70,'reason':f'Buy pressure {ratio:.2f}'}
            if ratio<0.67: return {'signal':-1,'confidence':0.70,'reason':f'Sell pressure {ratio:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Flow neutral {ratio:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SpreadAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            sp = h[-20:]-l[-20:]
            avg_sp = np.mean(sp)
            cur_sp = sp[-1]
            if cur_sp>avg_sp*1.5: return {'signal':0,'confidence':0.62,'reason':f'Wide spread avoid'}
            if cur_sp<avg_sp*0.7: return {'signal':1,'confidence':0.58,'reason':f'Tight spread good liquidity'}
            return {'signal':0,'confidence':0.4,'reason':'Normal spread'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CumulativeDeltaAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,v = df['close'].values,df['volume'].values
            delta = np.array([v[i] if c[i]>c[i-1] else -v[i] for i in range(1,len(c))])
            cd = np.cumsum(delta)
            cd_trend = cd[-1]-cd[-20]
            price_trend = c[-1]-c[-20]
            if cd_trend>0 and price_trend>0: return {'signal':1,'confidence':0.68,'reason':'CD confirms bull trend'}
            if cd_trend<0 and price_trend<0: return {'signal':-1,'confidence':0.68,'reason':'CD confirms bear trend'}
            if cd_trend>0 and price_trend<0: return {'signal':1,'confidence':0.72,'reason':'CD divergence bull'}
            if cd_trend<0 and price_trend>0: return {'signal':-1,'confidence':0.72,'reason':'CD divergence bear'}
            return {'signal':0,'confidence':0.4,'reason':'CD neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class TickDataProxyAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            a_vals = atr(h,l,c)
            cur_a = a_vals[-1]
            avg_a = np.mean(a_vals[-20:])
            pip = MARKETS.get(symbol,{}).get('pip',0.0001)
            cur_pips = cur_a/pip
            if cur_pips<5: return {'signal':0,'confidence':0.65,'reason':f'Very low tick activity {cur_pips:.0f} pips'}
            if cur_pips>50: return {'signal':0,'confidence':0.60,'reason':f'Very high tick activity {cur_pips:.0f} pips avoid'}
            if cur_a<avg_a*0.5: return {'signal':1,'confidence':0.60,'reason':'Low tick - breakout building'}
            return {'signal':0,'confidence':0.4,'reason':f'Normal tick {cur_pips:.0f} pips'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 6 — INTERMARKET (10 agents)
# ============================================================
class DXYAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            dxy = ctx.get('dxy',104) if ctx else 104
            ub = symbol.startswith('USD')
            uq = symbol[3:]=='USD' or symbol.endswith('USD')
            if dxy>106:
                if ub: return {'signal':1,'confidence':0.70,'reason':f'DXY strong {dxy:.1f}'}
                if uq: return {'signal':-1,'confidence':0.70,'reason':f'DXY strong {dxy:.1f}'}
            elif dxy<101:
                if ub: return {'signal':-1,'confidence':0.70,'reason':f'DXY weak {dxy:.1f}'}
                if uq: return {'signal':1,'confidence':0.70,'reason':f'DXY weak {dxy:.1f}'}
            return {'signal':0,'confidence':0.4,'reason':f'DXY neutral {dxy:.1f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VIXAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            vix = ctx.get('vix',20) if ctx else 20
            safe = ['USDJPY','USDCHF','XAUUSD','XAGUSD']
            risk = ['AUDUSD','NZDUSD','BTCUSD','ETHUSD','GBPUSD']
            if vix>30:
                if symbol in safe: return {'signal':1,'confidence':0.75,'reason':f'VIX fear {vix:.1f} safe haven'}
                if symbol in risk: return {'signal':-1,'confidence':0.75,'reason':f'VIX fear {vix:.1f} risk off'}
            elif vix<15:
                if symbol in risk: return {'signal':1,'confidence':0.68,'reason':f'VIX low {vix:.1f} risk on'}
                if symbol in safe and symbol!='XAUUSD': return {'signal':-1,'confidence':0.62,'reason':f'VIX low safe out'}
            return {'signal':0,'confidence':0.4,'reason':f'VIX neutral {vix:.1f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BondYieldAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            fred = ctx.get('fred_data',{}) if ctx else {}
            yc = fred.get('yield_curve',0.5)
            fr = fred.get('fed_rate',5.25)
            if yc<0:
                if symbol in ['USDJPY','XAUUSD']: return {'signal':1,'confidence':0.70,'reason':f'Inverted curve {yc:.2f}'}
                return {'signal':-1,'confidence':0.58,'reason':'Inverted curve recession'}
            if fr>5 and symbol.startswith('USD'): return {'signal':1,'confidence':0.62,'reason':f'High rates {fr:.2f}%'}
            return {'signal':0,'confidence':0.4,'reason':f'Rates normal {fr:.2f}%'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CarryTradeAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            fred = ctx.get('fred_data',{}) if ctx else {}
            us = fred.get('fed_rate',5.25)
            rates = {'USDJPY':us-0.1,'USDCHF':us-0.75,'AUDUSD':4.35-us,'NZDUSD':5.5-us,'EURJPY':4.0-0.1}
            if symbol in rates:
                diff = rates[symbol]
                if diff>2: return {'signal':1,'confidence':0.68,'reason':f'Carry long {diff:.2f}%'}
                if diff<-2: return {'signal':-1,'confidence':0.68,'reason':f'Negative carry {diff:.2f}%'}
            return {'signal':0,'confidence':0.4,'reason':'Carry neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class GoldAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            gold = ctx.get('gold',2000) if ctx else 2000
            if symbol=='XAUUSD': return {'signal':0,'confidence':0.4,'reason':'Is gold'}
            if gold>2200:
                if symbol in ['AUDUSD','NZDUSD']: return {'signal':1,'confidence':0.65,'reason':f'Gold high {gold:.0f}'}
                if symbol.startswith('USD'): return {'signal':-1,'confidence':0.60,'reason':f'Gold high {gold:.0f}'}
            elif gold<1800:
                if symbol.startswith('USD'): return {'signal':1,'confidence':0.60,'reason':f'Gold low {gold:.0f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Gold neutral {gold:.0f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class RiskSentimentAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            vix = ctx.get('vix',20) if ctx else 20
            dxy = ctx.get('dxy',104) if ctx else 104
            score = 0
            if vix<15: score+=1
            elif vix>25: score-=1
            if dxy<102: score+=1
            elif dxy>106: score-=1
            risk = ['AUDUSD','NZDUSD','GBPUSD','BTCUSD','ETHUSD']
            safe = ['USDJPY','USDCHF','XAUUSD']
            if score>0:
                if symbol in risk: return {'signal':1,'confidence':0.65,'reason':'Risk ON'}
                if symbol in safe: return {'signal':-1,'confidence':0.60,'reason':'Risk ON safe out'}
            elif score<0:
                if symbol in safe: return {'signal':1,'confidence':0.65,'reason':'Risk OFF'}
                if symbol in risk: return {'signal':-1,'confidence':0.65,'reason':'Risk OFF'}
            return {'signal':0,'confidence':0.4,'reason':'Mixed sentiment'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class OilCadAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            if 'CAD' not in symbol: return {'signal':0,'confidence':0.4,'reason':'Not CAD pair'}
            try:
                import yfinance as yf
                oil = yf.download('CL=F', period='5d', interval='1d', progress=False, auto_adjust=True)
                if oil.empty: return {'signal':0,'confidence':0.4,'reason':'No oil data'}
                oil_ret = (float(oil['Close'].iloc[-1])-float(oil['Close'].iloc[-2]))/float(oil['Close'].iloc[-2])
                if symbol=='USDCAD':
                    if oil_ret>0.01: return {'signal':-1,'confidence':0.65,'reason':f'Oil up {oil_ret:.2%} CAD bull'}
                    if oil_ret<-0.01: return {'signal':1,'confidence':0.65,'reason':f'Oil down {oil_ret:.2%} CAD bear'}
            except: pass
            return {'signal':0,'confidence':0.4,'reason':'Oil neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class InterestRateDiffAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            fred = ctx.get('fred_data',{}) if ctx else {}
            us_rate = fred.get('fed_rate',5.25)
            rates = {'EUR':4.0,'GBP':5.0,'AUD':4.35,'NZD':5.5,'JPY':0.1,'CHF':1.5,'CAD':4.5}
            base,quote = symbol[:3],symbol[3:]
            br = rates.get(base,us_rate if base=='USD' else 0)
            qr = rates.get(quote,us_rate if quote=='USD' else 0)
            diff = br-qr
            if diff>1.5: return {'signal':1,'confidence':0.65,'reason':f'Rate diff {diff:.2f}% base favored'}
            if diff<-1.5: return {'signal':-1,'confidence':0.65,'reason':f'Rate diff {diff:.2f}% quote favored'}
            return {'signal':0,'confidence':0.4,'reason':f'Rate diff neutral {diff:.2f}%'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class EquityCorrelationAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            import yfinance as yf
            spx = yf.download('^GSPC', period='5d', interval='1d', progress=False, auto_adjust=True)
            if spx.empty: return {'signal':0,'confidence':0.4,'reason':'No equity data'}
            spx_ret = (float(spx['Close'].iloc[-1])-float(spx['Close'].iloc[-2]))/float(spx['Close'].iloc[-2])
            risk = ['AUDUSD','NZDUSD','GBPUSD']
            safe = ['USDJPY','USDCHF','XAUUSD']
            if spx_ret>0.01:
                if symbol in risk: return {'signal':1,'confidence':0.62,'reason':f'Equity up {spx_ret:.2%} risk on'}
                if symbol in safe: return {'signal':-1,'confidence':0.58,'reason':f'Equity up safe out'}
            elif spx_ret<-0.01:
                if symbol in safe: return {'signal':1,'confidence':0.62,'reason':f'Equity down {spx_ret:.2%} safe haven'}
                if symbol in risk: return {'signal':-1,'confidence':0.58,'reason':f'Equity down risk off'}
            return {'signal':0,'confidence':0.4,'reason':f'Equity neutral {spx_ret:.2%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CryptoSentimentAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            r = requests.get('https://api.alternative.me/fng/', timeout=8)
            if r.status_code==200:
                data = r.json()
                score = int(data['data'][0]['value'])
                label = data['data'][0]['value_classification']
                if symbol in ['BTCUSD','ETHUSD']:
                    if score>70: return {'signal':1,'confidence':0.68,'reason':f'Crypto F&G greed {score}'}
                    if score<30: return {'signal':-1,'confidence':0.68,'reason':f'Crypto F&G fear {score}'}
                elif symbol in ['AUDUSD','NZDUSD']:
                    if score>70: return {'signal':1,'confidence':0.55,'reason':f'Crypto greed risk on'}
                    if score<30: return {'signal':-1,'confidence':0.55,'reason':f'Crypto fear risk off'}
            return {'signal':0,'confidence':0.4,'reason':'Crypto sentiment neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 7 — QUANTITATIVE (10 agents)
# ============================================================
class HurstAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            if len(c)<100: return {'signal':0,'confidence':0.3,'reason':'insufficient'}
            rs_vals = []
            for lag in [10,20,40,80]:
                if lag>len(c): continue
                s = c[-lag:]
                m = np.mean(s)
                dev = s-m
                R = np.max(np.cumsum(dev))-np.min(np.cumsum(dev))
                S = np.std(s)
                if S>0: rs_vals.append(np.log(R/S)/np.log(lag))
            if not rs_vals: return {'signal':0,'confidence':0.3,'reason':'Cannot calc'}
            h = np.mean(rs_vals)
            if h>0.6:
                trend = c[-1]-c[-20]
                return {'signal':1 if trend>0 else -1,'confidence':0.74,'reason':f'Hurst {h:.2f} trending'}
            if h<0.4:
                z = (c[-1]-np.mean(c[-50:]))/(np.std(c[-50:])+1e-10)
                return {'signal':-1 if z>1 else (1 if z<-1 else 0),'confidence':0.68,'reason':f'Hurst {h:.2f} MR'}
            return {'signal':0,'confidence':0.4,'reason':f'Hurst {h:.2f} random'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MonteCarloAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            mu,sigma = np.mean(ret[-100:]),np.std(ret[-100:])
            sims = np.random.normal(mu,sigma,(1000,24))
            final = np.sum(sims,axis=1)
            pu = np.mean(final>0)
            var95 = np.percentile(final,5)
            if pu>0.62: return {'signal':1,'confidence':pu,'reason':f'MC {pu:.1%} bull VaR={var95:.4f}'}
            if pu<0.38: return {'signal':-1,'confidence':1-pu,'reason':f'MC {1-pu:.1%} bear'}
            return {'signal':0,'confidence':0.4,'reason':f'MC uncertain {pu:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class FibTimeAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            fib = [1,1,2,3,5,8,13,21,34,55,89]
            sh = swh(c[-100:])
            sl = swl(c[-100:])
            if not sh or not sl: return {'signal':0,'confidence':0.3,'reason':'No swings'}
            last = max(sh[-1][0] if sh else 0, sl[-1][0] if sl else 0)
            bars = len(c)-100+last
            if bars in fib:
                trend = c[-1]-c[-20]
                return {'signal':1 if trend>0 else -1,'confidence':0.68,'reason':f'Fib time {bars} bars'}
            return {'signal':0,'confidence':0.35,'reason':f'No fib time {bars}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PsychLevelAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            levels = MARKETS.get(symbol,{}).get('psych',[])
            cur = c[-1]
            a = np.mean(np.diff(c[-14:]))
            for level in levels:
                dist = abs(cur-level)/level
                if dist<0.002:
                    if cur<level: return {'signal':1,'confidence':0.74,'reason':f'Psych level {level}'}
                    return {'signal':-1,'confidence':0.74,'reason':f'Psych level {level}'}
            return {'signal':0,'confidence':0.35,'reason':'No psych level'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class KellyAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            import yfinance as yf
            c = df['close'].values
            ret = np.diff(c)/c[:-1]
            wins = ret[ret>0]
            losses = ret[ret<0]
            if len(wins)<5 or len(losses)<5: return {'signal':0,'confidence':0.5,'reason':'Insufficient Kelly data'}
            wr = len(wins)/(len(wins)+len(losses))
            avg_win = np.mean(wins)
            avg_loss = abs(np.mean(losses))
            kelly = wr-(1-wr)/(avg_win/(avg_loss+1e-10))
            if kelly>0.2: return {'signal':1,'confidence':min(kelly+0.4,0.85),'reason':f'Kelly {kelly:.2f} positive'}
            if kelly<0: return {'signal':0,'confidence':0.72,'reason':f'Kelly {kelly:.2f} negative reduce'}
            return {'signal':0,'confidence':0.5,'reason':f'Kelly neutral {kelly:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class StatArbitAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            z_score = (c[-1]-np.mean(c[-50:]))/np.std(c[-50:]+1e-10)
            half_life = 10
            mean_rev_speed = 1-np.exp(-np.log(2)/half_life)
            expected_move = -mean_rev_speed*z_score
            if expected_move>0.5: return {'signal':1,'confidence':0.68,'reason':f'StatArb bull z={z_score:.2f}'}
            if expected_move<-0.5: return {'signal':-1,'confidence':0.68,'reason':f'StatArb bear z={z_score:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'StatArb neutral z={z_score:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CVaRAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            var95 = np.percentile(ret[-100:],5)
            cvar = np.mean(ret[ret<var95]) if len(ret[ret<var95])>0 else var95
            sigma = np.std(ret[-20:])
            if abs(cvar)/sigma>3: return {'signal':0,'confidence':0.80,'reason':f'CVaR extreme {cvar:.4f} reduce size'}
            if abs(cvar)/sigma>2: return {'signal':0,'confidence':0.65,'reason':f'CVaR elevated {cvar:.4f}'}
            return {'signal':1,'confidence':0.45,'reason':f'CVaR normal {cvar:.4f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CorrelationAgent(Agent):
    _pairs_cache = {}
    def analyze(self, df, symbol, ctx=None):
        try:
            pairs = ['EURUSD','GBPUSD','USDJPY','AUDUSD']
            corr_map = {
                ('EURUSD','GBPUSD'): 0.85,
                ('EURUSD','AUDUSD'): 0.70,
                ('EURUSD','USDJPY'): -0.75,
                ('GBPUSD','AUDUSD'): 0.75,
            }
            c = df['close'].values
            trend = 1 if c[-1]>c[-20] else -1
            for (p1,p2),corr in corr_map.items():
                if symbol in [p1,p2]:
                    other = p2 if symbol==p1 else p1
                    df2 = loader.ohlcv(other,'30d','1h')
                    if safe_df(df2):
                        c2 = df2['close'].values
                        trend2 = 1 if c2[-1]>c2[-20] else -1
                        if corr>0.7 and trend==trend2:
                            return {'signal':trend,'confidence':0.65,'reason':f'Corr {other} {corr:.2f} confirms'}
            return {'signal':0,'confidence':0.4,'reason':'No strong correlation signal'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class RegimeDetectorAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            vol20 = np.std(ret[-20:])
            vol100 = np.std(ret[-100:])
            trend20 = (c[-1]-c[-20])/c[-20]
            trend5 = (c[-1]-c[-5])/c[-5]
            vol_ratio = vol20/vol100
            if vol_ratio<0.7 and abs(trend20)<0.005:
                return {'signal':0,'confidence':0.65,'reason':'Ranging regime use MR strategy'}
            elif vol_ratio>1.3 and abs(trend20)>0.01:
                signal = 1 if trend20>0 else -1
                return {'signal':signal,'confidence':0.70,'reason':f'Trending regime {trend20:.2%}'}
            elif vol_ratio>2.0:
                return {'signal':0,'confidence':0.75,'reason':'Volatile regime avoid trading'}
            return {'signal':0,'confidence':0.4,'reason':'Mixed regime'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VolForecastAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            garch_vol = np.sqrt(0.1*ret[-1]**2 + 0.9*np.var(ret[-20:]))
            hist_vol = np.std(ret[-20:])
            ratio = garch_vol/hist_vol
            if ratio>1.3: return {'signal':0,'confidence':0.68,'reason':f'Vol expanding {ratio:.2f} caution'}
            if ratio<0.7: return {'signal':1,'confidence':0.62,'reason':f'Vol contracting {ratio:.2f} breakout likely'}
            return {'signal':0,'confidence':0.4,'reason':f'Vol stable {ratio:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 8 — SENTIMENT (10 agents)
# ============================================================
class FearGreedAgent(Agent):
    _cache = None
    _cache_time = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            now = time.time()
            if self._cache is None or now-self._cache_time>3600:
                FearGreedAgent._cache = loader.fear_greed()
                FearGreedAgent._cache_time = now
            fg = self._cache
            score = fg.get('score',50)
            rating = fg.get('rating','neutral')
            risk = ['AUDUSD','NZDUSD','GBPUSD','BTCUSD','ETHUSD']
            safe = ['USDJPY','USDCHF','XAUUSD']
            if score<25:
                if symbol in safe: return {'signal':1,'confidence':0.72,'reason':f'F&G extreme fear {score:.0f}'}
                if symbol in risk: return {'signal':-1,'confidence':0.72,'reason':f'F&G extreme fear {score:.0f}'}
            elif score>75:
                if symbol in risk: return {'signal':1,'confidence':0.68,'reason':f'F&G greed {score:.0f}'}
                if symbol in safe: return {'signal':-1,'confidence':0.62,'reason':f'F&G greed safe out'}
            return {'signal':0,'confidence':0.4,'reason':f'F&G neutral {score:.0f} {rating}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MyFxBookAgent(Agent):
    _cache = {}
    _cache_time = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            now = time.time()
            if not self._cache or now-self._cache_time>3600:
                MyFxBookAgent._cache = loader.myfxbook_sentiment()
                MyFxBookAgent._cache_time = now
            sent = self._cache.get(symbol, 0.5)
            if sent>0.7: return {'signal':-1,'confidence':0.68,'reason':f'MyFxBook {sent:.0%} long retail fade'}
            if sent<0.3: return {'signal':1,'confidence':0.68,'reason':f'MyFxBook {sent:.0%} short retail fade'}
            return {'signal':0,'confidence':0.4,'reason':f'MyFxBook neutral {sent:.0%} long'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class COTAgent(Agent):
    _cache = {}
    _cache_time = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            cot = ctx.get('cot',{}) if ctx else {}
            score = cot.get(symbol,0)
            if score>0.2: return {'signal':1,'confidence':0.70,'reason':f'COT inst net long {score:.2f}'}
            if score<-0.2: return {'signal':-1,'confidence':0.70,'reason':f'COT inst net short {score:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'COT neutral {score:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class NewsSentimentAgent(Agent):
    _cache = {}
    _cache_time = {}
    def analyze(self, df, symbol, ctx=None):
        try:
            now = time.time()
            if symbol not in self._cache or now-self._cache_time.get(symbol,0)>3600:
                NewsSentimentAgent._cache[symbol] = loader.news_sentiment(symbol)
                NewsSentimentAgent._cache_time[symbol] = now
            score = self._cache[symbol]
            if score>0.3: return {'signal':1,'confidence':min(0.5+score,0.80),'reason':f'News positive {score:.2f}'}
            if score<-0.3: return {'signal':-1,'confidence':min(0.5+abs(score),0.80),'reason':f'News negative {score:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'News neutral {score:.2f}'}
        except: return {'signal':0,'confidence':0.3,'reason':'News unavailable'}

class GoogleTrendsAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            cur = symbol[:3]
            keywords = {'EUR':'euro','GBP':'pound','JPY':'yen','AUD':'australian dollar','USD':'dollar'}
            kw = keywords.get(cur,'forex')
            trend = loader.google_trends(kw)
            if trend>0.2: return {'signal':1,'confidence':0.58,'reason':f'Google Trends {kw} rising {trend:.2f}'}
            if trend<-0.2: return {'signal':-1,'confidence':0.58,'reason':f'Google Trends {kw} falling {trend:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Google Trends neutral {trend:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CryptoFGAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            r = requests.get('https://api.alternative.me/fng/', timeout=8)
            if r.status_code==200:
                score = int(r.json()['data'][0]['value'])
                if symbol in ['BTCUSD','ETHUSD']:
                    if score>70: return {'signal':1,'confidence':0.70,'reason':f'Crypto FG greed {score}'}
                    if score<30: return {'signal':-1,'confidence':0.70,'reason':f'Crypto FG fear {score}'}
            return {'signal':0,'confidence':0.4,'reason':'Crypto FG neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MacroSentimentAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            fg = ctx.get('fear_greed',{}) if ctx else {}
            vix = ctx.get('vix',20) if ctx else 20
            score = fg.get('score',50)
            macro_bull = 0
            if score>60: macro_bull+=1
            elif score<40: macro_bull-=1
            if vix<18: macro_bull+=1
            elif vix>25: macro_bull-=1
            if macro_bull>0: return {'signal':1,'confidence':0.62,'reason':f'Macro bull FG={score:.0f} VIX={vix:.0f}'}
            if macro_bull<0: return {'signal':-1,'confidence':0.62,'reason':f'Macro bear FG={score:.0f} VIX={vix:.0f}'}
            return {'signal':0,'confidence':0.4,'reason':'Macro neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SocialSentimentAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            r = requests.get(f'https://api.coingecko.com/api/v3/search/trending', timeout=8)
            if r.status_code==200:
                data = r.json()
                trending = [c['item']['symbol'].upper() for c in data.get('coins',[])]
                cur = symbol[:3]
                if cur in ['BTC','ETH'] and symbol in ['BTCUSD','ETHUSD']:
                    if any(t in ['BTC','ETH'] for t in trending[:3]):
                        return {'signal':1,'confidence':0.62,'reason':f'{cur} trending on social'}
            return {'signal':0,'confidence':0.4,'reason':'Social neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class RetailSentimentContraryAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            myfx = ctx.get('myfxbook',{}) if ctx else {}
            sent = myfx.get(symbol, 0.5)
            if sent>0.75: return {'signal':-1,'confidence':0.72,'reason':f'Retail {sent:.0%} long - contrary SELL'}
            if sent<0.25: return {'signal':1,'confidence':0.72,'reason':f'Retail {sent:.0%} short - contrary BUY'}
            return {'signal':0,'confidence':0.4,'reason':f'Retail balanced {sent:.0%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PutCallAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            r = requests.get('https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_EOD.csv', timeout=10)
            if r.status_code==200:
                lines = r.text.strip().split('\n')
                if len(lines)>2:
                    last = lines[-1].split(',')
                    if len(last)>4:
                        vix_close = float(last[4])
                        if vix_close>30: return {'signal':1,'confidence':0.65,'reason':f'CBOE VIX high {vix_close:.1f} contrarian bull'}
                        if vix_close<15: return {'signal':-1,'confidence':0.60,'reason':f'CBOE VIX low {vix_close:.1f} complacency'}
            return {'signal':0,'confidence':0.4,'reason':'VIX neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 9 — CALENDAR AND FUNDAMENTAL (10 agents)
# ============================================================
class EconomicCalendarAgent(Agent):
    _cache = []
    _cache_time = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            now = time.time()
            if not self._cache or now-self._cache_time>1800:
                EconomicCalendarAgent._cache = loader.economic_calendar()
                EconomicCalendarAgent._cache_time = now
            events = self._cache
            cur = symbol[:3]
            for ev in events:
                if ev.get('currency','').upper()==cur or ev.get('currency','').upper()==symbol[3:]:
                    mins = ev.get('minutes',99)
                    impact = ev.get('impact','Low')
                    if impact=='High' and -15<mins<60:
                        return {'signal':0,'confidence':0.92,'reason':f"High impact {ev.get('title','')} in {mins:.0f}min"}
                    if impact=='Medium' and -10<mins<30:
                        return {'signal':0,'confidence':0.75,'reason':f"Medium impact {ev.get('title','')} in {mins:.0f}min"}
            return {'signal':0,'confidence':0.4,'reason':'No news risk'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class FREDMacroAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            fred = ctx.get('fred_data',{}) if ctx else {}
            rate = fred.get('fed_rate',5.25)
            yc = fred.get('yield_curve',0.5)
            trade = fred.get('trade_usd',104)
            signal = 0
            reasons = []
            if rate>5 and 'USD' in symbol[:3]: signal+=1; reasons.append(f'High Fed rate {rate:.2f}%')
            if yc<0: signal-=1; reasons.append(f'Inverted curve {yc:.2f}')
            if trade>108 and symbol.startswith('USD'): signal+=1; reasons.append(f'Trade USD strong {trade:.1f}')
            return {'signal':int(np.sign(signal)),'confidence':min(abs(signal)*0.2+0.4,0.75),'reason':' | '.join(reasons) or 'FRED neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SeasonalAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            month = datetime.utcnow().month
            seasonal = {
                'USDJPY':{1:1,3:-1,9:1,12:1},
                'EURUSD':{1:-1,4:1,8:-1,12:-1},
                'GBPUSD':{1:-1,5:1,9:-1},
                'XAUUSD':{1:1,8:1,11:1,12:1},
                'AUDUSD':{3:1,7:-1,9:-1},
                'BTCUSD':{1:1,4:1,11:1,12:1,9:-1},
            }
            bias = seasonal.get(symbol,{}).get(month,0)
            if bias!=0: return {'signal':bias,'confidence':0.60,'reason':f'Seasonal {month} month bias {symbol}'}
            return {'signal':0,'confidence':0.4,'reason':'No seasonal signal'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CentralBankAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            fred = ctx.get('fred_data',{}) if ctx else {}
            rate = fred.get('fed_rate',5.25)
            yc = fred.get('yield_curve',0.5)
            if rate>5 and yc>0 and symbol.startswith('USD'):
                return {'signal':1,'confidence':0.65,'reason':f'Fed hawkish {rate:.2f}%'}
            if yc<0:
                return {'signal':0,'confidence':0.68,'reason':'Inverted curve pivot likely'}
            return {'signal':0,'confidence':0.4,'reason':f'CB neutral rate={rate:.2f}%'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class COTPositioningAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            cot = ctx.get('cot',{}) if ctx else {}
            score = cot.get(symbol,0)
            if abs(score)>0.4:
                signal = 1 if score>0 else -1
                return {'signal':signal,'confidence':0.74,'reason':f'COT extreme positioning {score:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'COT normal {score:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SafeHavenAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            vix = ctx.get('vix',20) if ctx else 20
            gold = ctx.get('gold',2000) if ctx else 2000
            score = 0
            if vix>25: score+=1
            if gold>2200: score+=1
            safe = ['USDJPY','USDCHF','XAUUSD','XAGUSD']
            risk = ['AUDUSD','NZDUSD','GBPUSD']
            if score>=2:
                if symbol in safe: return {'signal':1,'confidence':0.72,'reason':'Safe haven demand strong'}
                if symbol in risk: return {'signal':-1,'confidence':0.70,'reason':'Risk assets pressure'}
            return {'signal':0,'confidence':0.4,'reason':'Normal sentiment'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WorldBankAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            r = requests.get('https://api.worldbank.org/v2/country/US/indicator/NY.GDP.MKTP.KD.ZG?format=json&mrv=2',
                timeout=10)
            if r.status_code==200:
                data = r.json()
                if len(data)>1 and data[1]:
                    gdp = data[1][0].get('value')
                    if gdp and gdp>3:
                        if 'USD' in symbol[:3]: return {'signal':1,'confidence':0.58,'reason':f'US GDP strong {gdp:.1f}%'}
                    elif gdp and gdp<1:
                        if 'USD' in symbol[:3]: return {'signal':-1,'confidence':0.55,'reason':f'US GDP weak {gdp:.1f}%'}
            return {'signal':0,'confidence':0.4,'reason':'GDP neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class InflationAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            from fredapi import Fred
            fred = Fred(api_key=CONFIG['FRED_API_KEY'])
            cpi = fred.get_series('CPIAUCSL', limit=3)
            cpi_yoy = (cpi.iloc[-1]-cpi.iloc[-13])/cpi.iloc[-13]*100 if len(cpi)>13 else 3.0
            if cpi_yoy>4:
                if 'USD' in symbol[:3]: return {'signal':1,'confidence':0.60,'reason':f'High CPI {cpi_yoy:.1f}% Fed hawkish'}
                return {'signal':-1,'confidence':0.55,'reason':f'High inflation risk off'}
            if cpi_yoy<2:
                if 'USD' in symbol[:3]: return {'signal':-1,'confidence':0.58,'reason':f'Low CPI {cpi_yoy:.1f}% Fed dovish'}
            return {'signal':0,'confidence':0.4,'reason':f'CPI normal {cpi_yoy:.1f}%'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class GeopoliticalAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            from newsapi import NewsApiClient
            api = NewsApiClient(api_key=CONFIG['NEWS_API_KEY'])
            arts = api.get_top_headlines(q='war sanctions conflict crisis', language='en', page_size=5)
            count = len(arts.get('articles',[]))
            safe = ['USDJPY','USDCHF','XAUUSD']
            risk = ['AUDUSD','NZDUSD']
            if count>3:
                if symbol in safe: return {'signal':1,'confidence':0.65,'reason':f'Geopolitical risk {count} events'}
                if symbol in risk: return {'signal':-1,'confidence':0.62,'reason':f'Geopolitical risk off'}
            return {'signal':0,'confidence':0.4,'reason':'No geopolitical risk'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 10 — SESSION AND TIME (8 agents)
# ============================================================
class SessionDNAAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h = datetime.utcnow().hour
            c = df['close'].values
            r_val = rsi(c)[-1]
            if 8<=h<13:
                if r_val<45: return {'signal':1,'confidence':0.65,'reason':f'London bull session {h}:00'}
                if r_val>55: return {'signal':-1,'confidence':0.65,'reason':f'London bear session {h}:00'}
            elif 13<=h<21:
                if r_val<45: return {'signal':1,'confidence':0.68,'reason':f'NY bull session {h}:00'}
                if r_val>55: return {'signal':-1,'confidence':0.68,'reason':f'NY bear session {h}:00'}
            elif 21<=h or h<6:
                return {'signal':0,'confidence':0.65,'reason':f'Dead zone {h}:00 avoid'}
            return {'signal':0,'confidence':0.4,'reason':f'Session {h}:00'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class DayOfWeekAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            day = datetime.utcnow().weekday()
            c = df['close'].values
            if day==4: return {'signal':0,'confidence':0.70,'reason':'Friday close risk positions'}
            if day==0:
                gap = c[-1]-c[-2]
                if abs(gap)/c[-2]>0.001:
                    return {'signal':-1 if gap>0 else 1,'confidence':0.67,'reason':f'Monday gap fill expected'}
            if day==2: return {'signal':0,'confidence':0.55,'reason':'Wednesday caution FOMC risk'}
            return {'signal':0,'confidence':0.4,'reason':f'Day {day} neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class NewsTrapAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h = datetime.utcnow().hour
            m = datetime.utcnow().minute
            danger = [(8,30),(13,30),(14,0),(15,0),(17,30),(18,0)]
            for dh,dm in danger:
                diff = abs((h*60+m)-(dh*60+dm))
                if diff<=30:
                    return {'signal':0,'confidence':0.88,'reason':f'News danger {dh}:{dm:02d} UTC avoid'}
            return {'signal':0,'confidence':0.4,'reason':'News safe'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class TimeOfDayAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h = datetime.utcnow().hour
            c = df['close'].values
            best_hours = {
                'EURUSD':[8,9,10,13,14],'GBPUSD':[8,9,10,13,14],
                'USDJPY':[0,1,2,13,14],'XAUUSD':[8,13,14,15],
                'AUDUSD':[0,1,2,22,23],'BTCUSD':[13,14,20,21],
            }
            good = best_hours.get(symbol,[8,13,14])
            if h in good:
                r_val = rsi(c)[-1]
                if r_val<45: return {'signal':1,'confidence':0.62,'reason':f'Best hour {h}:00 for {symbol} bull'}
                if r_val>55: return {'signal':-1,'confidence':0.62,'reason':f'Best hour {h}:00 for {symbol} bear'}
            return {'signal':0,'confidence':0.4,'reason':f'Off-peak {h}:00'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MonthlyOpenAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            mo = c[-30*24] if len(c)>720 else c[0]
            cur = c[-1]
            if cur>mo*1.01: return {'signal':1,'confidence':0.62,'reason':f'Above monthly open {mo:.5f}'}
            if cur<mo*0.99: return {'signal':-1,'confidence':0.62,'reason':f'Below monthly open {mo:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'Near monthly open'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WeekendRiskAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            day = datetime.utcnow().weekday()
            h = datetime.utcnow().hour
            if day==4 and h>=18:
                return {'signal':0,'confidence':0.85,'reason':'Friday evening close positions weekend gap risk'}
            if day==6 or (day==0 and h<6):
                return {'signal':0,'confidence':0.75,'reason':'Weekend gap risk wait for market open'}
            return {'signal':0,'confidence':0.4,'reason':'No weekend risk'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class QuarterlyTheoryAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            month = datetime.utcnow().month
            qmap = {1:'Q1 start bull bias',2:'Q1 mid',3:'Q1 end rebalance',
                    4:'Q2 start',5:'Q2 mid',6:'Q2 end rebalance',
                    7:'Q3 start',8:'Q3 mid',9:'Q3 end rebalance',
                    10:'Q4 start bull',11:'Q4 mid bull',12:'Q4 end santa rally'}
            bull_months = [1,4,7,10,11,12]
            bear_months = [3,6,9]
            if month in bull_months:
                return {'signal':1,'confidence':0.60,'reason':f'Quarterly theory {qmap.get(month,"")}'}
            if month in bear_months:
                return {'signal':-1,'confidence':0.58,'reason':f'Quarterly rebalance {qmap.get(month,"")}'}
            return {'signal':0,'confidence':0.4,'reason':f'Quarter neutral {qmap.get(month,"")}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class EndOfMonthAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            day = datetime.utcnow().day
            import calendar
            last = calendar.monthrange(datetime.utcnow().year, datetime.utcnow().month)[1]
            days_left = last-day
            if days_left<=3:
                return {'signal':0,'confidence':0.68,'reason':f'End of month rebalancing {days_left}d left'}
            if day<=3:
                return {'signal':1,'confidence':0.58,'reason':f'Start of month fresh positioning'}
            return {'signal':0,'confidence':0.4,'reason':'Normal month period'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 11 — RISK PROTECTION (10 agents)
# ============================================================
class DrawdownGuardAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            cap = system_status.get('capital',CONFIG['INITIAL_CAPITAL'])
            init = CONFIG['INITIAL_CAPITAL']
            dd = (init-cap)/init
            if dd>0.10: return {'signal':0,'confidence':0.98,'reason':f'DD {dd:.1%} HALT ALL TRADING'}
            if dd>0.07: return {'signal':0,'confidence':0.90,'reason':f'DD {dd:.1%} stop trading reduce'}
            if dd>0.05: return {'signal':0,'confidence':0.80,'reason':f'DD {dd:.1%} caution reduce size'}
            if dd>0.03: return {'signal':0,'confidence':0.65,'reason':f'DD {dd:.1%} be selective'}
            return {'signal':1,'confidence':0.4,'reason':f'DD ok {dd:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MaxExposureAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            open_pos = len([s for s in signals_store if s.get('status')=='open'])
            if open_pos>=CONFIG['MAX_POSITIONS']:
                return {'signal':0,'confidence':0.92,'reason':f'Max positions {open_pos} reached'}
            if open_pos>=CONFIG['MAX_POSITIONS']-1:
                return {'signal':0,'confidence':0.72,'reason':f'Near max {open_pos} positions'}
            return {'signal':1,'confidence':0.4,'reason':f'Positions ok {open_pos}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VolatilityFilterAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h,l,c = df['high'].values,df['low'].values,df['close'].values
            a_vals = atr(h,l,c)[-14:]
            cur_a = a_vals[-1]
            avg_a = np.mean(a_vals)
            if cur_a>avg_a*2.5: return {'signal':0,'confidence':0.80,'reason':f'ATR spike {cur_a:.5f} avoid'}
            if cur_a<avg_a*0.3: return {'signal':0,'confidence':0.62,'reason':f'ATR too low {cur_a:.5f}'}
            return {'signal':1,'confidence':0.4,'reason':f'ATR normal {cur_a:.5f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CorrelationBlockerAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            corr_groups = [
                ['EURUSD','GBPUSD','AUDUSD','NZDUSD'],
                ['USDJPY','USDCHF'],
                ['BTCUSD','ETHUSD'],
            ]
            open_sigs = [s.get('symbol') for s in signals_store if s.get('status')=='open']
            for group in corr_groups:
                if symbol in group:
                    others_open = [s for s in open_sigs if s in group and s!=symbol]
                    if len(others_open)>=2:
                        return {'signal':0,'confidence':0.80,'reason':f'Correlated position limit {others_open}'}
            return {'signal':1,'confidence':0.4,'reason':'No correlation block'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PositionSizerAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            cap = system_status.get('capital',CONFIG['INITIAL_CAPITAL'])
            risk_amount = cap*CONFIG['RISK_PER_TRADE']
            if risk_amount<10: return {'signal':0,'confidence':0.85,'reason':f'Risk amount ${risk_amount:.2f} too small'}
            if cap<CONFIG['INITIAL_CAPITAL']*0.5:
                return {'signal':0,'confidence':0.75,'reason':f'Capital halved ${cap:.0f} reduce trading'}
            return {'signal':1,'confidence':0.4,'reason':f'Position size ok ${risk_amount:.0f} risk'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class TrailingStopConceptAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,h,l = df['close'].values,df['high'].values,df['low'].values
            a = np.mean(atr(h,l,c)[-14:])
            recent_high = np.max(h[-10:])
            recent_low = np.min(l[-10:])
            cur = c[-1]
            if cur>recent_high-a*0.5: return {'signal':1,'confidence':0.60,'reason':f'Near 10p high trail bull {recent_high:.5f}'}
            if cur<recent_low+a*0.5: return {'signal':-1,'confidence':0.60,'reason':f'Near 10p low trail bear {recent_low:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'Trail neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BreakevenConceptAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values
            ret_1d = (c[-1]-c[-24])/c[-24] if len(c)>24 else 0
            if abs(ret_1d)>0.01:
                signal = 1 if ret_1d>0 else -1
                return {'signal':signal,'confidence':0.60,'reason':f'1D move {ret_1d:.2%} momentum'}
            return {'signal':0,'confidence':0.4,'reason':f'1D flat {ret_1d:.3%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class LiquidityFilterAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            h = datetime.utcnow().hour
            low_liq = ['NZDUSD','USDNOK','USDSEK']
            if symbol in low_liq and (h<6 or h>21):
                return {'signal':0,'confidence':0.70,'reason':f'{symbol} low liquidity hours {h}:00'}
            mtype = MARKETS.get(symbol,{}).get('type','forex')
            if mtype=='crypto' and h in [7,12,16,20]:
                return {'signal':1,'confidence':0.55,'reason':f'Crypto active hour {h}:00'}
            return {'signal':1,'confidence':0.4,'reason':'Liquidity ok'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class AccountProtectionAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            cap = system_status.get('capital',CONFIG['INITIAL_CAPITAL'])
            init = CONFIG['INITIAL_CAPITAL']
            if cap<init*0.7:
                return {'signal':0,'confidence':0.98,'reason':f'Account down 30% STOP TRADING ${cap:.0f}'}
            if cap<init*0.85:
                return {'signal':0,'confidence':0.88,'reason':f'Account down 15% reduce ${cap:.0f}'}
            return {'signal':1,'confidence':0.4,'reason':f'Account healthy ${cap:.0f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MarginSafetyAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            cap = system_status.get('capital',CONFIG['INITIAL_CAPITAL'])
            open_count = len([s for s in signals_store if s.get('status')=='open'])
            est_margin = open_count * cap * 0.02
            margin_use = est_margin/cap if cap>0 else 0
            if margin_use>0.3: return {'signal':0,'confidence':0.85,'reason':f'Margin {margin_use:.1%} high avoid'}
            if margin_use>0.2: return {'signal':0,'confidence':0.65,'reason':f'Margin {margin_use:.1%} elevated'}
            return {'signal':1,'confidence':0.4,'reason':f'Margin safe {margin_use:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 12 — ML MODELS (5 agents)
# ============================================================
class RandomForestAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            from sklearn.ensemble import RandomForestClassifier
            c,h,l,v = df['close'].values,df['high'].values,df['low'].values,df['volume'].values
            if len(c)<60: return {'signal':0,'confidence':0.5,'reason':'RF insufficient data'}
            r_vals = rsi(c)
            m_vals = ema(c,12)-ema(c,26)
            a_vals = atr(h,l,c)
            X,y = [],[]
            for i in range(30,len(c)-5):
                X.append([r_vals[i],m_vals[i],a_vals[i],(c[i]-c[i-20])/c[i-20],(c[i]-c[i-5])/c[i-5],v[i]/(np.mean(v[max(0,i-20):i])+1e-10)])
                y.append(1 if c[i+5]>c[i]*1.001 else (-1 if c[i+5]<c[i]*0.999 else 0))
            if len(set(y))<2: return {'signal':0,'confidence':0.5,'reason':'RF no variance'}
            Xa,ya = np.array(X[:-5]),np.array(y[:-5])
            rf = RandomForestClassifier(n_estimators=50,random_state=42,max_depth=5)
            rf.fit(Xa,ya)
            feat = [[r_vals[-1],m_vals[-1],a_vals[-1],(c[-1]-c[-20])/c[-20],(c[-1]-c[-5])/c[-5],v[-1]/(np.mean(v[-20:])+1e-10)]]
            pred = rf.predict(feat)[0]
            prob = max(rf.predict_proba(feat)[0])
            return {'signal':int(pred),'confidence':float(prob),'reason':f'RF pred={pred} prob={prob:.2f}'}
        except: return {'signal':0,'confidence':0.5,'reason':'RF error'}

class GradientBoostAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            c,h,l = df['close'].values,df['high'].values,df['low'].values
            if len(c)<50: return {'signal':0,'confidence':0.5,'reason':'GB insufficient'}
            r_vals = rsi(c)
            X,y = [],[]
            for i in range(20,len(c)-3):
                X.append([r_vals[i],(c[i]-np.mean(c[i-20:i]))/(np.std(c[i-20:i])+1e-10),(h[i]-l[i])/(np.mean(h[i-10:i]-l[i-10:i])+1e-10)])
                y.append(1 if c[i+3]>c[i] else -1)
            Xa,ya = np.array(X[:-3]),np.array(y[:-3])
            gb = GradientBoostingClassifier(n_estimators=30,max_depth=3,random_state=42)
            gb.fit(Xa,ya)
            feat = [[r_vals[-1],(c[-1]-np.mean(c[-20:]))/(np.std(c[-20:])+1e-10),(h[-1]-l[-1])/(np.mean(h[-10:]-l[-10:])+1e-10)]]
            pred = gb.predict(feat)[0]
            prob = max(gb.predict_proba(feat)[0])
            return {'signal':int(pred),'confidence':float(prob),'reason':f'GB pred={pred} conf={prob:.2f}'}
        except: return {'signal':0,'confidence':0.5,'reason':'GB error'}

class LSTMProxyAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c = df['close'].values[-50:]
            seq_len = 10
            X,y = [],[]
            for i in range(seq_len,len(c)-1):
                seq = (c[i-seq_len:i]-np.mean(c[i-seq_len:i]))/(np.std(c[i-seq_len:i])+1e-10)
                X.append(seq)
                y.append(1 if c[i+1]>c[i] else 0)
            if len(X)<10: return {'signal':0,'confidence':0.5,'reason':'LSTM insufficient'}
            from sklearn.linear_model import LogisticRegression
            lr = LogisticRegression(random_state=42)
            lr.fit(X[:-2],y[:-2])
            seq_cur = (c[-seq_len:]-np.mean(c[-seq_len:]))/(np.std(c[-seq_len:])+1e-10)
            pred = lr.predict([seq_cur])[0]
            prob = max(lr.predict_proba([seq_cur])[0])
            signal = 1 if pred==1 else -1
            return {'signal':signal,'confidence':float(prob),'reason':f'LSTM-proxy {signal} conf={prob:.2f}'}
        except: return {'signal':0,'confidence':0.5,'reason':'LSTM error'}

class EnsembleMLAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            from sklearn.ensemble import VotingClassifier
            from sklearn.tree import DecisionTreeClassifier
            from sklearn.neighbors import KNeighborsClassifier
            c,h,l = df['close'].values,df['high'].values,df['low'].values
            if len(c)<40: return {'signal':0,'confidence':0.5,'reason':'Ensemble insufficient'}
            r_vals = rsi(c)
            X,y = [],[]
            for i in range(15,len(c)-3):
                X.append([r_vals[i],(c[i]-c[i-5])/c[i-5],(c[i]-c[i-10])/c[i-10],(h[i]-l[i])/c[i]])
                y.append(1 if c[i+3]>c[i] else -1)
            Xa,ya = np.array(X[:-3]),np.array(y[:-3])
            if len(set(ya))<2: return {'signal':0,'confidence':0.5,'reason':'No variance'}
            vc = VotingClassifier([
                ('dt',DecisionTreeClassifier(max_depth=3,random_state=42)),
                ('knn',KNeighborsClassifier(n_neighbors=5))
            ])
            vc.fit(Xa,ya)
            feat = [[r_vals[-1],(c[-1]-c[-5])/c[-5],(c[-1]-c[-10])/c[-10],(h[-1]-l[-1])/c[-1]]]
            pred = vc.predict(feat)[0]
            prob = max(vc.predict_proba(feat)[0])
            return {'signal':int(pred),'confidence':float(prob),'reason':f'Ensemble {pred} conf={prob:.2f}'}
        except: return {'signal':0,'confidence':0.5,'reason':'Ensemble error'}

class PatternRecognitionAgent(Agent):
    def analyze(self, df, symbol, ctx=None):
        try:
            c,h,l = df['close'].values,df['high'].values,df['low'].values
            patterns = []
            if len(c)<30: return {'signal':0,'confidence':0.3,'reason':'insufficient'}
            hl_ratio = (c[-1]-np.min(l[-20:]))/(np.max(h[-20:])-np.min(l[-20:])+1e-10)
            momentum = (c[-1]-c[-10])/c[-10]
            vol_comp = (h[-1]-l[-1])/(np.mean(h[-10:]-l[-10:])+1e-10)
            if hl_ratio<0.2 and momentum>0.001: patterns.append(('bull_reversal',0.75))
            if hl_ratio>0.8 and momentum<-0.001: patterns.append(('bear_reversal',0.75))
            if vol_comp>2 and momentum>0: patterns.append(('bull_breakout',0.70))
            if vol_comp>2 and momentum<0: patterns.append(('bear_breakout',0.70))
            if not patterns: return {'signal':0,'confidence':0.35,'reason':'No pattern'}
            best = max(patterns,key=lambda x:x[1])
            signal = 1 if 'bull' in best[0] else -1
            return {'signal':signal,'confidence':best[1],'reason':f'Pattern: {best[0]}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 13 — LLM SPECIALISTS (8 agents)
# ============================================================
class LLMReasoningAgent(Agent):
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<15: return {'signal':0,'confidence':0.5,'reason':'LLM rate limited'}
            c = df['close'].values
            ret = (c[-1]-c[-24])/c[-24]*100 if len(c)>24 else 0
            vix = ctx.get('vix',20) if ctx else 20
            dxy = ctx.get('dxy',104) if ctx else 104
            fg = ctx.get('fear_greed',{}) if ctx else {}
            prompt = f"""Expert forex trader. Analyze {symbol}:
24h: {ret:.2f}% | Price: {c[-1]:.5f} | VIX: {vix:.1f} | DXY: {dxy:.1f} | FG: {fg.get('score',50):.0f}
Agent votes: {ctx.get('votes_summary','mixed') if ctx else 'mixed'}
JSON only: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            LLMReasoningAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"LLM: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'LLM unavailable'}

class MacroAnalystAgent(Agent):
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<30: return {'signal':0,'confidence':0.5,'reason':'Macro LLM cooling'}
            fred = ctx.get('fred_data',{}) if ctx else {}
            prompt = f"""Macro analyst. {symbol} outlook:
Fed Rate: {fred.get('fed_rate',5.25):.2f}% | Yield Curve: {fred.get('yield_curve',0.5):.3f} | VIX: {ctx.get('vix',20) if ctx else 20:.1f}
JSON: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            MacroAnalystAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"Macro: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'Macro analyst unavailable'}

class RiskReviewerAgent(Agent):
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<30: return {'signal':0,'confidence':0.5,'reason':'Risk LLM cooling'}
            cap = system_status.get('capital',CONFIG['INITIAL_CAPITAL'])
            dd = (CONFIG['INITIAL_CAPITAL']-cap)/CONFIG['INITIAL_CAPITAL']
            prompt = f"""Risk reviewer. {symbol}:
Capital: ${cap:.0f} | Drawdown: {dd:.1%} | VIX: {ctx.get('vix',20) if ctx else 20:.1f}
JSON: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words"}}
If drawdown>5% return signal 0."""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            RiskReviewerAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"Risk: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'Risk reviewer unavailable'}

class SentimentAnalystAgent(Agent):
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<30: return {'signal':0,'confidence':0.5,'reason':'Sentiment LLM cooling'}
            fg = ctx.get('fear_greed',{}) if ctx else {}
            cot = ctx.get('cot',{}) if ctx else {}
            prompt = f"""{symbol} sentiment analysis:
Fear&Greed: {fg.get('score',50):.0f} {fg.get('rating','neutral')} | COT: {cot.get(symbol,0):.2f}
JSON: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            SentimentAnalystAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"Sent: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'Sentiment analyst unavailable'}

class DebateAgent(Agent):
    """Debate framework - argues opposite side to challenge consensus"""
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<30: return {'signal':0,'confidence':0.5,'reason':'Debate cooling'}
            votes = ctx.get('votes_summary','Buy:0 Sell:0') if ctx else 'mixed'
            c = df['close'].values
            ret = (c[-1]-c[-5])/c[-5]*100
            prompt = f"""Devil's advocate for {symbol}. Current votes: {votes}, 5h move: {ret:.2f}%
Challenge the consensus. Find reasons the opposite side is right.
JSON: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words opposing view"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            DebateAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5))*0.8,'reason':f"Debate: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'Debate unavailable'}

class StrategyEvolverAgent(Agent):
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<60: return {'signal':0,'confidence':0.5,'reason':'Evolver cooling'}
            weights = ctx.get('top_agents','') if ctx else ''
            prompt = f"""Strategy evolver for {symbol}. Best performing agents: {weights[:200]}
Based on what is working, what is the optimal signal?
JSON: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            StrategyEvolverAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"Evolver: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'Evolver unavailable'}

class PortfolioAdvisorAgent(Agent):
    _last = 0
    def analyze(self, df, symbol, ctx=None):
        try:
            if time.time()-self._last<30: return {'signal':0,'confidence':0.5,'reason':'Portfolio cooling'}
            open_count = len([s for s in signals_store if s.get('status')=='open'])
            cap = system_status.get('capital',CONFIG['INITIAL_CAPITAL'])
            prompt = f"""Portfolio advisor. {symbol} trade consideration:
Open positions: {open_count}/{CONFIG['MAX_POSITIONS']} | Capital: ${cap:.0f}
JSON: {{"signal":1 or -1 or 0,"confidence":0.0-1.0,"reason":"max 12 words portfolio perspective"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            PortfolioAdvisorAgent._last = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"Portfolio: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'Portfolio unavailable'}

class JournalWriterAgent(Agent):
    """Writes AI trade journal entry for every signal"""
    def analyze(self, df, symbol, ctx=None):
        return {'signal':0,'confidence':0.5,'reason':'Journal writer active'}

    def write_journal(self, signal_data, ctx=None):
        try:
            prompt = f"""Write a brief trade journal entry for this signal:
{symbol}: {signal_data.get('signal')} @ {signal_data.get('entry')}
SL: {signal_data.get('stop_loss')} TP: {signal_data.get('take_profit')}
Confidence: {signal_data.get('confidence')} Votes: {signal_data.get('buy_votes')} buy {signal_data.get('sell_votes')} sell
Write 3 sentences: 1) Why this trade 2) Key risk 3) What to watch"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':150,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            if r.status_code==200:
                return r.json()['content'][0]['text']
        except: pass
        return f"Signal: {signal_data.get('symbol')} {signal_data.get('signal')} at {signal_data.get('entry')}"

# ============================================================
# TELEGRAM
# ============================================================
class Telegram:
    BASE = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}"
    @staticmethod
    def send(msg):
        try:
            requests.post(f"{Telegram.BASE}/sendMessage",
                json={'chat_id':CONFIG['TELEGRAM_CHAT_ID'],'text':msg,'parse_mode':'HTML'},timeout=10)
        except: pass

# ============================================================
# RISK MANAGER
# ============================================================
class RiskManager:
    def __init__(self):
        self.capital = CONFIG['INITIAL_CAPITAL']
        self.peak = CONFIG['INITIAL_CAPITAL']

    def position_size(self, symbol, entry, sl, confidence, cap=None):
        c = cap or self.capital
        risk = c * CONFIG['RISK_PER_TRADE'] * min(confidence,1.0)
        pip = MARKETS[symbol]['pip']
        pusd = MARKETS[symbol]['pusd']
        sl_pips = abs(entry-sl)/pip
        if sl_pips==0: return 0.01
        lots = risk/(sl_pips*pusd)
        return round(min(max(lots,0.01),10.0),2)

    def get_sl(self, df, signal):
        h,l,c = df['high'].values,df['low'].values,df['close'].values
        a = np.mean(atr(h,l,c)[-14:])
        return c[-1]-signal*a*1.5

    def get_tp(self, entry, sl, signal, rr=2.5):
        return entry+signal*abs(entry-sl)*rr

    def update(self, pnl):
        self.capital += pnl
        if self.capital>self.peak: self.peak = self.capital
        system_status['capital'] = self.capital

    def drawdown(self):
        return (self.peak-self.capital)/self.peak

# ============================================================
# MASTER ORCHESTRATOR — 120 AGENTS
# ============================================================
class Orchestrator:
    def __init__(self):
        self.agents = self._build()
        self.risk = RiskManager()
        self.journal = JournalWriterAgent('JournalWriter')
        print(f"✅ {len(self.agents)} agents initialized")

    def _build(self):
        return [
            # Layer 1 — Market Structure (8)
            BOS_CHOCHAgent('BOS_CHOCH'),
            LiquiditySweepAgent('LiquiditySweep'),
            OrderBlockAgent('OrderBlock'),
            FairValueGapAgent('FairValueGap'),
            PremiumDiscountAgent('PremiumDiscount'),
            BreakerBlockAgent('BreakerBlock'),
            InducementAgent('Inducement'),
            MitigationBlockAgent('MitigationBlock'),
            # Layer 2 — ICT (8)
            KillzoneAgent('Killzone'),
            OTEAgent('OTE'),
            SilverBulletAgent('SilverBullet'),
            MidnightOpenAgent('MidnightOpen'),
            AsianRangeAgent('AsianRange'),
            PowerOf3Agent('PowerOf3'),
            WeeklyOpenAgent('WeeklyOpen'),
            GapFillAgent('GapFill'),
            # Layer 3 — Wyckoff (6)
            WyckoffPhaseAgent('WyckoffPhase'),
            SpringUpthrustAgent('SpringUpthrust'),
            WyckoffVolumeAgent('WyckoffVolume'),
            AccumulationAgent('Accumulation'),
            DistributionAgent('Distribution'),
            CompositeManAgent('CompositeMan'),
            # Layer 4 — Technical (15)
            MomentumAgent('Momentum'),
            TrendStrengthAgent('TrendStrength'),
            SupportResistanceAgent('SupportResistance'),
            BollingerAgent('Bollinger'),
            MeanReversionAgent('MeanReversion'),
            BreakoutAgent('Breakout'),
            CandlestickAgent('Candlestick'),
            StochasticAgent('Stochastic'),
            ElliottWaveAgent('ElliottWave'),
            ADXTrendAgent('ADXTrend'),
            CCIAgent('CCI'),
            WilliamsRAgent('WilliamsR'),
            ParabolicSARAgent('ParabolicSAR'),
            VolatilityRegimeAgent('VolatilityRegime'),
            PatternRecognitionAgent('PatternRecognition'),
            # Layer 5 — Volume (8)
            VWAPAgent('VWAP'),
            DarkPoolAgent('DarkPool'),
            SmartMoneyAgent('SmartMoney'),
            VolumeProfileAgent('VolumeProfile'),
            OrderFlowAgent('OrderFlow'),
            SpreadAgent('Spread'),
            CumulativeDeltaAgent('CumulativeDelta'),
            TickDataProxyAgent('TickDataProxy'),
            # Layer 6 — Intermarket (10)
            DXYAgent('DXY'),
            VIXAgent('VIX'),
            BondYieldAgent('BondYield'),
            CarryTradeAgent('CarryTrade'),
            GoldAgent('Gold'),
            RiskSentimentAgent('RiskSentiment'),
            OilCadAgent('OilCad'),
            InterestRateDiffAgent('InterestRateDiff'),
            EquityCorrelationAgent('EquityCorrelation'),
            CryptoSentimentAgent('CryptoSentiment'),
            # Layer 7 — Quantitative (10)
            HurstAgent('Hurst'),
            MonteCarloAgent('MonteCarlo'),
            FibTimeAgent('FibTime'),
            PsychLevelAgent('PsychLevel'),
            KellyAgent('Kelly'),
            StatArbitAgent('StatArbit'),
            CVaRAgent('CVaR'),
            CorrelationAgent('Correlation'),
            RegimeDetectorAgent('RegimeDetector'),
            VolForecastAgent('VolForecast'),
            # Layer 8 — Sentiment (10)
            FearGreedAgent('FearGreed'),
            MyFxBookAgent('MyFxBook'),
            COTAgent('COT'),
            NewsSentimentAgent('NewsSentiment'),
            GoogleTrendsAgent('GoogleTrends'),
            CryptoFGAgent('CryptoFG'),
            MacroSentimentAgent('MacroSentiment'),
            SocialSentimentAgent('SocialSentiment'),
            RetailSentimentContraryAgent('RetailContrary'),
            PutCallAgent('PutCall'),
            # Layer 9 — Calendar (10)
            EconomicCalendarAgent('EconomicCalendar'),
            FREDMacroAgent('FREDMacro'),
            SeasonalAgent('Seasonal'),
            CentralBankAgent('CentralBank'),
            COTPositioningAgent('COTPositioning'),
            SafeHavenAgent('SafeHaven'),
            WorldBankAgent('WorldBank'),
            InflationAgent('Inflation'),
            GeopoliticalAgent('Geopolitical'),
            QuarterlyTheoryAgent('QuarterlyTheory'),
            # Layer 10 — Session (8)
            SessionDNAAgent('SessionDNA'),
            DayOfWeekAgent('DayOfWeek'),
            NewsTrapAgent('NewsTrap'),
            TimeOfDayAgent('TimeOfDay'),
            MonthlyOpenAgent('MonthlyOpen'),
            WeekendRiskAgent('WeekendRisk'),
            EndOfMonthAgent('EndOfMonth'),
            AsianRangeAgent('AsianRange2'),
            # Layer 11 — Risk (10)
            DrawdownGuardAgent('DrawdownGuard'),
            MaxExposureAgent('MaxExposure'),
            VolatilityFilterAgent('VolatilityFilter'),
            CorrelationBlockerAgent('CorrelationBlocker'),
            PositionSizerAgent('PositionSizer'),
            TrailingStopConceptAgent('TrailingStop'),
            BreakevenConceptAgent('Breakeven'),
            LiquidityFilterAgent('LiquidityFilter'),
            AccountProtectionAgent('AccountProtection'),
            MarginSafetyAgent('MarginSafety'),
            # Layer 12 — ML (5)
            RandomForestAgent('RandomForest'),
            GradientBoostAgent('GradientBoost'),
            LSTMProxyAgent('LSTMProxy'),
            EnsembleMLAgent('EnsembleML'),
            PatternRecognitionAgent('PatternRec2'),
            # Layer 13 — LLM (8)
            LLMReasoningAgent('LLMReasoning'),
            MacroAnalystAgent('MacroAnalyst'),
            RiskReviewerAgent('RiskReviewer'),
            SentimentAnalystAgent('SentimentAnalyst'),
            DebateAgent('DebateAgent'),
            StrategyEvolverAgent('StrategyEvolver'),
            PortfolioAdvisorAgent('PortfolioAdvisor'),
            JournalWriterAgent('JournalWriter2'),
        ]

    def get_context(self):
        print("  📡 Loading global context...", end='', flush=True)
        ctx = {
            'vix': loader.vix(),
            'dxy': loader.dxy(),
            'gold': loader.gold(),
            'fred_data': loader.fred_data(),
            'cot': loader.cot_data(),
            'fear_greed': loader.fear_greed(),
            'myfxbook': loader.myfxbook_sentiment(),
        }
        top = sorted(agent_weights_store.items(), key=lambda x: x[1], reverse=True)[:5]
        ctx['top_agents'] = str(top)
        print(f" VIX:{ctx['vix']:.1f} DXY:{ctx['dxy']:.1f} Gold:{ctx['gold']:.0f} FG:{ctx['fear_greed'].get('score',50):.0f}")
        return ctx

    def analyze(self, symbol, df, ctx, cap=None):
        if not safe_df(df): return None
        vb,vs,reasons = [],[],[]
        for agent in self.agents:
            try:
                res = agent.analyze(df, symbol, ctx)
                sig = res.get('signal',0)
                conf = res.get('confidence',0.5)
                reason = res.get('reason','')
                wc = conf*agent.weight
                if sig==1: vb.append(wc); reasons.append(f'✅ {agent.name}: {reason}')
                elif sig==-1: vs.append(wc); reasons.append(f'❌ {agent.name}: {reason}')
            except: continue

        total = len(vb)+len(vs)
        if total<CONFIG['MIN_VOTES']: return None

        bp = len(vb)/total
        sp = len(vs)/total
        ctx['votes_summary'] = f'Buy:{len(vb)} Sell:{len(vs)}'

        if bp>=CONFIG['VOTE_THRESHOLD']:
            sig,conf = 1,sum(vb)/total
        elif sp>=CONFIG['VOTE_THRESHOLD']:
            sig,conf = -1,sum(vs)/total
        else:
            return None

        entry = float(df['close'].values[-1])
        sl = self.risk.get_sl(df, sig)
        tp = self.risk.get_tp(entry, sl, sig)
        lots = self.risk.position_size(symbol, entry, sl, conf, cap)
        pip = MARKETS[symbol]['pip']
        pusd = MARKETS[symbol]['pusd']
        sl_pips = abs(entry-sl)/pip
        dollar_risk = sl_pips*pusd*lots
        rr = abs(tp-entry)/abs(entry-sl) if abs(entry-sl)>0 else 0

        return {
            'symbol': symbol,
            'signal': sig,
            'confidence': conf,
            'entry': entry,
            'stop_loss': sl,
            'take_profit': tp,
            'lots': lots,
            'dollar_risk': dollar_risk,
            'rr': rr,
            'buy_votes': len(vb),
            'sell_votes': len(vs),
            'total_votes': total,
            'reasons': reasons,
            'timestamp': datetime.utcnow().isoformat(),
        }

    def run(self, capital_override=None):
        print(f"\n{'='*65}")
        print(f"🚀 V8 ULTIMATE | {len(self.agents)} AGENTS | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*65}")

        ctx = self.get_context()
        found = []

        for symbol in TRADING_PAIRS:
            print(f"\n  ⚡ {symbol}", end='', flush=True)
            df = loader.ohlcv(symbol)
            if df is None or df.empty:
                print(" ❌ No data")
                continue
            print(f" | {len(df)} candles", end='', flush=True)

            result = self.analyze(symbol, df, ctx.copy(), capital_override)

            if result:
                act = '🟢 BUY' if result['signal']==1 else '🔴 SELL'
                print(f"\n    {act} conf={result['confidence']:.1%} lots={result['lots']} RR=1:{result['rr']:.1f}")
                print(f"    Entry:{result['entry']:.5f} SL:{result['stop_loss']:.5f} TP:{result['take_profit']:.5f}")
                print(f"    Votes 🟢{result['buy_votes']} 🔴{result['sell_votes']} / {result['total_votes']}")

                journal = self.journal.write_journal(result, ctx)
                result['journal'] = journal

                Telegram.send(f"""
{act} <b>{symbol}</b>
💰 Entry: <code>{result['entry']:.5f}</code>
🛡 SL: <code>{result['stop_loss']:.5f}</code>
🎯 TP: <code>{result['take_profit']:.5f}</code>
📦 Lots: <b>{result['lots']}</b> | R:R <b>1:{result['rr']:.1f}</b>
🧠 Conf: <b>{result['confidence']:.1%}</b> | Votes 🟢{result['buy_votes']} 🔴{result['sell_votes']}
💵 Risk: ${result['dollar_risk']:.2f}
📝 {journal[:100]}...
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
                """)

                signals_store.insert(0, result)
                if len(signals_store)>100: signals_store.pop()
                found.append(result)
            else:
                print(" | ⚪ HOLD")

        system_status['last_run'] = datetime.utcnow().isoformat()
        system_status['running'] = True

        print(f"\n{'='*65}")
        print(f"📊 {len(found)} signals | Buy:{sum(1 for s in found if s['signal']==1)} Sell:{sum(1 for s in found if s['signal']==-1)}")
        print(f"💵 Capital: ${self.risk.capital:,.2f} | DD: {self.risk.drawdown():.2%}")
        print(f"{'='*65}")
        print("📱 Check Telegram!")
        return found

# Global orchestrator
_orch = None

def run_system(capital_override=None):
    global _orch
    if _orch is None:
        _orch = Orchestrator()
        Telegram.send(f"""
🚀 <b>V8 ULTIMATE STARTED</b>
🤖 {len(_orch.agents)} Agents | 25 Instruments
📊 SMC+ICT+Wyckoff+ML+LLM+Sentiment
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        """)
    return _orch.run(capital_override)

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║              V8 ULTIMATE — 120 AGENTS COMPLETE             ║
║  SMC+ICT+Wyckoff+Volume+Intermarket+Quant+Sentiment+ML+LLM ║
╚══════════════════════════════════════════════════════════════╝
    """)
    run_system()
