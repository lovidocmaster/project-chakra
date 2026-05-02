"""
V6 ULTIMATE TRADING SYSTEM - COMPLETE BRAIN
100 Agents | Multi-Timeframe | Self-Evolving | Full AI Integration
SMC + ICT + Wyckoff + Intermarket + Volume + ML + LLM + Risk
"""

import numpy as np
import pandas as pd
import json
import time
import requests
import warnings
import os
import schedule
import threading
from datetime import datetime, timedelta
from collections import deque, defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import base64

warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
CONFIG = {
    'ANTHROPIC_API_KEY':  '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',
    'OANDA_API_KEY':      '500c5382d32fcc8a3a58b0ea0507c083-64e0d997e301a20caa3270a846d33402',
    'OANDA_ACCOUNT_ID':   '101-001-39217670-001',
    'OANDA_ENV':          'practice',
    'FRED_API_KEY':       '0d5051e1563e45866badf276454ce1ec',
    'NEWS_API_KEY':       '00ce3b995b134bf98265358f98b9d41e',
    'TELEGRAM_TOKEN':     '8635098808:AAG07lR1RTnImndoCbnIEEXn8mGrIzR0nOc',
    'TELEGRAM_CHAT_ID':   '757855988',
    'SUPABASE_URL':       'https://jvnaphbygmqjeyawkmnz.supabase.co',
    'SUPABASE_KEY':       'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2bmFwaGJ5Z21xamV5YXdrbW56Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ3NDI2NzcsImV4cCI6MjA2MDMxODY3N30.Suz0H3jrDn89vzCLCPPFlbo3oVYcqVbn7d_OtB3zLR0',
    'INITIAL_CAPITAL':    10000,
    'RISK_PER_TRADE':     0.01,
    'MAX_POSITIONS':      5,
    'MIN_AGENT_VOTES':    5,
    'VOTE_THRESHOLD':     0.60,
    'MAX_DRAWDOWN':       0.10,
    'NEWS_AVOID_MINUTES': 30,
    'ANALYSIS_INTERVAL':  5,
}

MARKETS = {
    'EURUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'EURUSD=X','psychological':[1.05,1.10,1.15,1.20]},
    'USDJPY': {'type':'forex','pip':0.01,  'pip_usd':9.0, 'yahoo':'USDJPY=X','psychological':[145,150,155,160]},
    'GBPUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'GBPUSD=X','psychological':[1.25,1.30,1.35,1.40]},
    'AUDUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'AUDUSD=X','psychological':[0.60,0.65,0.70,0.75]},
    'USDCAD': {'type':'forex','pip':0.0001,'pip_usd':7.5, 'yahoo':'USDCAD=X','psychological':[1.30,1.35,1.40,1.45]},
    'NZDUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'NZDUSD=X','psychological':[0.58,0.60,0.62,0.65]},
    'USDCHF': {'type':'forex','pip':0.0001,'pip_usd':11.0,'yahoo':'USDCHF=X','psychological':[0.88,0.90,0.92,0.95]},
    'EURJPY': {'type':'forex','pip':0.01,  'pip_usd':9.0, 'yahoo':'EURJPY=X','psychological':[155,160,165,170]},
    'GBPJPY': {'type':'forex','pip':0.01,  'pip_usd':9.0, 'yahoo':'GBPJPY=X','psychological':[185,190,195,200]},
    'EURGBP': {'type':'forex','pip':0.0001,'pip_usd':12.5,'yahoo':'EURGBP=X','psychological':[0.83,0.85,0.87,0.90]},
    'XAUUSD': {'type':'metal','pip':0.1,   'pip_usd':1.0, 'yahoo':'GC=F',    'psychological':[2000,2100,2200,2300]},
}

TRADING_PAIRS = list(MARKETS.keys())
TIMEFRAMES = {'1h': '1h', '4h': '4h', '1d': '1d'}

# Global state
signals_store = []
trades_store = []
performance_store = defaultdict(lambda: {'trades':0,'wins':0,'pnl':0.0,'signals':[]})
agent_weights = {}
system_status = {'running': False, 'last_run': None, 'capital': CONFIG['INITIAL_CAPITAL']}

# ============================================================
# BASE AGENT
# ============================================================
class BaseAgent:
    def __init__(self, name, base_weight=1.0):
        self.name = name
        self.weight = base_weight
        self.correct = 0
        self.total = 0
        agent_weights[name] = base_weight

    def analyze(self, df, symbol, context=None):
        return {'signal': 0, 'confidence': 0.0, 'reason': 'base'}

    def update_weight(self, correct):
        self.total += 1
        if correct: self.correct += 1
        if self.total >= 10:
            accuracy = self.correct / self.total
            self.weight = 0.3 + (accuracy * 1.4)
            agent_weights[self.name] = self.weight

# ============================================================
# DATA LOADER
# ============================================================
class DataLoader:
    _cache = {}
    _cache_time = {}

    def get_ohlcv(self, symbol, period='365d', interval='1h'):
        cache_key = f"{symbol}_{interval}"
        now = time.time()
        if cache_key in self._cache and now - self._cache_time.get(cache_key,0) < 300:
            return self._cache[cache_key]
        try:
            import yfinance as yf
            yahoo = MARKETS[symbol]['yahoo']
            df = yf.download(yahoo, period=period, interval=interval, progress=False)
            if df.empty: return None
            df.columns = [c[0].lower() if isinstance(c,tuple) else c.lower() for c in df.columns]
            df = df[['open','high','low','close','volume']].dropna()
            self._cache[cache_key] = df
            self._cache_time[cache_key] = now
            return df
        except: return None

    def get_multi_tf(self, symbol):
        df_4h = self.get_ohlcv(symbol, '180d', '4h')
        if df_4h is None or df_4h.empty:
            df_4h = self.get_ohlcv(symbol, '180d', '1h')
        return {
            '1h':  self.get_ohlcv(symbol, '60d',  '1h'),
            '4h':  df_4h,
            '1d':  self.get_ohlcv(symbol, '365d', '1d'),
        }

    def get_vix(self):
        try:
            import yfinance as yf
            df = yf.download('^VIX', period='5d', interval='1d', progress=False)
            return float(df['Close'].iloc[-1]) if not df.empty else 20.0
        except: return 20.0

    def get_dxy(self):
        try:
            import yfinance as yf
            df = yf.download('DX-Y.NYB', period='5d', interval='1d', progress=False)
            return float(df['Close'].iloc[-1]) if not df.empty else 104.0
        except: return 104.0

    def get_gold(self):
        try:
            import yfinance as yf
            df = yf.download('GC=F', period='5d', interval='1d', progress=False)
            return float(df['Close'].iloc[-1]) if not df.empty else 2000.0
        except: return 2000.0

    def get_fred_data(self):
        try:
            from fredapi import Fred
            fred = Fred(api_key=CONFIG['FRED_API_KEY'])
            data = {}
            for sid, name in [('DFF','fed_rate'),('T10Y2Y','yield_curve'),('VIXCLS','vix_fred')]:
                try: data[name] = float(fred.get_series(sid, limit=3).dropna().iloc[-1])
                except: data[name] = 0.0
            return data
        except: return {'fed_rate':5.25,'yield_curve':0.5,'vix_fred':20.0}

    def get_cot_data(self):
        try:
            url = "https://www.cftc.gov/dea/newcot/f_disagg.txt"
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                lines = response.text.split('\n')
                cot = {}
                for line in lines[:50]:
                    if 'EURO FX' in line.upper():
                        parts = line.split(',')
                        if len(parts) > 10:
                            try:
                                long = int(parts[8].strip().replace('"',''))
                                short = int(parts[9].strip().replace('"',''))
                                cot['EURUSD'] = (long - short) / (long + short + 1)
                            except: cot['EURUSD'] = 0.0
                return cot
        except: pass
        return {'EURUSD': 0.0, 'GBPUSD': 0.0, 'USDJPY': 0.0}

    def get_news(self, symbol):
        try:
            from newsapi import NewsApiClient
            api = NewsApiClient(api_key=CONFIG['NEWS_API_KEY'])
            currency = symbol[:3]
            articles = api.get_everything(q=f'{currency} forex', language='en', page_size=5, sort_by='publishedAt')
            pos = ['bullish','rally','rise','gain','surge','strong','up']
            neg = ['bearish','fall','drop','weak','decline','down','crash']
            score = 0
            for a in articles.get('articles',[]):
                text = (a.get('title','') + ' ' + a.get('description','')).lower()
                score += sum(1 for w in pos if w in text) - sum(1 for w in neg if w in text)
            return score / max(len(articles.get('articles',[])),1) / 5.0
        except: return 0.0

loader = DataLoader()

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    ag = pd.Series(gains).ewm(span=period).mean().values
    al = pd.Series(losses).ewm(span=period).mean().values
    rs = ag / (al + 1e-10)
    return np.concatenate([np.full(1, 50), 100 - 100/(1+rs)])

def ema(prices, period):
    return pd.Series(prices).ewm(span=period, adjust=False).mean().values

def atr(high, low, close, period=14):
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    return np.concatenate([[tr[0]], pd.Series(tr).ewm(span=period).mean().values])

def swing_highs(h, w=5):
    return [(i,h[i]) for i in range(w, len(h)-w) if h[i]==max(h[i-w:i+w+1])]

def swing_lows(l, w=5):
    return [(i,l[i]) for i in range(w, len(l)-w) if l[i]==min(l[i-w:i+w+1])]

# ============================================================
# LAYER 1 — MARKET STRUCTURE AGENTS
# ============================================================
class MarketStructureAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            sh = swing_highs(h[-100:])
            sl = swing_lows(l[-100:])
            if len(sh)<2 or len(sl)<2: return {'signal':0,'confidence':0.3,'reason':'No structure'}
            lsh,psh = sh[-1][1],sh[-2][1]
            lsl,psl = sl[-1][1],sl[-2][1]
            cur = c[-1]
            if cur>lsh and lsh>psh: return {'signal':1,'confidence':0.85,'reason':f'Bullish BOS broke {lsh:.5f}'}
            if cur<lsl and lsl<psl: return {'signal':-1,'confidence':0.85,'reason':f'Bearish BOS broke {lsl:.5f}'}
            if cur>lsh and lsh<psh: return {'signal':1,'confidence':0.75,'reason':'Bullish CHOCH'}
            if cur<lsl and lsl>psl: return {'signal':-1,'confidence':0.75,'reason':'Bearish CHOCH'}
            return {'signal':0,'confidence':0.4,'reason':'Structure intact'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class LiquiditySweepAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            a = np.mean(atr(h,l,c))
            kh = np.max(h[-25:-5])
            kl = np.min(l[-25:-5])
            rh = np.max(h[-3:])
            rl = np.min(l[-3:])
            cur = c[-1]
            if rl<kl and cur>kl+a*0.3: return {'signal':1,'confidence':0.88,'reason':f'Bullish sweep below {kl:.5f}'}
            if rh>kh and cur<kh-a*0.3: return {'signal':-1,'confidence':0.88,'reason':f'Bearish sweep above {kh:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No sweep'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class OrderBlockAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            o,h,l,c = df['open'].values, df['high'].values, df['low'].values, df['close'].values
            a = np.mean(atr(h,l,c))
            cur = c[-1]
            for i in range(len(c)-10, len(c)-2):
                if i<5: continue
                if c[i]<o[i]:
                    if np.max(h[i+1:min(i+6,len(h))])>h[i]+a*1.5:
                        ob_h,ob_l = max(o[i],c[i]),min(o[i],c[i])
                        if ob_l<=cur<=ob_h+a*0.5:
                            return {'signal':1,'confidence':0.82,'reason':f'Bullish OB {ob_l:.5f}-{ob_h:.5f}'}
                if c[i]>o[i]:
                    if np.min(l[i+1:min(i+6,len(l))])<l[i]-a*1.5:
                        ob_h,ob_l = max(o[i],c[i]),min(o[i],c[i])
                        if ob_l-a*0.5<=cur<=ob_h:
                            return {'signal':-1,'confidence':0.82,'reason':f'Bearish OB {ob_l:.5f}-{ob_h:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No OB'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class FairValueGapAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            cur = c[-1]
            for i in range(len(c)-30, len(c)-2):
                if i<2: continue
                if l[i+1]>h[i-1] and cur>=h[i-1] and cur<=l[i+1]:
                    return {'signal':1,'confidence':0.78,'reason':f'Bullish FVG {h[i-1]:.5f}-{l[i+1]:.5f}'}
                if h[i+1]<l[i-1] and cur>=h[i+1] and cur<=l[i-1]:
                    return {'signal':-1,'confidence':0.78,'reason':f'Bearish FVG {h[i+1]:.5f}-{l[i-1]:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No FVG'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PremiumDiscountAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            rh,rl = np.max(h[-100:]),np.min(l[-100:])
            rng = rh-rl
            if rng==0: return {'signal':0,'confidence':0.3,'reason':'No range'}
            pos = (c[-1]-rl)/rng
            if pos<0.25: return {'signal':1,'confidence':0.78,'reason':f'Deep discount {pos:.1%}'}
            if pos<0.40: return {'signal':1,'confidence':0.58,'reason':f'Discount {pos:.1%}'}
            if pos>0.75: return {'signal':-1,'confidence':0.78,'reason':f'Deep premium {pos:.1%}'}
            if pos>0.60: return {'signal':-1,'confidence':0.58,'reason':f'Premium {pos:.1%}'}
            return {'signal':0,'confidence':0.4,'reason':f'Equilibrium {pos:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class InducementAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            sh = swing_highs(h[-50:])
            sl = swing_lows(l[-50:])
            if len(sh)<2 or len(sl)<2: return {'signal':0,'confidence':0.3,'reason':'No inducement'}
            prev_high = sh[-2][1]
            prev_low = sl[-2][1]
            cur = c[-1]
            a = np.mean(atr(h,l,c)[-14:])
            if cur>prev_high+a*0.5 and c[-2]<prev_high:
                return {'signal':-1,'confidence':0.72,'reason':f'Inducement above {prev_high:.5f} - reversal likely'}
            if cur<prev_low-a*0.5 and c[-2]>prev_low:
                return {'signal':1,'confidence':0.72,'reason':f'Inducement below {prev_low:.5f} - reversal likely'}
            return {'signal':0,'confidence':0.3,'reason':'No inducement'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 2 — ICT AGENTS
# ============================================================
class KillzoneAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            hour = datetime.utcnow().hour
            if hour==13: return {'signal':1,'confidence':0.88,'reason':'NY-London overlap peak volume'}
            if 8<=hour<=10: return {'signal':1,'confidence':0.72,'reason':f'London killzone {hour}:00 UTC'}
            if 13<=hour<=16: return {'signal':1,'confidence':0.72,'reason':f'NY killzone {hour}:00 UTC'}
            if 0<=hour<=6: return {'signal':0,'confidence':0.55,'reason':'Asian low volatility'}
            return {'signal':0,'confidence':0.4,'reason':f'Off-session {hour}:00 UTC'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class OptimalTradeEntryAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            rh,rl = np.max(h[-20:]),np.min(l[-20:])
            rng = rh-rl
            if rng==0: return {'signal':0,'confidence':0.3,'reason':'No range'}
            if c[-20]<c[-1]:
                ret = (rh-c[-1])/rng
                if 0.62<=ret<=0.79: return {'signal':1,'confidence':0.82,'reason':f'Bullish OTE {ret:.1%}'}
            if c[-20]>c[-1]:
                ret = (c[-1]-rl)/rng
                if 0.62<=ret<=0.79: return {'signal':-1,'confidence':0.82,'reason':f'Bearish OTE {ret:.1%}'}
            return {'signal':0,'confidence':0.3,'reason':'Not at OTE'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class AsianRangeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            hour = datetime.utcnow().hour
            asian_high = np.max(h[-10:])
            asian_low = np.min(l[-10:])
            cur = c[-1]
            a = np.mean(atr(h,l,c)[-14:])
            if hour>=8:
                if cur>asian_high+a*0.2: return {'signal':1,'confidence':0.72,'reason':f'Asian range breakout up {asian_high:.5f}'}
                if cur<asian_low-a*0.2: return {'signal':-1,'confidence':0.72,'reason':f'Asian range breakdown {asian_low:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'Within Asian range'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PowerOfThreeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            h = df['high'].values
            l = df['low'].values
            hour = datetime.utcnow().hour
            day_open = c[-24] if len(c)>24 else c[0]
            cur = c[-1]
            day_high = np.max(h[-24:]) if len(h)>24 else np.max(h)
            day_low = np.min(l[-24:]) if len(l)>24 else np.min(l)
            if 8<=hour<=10:
                if cur>day_open: return {'signal':1,'confidence':0.68,'reason':'Power of 3 accumulation bullish'}
                else: return {'signal':-1,'confidence':0.68,'reason':'Power of 3 accumulation bearish'}
            return {'signal':0,'confidence':0.4,'reason':'Power of 3 waiting'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SilverBulletAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            ny_hour = (datetime.utcnow().hour - 4) % 24
            if ny_hour in [3,10,14]:
                c,h,l = df['close'].values, df['high'].values, df['low'].values
                a = np.mean(atr(h,l,c)[-14:])
                move = c[-1]-c[-6]
                if move>a*0.5: return {'signal':1,'confidence':0.76,'reason':f'Silver Bullet bullish {ny_hour}:00 NY'}
                if move<-a*0.5: return {'signal':-1,'confidence':0.76,'reason':f'Silver Bullet bearish {ny_hour}:00 NY'}
            return {'signal':0,'confidence':0.3,'reason':f'No Silver Bullet'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MidnightOpenAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            ny_hour = (datetime.utcnow().hour - 4) % 24
            c = df['close'].values
            midnight_open = c[-ny_hour-1] if ny_hour<len(c) else c[0]
            cur = c[-1]
            if cur>midnight_open*1.001: return {'signal':1,'confidence':0.65,'reason':f'Above midnight open {midnight_open:.5f}'}
            if cur<midnight_open*0.999: return {'signal':-1,'confidence':0.65,'reason':f'Below midnight open {midnight_open:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':'At midnight open'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 3 — WYCKOFF AGENTS
# ============================================================
class WyckoffPhaseAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c,h,l,v = df['close'].values, df['high'].values, df['low'].values, df['volume'].values
            rng = np.max(h[-50:])-np.min(l[-50:])
            avg = np.mean(c[-50:])
            rng_pct = rng/avg
            if rng_pct<0.02:
                vt = np.mean(v[-10:])/(np.mean(v[-50:-10])+1e-10)
                pos = (c[-1]-np.min(l[-50:]))/(rng+1e-10)
                if vt>1.2 and pos<0.4: return {'signal':1,'confidence':0.72,'reason':'Wyckoff accumulation'}
                if vt>1.2 and pos>0.6: return {'signal':-1,'confidence':0.72,'reason':'Wyckoff distribution'}
            ret = np.diff(c[-20:])
            if np.sum(ret>0)>14: return {'signal':1,'confidence':0.65,'reason':'Wyckoff markup'}
            if np.sum(ret<0)>14: return {'signal':-1,'confidence':0.65,'reason':'Wyckoff markdown'}
            return {'signal':0,'confidence':0.4,'reason':f'Wyckoff range {rng_pct:.2%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SpringUpthrustAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            sup = np.min(l[-50:-5]) if len(l)>55 else np.min(l[:-5])
            res = np.max(h[-50:-5]) if len(h)>55 else np.max(h[:-5])
            a = np.mean(atr(h,l,c)[-14:])
            if l[-2]<sup and c[-1]>sup+a*0.3: return {'signal':1,'confidence':0.88,'reason':f'Wyckoff Spring below {sup:.5f}'}
            if h[-2]>res and c[-1]<res-a*0.3: return {'signal':-1,'confidence':0.88,'reason':f'Wyckoff Upthrust above {res:.5f}'}
            return {'signal':0,'confidence':0.3,'reason':'No spring/upthrust'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WyckoffVolumeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c,v = df['close'].values, df['volume'].values
            price_up = c[-1]>c[-2]
            vol_up = v[-1]>np.mean(v[-20:])
            if price_up and vol_up: return {'signal':1,'confidence':0.68,'reason':'High volume bullish move - institutional buying'}
            if not price_up and vol_up: return {'signal':-1,'confidence':0.68,'reason':'High volume bearish move - institutional selling'}
            if price_up and not vol_up: return {'signal':-1,'confidence':0.55,'reason':'Low volume rally - weak, prepare short'}
            if not price_up and not vol_up: return {'signal':1,'confidence':0.55,'reason':'Low volume decline - weak, prepare long'}
            return {'signal':0,'confidence':0.4,'reason':'Volume neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 4 — TECHNICAL AGENTS
# ============================================================
class MomentumAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            r = rsi(c)
            m = ema(c,12)-ema(c,26)
            sig = ema(m,9)
            s = 0
            reasons = []
            if r[-1]<30: s+=1; reasons.append(f'RSI oversold {r[-1]:.1f}')
            elif r[-1]>70: s-=1; reasons.append(f'RSI overbought {r[-1]:.1f}')
            if m[-1]>sig[-1] and m[-2]<=sig[-2]: s+=1; reasons.append('MACD bullish cross')
            elif m[-1]<sig[-1] and m[-2]>=sig[-2]: s-=1; reasons.append('MACD bearish cross')
            conf = min(abs(s)*0.35+0.25,0.85)
            return {'signal':int(np.sign(s)),'confidence':conf,'reason':' | '.join(reasons) or 'Neutral momentum'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class TrendStrengthAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c,h,l = df['close'].values, df['high'].values, df['low'].values
            ma20 = ema(c,20)
            ma50 = ema(c,50)
            ma200 = ema(c,200) if len(c)>200 else ema(c,50)
            s = 0
            reasons = []
            if c[-1]>ma20[-1]>ma50[-1]: s+=2; reasons.append('Price above MA20>MA50 strong bull')
            elif c[-1]<ma20[-1]<ma50[-1]: s-=2; reasons.append('Price below MA20<MA50 strong bear')
            elif ma20[-1]>ma50[-1]: s+=1; reasons.append('MA20>MA50 bullish')
            else: s-=1; reasons.append('MA20<MA50 bearish')
            if len(c)>200:
                if c[-1]>ma200[-1]: s+=1; reasons.append('Above MA200 long term bull')
                else: s-=1; reasons.append('Below MA200 long term bear')
            return {'signal':int(np.sign(s)),'confidence':min(abs(s)*0.2+0.3,0.85),'reason':' | '.join(reasons)}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SupportResistanceAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            rh,rl = np.max(h[-50:]),np.min(l[-50:])
            cur = c[-1]
            rng = rh-rl
            if rng==0: return {'signal':0,'confidence':0.3,'reason':'Flat'}
            pos = (cur-rl)/rng
            if pos<0.15: return {'signal':1,'confidence':0.75,'reason':f'Near strong support {rl:.5f}'}
            if pos>0.85: return {'signal':-1,'confidence':0.75,'reason':f'Near strong resistance {rh:.5f}'}
            return {'signal':0,'confidence':0.35,'reason':f'Mid range {pos:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BollingerBandAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            ma = ema(c,20)
            std = pd.Series(c).rolling(20).std().values
            upper = ma+2*std
            lower = ma-2*std
            cur = c[-1]
            if cur<lower[-1]: return {'signal':1,'confidence':0.72,'reason':f'Below BB lower {lower[-1]:.5f} oversold'}
            if cur>upper[-1]: return {'signal':-1,'confidence':0.72,'reason':f'Above BB upper {upper[-1]:.5f} overbought'}
            if cur>ma[-1]: return {'signal':1,'confidence':0.5,'reason':'Above BB midline'}
            return {'signal':-1,'confidence':0.5,'reason':'Below BB midline'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MeanReversionAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values[-100:]
            z = (c[-1]-np.mean(c))/(np.std(c)+1e-10)
            if z<-2.5: return {'signal':1,'confidence':0.82,'reason':f'Extreme Z={z:.2f} strong oversold'}
            if z>2.5: return {'signal':-1,'confidence':0.82,'reason':f'Extreme Z={z:.2f} strong overbought'}
            if z<-1.5: return {'signal':1,'confidence':0.65,'reason':f'Z={z:.2f} oversold'}
            if z>1.5: return {'signal':-1,'confidence':0.65,'reason':f'Z={z:.2f} overbought'}
            return {'signal':0,'confidence':0.35,'reason':f'Z={z:.2f} neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BreakoutAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            kh = np.max(h[-21:-1])
            kl = np.min(l[-21:-1])
            a = np.mean(atr(h,l,c)[-14:])
            if c[-1]>kh+a*0.1: return {'signal':1,'confidence':0.76,'reason':f'20-period breakout above {kh:.5f}'}
            if c[-1]<kl-a*0.1: return {'signal':-1,'confidence':0.76,'reason':f'20-period breakdown below {kl:.5f}'}
            return {'signal':0,'confidence':0.35,'reason':'No breakout'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CandlestickAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            o,h,l,c = df['open'].values[-5:], df['high'].values[-5:], df['low'].values[-5:], df['close'].values[-5:]
            body = abs(c[-1]-o[-1])
            uw = h[-1]-max(c[-1],o[-1])
            lw = min(c[-1],o[-1])-l[-1]
            if lw>body*2 and uw<body*0.5: return {'signal':1,'confidence':0.68,'reason':'Hammer bullish reversal'}
            if uw>body*2 and lw<body*0.5: return {'signal':-1,'confidence':0.68,'reason':'Shooting star bearish'}
            if c[-1]>o[-1] and c[-2]<o[-2] and c[-1]>o[-2] and o[-1]<c[-2]: return {'signal':1,'confidence':0.72,'reason':'Bullish engulfing'}
            if c[-1]<o[-1] and c[-2]>o[-2] and c[-1]<o[-2] and o[-1]>c[-2]: return {'signal':-1,'confidence':0.72,'reason':'Bearish engulfing'}
            if c[-1]>o[-1] and c[-2]>o[-2] and c[-3]>o[-3]: return {'signal':1,'confidence':0.65,'reason':'Three white soldiers'}
            if c[-1]<o[-1] and c[-2]<o[-2] and c[-3]<o[-3]: return {'signal':-1,'confidence':0.65,'reason':'Three black crows'}
            return {'signal':0,'confidence':0.3,'reason':'No pattern'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class StochasticAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            k_period = 14
            lows = pd.Series(l).rolling(k_period).min().values
            highs = pd.Series(h).rolling(k_period).max().values
            k = 100*(c-lows)/(highs-lows+1e-10)
            d = pd.Series(k).rolling(3).mean().values
            if k[-1]<20 and d[-1]<20: return {'signal':1,'confidence':0.70,'reason':f'Stochastic oversold K={k[-1]:.1f}'}
            if k[-1]>80 and d[-1]>80: return {'signal':-1,'confidence':0.70,'reason':f'Stochastic overbought K={k[-1]:.1f}'}
            if k[-1]>d[-1] and k[-2]<=d[-2] and k[-1]<50: return {'signal':1,'confidence':0.62,'reason':'Stochastic bullish cross'}
            if k[-1]<d[-1] and k[-2]>=d[-2] and k[-1]>50: return {'signal':-1,'confidence':0.62,'reason':'Stochastic bearish cross'}
            return {'signal':0,'confidence':0.35,'reason':f'Stochastic neutral {k[-1]:.1f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VolatilityRegimeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            cv = np.std(ret[-20:])*np.sqrt(252)
            hv = np.std(ret[-100:])*np.sqrt(252)
            ratio = cv/(hv+1e-10)
            if ratio<0.7: return {'signal':1,'confidence':0.62,'reason':f'Low vol {cv:.3f} breakout imminent'}
            if ratio>1.8: return {'signal':0,'confidence':0.62,'reason':f'High vol {cv:.3f} reduce exposure'}
            return {'signal':0,'confidence':0.4,'reason':f'Normal vol {cv:.3f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 5 — VOLUME AND FLOW AGENTS
# ============================================================
class AnchoredVWAPAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c,v = df['high'].values, df['low'].values, df['close'].values, df['volume'].values
            tp = (h+l+c)/3
            vwap = np.cumsum(tp*v)/(np.cumsum(v)+1e-10)
            a = np.mean(atr(h,l,c)[-14:])
            cur = c[-1]
            cvwap = vwap[-1]
            dev = (cur-cvwap)/(a+1e-10)
            if dev<-2: return {'signal':1,'confidence':0.72,'reason':f'Price {dev:.1f}x ATR below VWAP extreme'}
            if dev>2: return {'signal':-1,'confidence':0.72,'reason':f'Price {dev:.1f}x ATR above VWAP extreme'}
            if cur>cvwap: return {'signal':1,'confidence':0.55,'reason':'Above VWAP bullish'}
            return {'signal':-1,'confidence':0.55,'reason':'Below VWAP bearish'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class DarkPoolProxyAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c,v = df['close'].values, df['volume'].values
            avg_vol = np.mean(v[-50:])
            large_vol = v[-1]>avg_vol*2.5
            price_move = abs(c[-1]-c[-2])/c[-2]
            if large_vol and price_move<0.001:
                if c[-1]>c[-2]: return {'signal':1,'confidence':0.75,'reason':'Dark pool accumulation - large vol small move bullish'}
                else: return {'signal':-1,'confidence':0.75,'reason':'Dark pool distribution - large vol small move bearish'}
            if large_vol and price_move>0.003:
                if c[-1]>c[-2]: return {'signal':1,'confidence':0.70,'reason':'Institutional buying confirmed high vol'}
                else: return {'signal':-1,'confidence':0.70,'reason':'Institutional selling confirmed high vol'}
            return {'signal':0,'confidence':0.35,'reason':'Normal volume activity'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SmartMoneyFootprintAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c,v,h,l = df['close'].values, df['volume'].values, df['high'].values, df['low'].values
            bullish_vol = sum(v[i] for i in range(len(c)-20,len(c)) if c[i]>c[i-1])
            bearish_vol = sum(v[i] for i in range(len(c)-20,len(c)) if c[i]<c[i-1])
            total = bullish_vol+bearish_vol+1
            delta = (bullish_vol-bearish_vol)/total
            if delta>0.3: return {'signal':1,'confidence':0.70,'reason':f'Smart money footprint bullish delta {delta:.2f}'}
            if delta<-0.3: return {'signal':-1,'confidence':0.70,'reason':f'Smart money footprint bearish delta {delta:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Neutral footprint delta {delta:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SpreadAnalysisAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            spreads = h[-20:]-l[-20:]
            avg_spread = np.mean(spreads)
            cur_spread = spreads[-1]
            if cur_spread>avg_spread*1.5: return {'signal':0,'confidence':0.60,'reason':f'Wide spread {cur_spread:.5f} - high risk avoid'}
            if cur_spread<avg_spread*0.7: return {'signal':1,'confidence':0.58,'reason':f'Tight spread {cur_spread:.5f} - good liquidity'}
            return {'signal':0,'confidence':0.4,'reason':f'Normal spread {cur_spread:.5f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 6 — INTERMARKET AGENTS
# ============================================================
class DXYCorrelationAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            dxy = context.get('dxy',104.0) if context else 104.0
            usd_base = symbol.startswith('USD')
            usd_quote = symbol[3:]=='USD' or symbol.endswith('USD')
            if dxy>106:
                if usd_base: return {'signal':1,'confidence':0.68,'reason':f'DXY strong {dxy:.1f} USD base bullish'}
                if usd_quote: return {'signal':-1,'confidence':0.68,'reason':f'DXY strong {dxy:.1f} USD quote bearish'}
            elif dxy<101:
                if usd_base: return {'signal':-1,'confidence':0.68,'reason':f'DXY weak {dxy:.1f}'}
                if usd_quote: return {'signal':1,'confidence':0.68,'reason':f'DXY weak {dxy:.1f} USD quote bullish'}
            return {'signal':0,'confidence':0.4,'reason':f'DXY neutral {dxy:.1f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VIXSentimentAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            vix = context.get('vix',20.0) if context else 20.0
            safe = ['USDJPY','USDCHF','XAUUSD','XAGUSD']
            risk = ['AUDUSD','NZDUSD','BTCUSD','ETHUSD','GBPUSD']
            if vix>30:
                if symbol in safe: return {'signal':1,'confidence':0.72,'reason':f'VIX fear {vix:.1f} safe haven demand'}
                if symbol in risk: return {'signal':-1,'confidence':0.72,'reason':f'VIX fear {vix:.1f} risk off'}
            elif vix<15:
                if symbol in risk: return {'signal':1,'confidence':0.65,'reason':f'VIX low {vix:.1f} risk on'}
                if symbol in safe and symbol!='XAUUSD': return {'signal':-1,'confidence':0.60,'reason':f'VIX low {vix:.1f} safe haven out'}
            return {'signal':0,'confidence':0.4,'reason':f'VIX neutral {vix:.1f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class BondYieldAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            fred = context.get('fred_data',{}) if context else {}
            yc = fred.get('yield_curve',0.5)
            fr = fred.get('fed_rate',5.25)
            if yc<0:
                if symbol in ['USDJPY','XAUUSD']: return {'signal':1,'confidence':0.68,'reason':f'Inverted curve {yc:.2f} safe havens'}
                return {'signal':-1,'confidence':0.58,'reason':'Inverted yield curve recession risk'}
            if fr>5.0 and symbol.startswith('USD'): return {'signal':1,'confidence':0.62,'reason':f'High Fed rate {fr:.2f}% USD bullish'}
            return {'signal':0,'confidence':0.4,'reason':f'Rates normal curve={yc:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CarryTradeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            fred = context.get('fred_data',{}) if context else {}
            us_rate = fred.get('fed_rate',5.25)
            carry_pairs = {
                'USDJPY': us_rate-0.1,
                'USDCHF': us_rate-0.75,
                'AUDUSD': 4.35-us_rate,
                'NZDUSD': 5.5-us_rate,
                'EURJPY': 4.0-0.1,
            }
            if symbol in carry_pairs:
                diff = carry_pairs[symbol]
                if diff>2: return {'signal':1,'confidence':0.65,'reason':f'Carry trade long {diff:.2f}% interest diff'}
                if diff<-2: return {'signal':-1,'confidence':0.65,'reason':f'Negative carry {diff:.2f}% short'}
            return {'signal':0,'confidence':0.4,'reason':'Carry neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class RiskOnOffAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            vix = context.get('vix',20) if context else 20
            dxy = context.get('dxy',104) if context else 104
            score = 0
            if vix<15: score+=1
            elif vix>25: score-=1
            if dxy<102: score+=1
            elif dxy>106: score-=1
            risk = ['AUDUSD','NZDUSD','GBPUSD','BTCUSD','ETHUSD']
            safe = ['USDJPY','USDCHF','XAUUSD','XAGUSD']
            if score>0:
                if symbol in risk: return {'signal':1,'confidence':0.62,'reason':'Risk ON'}
                if symbol in safe and symbol!='XAUUSD': return {'signal':-1,'confidence':0.58,'reason':'Risk ON safe haven out'}
            elif score<0:
                if symbol in safe: return {'signal':1,'confidence':0.62,'reason':'Risk OFF safe haven demand'}
                if symbol in risk: return {'signal':-1,'confidence':0.62,'reason':'Risk OFF'}
            return {'signal':0,'confidence':0.4,'reason':'Mixed sentiment'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class GoldCorrelationAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            gold = context.get('gold',2000) if context else 2000
            if symbol=='XAUUSD': return {'signal':0,'confidence':0.4,'reason':'Is gold'}
            if gold>2200:
                if symbol in ['AUDUSD','NZDUSD']: return {'signal':1,'confidence':0.62,'reason':f'Gold high {gold:.0f} commodity currencies bullish'}
                if symbol.startswith('USD'): return {'signal':-1,'confidence':0.58,'reason':f'Gold high {gold:.0f} USD bearish'}
            return {'signal':0,'confidence':0.4,'reason':f'Gold neutral {gold:.0f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 7 — QUANTITATIVE AGENTS
# ============================================================
class HurstExponentAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
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
                return {'signal':1 if trend>0 else -1,'confidence':0.72,'reason':f'Hurst {h:.2f} trending follow trend'}
            if h<0.4:
                z = (c[-1]-np.mean(c[-50:]))/(np.std(c[-50:])+1e-10)
                return {'signal':-1 if z>1 else (1 if z<-1 else 0),'confidence':0.65,'reason':f'Hurst {h:.2f} mean reverting'}
            return {'signal':0,'confidence':0.4,'reason':f'Hurst {h:.2f} random walk'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MonteCarloAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            ret = np.diff(np.log(c+1e-10))
            mu,sigma = np.mean(ret[-100:]),np.std(ret[-100:])
            sims = np.random.normal(mu,sigma,(1000,24))
            final = np.sum(sims,axis=1)
            prob_up = np.mean(final>0)
            var95 = np.percentile(final,5)
            if prob_up>0.62: return {'signal':1,'confidence':prob_up,'reason':f'Monte Carlo {prob_up:.1%} bullish VaR={var95:.4f}'}
            if prob_up<0.38: return {'signal':-1,'confidence':1-prob_up,'reason':f'Monte Carlo {1-prob_up:.1%} bearish'}
            return {'signal':0,'confidence':0.4,'reason':f'Monte Carlo uncertain {prob_up:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class FibonacciTimeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            fib_nums = [1,1,2,3,5,8,13,21,34,55,89]
            sh = swing_highs(c[-100:])
            sl = swing_lows(c[-100:])
            if not sh or not sl: return {'signal':0,'confidence':0.3,'reason':'No swings'}
            last_swing_bar = max(sh[-1][0] if sh else 0, sl[-1][0] if sl else 0)
            bars_since = len(c)-100+last_swing_bar
            if bars_since in fib_nums:
                trend = c[-1]-c[-20]
                return {'signal':1 if trend>0 else -1,'confidence':0.65,'reason':f'Fibonacci time {bars_since} bars - potential reversal'}
            return {'signal':0,'confidence':0.35,'reason':f'No Fibonacci time {bars_since} bars'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class PsychologicalLevelAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            levels = MARKETS.get(symbol,{}).get('psychological',[])
            cur = c[-1]
            a = np.mean(np.diff(c[-14:]))
            for level in levels:
                dist = abs(cur-level)/level
                if dist<0.002:
                    if cur<level: return {'signal':1,'confidence':0.72,'reason':f'Near psychological level {level} expect rejection'}
                    else: return {'signal':-1,'confidence':0.72,'reason':f'Near psychological level {level} expect rejection'}
            return {'signal':0,'confidence':0.35,'reason':'No psychological level nearby'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class GapFillAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            o = df['open'].values
            if len(c)<3: return {'signal':0,'confidence':0.3,'reason':'insufficient'}
            gap = o[-1]-c[-2]
            gap_pct = abs(gap)/c[-2]
            if gap_pct>0.002:
                if gap>0: return {'signal':-1,'confidence':0.70,'reason':f'Gap up {gap_pct:.3%} likely to fill'}
                else: return {'signal':1,'confidence':0.70,'reason':f'Gap down {gap_pct:.3%} likely to fill'}
            return {'signal':0,'confidence':0.35,'reason':'No significant gap'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class KellyCriterionAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            perf = performance_store.get(symbol,{})
            trades = perf.get('trades',0)
            wins = perf.get('wins',0)
            if trades<10: return {'signal':0,'confidence':0.5,'reason':'Insufficient trades for Kelly'}
            win_rate = wins/trades
            avg_win = 1.5
            avg_loss = 1.0
            kelly = win_rate-(1-win_rate)/avg_win
            if kelly>0.2: return {'signal':1,'confidence':min(kelly+0.4,0.85),'reason':f'Kelly positive {kelly:.2f} increase exposure'}
            if kelly<0: return {'signal':0,'confidence':0.70,'reason':f'Kelly negative {kelly:.2f} reduce exposure'}
            return {'signal':0,'confidence':0.5,'reason':f'Kelly neutral {kelly:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 8 — FUNDAMENTAL AGENTS
# ============================================================
class COTReportAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            cot = context.get('cot',{}) if context else {}
            score = cot.get(symbol, cot.get(symbol[:6],0))
            if score>0.2: return {'signal':1,'confidence':0.68,'reason':f'COT institutional net long {score:.2f}'}
            if score<-0.2: return {'signal':-1,'confidence':0.68,'reason':f'COT institutional net short {score:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'COT neutral {score:.2f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SeasonalAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            month = datetime.utcnow().month
            day = datetime.utcnow().weekday()
            seasonal = {
                'USDJPY': {1:1, 3:-1, 9:1, 12:1},
                'EURUSD': {1:-1, 4:1, 8:-1, 12:-1},
                'GBPUSD': {1:-1, 5:1, 9:-1},
                'XAUUSD': {1:1, 8:1, 11:1, 12:1},
                'AUDUSD': {3:1, 7:-1, 9:-1},
            }
            best_days = {0: 'Monday gap fill', 4: 'Friday close positions'}
            bias = seasonal.get(symbol,{}).get(month,0)
            if bias!=0: return {'signal':bias,'confidence':0.58,'reason':f'Seasonal bias month {month} for {symbol}'}
            if day==4: return {'signal':0,'confidence':0.60,'reason':'Friday close risk - reduce size'}
            return {'signal':0,'confidence':0.4,'reason':'No seasonal signal'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class EconomicCalendarAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            hour = datetime.utcnow().hour
            minute = datetime.utcnow().minute
            high_impact_hours = [8,13,14,15,18]
            if hour in high_impact_hours and minute<30:
                return {'signal':0,'confidence':0.80,'reason':f'High impact news risk {hour}:00 UTC avoid trading'}
            return {'signal':0,'confidence':0.4,'reason':'No news risk'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class SafeHavenAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            vix = context.get('vix',20) if context else 20
            gold = context.get('gold',2000) if context else 2000
            safe_score = 0
            if vix>25: safe_score+=1
            if gold>2200: safe_score+=1
            safe = ['USDJPY','USDCHF','XAUUSD','XAGUSD']
            risk = ['AUDUSD','NZDUSD','GBPUSD']
            if safe_score>=2:
                if symbol in safe: return {'signal':1,'confidence':0.70,'reason':'Safe haven demand strong'}
                if symbol in risk: return {'signal':-1,'confidence':0.68,'reason':'Risk assets under pressure'}
            return {'signal':0,'confidence':0.4,'reason':'Normal sentiment'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class CentralBankAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            fred = context.get('fred_data',{}) if context else {}
            rate = fred.get('fed_rate',5.25)
            yc = fred.get('yield_curve',0.5)
            if rate>5 and yc>0:
                if 'USD' in symbol[:3]: return {'signal':1,'confidence':0.62,'reason':f'Fed hawkish rate={rate:.2f}% USD positive'}
            if yc<0: return {'signal':0,'confidence':0.65,'reason':'Inverted curve Fed dovish pivot likely'}
            return {'signal':0,'confidence':0.4,'reason':f'Central bank neutral rate={rate:.2f}%'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 9 — SESSION AND TIME AGENTS
# ============================================================
class SessionDNAAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            hour = datetime.utcnow().hour
            c,h,l = df['close'].values, df['high'].values, df['low'].values
            sessions = {
                'asian': (0,8,'Mean reversion'),
                'london': (8,13,'Trend following breakout'),
                'ny': (13,21,'Reversal and continuation'),
                'dead': (21,24,'Low volatility avoid'),
            }
            for name,(start,end,strategy) in sessions.items():
                if start<=hour<end:
                    if name=='dead': return {'signal':0,'confidence':0.70,'reason':f'Dead zone {hour}:00 avoid trading'}
                    if name=='asian': return {'signal':0,'confidence':0.55,'reason':f'Asian session mean reversion {strategy}'}
                    if name in ['london','ny']:
                        rsi_val = rsi(c)[-1]
                        if rsi_val<45: return {'signal':1,'confidence':0.62,'reason':f'{name.title()} session bullish {strategy}'}
                        if rsi_val>55: return {'signal':-1,'confidence':0.62,'reason':f'{name.title()} session bearish {strategy}'}
            return {'signal':0,'confidence':0.4,'reason':f'Session {hour}:00'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class DayOfWeekAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            day = datetime.utcnow().weekday()
            c = df['close'].values
            day_bias = {0:0.5, 1:0.6, 2:0.0, 3:0.6, 4:-0.5}
            bias = day_bias.get(day,0)
            days = ['Monday','Tuesday','Wednesday','Thursday','Friday']
            if day==4: return {'signal':0,'confidence':0.68,'reason':'Friday close positions weekend risk'}
            if day==0:
                gap = c[-1]-c[-2] if len(c)>1 else 0
                if abs(gap)/c[-2]>0.001:
                    return {'signal':-1 if gap>0 else 1,'confidence':0.65,'reason':f'Monday gap fill expected'}
            return {'signal':0,'confidence':0.4,'reason':f'{days[day]} neutral'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class NewsTrapKillerAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            hour = datetime.utcnow().hour
            minute = datetime.utcnow().minute
            danger_windows = [(8,30),(13,30),(15,0),(18,0)]
            for dh,dm in danger_windows:
                diff = abs((hour*60+minute)-(dh*60+dm))
                if diff<=CONFIG['NEWS_AVOID_MINUTES']:
                    return {'signal':0,'confidence':0.90,'reason':f'News danger window {dh}:{dm:02d} UTC avoid'}
            return {'signal':0,'confidence':0.4,'reason':'News safe window'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class WeeklyOpenAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            c = df['close'].values
            weekly_open = c[-5*24] if len(c)>120 else c[0]
            cur = c[-1]
            if cur>weekly_open*1.005: return {'signal':1,'confidence':0.62,'reason':f'Above weekly open {weekly_open:.5f}'}
            if cur<weekly_open*0.995: return {'signal':-1,'confidence':0.62,'reason':f'Below weekly open {weekly_open:.5f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Near weekly open {weekly_open:.5f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 10 — RISK AND PROTECTION AGENTS
# ============================================================
class DrawdownRecoveryAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            capital = system_status.get('capital', CONFIG['INITIAL_CAPITAL'])
            initial = CONFIG['INITIAL_CAPITAL']
            dd = (initial-capital)/initial
            if dd>0.08:
                return {'signal':0,'confidence':0.95,'reason':f'Drawdown {dd:.1%} exceeded 8% HALT TRADING'}
            if dd>0.05:
                return {'signal':0,'confidence':0.80,'reason':f'Drawdown {dd:.1%} reduce size 50%'}
            if dd>0.03:
                return {'signal':0,'confidence':0.65,'reason':f'Drawdown {dd:.1%} be cautious'}
            return {'signal':1,'confidence':0.4,'reason':f'Drawdown ok {dd:.1%}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class MaxExposureAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            open_positions = len(trades_store)
            if open_positions>=CONFIG['MAX_POSITIONS']:
                return {'signal':0,'confidence':0.90,'reason':f'Max positions {open_positions} reached no new trades'}
            if open_positions>=CONFIG['MAX_POSITIONS']-1:
                return {'signal':0,'confidence':0.70,'reason':f'Near max positions {open_positions} be selective'}
            return {'signal':1,'confidence':0.4,'reason':f'Positions ok {open_positions}/{CONFIG["MAX_POSITIONS"]}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

class VolatilityFilterAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            h,l,c = df['high'].values, df['low'].values, df['close'].values
            a = atr(h,l,c)[-14:]
            cur_atr = a[-1]
            avg_atr = np.mean(a)
            if cur_atr>avg_atr*2.5:
                return {'signal':0,'confidence':0.78,'reason':f'ATR spike {cur_atr:.5f} 2.5x normal avoid'}
            if cur_atr<avg_atr*0.3:
                return {'signal':0,'confidence':0.60,'reason':f'ATR too low {cur_atr:.5f} no opportunity'}
            return {'signal':1,'confidence':0.4,'reason':f'ATR normal {cur_atr:.5f}'}
        except: return {'signal':0,'confidence':0.0,'reason':'error'}

# ============================================================
# LAYER 11 — ML AGENTS
# ============================================================
class RandomForestAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            from sklearn.ensemble import RandomForestClassifier
            c,h,l,v = df['close'].values, df['high'].values, df['low'].values, df['volume'].values
            if len(c)<60: return {'signal':0,'confidence':0.5,'reason':'insufficient data'}
            r = rsi(c)
            m = ema(c,12)-ema(c,26)
            a_vals = atr(h,l,c)
            X,y = [],[]
            for i in range(30,len(c)-5):
                feat = [r[i],m[i],a_vals[i],(c[i]-c[i-20])/c[i-20],(c[i]-c[i-5])/c[i-5],v[i]/(np.mean(v[max(0,i-20):i])+1e-10)]
                label = 1 if c[i+5]>c[i]*1.001 else (-1 if c[i+5]<c[i]*0.999 else 0)
                X.append(feat)
                y.append(label)
            if len(set(y))<2: return {'signal':0,'confidence':0.5,'reason':'No variance in labels'}
            X,y = np.array(X[:-5]),np.array(y[:-5])
            rf = RandomForestClassifier(n_estimators=50,random_state=42,max_depth=5)
            rf.fit(X,y)
            r_cur,m_cur,a_cur = rsi(c)[-1],ema(c,12)[-1]-ema(c,26)[-1],atr(h,l,c)[-1]
            feat_cur = [[r_cur,m_cur,a_cur,(c[-1]-c[-20])/c[-20],(c[-1]-c[-5])/c[-5],v[-1]/(np.mean(v[-20:])+1e-10)]]
            pred = rf.predict(feat_cur)[0]
            prob = max(rf.predict_proba(feat_cur)[0])
            return {'signal':int(pred),'confidence':float(prob),'reason':f'RandomForest pred={pred} prob={prob:.2f}'}
        except: return {'signal':0,'confidence':0.5,'reason':'RF error'}

class EnsembleMLAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            c,h,l = df['close'].values, df['high'].values, df['low'].values
            if len(c)<50: return {'signal':0,'confidence':0.5,'reason':'insufficient'}
            r = rsi(c)
            X,y = [],[]
            for i in range(20,len(c)-3):
                feat = [r[i],(c[i]-np.mean(c[i-20:i]))/np.std(c[i-20:i]+1e-10),(h[i]-l[i])/(np.mean(h[i-10:i]-l[i-10:i])+1e-10)]
                label = 1 if c[i+3]>c[i] else -1
                X.append(feat)
                y.append(label)
            X,y = np.array(X[:-3]),np.array(y[:-3])
            gb = GradientBoostingClassifier(n_estimators=30,max_depth=3,random_state=42)
            gb.fit(X,y)
            r_cur = rsi(c)[-1]
            feat = [[(r_cur,(c[-1]-np.mean(c[-20:]))/np.std(c[-20:]+1e-10),(h[-1]-l[-1])/(np.mean(h[-10:]-l[-10:])+1e-10))]]
            feat_flat = [[r_cur,(c[-1]-np.mean(c[-20:]))/np.std(c[-20:]+1e-10),(h[-1]-l[-1])/(np.mean(h[-10:]-l[-10:])+1e-10)]]
            pred = gb.predict(feat_flat)[0]
            prob = max(gb.predict_proba(feat_flat)[0])
            return {'signal':int(pred),'confidence':float(prob),'reason':f'GradBoost pred={pred} conf={prob:.2f}'}
        except: return {'signal':0,'confidence':0.5,'reason':'GB error'}

# ============================================================
# LAYER 12 — NEWS AGENT
# ============================================================
class NewsSentimentAgent(BaseAgent):
    _cache = {}
    _cache_time = {}
    def analyze(self, df, symbol, context=None):
        try:
            now = time.time()
            if symbol in self._cache and now-self._cache_time.get(symbol,0)<3600:
                score = self._cache[symbol]
            else:
                score = loader.get_news(symbol)
                self._cache[symbol] = score
                self._cache_time[symbol] = now
            if score>0.3: return {'signal':1,'confidence':min(0.5+score,0.80),'reason':f'Positive news {score:.2f}'}
            if score<-0.3: return {'signal':-1,'confidence':min(0.5+abs(score),0.80),'reason':f'Negative news {score:.2f}'}
            return {'signal':0,'confidence':0.4,'reason':f'Neutral news {score:.2f}'}
        except: return {'signal':0,'confidence':0.3,'reason':'News unavailable'}

# ============================================================
# LAYER 13 — LLM SPECIALIST AGENTS
# ============================================================
class LLMReasoningAgent(BaseAgent):
    _last_call = 0
    def analyze(self, df, symbol, context=None):
        try:
            now = time.time()
            if now-self._last_call<15: return {'signal':0,'confidence':0.5,'reason':'LLM rate limited'}
            c = df['close'].values
            ret_pct = (c[-1]-c[-24])/c[-24]*100 if len(c)>24 else 0
            vix = context.get('vix',20) if context else 20
            dxy = context.get('dxy',104) if context else 104
            votes = context.get('votes_summary','mixed') if context else 'mixed'
            prompt = f"""Expert forex trader analysis for {symbol}:
- 24h change: {ret_pct:.2f}%
- Price: {c[-1]:.5f}
- VIX: {vix:.1f} DXY: {dxy:.1f}
- Agent votes: {votes}
Respond ONLY with JSON: {{"signal": 1 or -1 or 0, "confidence": 0.0-1.0, "reason": "max 15 words"}}"""
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CONFIG['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'},
                json={'model':'claude-sonnet-4-20250514','max_tokens':80,'messages':[{'role':'user','content':prompt}]},
                timeout=12)
            LLMReasoningAgent._last_call = time.time()
            if r.status_code==200:
                txt = r.json()['content'][0]['text'].strip().replace('```json','').replace('```','')
                res = json.loads(txt)
                return {'signal':int(res.get('signal',0)),'confidence':float(res.get('confidence',0.5)),'reason':f"LLM: {res.get('reason','')}"}
        except: pass
        return {'signal':0,'confidence':0.5,'reason':'LLM unavailable'}

# ============================================================
# RISK MANAGER
# ============================================================
class RiskManager:
    def __init__(self):
        self.capital = CONFIG['INITIAL_CAPITAL']
        self.peak = CONFIG['INITIAL_CAPITAL']

    def position_size(self, symbol, entry, sl, confidence, capital_override=None):
        cap = capital_override or self.capital
        risk_amount = cap * CONFIG['RISK_PER_TRADE'] * min(confidence, 1.0)
        pip = MARKETS[symbol]['pip']
        pip_usd = MARKETS[symbol]['pip_usd']
        sl_pips = abs(entry-sl)/pip
        if sl_pips==0: return 0.01
        lots = risk_amount/(sl_pips*pip_usd)
        return round(min(max(lots,0.01),10.0),2)

    def get_sl(self, df, signal):
        h,l,c = df['high'].values, df['low'].values, df['close'].values
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
# CHART GENERATOR
# ============================================================
class ChartGenerator:
    def generate_signal_chart(self, df, symbol, signal, entry, sl, tp, reasons):
        try:
            fig, ax = plt.subplots(figsize=(14,7), facecolor='#1a1a2e')
            ax.set_facecolor('#16213e')
            c = df['close'].values[-100:]
            h = df['high'].values[-100:]
            l = df['low'].values[-100:]
            x = range(len(c))
            for i in x:
                color = '#00ff88' if df['close'].values[-100+i]>=df['open'].values[-100+i] else '#ff4444'
                ax.plot([i,i],[l[i],h[i]],color=color,linewidth=0.8)
                ax.plot([i,i],[df['open'].values[-100+i],df['close'].values[-100+i]],color=color,linewidth=3)
            ax.axhline(y=entry,color='#00bfff',linewidth=2,linestyle='--',label=f'Entry: {entry:.5f}')
            ax.axhline(y=sl,color='#ff4444',linewidth=2,linestyle='--',label=f'SL: {sl:.5f}')
            ax.axhline(y=tp,color='#00ff88',linewidth=2,linestyle='--',label=f'TP: {tp:.5f}')
            ax.fill_between(x,sl,entry,alpha=0.1,color='#ff4444')
            ax.fill_between(x,entry,tp,alpha=0.1,color='#00ff88')
            arrow_color = '#00ff88' if signal==1 else '#ff4444'
            direction = '▲ BUY' if signal==1 else '▼ SELL'
            ax.annotate(direction,xy=(len(c)-1,entry),fontsize=16,color=arrow_color,fontweight='bold',
                        xytext=(-20,20 if signal==1 else -30),textcoords='offset points')
            top_reasons = [r.replace('✅','').replace('❌','').strip() for r in reasons[:5]]
            reason_text = '\n'.join(top_reasons)
            ax.text(0.02,0.98,reason_text,transform=ax.transAxes,fontsize=8,color='#aaaaaa',
                    verticalalignment='top',bbox=dict(boxstyle='round',facecolor='#1a1a2e',alpha=0.8))
            ax.set_title(f'{symbol} | {direction} | Entry:{entry:.5f} SL:{sl:.5f} TP:{tp:.5f}',
                        color='white',fontsize=12,fontweight='bold')
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('#333366')
            ax.spines['top'].set_color('#333366')
            ax.spines['left'].set_color('#333366')
            ax.spines['right'].set_color('#333366')
            ax.legend(loc='upper left',facecolor='#1a1a2e',labelcolor='white',fontsize=9)
            plt.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf,format='png',dpi=100,bbox_inches='tight')
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode()
            plt.close()
            chart_path = f'charts/{symbol}_{int(time.time())}.png'
            os.makedirs('charts',exist_ok=True)
            with open(chart_path,'wb') as f:
                buf.seek(0)
                f.write(buf.read())
            return img_b64, chart_path
        except Exception as e:
            return None, None

# ============================================================
# TELEGRAM NOTIFIER
# ============================================================
class TelegramNotifier:
    BASE = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}"

    def send(self, msg):
        try:
            requests.post(f"{self.BASE}/sendMessage",
                json={'chat_id':CONFIG['TELEGRAM_CHAT_ID'],'text':msg,'parse_mode':'HTML'},timeout=10)
        except: pass

    def send_photo(self, path, caption):
        try:
            with open(path,'rb') as f:
                requests.post(f"{self.BASE}/sendPhoto",
                    data={'chat_id':CONFIG['TELEGRAM_CHAT_ID'],'caption':caption,'parse_mode':'HTML'},
                    files={'photo':f},timeout=15)
        except: pass

    def trade_alert(self, sym, sig, entry, sl, tp, lots, conf, reasons, chart_path=None):
        emoji = '🟢 BUY' if sig==1 else '🔴 SELL'
        rr = abs(tp-entry)/abs(entry-sl) if abs(entry-sl)>0 else 0
        pip = MARKETS[sym]['pip']
        sl_pips = abs(entry-sl)/pip
        tp_pips = abs(tp-entry)/pip
        msg = f"""
<b>{emoji} {sym}</b>
💰 Entry: <code>{entry:.5f}</code>
🛡 Stop Loss: <code>{sl:.5f}</code> ({sl_pips:.0f} pips)
🎯 Take Profit: <code>{tp:.5f}</code> ({tp_pips:.0f} pips)
📊 Lots: <b>{lots}</b> | R:R <b>1:{rr:.1f}</b>
🧠 Confidence: <b>{conf:.1%}</b>
📋 Top Reasons:
{chr(10).join(reasons[:5])}
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
        if chart_path and os.path.exists(chart_path):
            self.send_photo(chart_path, msg)
        else:
            self.send(msg)

    def daily_summary(self, capital, trades, pnl):
        self.send(f"""
📊 <b>DAILY SUMMARY</b>
💵 Capital: <b>${capital:,.2f}</b>
📈 Trades today: <b>{trades}</b>
💰 PnL today: <b>${pnl:+,.2f}</b>
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
""")

# ============================================================
# SUPABASE SAVER
# ============================================================
class SupabaseSaver:
    def save_signal(self, signal_data):
        try:
            requests.post(f"{CONFIG['SUPABASE_URL']}/rest/v1/signals",
                headers={'apikey':CONFIG['SUPABASE_KEY'],'Content-Type':'application/json','Prefer':'return=minimal'},
                json=signal_data, timeout=10)
        except: pass

    def save_trade(self, trade_data):
        try:
            requests.post(f"{CONFIG['SUPABASE_URL']}/rest/v1/trades",
                headers={'apikey':CONFIG['SUPABASE_KEY'],'Content-Type':'application/json','Prefer':'return=minimal'},
                json=trade_data, timeout=10)
        except: pass

# ============================================================
# MASTER ORCHESTRATOR
# ============================================================
class MasterOrchestrator:
    def __init__(self):
        self.agents = self._build_all_agents()
        self.risk = RiskManager()
        self.telegram = TelegramNotifier()
        self.chart_gen = ChartGenerator()
        self.db = SupabaseSaver()
        print(f"✅ {len(self.agents)} agents initialized")

    def _build_all_agents(self):
        return [
            # Layer 1 — Market Structure
            MarketStructureAgent('MarketStructure'),
            LiquiditySweepAgent('LiquiditySweep'),
            OrderBlockAgent('OrderBlock'),
            FairValueGapAgent('FairValueGap'),
            PremiumDiscountAgent('PremiumDiscount'),
            InducementAgent('Inducement'),
            # Layer 2 — ICT
            KillzoneAgent('Killzone'),
            OptimalTradeEntryAgent('OptimalTradeEntry'),
            AsianRangeAgent('AsianRange'),
            PowerOfThreeAgent('PowerOfThree'),
            SilverBulletAgent('SilverBullet'),
            MidnightOpenAgent('MidnightOpen'),
            # Layer 3 — Wyckoff
            WyckoffPhaseAgent('WyckoffPhase'),
            SpringUpthrustAgent('SpringUpthrust'),
            WyckoffVolumeAgent('WyckoffVolume'),
            # Layer 4 — Technical
            MomentumAgent('Momentum'),
            TrendStrengthAgent('TrendStrength'),
            SupportResistanceAgent('SupportResistance'),
            BollingerBandAgent('BollingerBand'),
            MeanReversionAgent('MeanReversion'),
            BreakoutAgent('Breakout'),
            CandlestickAgent('Candlestick'),
            StochasticAgent('Stochastic'),
            VolatilityRegimeAgent('VolatilityRegime'),
            # Layer 5 — Volume
            AnchoredVWAPAgent('AnchoredVWAP'),
            DarkPoolProxyAgent('DarkPoolProxy'),
            SmartMoneyFootprintAgent('SmartMoneyFootprint'),
            SpreadAnalysisAgent('SpreadAnalysis'),
            # Layer 6 — Intermarket
            DXYCorrelationAgent('DXYCorrelation'),
            VIXSentimentAgent('VIXSentiment'),
            BondYieldAgent('BondYield'),
            CarryTradeAgent('CarryTrade'),
            RiskOnOffAgent('RiskOnOff'),
            GoldCorrelationAgent('GoldCorrelation'),
            # Layer 7 — Quantitative
            HurstExponentAgent('HurstExponent'),
            MonteCarloAgent('MonteCarlo'),
            FibonacciTimeAgent('FibonacciTime'),
            PsychologicalLevelAgent('PsychologicalLevel'),
            GapFillAgent('GapFill'),
            KellyCriterionAgent('KellyCriterion'),
            # Layer 8 — Fundamental
            COTReportAgent('COTReport'),
            SeasonalAgent('Seasonal'),
            EconomicCalendarAgent('EconomicCalendar'),
            SafeHavenAgent('SafeHaven'),
            CentralBankAgent('CentralBank'),
            # Layer 9 — Session
            SessionDNAAgent('SessionDNA'),
            DayOfWeekAgent('DayOfWeek'),
            NewsTrapKillerAgent('NewsTrapKiller'),
            WeeklyOpenAgent('WeeklyOpen'),
            # Layer 10 — Risk Protection
            DrawdownRecoveryAgent('DrawdownRecovery'),
            MaxExposureAgent('MaxExposure'),
            VolatilityFilterAgent('VolatilityFilter'),
            # Layer 11 — ML
            RandomForestAgent('RandomForest'),
            EnsembleMLAgent('EnsembleML'),
            # Layer 12 — News
            NewsSentimentAgent('NewsSentiment'),
            # Layer 13 — LLM
            LLMReasoningAgent('LLMReasoning'),
        ]

    def get_context(self):
        print("  📡 Loading global context...", end='', flush=True)
        ctx = {
            'vix': loader.get_vix(),
            'dxy': loader.get_dxy(),
            'gold': loader.get_gold(),
            'fred_data': loader.get_fred_data(),
            'cot': loader.get_cot_data(),
        }
        print(f" VIX:{ctx['vix']:.1f} DXY:{ctx['dxy']:.1f} Gold:{ctx['gold']:.0f}")
        return ctx

    def analyze_pair(self, symbol, df, context, capital_override=None):
        if df is None or len(df)<50: return None

        votes_buy, votes_sell, all_reasons = [], [], []

        for agent in self.agents:
            try:
                result = agent.analyze(df, symbol, context)
                sig = result.get('signal',0)
                conf = result.get('confidence',0.5)
                reason = result.get('reason','')
                wconf = conf * agent.weight

                if sig==1:
                    votes_buy.append(wconf)
                    all_reasons.append(f'✅ {agent.name}: {reason}')
                elif sig==-1:
                    votes_sell.append(wconf)
                    all_reasons.append(f'❌ {agent.name}: {reason}')
            except: continue

        total = len(votes_buy)+len(votes_sell)
        if total<CONFIG['MIN_AGENT_VOTES']: return None

        buy_pct = len(votes_buy)/total
        sell_pct = len(votes_sell)/total

        context['votes_summary'] = f'Buy:{len(votes_buy)} Sell:{len(votes_sell)}'

        if buy_pct>=CONFIG['VOTE_THRESHOLD']:
            final_sig = 1
            final_conf = sum(votes_buy)/total
        elif sell_pct>=CONFIG['VOTE_THRESHOLD']:
            final_sig = -1
            final_conf = sum(votes_sell)/total
        else:
            return None

        entry = float(df['close'].values[-1])
        sl = self.risk.get_sl(df, final_sig)
        tp = self.risk.get_tp(entry, sl, final_sig)
        capital = capital_override or self.risk.capital
        lots = self.risk.position_size(symbol, entry, sl, final_conf, capital)
        pip = MARKETS[symbol]['pip']
        pip_usd = MARKETS[symbol]['pip_usd']
        sl_pips = abs(entry-sl)/pip
        dollar_risk = sl_pips * pip_usd * lots

        return {
            'symbol': symbol,
            'signal': final_sig,
            'confidence': final_conf,
            'entry': entry,
            'stop_loss': sl,
            'take_profit': tp,
            'lots': lots,
            'dollar_risk': dollar_risk,
            'rr': abs(tp-entry)/abs(entry-sl) if abs(entry-sl)>0 else 0,
            'buy_votes': len(votes_buy),
            'sell_votes': len(votes_sell),
            'total_votes': total,
            'reasons': all_reasons,
            'timestamp': datetime.utcnow().isoformat(),
        }

    def run_analysis(self, capital_override=None):
        print(f"\n{'='*65}")
        print(f"🚀 V6 | {len(self.agents)} AGENTS | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*65}")

        context = self.get_context()
        signals = []

        for symbol in TRADING_PAIRS:
            print(f"\n  ⚡ {symbol}", end='', flush=True)
            dfs = loader.get_multi_tf(symbol)
            df = dfs.get('1h')
            if df is None:
                print(" ❌ No data")
                continue
            print(f" | {len(df)} candles", end='', flush=True)

            result = self.analyze_pair(symbol, df, context.copy(), capital_override)

            if result:
                action = '🟢 BUY' if result['signal']==1 else '🔴 SELL'
                print(f"\n    {action} conf={result['confidence']:.1%} lots={result['lots']} RR=1:{result['rr']:.1f}")
                print(f"    Entry:{result['entry']:.5f} SL:{result['stop_loss']:.5f} TP:{result['take_profit']:.5f}")
                print(f"    Votes 🟢{result['buy_votes']} 🔴{result['sell_votes']} / {result['total_votes']} active")
                print(f"    💵 Dollar risk: ${result['dollar_risk']:.2f}")

                img_b64, chart_path = self.chart_gen.generate_signal_chart(
                    df, symbol, result['signal'], result['entry'],
                    result['stop_loss'], result['take_profit'], result['reasons'])

                result['chart_b64'] = img_b64

                self.telegram.trade_alert(
                    symbol, result['signal'], result['entry'],
                    result['stop_loss'], result['take_profit'],
                    result['lots'], result['confidence'],
                    [r for r in result['reasons'][:5]], chart_path)

                self.db.save_signal({
                    'symbol': symbol,
                    'signal': result['signal'],
                    'confidence': result['confidence'],
                    'entry': result['entry'],
                    'stop_loss': result['stop_loss'],
                    'take_profit': result['take_profit'],
                    'lots': result['lots'],
                    'timestamp': result['timestamp'],
                })

                signals.append(result)
                signals_store.insert(0, result)
                if len(signals_store)>100: signals_store.pop()

            else:
                print(" | ⚪ HOLD")

        system_status['last_run'] = datetime.utcnow().isoformat()
        system_status['running'] = True

        print(f"\n{'='*65}")
        print(f"📊 COMPLETE | Signals:{len(signals)} Buy:{sum(1 for s in signals if s['signal']==1)} Sell:{sum(1 for s in signals if s['signal']==-1)}")
        print(f"💵 Capital: ${self.risk.capital:,.2f} | Drawdown: {self.risk.drawdown():.2%}")
        print(f"{'='*65}")
        print("📱 Check Telegram for alerts with charts!")

        return signals

# ============================================================
# MAIN
# ============================================================
orchestrator = None

def run_system(capital_override=None):
    global orchestrator
    if orchestrator is None:
        orchestrator = MasterOrchestrator()
        orchestrator.telegram.send(f"""
🚀 <b>V6 ULTIMATE SYSTEM STARTED</b>
🤖 Agents: {len(orchestrator.agents)}
📈 Markets: {len(TRADING_PAIRS)}
💵 Capital: ${CONFIG['INITIAL_CAPITAL']:,}
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        """)
    return orchestrator.run_analysis(capital_override)

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║            V6 ULTIMATE MULTI-AGENT TRADING SYSTEM           ║
║   SMC + ICT + Wyckoff + Intermarket + ML + LLM + Risk      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    run_system()
    print("\n✅ V6 Brain complete!")
    print("📱 Check Telegram for trade alerts with charts!")
    print("\nTo run with dashboard: py -3.11 v6_dashboard_server.py")
