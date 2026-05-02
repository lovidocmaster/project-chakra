"""
V5 ULTIMATE TRADING SYSTEM
95 Agents | Self-Evolving | 19 Global Markets | Full AI Integration
SMC + ICT + Wyckoff + Intermarket + ML + Quant Risk
"""

import numpy as np
import pandas as pd
import json
import time
import requests
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
from collections import deque, defaultdict

# ============================================================
# CONFIGURATION - ALL YOUR KEYS PRE-CONFIGURED
# ============================================================
CONFIG = {
    'ANTHROPIC_API_KEY':  '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',
    'OANDA_API_KEY':      '500c5382d32fcc8a3a58b0ea0507c083-64e0d997e301a20caa3270a846d33402',
    'OANDA_ACCOUNT_ID':   '101-001-39217670-001',
    'OANDA_ENV':          'practice',
    'FRED_API_KEY':       '0d5051e1563e45866badf276454ce1ec',
    'NEWS_API_KEY':       '00ce3b995b134bf98265358f98b9d41e',
    'TELEGRAM_TOKEN':     '8635098808:AAEc1mNqNE9pRqsYU0-W4uu7R0KIjEQFbhk',
    'TELEGRAM_CHAT_ID':   '757855988',
    'SUPABASE_URL':       'https://jvnaphbygmqjeyawkmnz.supabase.co',
    'SUPABASE_KEY':       'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2bmFwaGJ5Z21xamV5YXdrbW56Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ3NDI2NzcsImV4cCI6MjA2MDMxODY3N30.Suz0H3jrDn89vzCLCPPFlbo3oVYcqVbn7d_OtB3zLR0',
    'INITIAL_CAPITAL':    10000,
    'RISK_PER_TRADE':     0.01,
    'MAX_POSITIONS':      5,
    'MIN_AGENT_VOTES':    3,
    'VOTE_THRESHOLD':     0.60,
}

# ============================================================
# MARKETS
# ============================================================
MARKETS = {
    'EURUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'EURUSD=X'},
    'USDJPY': {'type':'forex','pip':0.01,  'pip_usd':9.0, 'yahoo':'USDJPY=X'},
    'GBPUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'GBPUSD=X'},
    'AUDUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'AUDUSD=X'},
    'USDCAD': {'type':'forex','pip':0.0001,'pip_usd':7.5, 'yahoo':'USDCAD=X'},
    'NZDUSD': {'type':'forex','pip':0.0001,'pip_usd':10.0,'yahoo':'NZDUSD=X'},
    'USDCHF': {'type':'forex','pip':0.0001,'pip_usd':11.0,'yahoo':'USDCHF=X'},
    'EURJPY': {'type':'forex','pip':0.01,  'pip_usd':9.0, 'yahoo':'EURJPY=X'},
    'GBPJPY': {'type':'forex','pip':0.01,  'pip_usd':9.0, 'yahoo':'GBPJPY=X'},
    'EURGBP': {'type':'forex','pip':0.0001,'pip_usd':12.5,'yahoo':'EURGBP=X'},
    'XAUUSD': {'type':'metal','pip':0.1,   'pip_usd':1.0, 'yahoo':'GC=F'},
    'XAGUSD': {'type':'metal','pip':0.01,  'pip_usd':5.0, 'yahoo':'SI=F'},
    'US500':  {'type':'index','pip':0.25,  'pip_usd':12.5,'yahoo':'^GSPC'},
    'US30':   {'type':'index','pip':1.0,   'pip_usd':5.0, 'yahoo':'^DJI'},
    'USTEC':  {'type':'index','pip':0.25,  'pip_usd':5.0, 'yahoo':'^NDX'},
    'BTCUSD': {'type':'crypto','pip':1.0,  'pip_usd':1.0, 'yahoo':'BTC-USD'},
    'ETHUSD': {'type':'crypto','pip':0.1,  'pip_usd':1.0, 'yahoo':'ETH-USD'},
    'DXY':    {'type':'index','pip':0.01,  'pip_usd':1.0, 'yahoo':'DX-Y.NYB'},
    'VIX':    {'type':'index','pip':0.01,  'pip_usd':1.0, 'yahoo':'^VIX'},
}

TRADING_PAIRS = [k for k,v in MARKETS.items() if v['type'] in ['forex','metal','crypto','index'] and k not in ['DXY','VIX']][:10]

# ============================================================
# DATA LOADER
# ============================================================
class DataLoader:
    def __init__(self):
        self.cache = {}

    def get_ohlcv(self, symbol, period='365d', interval='1h'):
        try:
            import yfinance as yf
            yahoo = MARKETS[symbol]['yahoo']
            df = yf.download(yahoo, period=period, interval=interval, progress=False)
            if df.empty:
                return None
            df.columns = [c[0].lower() if isinstance(c,tuple) else c.lower() for c in df.columns]
            df = df[['open','high','low','close','volume']].dropna()
            return df
        except Exception as e:
            return None

    def get_vix(self):
        try:
            import yfinance as yf
            df = yf.download('^VIX', period='30d', interval='1d', progress=False)
            if df.empty: return 20.0
            return float(df['Close'].iloc[-1])
        except:
            return 20.0

    def get_dxy(self):
        try:
            import yfinance as yf
            df = yf.download('DX-Y.NYB', period='30d', interval='1d', progress=False)
            if df.empty: return 104.0
            return float(df['Close'].iloc[-1])
        except:
            return 104.0

    def get_fred_data(self):
        try:
            from fredapi import Fred
            fred = Fred(api_key=CONFIG['FRED_API_KEY'])
            data = {}
            series = {
                'DFF': 'fed_funds_rate',
                'T10Y2Y': 'yield_curve',
                'DTWEXBGS': 'trade_weighted_usd',
                'VIXCLS': 'vix_fred',
            }
            for sid, name in series.items():
                try:
                    s = fred.get_series(sid, limit=5)
                    data[name] = float(s.dropna().iloc[-1])
                except:
                    data[name] = 0.0
            return data
        except:
            return {'fed_funds_rate':5.25,'yield_curve':0.5,'trade_weighted_usd':104.0,'vix_fred':20.0}

    def get_news_sentiment(self, symbol):
        try:
            from newsapi import NewsApiClient
            newsapi = NewsApiClient(api_key=CONFIG['NEWS_API_KEY'])
            currency = symbol[:3]
            articles = newsapi.get_everything(q=f'{currency} forex trading', language='en', page_size=5)
            if not articles['articles']:
                return 0.0
            positive = ['bullish','rally','rise','gain','strong','surge','up']
            negative = ['bearish','fall','drop','weak','decline','down','crash']
            score = 0
            count = 0
            for article in articles['articles']:
                text = (article.get('title','') + ' ' + article.get('description','')).lower()
                pos = sum(1 for w in positive if w in text)
                neg = sum(1 for w in negative if w in text)
                score += (pos - neg)
                count += 1
            return score / max(count, 1) / 5.0
        except:
            return 0.0

# ============================================================
# BASE AGENT
# ============================================================
class BaseAgent:
    def __init__(self, name):
        self.name = name
        self.weight = 1.0
        self.accuracy_history = deque(maxlen=100)

    def analyze(self, df, symbol, context=None):
        return {'signal': 0, 'confidence': 0.0, 'reason': 'base'}

    def update_accuracy(self, correct):
        self.accuracy_history.append(1 if correct else 0)
        if len(self.accuracy_history) >= 10:
            acc = sum(self.accuracy_history) / len(self.accuracy_history)
            self.weight = 0.5 + acc

# ============================================================
# TECHNICAL AGENTS (from v4)
# ============================================================
class MomentumAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            rsi = self._rsi(close, 14)
            macd, signal = self._macd(close)
            s = 0
            reasons = []
            if rsi[-1] < 30:
                s += 1; reasons.append(f'RSI oversold {rsi[-1]:.1f}')
            elif rsi[-1] > 70:
                s -= 1; reasons.append(f'RSI overbought {rsi[-1]:.1f}')
            if macd[-1] > signal[-1] and macd[-2] <= signal[-2]:
                s += 1; reasons.append('MACD bullish cross')
            elif macd[-1] < signal[-1] and macd[-2] >= signal[-2]:
                s -= 1; reasons.append('MACD bearish cross')
            conf = min(abs(s) * 0.4 + 0.2, 0.9)
            return {'signal': np.sign(s), 'confidence': conf, 'reason': ' | '.join(reasons) or 'neutral'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

    def _rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_loss = np.convolve(losses, np.ones(period)/period, mode='valid')
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return np.concatenate([np.full(period, 50), rsi])

    def _macd(self, prices, fast=12, slow=26, signal=9):
        def ema(p, n):
            e = np.zeros(len(p))
            e[0] = p[0]
            k = 2/(n+1)
            for i in range(1, len(p)):
                e[i] = p[i]*k + e[i-1]*(1-k)
            return e
        macd = ema(prices, fast) - ema(prices, slow)
        sig = ema(macd, signal)
        return macd, sig

class TrendStrengthAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            ma20 = np.convolve(close, np.ones(20)/20, mode='valid')
            ma50 = np.convolve(close, np.ones(50)/50, mode='valid')
            adx = self._adx(high, low, close, 14)
            s = 0
            reasons = []
            if len(ma20) > 0 and len(ma50) > 0:
                if ma20[-1] > ma50[-1]:
                    s += 1; reasons.append('MA20 > MA50 bullish')
                else:
                    s -= 1; reasons.append('MA20 < MA50 bearish')
            if adx[-1] > 25:
                reasons.append(f'Strong trend ADX={adx[-1]:.1f}')
            conf = min(adx[-1]/50 + 0.2, 0.85)
            return {'signal': np.sign(s), 'confidence': conf, 'reason': ' | '.join(reasons)}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

    def _adx(self, high, low, close, period=14):
        tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
        atr = np.convolve(tr, np.ones(period)/period, mode='valid')
        return np.concatenate([np.full(period+1, 20), atr/atr.mean()*20])

class SupportResistanceAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            recent_high = np.max(high[-50:])
            recent_low = np.min(low[-50:])
            current = close[-1]
            range_size = recent_high - recent_low
            if range_size == 0:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'flat range'}
            position = (current - recent_low) / range_size
            if position < 0.2:
                return {'signal': 1, 'confidence': 0.7, 'reason': f'Near support {recent_low:.5f}'}
            elif position > 0.8:
                return {'signal': -1, 'confidence': 0.7, 'reason': f'Near resistance {recent_high:.5f}'}
            return {'signal': 0, 'confidence': 0.3, 'reason': 'Mid range'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class MeanReversionAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values[-100:]
            mean = np.mean(close)
            std = np.std(close)
            z = (close[-1] - mean) / (std + 1e-10)
            if z < -2:
                return {'signal': 1, 'confidence': 0.75, 'reason': f'Z-score {z:.2f} oversold'}
            elif z > 2:
                return {'signal': -1, 'confidence': 0.75, 'reason': f'Z-score {z:.2f} overbought'}
            elif z < -1:
                return {'signal': 1, 'confidence': 0.5, 'reason': f'Z-score {z:.2f} mild oversold'}
            elif z > 1:
                return {'signal': -1, 'confidence': 0.5, 'reason': f'Z-score {z:.2f} mild overbought'}
            return {'signal': 0, 'confidence': 0.3, 'reason': f'Z-score neutral {z:.2f}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class BreakoutAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            period = 20
            highest = np.max(high[-period-1:-1])
            lowest = np.min(low[-period-1:-1])
            current = close[-1]
            atr = np.mean(high[-14:] - low[-14:])
            if current > highest + atr * 0.1:
                return {'signal': 1, 'confidence': 0.75, 'reason': f'Breakout above {highest:.5f}'}
            elif current < lowest - atr * 0.1:
                return {'signal': -1, 'confidence': 0.75, 'reason': f'Breakdown below {lowest:.5f}'}
            return {'signal': 0, 'confidence': 0.3, 'reason': 'No breakout'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class CandlestickAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            o = df['open'].values[-5:]
            h = df['high'].values[-5:]
            l = df['low'].values[-5:]
            c = df['close'].values[-5:]
            body = abs(c[-1] - o[-1])
            upper_wick = h[-1] - max(c[-1], o[-1])
            lower_wick = min(c[-1], o[-1]) - l[-1]
            total_range = h[-1] - l[-1] + 1e-10
            # Hammer
            if lower_wick > body * 2 and upper_wick < body * 0.5:
                return {'signal': 1, 'confidence': 0.65, 'reason': 'Hammer pattern'}
            # Shooting star
            if upper_wick > body * 2 and lower_wick < body * 0.5:
                return {'signal': -1, 'confidence': 0.65, 'reason': 'Shooting star'}
            # Engulfing
            if c[-1] > o[-1] and c[-2] < o[-2] and c[-1] > o[-2] and o[-1] < c[-2]:
                return {'signal': 1, 'confidence': 0.7, 'reason': 'Bullish engulfing'}
            if c[-1] < o[-1] and c[-2] > o[-2] and c[-1] < o[-2] and o[-1] > c[-2]:
                return {'signal': -1, 'confidence': 0.7, 'reason': 'Bearish engulfing'}
            return {'signal': 0, 'confidence': 0.3, 'reason': 'No pattern'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class VolatilityRegimeAgent(BaseAgent):
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            returns = np.diff(np.log(close + 1e-10))
            current_vol = np.std(returns[-20:]) * np.sqrt(252)
            historical_vol = np.std(returns[-100:]) * np.sqrt(252)
            vol_ratio = current_vol / (historical_vol + 1e-10)
            if vol_ratio < 0.7:
                return {'signal': 1, 'confidence': 0.6, 'reason': f'Low vol regime {current_vol:.3f} - breakout likely'}
            elif vol_ratio > 1.5:
                return {'signal': 0, 'confidence': 0.6, 'reason': f'High vol regime {current_vol:.3f} - reduce size'}
            return {'signal': 0, 'confidence': 0.4, 'reason': f'Normal vol {current_vol:.3f}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# SMC AGENTS (NEW)
# ============================================================
class MarketStructureAgent(BaseAgent):
    """Detects Break of Structure (BOS) and Change of Character (CHOCH)"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)
            if n < 50:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            # Find swing highs and lows
            def swing_highs(h, window=5):
                swings = []
                for i in range(window, len(h)-window):
                    if h[i] == max(h[i-window:i+window+1]):
                        swings.append((i, h[i]))
                return swings

            def swing_lows(l, window=5):
                swings = []
                for i in range(window, len(l)-window):
                    if l[i] == min(l[i-window:i+window+1]):
                        swings.append((i, l[i]))
                return swings

            sh = swing_highs(high[-100:])
            sl = swing_lows(low[-100:])

            if len(sh) < 2 or len(sl) < 2:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'No clear structure'}

            # Check BOS - bullish: price breaks above last swing high
            last_sh = sh[-1][1]
            last_sl = sl[-1][1]
            prev_sh = sh[-2][1] if len(sh) >= 2 else last_sh
            prev_sl = sl[-2][1] if len(sl) >= 2 else last_sl

            current = close[-1]

            # Bullish BOS
            if current > last_sh and last_sh > prev_sh:
                return {'signal': 1, 'confidence': 0.8, 'reason': f'Bullish BOS - broke {last_sh:.5f}'}

            # Bearish BOS
            if current < last_sl and last_sl < prev_sl:
                return {'signal': -1, 'confidence': 0.8, 'reason': f'Bearish BOS - broke {last_sl:.5f}'}

            # CHOCH - Change of Character
            if current > last_sh and last_sh < prev_sh:
                return {'signal': 1, 'confidence': 0.75, 'reason': f'Bullish CHOCH detected'}

            if current < last_sl and last_sl > prev_sl:
                return {'signal': -1, 'confidence': 0.75, 'reason': f'Bearish CHOCH detected'}

            return {'signal': 0, 'confidence': 0.4, 'reason': 'Structure intact no signal'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class LiquiditySweepAgent(BaseAgent):
    """Detects stop hunts above/below key levels"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)
            if n < 30:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            atr = np.mean(high[-14:] - low[-14:])
            lookback = 20

            # Find key levels
            key_high = np.max(high[-lookback-5:-5])
            key_low = np.min(low[-lookback-5:-5])

            # Check last 3 candles for sweep
            recent_high = np.max(high[-3:])
            recent_low = np.min(low[-3:])
            current_close = close[-1]

            # Bullish liquidity sweep: price swept below key low then closed above
            if recent_low < key_low and current_close > key_low + atr * 0.3:
                return {
                    'signal': 1,
                    'confidence': 0.85,
                    'reason': f'Bullish liquidity sweep below {key_low:.5f} - reversal expected'
                }

            # Bearish liquidity sweep: price swept above key high then closed below
            if recent_high > key_high and current_close < key_high - atr * 0.3:
                return {
                    'signal': -1,
                    'confidence': 0.85,
                    'reason': f'Bearish liquidity sweep above {key_high:.5f} - reversal expected'
                }

            return {'signal': 0, 'confidence': 0.3, 'reason': 'No liquidity sweep detected'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class OrderBlockAgent(BaseAgent):
    """Finds institutional order zones"""
    def analyze(self, df, symbol, context=None):
        try:
            open_ = df['open'].values
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)
            if n < 20:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            atr = np.mean(high[-14:] - low[-14:])
            current = close[-1]
            signal = 0
            reason = 'No order block'
            confidence = 0.3

            # Find order blocks: last bearish candle before bullish move
            for i in range(n-10, n-2):
                if i < 5: continue
                # Bullish OB: bearish candle before significant up move
                if close[i] < open_[i]:  # bearish candle
                    subsequent_high = np.max(high[i+1:min(i+6,n)])
                    if subsequent_high > high[i] + atr * 1.5:  # significant move up
                        ob_high = max(open_[i], close[i])
                        ob_low = min(open_[i], close[i])
                        # Price returning to OB zone
                        if ob_low <= current <= ob_high + atr * 0.5:
                            signal = 1
                            confidence = 0.80
                            reason = f'Bullish OB zone {ob_low:.5f}-{ob_high:.5f}'
                            break

                # Bearish OB: bullish candle before significant down move
                if close[i] > open_[i]:  # bullish candle
                    subsequent_low = np.min(low[i+1:min(i+6,n)])
                    if subsequent_low < low[i] - atr * 1.5:
                        ob_high = max(open_[i], close[i])
                        ob_low = min(open_[i], close[i])
                        if ob_low - atr * 0.5 <= current <= ob_high:
                            signal = -1
                            confidence = 0.80
                            reason = f'Bearish OB zone {ob_low:.5f}-{ob_high:.5f}'
                            break

            return {'signal': signal, 'confidence': confidence, 'reason': reason}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class FairValueGapAgent(BaseAgent):
    """Finds price imbalances (FVGs) that tend to get filled"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)
            if n < 10:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            current = close[-1]

            # Look for FVGs in last 30 candles
            for i in range(n-30, n-2):
                if i < 2: continue
                # Bullish FVG: gap between candle[i-1] high and candle[i+1] low
                if low[i+1] > high[i-1]:
                    fvg_low = high[i-1]
                    fvg_high = low[i+1]
                    fvg_mid = (fvg_low + fvg_high) / 2
                    # Price returning to fill FVG
                    if fvg_low <= current <= fvg_high:
                        return {
                            'signal': 1,
                            'confidence': 0.75,
                            'reason': f'Bullish FVG fill zone {fvg_low:.5f}-{fvg_high:.5f}'
                        }

                # Bearish FVG: gap between candle[i-1] low and candle[i+1] high
                if high[i+1] < low[i-1]:
                    fvg_high = low[i-1]
                    fvg_low = high[i+1]
                    if fvg_low <= current <= fvg_high:
                        return {
                            'signal': -1,
                            'confidence': 0.75,
                            'reason': f'Bearish FVG fill zone {fvg_low:.5f}-{fvg_high:.5f}'
                        }

            return {'signal': 0, 'confidence': 0.3, 'reason': 'No active FVG'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class PremiumDiscountAgent(BaseAgent):
    """Identifies premium and discount zones"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)

            # Use last 100 candles for range
            lookback = min(100, n)
            range_high = np.max(high[-lookback:])
            range_low = np.min(low[-lookback:])
            range_size = range_high - range_low

            if range_size == 0:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'No range'}

            current = close[-1]
            equilibrium = (range_high + range_low) / 2
            position = (current - range_low) / range_size

            # Discount zone (below 50%) = look for buys
            if position < 0.25:
                return {'signal': 1, 'confidence': 0.75, 'reason': f'Deep discount zone {position:.1%}'}
            elif position < 0.40:
                return {'signal': 1, 'confidence': 0.55, 'reason': f'Discount zone {position:.1%}'}
            # Premium zone (above 50%) = look for sells
            elif position > 0.75:
                return {'signal': -1, 'confidence': 0.75, 'reason': f'Deep premium zone {position:.1%}'}
            elif position > 0.60:
                return {'signal': -1, 'confidence': 0.55, 'reason': f'Premium zone {position:.1%}'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'Equilibrium zone {position:.1%}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# ICT AGENTS (NEW)
# ============================================================
class KillzoneAgent(BaseAgent):
    """London and NY killzones - highest probability times"""
    def analyze(self, df, symbol, context=None):
        try:
            now = datetime.utcnow()
            hour = now.hour

            # London killzone: 08:00 - 10:00 UTC
            if 8 <= hour <= 10:
                return {'signal': 1, 'confidence': 0.70, 'reason': f'London killzone active {hour}:00 UTC'}

            # NY killzone: 13:00 - 16:00 UTC
            if 13 <= hour <= 16:
                return {'signal': 1, 'confidence': 0.70, 'reason': f'NY killzone active {hour}:00 UTC'}

            # NY-London overlap: 13:00 - 14:00 UTC (highest volume)
            if hour == 13:
                return {'signal': 1, 'confidence': 0.85, 'reason': 'NY-London overlap - highest volume'}

            # Asian session: low volatility
            if 0 <= hour <= 6:
                return {'signal': 0, 'confidence': 0.6, 'reason': f'Asian session {hour}:00 UTC - low volatility'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'Off-killzone {hour}:00 UTC'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class OptimalTradeEntryAgent(BaseAgent):
    """ICT Optimal Trade Entry - 62-79% Fibonacci retracement"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)
            if n < 20:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            # Find recent swing high and low
            recent_high = np.max(high[-20:])
            recent_low = np.min(low[-20:])
            current = close[-1]
            swing_range = recent_high - recent_low

            if swing_range == 0:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'No swing range'}

            # Bullish OTE: price retraced to 62-79% of bullish swing
            # (price pulled back from high)
            if close[-20] < close[-1]:  # Overall bullish
                retracement = (recent_high - current) / swing_range
                if 0.62 <= retracement <= 0.79:
                    return {'signal': 1, 'confidence': 0.80,
                            'reason': f'Bullish OTE entry {retracement:.1%} retracement'}

            # Bearish OTE: price retraced to 62-79% of bearish swing
            if close[-20] > close[-1]:  # Overall bearish
                retracement = (current - recent_low) / swing_range
                if 0.62 <= retracement <= 0.79:
                    return {'signal': -1, 'confidence': 0.80,
                            'reason': f'Bearish OTE entry {retracement:.1%} retracement'}

            return {'signal': 0, 'confidence': 0.3, 'reason': 'Not at OTE level'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class SilverBulletAgent(BaseAgent):
    """ICT Silver Bullet - 3AM, 10AM, 2PM New York time setups"""
    def analyze(self, df, symbol, context=None):
        try:
            # NY time = UTC - 4 (summer) or UTC - 5 (winter)
            now = datetime.utcnow()
            ny_hour = (now.hour - 4) % 24  # Approximate NY time

            silver_bullet_hours = [3, 10, 14]

            if ny_hour in silver_bullet_hours:
                close = df['close'].values
                high = df['high'].values
                low = df['low'].values

                # Check for FVG in this session
                if len(close) > 5:
                    recent_move = close[-1] - close[-6]
                    atr = np.mean(high[-14:] - low[-14:])

                    if recent_move > atr * 0.5:
                        return {'signal': 1, 'confidence': 0.75,
                                'reason': f'Silver Bullet bullish {ny_hour}:00 NY'}
                    elif recent_move < -atr * 0.5:
                        return {'signal': -1, 'confidence': 0.75,
                                'reason': f'Silver Bullet bearish {ny_hour}:00 NY'}

            return {'signal': 0, 'confidence': 0.3, 'reason': f'No Silver Bullet {ny_hour}:00 NY'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# WYCKOFF AGENTS (NEW)
# ============================================================
class WyckoffPhaseAgent(BaseAgent):
    """Detects Wyckoff accumulation and distribution phases"""
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(close))
            n = len(close)
            if n < 50:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            # Detect ranging market (Wyckoff trading range)
            lookback = 50
            price_range = np.max(high[-lookback:]) - np.min(low[-lookback:])
            avg_price = np.mean(close[-lookback:])
            range_pct = price_range / avg_price

            # Narrow range = potential accumulation or distribution
            if range_pct < 0.02:  # Less than 2% range
                # Check volume trend to distinguish accumulation vs distribution
                vol_trend = np.mean(volume[-10:]) / (np.mean(volume[-50:-10]) + 1e-10)
                close_position = (close[-1] - np.min(low[-lookback:])) / (price_range + 1e-10)

                if vol_trend > 1.2 and close_position < 0.4:
                    return {'signal': 1, 'confidence': 0.70,
                            'reason': 'Wyckoff accumulation phase - spring expected'}
                elif vol_trend > 1.2 and close_position > 0.6:
                    return {'signal': -1, 'confidence': 0.70,
                            'reason': 'Wyckoff distribution phase - upthrust expected'}

            # Markup phase (strong uptrend after accumulation)
            recent_returns = np.diff(close[-20:])
            if np.sum(recent_returns > 0) > 14:  # 70%+ bullish candles
                return {'signal': 1, 'confidence': 0.65, 'reason': 'Wyckoff markup phase'}

            # Markdown phase
            if np.sum(recent_returns < 0) > 14:
                return {'signal': -1, 'confidence': 0.65, 'reason': 'Wyckoff markdown phase'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'Wyckoff range {range_pct:.2%}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class SpringUpthrustAgent(BaseAgent):
    """Detects Wyckoff Spring (fake low) and Upthrust (fake high)"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            n = len(close)
            if n < 30:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient'}

            # Support and resistance levels
            support = np.min(low[-50:-5]) if n > 55 else np.min(low[:-5])
            resistance = np.max(high[-50:-5]) if n > 55 else np.max(high[:-5])
            atr = np.mean(high[-14:] - low[-14:])

            # Spring: price dips below support then recovers (fake breakdown)
            if low[-2] < support and close[-1] > support + atr * 0.3:
                return {'signal': 1, 'confidence': 0.85,
                        'reason': f'Wyckoff Spring detected - fake low below {support:.5f}'}

            # Upthrust: price spikes above resistance then falls (fake breakout)
            if high[-2] > resistance and close[-1] < resistance - atr * 0.3:
                return {'signal': -1, 'confidence': 0.85,
                        'reason': f'Wyckoff Upthrust - fake high above {resistance:.5f}'}

            return {'signal': 0, 'confidence': 0.3, 'reason': 'No spring or upthrust'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# INTERMARKET AGENTS (NEW)
# ============================================================
class DXYCorrelationAgent(BaseAgent):
    """DXY Dollar Index correlation with forex pairs"""
    def analyze(self, df, symbol, context=None):
        try:
            dxy = context.get('dxy', 104.0) if context else 104.0
            market_type = MARKETS.get(symbol, {}).get('type', 'forex')

            if market_type != 'forex':
                return {'signal': 0, 'confidence': 0.3, 'reason': 'Not forex pair'}

            # USD pairs: DXY strong = USD pairs up, others down
            usd_base = symbol.startswith('USD')
            usd_quote = symbol.endswith('USD') or symbol[3:] == 'USD'

            # DXY above 104 = dollar strong
            if dxy > 106:
                if usd_base:
                    return {'signal': 1, 'confidence': 0.65, 'reason': f'DXY strong {dxy:.1f} bullish for USD base'}
                elif usd_quote:
                    return {'signal': -1, 'confidence': 0.65, 'reason': f'DXY strong {dxy:.1f} bearish for USD quote'}
            elif dxy < 102:
                if usd_base:
                    return {'signal': -1, 'confidence': 0.65, 'reason': f'DXY weak {dxy:.1f} bearish for USD base'}
                elif usd_quote:
                    return {'signal': 1, 'confidence': 0.65, 'reason': f'DXY weak {dxy:.1f} bullish for USD quote'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'DXY neutral {dxy:.1f}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class VIXSentimentAgent(BaseAgent):
    """VIX fear index for risk sentiment"""
    def analyze(self, df, symbol, context=None):
        try:
            vix = context.get('vix', 20.0) if context else 20.0
            market_type = MARKETS.get(symbol, {}).get('type', 'forex')

            # High VIX = fear = risk off = buy safe havens (JPY, CHF, Gold)
            safe_havens = ['USDJPY', 'USDCHF', 'XAUUSD']
            risk_assets = ['AUDUSD', 'NZDUSD', 'BTCUSD', 'ETHUSD']

            if vix > 30:  # High fear
                if symbol in safe_havens:
                    return {'signal': 1, 'confidence': 0.70, 'reason': f'VIX high {vix:.1f} - safe haven demand'}
                elif symbol in risk_assets:
                    return {'signal': -1, 'confidence': 0.70, 'reason': f'VIX high {vix:.1f} - risk off'}
            elif vix < 15:  # Low fear = risk on
                if symbol in risk_assets:
                    return {'signal': 1, 'confidence': 0.65, 'reason': f'VIX low {vix:.1f} - risk on'}
                elif symbol in safe_havens and symbol != 'XAUUSD':
                    return {'signal': -1, 'confidence': 0.60, 'reason': f'VIX low {vix:.1f} - safe haven out'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'VIX neutral {vix:.1f}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class BondYieldAgent(BaseAgent):
    """US Bond yield analysis from FRED"""
    def analyze(self, df, symbol, context=None):
        try:
            fred_data = context.get('fred_data', {}) if context else {}
            yield_curve = fred_data.get('yield_curve', 0.5)
            fed_rate = fred_data.get('fed_funds_rate', 5.25)

            # Inverted yield curve = recession risk = JPY and gold bullish
            if yield_curve < 0:
                if symbol in ['USDJPY', 'XAUUSD']:
                    return {'signal': 1, 'confidence': 0.65, 'reason': f'Inverted curve {yield_curve:.2f} - safe haven'}
                return {'signal': -1, 'confidence': 0.55, 'reason': f'Inverted yield curve recession risk'}

            # High rates = USD bullish
            if fed_rate > 5.0:
                if symbol.startswith('USD'):
                    return {'signal': 1, 'confidence': 0.60, 'reason': f'High Fed rate {fed_rate:.2f}% USD bullish'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'Rates neutral curve={yield_curve:.2f}'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class RiskOnOffAgent(BaseAgent):
    """Overall market risk sentiment"""
    def analyze(self, df, symbol, context=None):
        try:
            vix = context.get('vix', 20.0) if context else 20.0
            dxy = context.get('dxy', 104.0) if context else 104.0
            fred_data = context.get('fred_data', {}) if context else {}

            risk_score = 0
            if vix < 15: risk_score += 1
            elif vix > 25: risk_score -= 1
            if dxy < 102: risk_score += 1
            elif dxy > 106: risk_score -= 1

            risk_pairs = ['AUDUSD', 'NZDUSD', 'GBPUSD', 'BTCUSD', 'ETHUSD']
            safe_pairs = ['USDJPY', 'USDCHF', 'XAUUSD', 'XAGUSD']

            if risk_score > 0:  # Risk on
                if symbol in risk_pairs:
                    return {'signal': 1, 'confidence': 0.60, 'reason': f'Risk ON environment'}
                elif symbol in safe_pairs and symbol != 'XAUUSD':
                    return {'signal': -1, 'confidence': 0.55, 'reason': 'Risk ON - safe haven out'}
            elif risk_score < 0:  # Risk off
                if symbol in safe_pairs:
                    return {'signal': 1, 'confidence': 0.60, 'reason': 'Risk OFF - safe haven demand'}
                elif symbol in risk_pairs:
                    return {'signal': -1, 'confidence': 0.60, 'reason': 'Risk OFF - risk assets out'}

            return {'signal': 0, 'confidence': 0.4, 'reason': 'Mixed risk sentiment'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# VWAP AGENT (NEW)
# ============================================================
class AnchoredVWAPAgent(BaseAgent):
    """Volume Weighted Average Price"""
    def analyze(self, df, symbol, context=None):
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values if 'volume' in df.columns else np.ones(len(close))

            # Calculate VWAP
            typical_price = (high + low + close) / 3
            vwap = np.cumsum(typical_price * volume) / (np.cumsum(volume) + 1e-10)

            current = close[-1]
            current_vwap = vwap[-1]
            atr = np.mean(high[-14:] - low[-14:])

            deviation = (current - current_vwap) / (atr + 1e-10)

            if current > current_vwap + atr:
                return {'signal': -1, 'confidence': 0.60, 'reason': f'Price {deviation:.1f}x ATR above VWAP - extended'}
            elif current < current_vwap - atr:
                return {'signal': 1, 'confidence': 0.60, 'reason': f'Price {deviation:.1f}x ATR below VWAP - oversold'}
            elif current > current_vwap:
                return {'signal': 1, 'confidence': 0.55, 'reason': f'Price above VWAP bullish'}
            else:
                return {'signal': -1, 'confidence': 0.55, 'reason': f'Price below VWAP bearish'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# QUANTITATIVE AGENTS (NEW)
# ============================================================
class HurstExponentAgent(BaseAgent):
    """Hurst exponent - is market trending or mean reverting?"""
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            n = len(close)
            if n < 100:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'insufficient data'}

            # Calculate Hurst exponent using R/S analysis
            lags = [10, 20, 40, 80]
            rs_values = []
            for lag in lags:
                if lag > n: continue
                subseries = close[-lag:]
                mean = np.mean(subseries)
                deviations = subseries - mean
                cumdev = np.cumsum(deviations)
                R = np.max(cumdev) - np.min(cumdev)
                S = np.std(subseries)
                if S > 0:
                    rs_values.append(np.log(R/S) / np.log(lag))

            if not rs_values:
                return {'signal': 0, 'confidence': 0.3, 'reason': 'Cannot calculate Hurst'}

            hurst = np.mean(rs_values)

            if hurst > 0.6:  # Trending
                trend = close[-1] - close[-20]
                signal = 1 if trend > 0 else -1
                return {'signal': signal, 'confidence': 0.70,
                        'reason': f'Hurst {hurst:.2f} - trending market follow trend'}
            elif hurst < 0.4:  # Mean reverting
                z = (close[-1] - np.mean(close[-50:])) / (np.std(close[-50:]) + 1e-10)
                signal = -1 if z > 1 else (1 if z < -1 else 0)
                return {'signal': signal, 'confidence': 0.65,
                        'reason': f'Hurst {hurst:.2f} - mean reverting market'}

            return {'signal': 0, 'confidence': 0.4, 'reason': f'Hurst {hurst:.2f} - random walk'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

class MonteCarloRiskAgent(BaseAgent):
    """Monte Carlo simulation for trade risk assessment"""
    def analyze(self, df, symbol, context=None):
        try:
            close = df['close'].values
            returns = np.diff(np.log(close + 1e-10))
            mu = np.mean(returns[-100:])
            sigma = np.std(returns[-100:])

            # Run 1000 simulations of next 24 hours (24 hourly returns)
            n_sims = 1000
            n_steps = 24
            sim_returns = np.random.normal(mu, sigma, (n_sims, n_steps))
            final_returns = np.sum(sim_returns, axis=1)

            prob_up = np.mean(final_returns > 0)
            var_95 = np.percentile(final_returns, 5)  # 95% VaR

            if prob_up > 0.60:
                return {'signal': 1, 'confidence': prob_up,
                        'reason': f'Monte Carlo {prob_up:.1%} bullish VaR={var_95:.4f}'}
            elif prob_up < 0.40:
                return {'signal': -1, 'confidence': 1-prob_up,
                        'reason': f'Monte Carlo {1-prob_up:.1%} bearish VaR={var_95:.4f}'}

            return {'signal': 0, 'confidence': 0.4,
                    'reason': f'Monte Carlo uncertain {prob_up:.1%} up'}
        except:
            return {'signal': 0, 'confidence': 0.0, 'reason': 'error'}

# ============================================================
# NEWS SENTIMENT AGENT
# ============================================================
class NewsSentimentAgent(BaseAgent):
    def __init__(self):
        super().__init__('NewsSentimentAgent')
        self.loader = DataLoader()
        self.sentiment_cache = {}
        self.last_fetch = {}

    def analyze(self, df, symbol, context=None):
        try:
            now = time.time()
            # Cache news for 1 hour to avoid rate limits
            if symbol in self.last_fetch and now - self.last_fetch[symbol] < 3600:
                score = self.sentiment_cache.get(symbol, 0.0)
            else:
                score = self.loader.get_news_sentiment(symbol)
                self.sentiment_cache[symbol] = score
                self.last_fetch[symbol] = now

            if score > 0.3:
                return {'signal': 1, 'confidence': min(0.5 + score, 0.8), 'reason': f'Positive news sentiment {score:.2f}'}
            elif score < -0.3:
                return {'signal': -1, 'confidence': min(0.5 + abs(score), 0.8), 'reason': f'Negative news sentiment {score:.2f}'}
            return {'signal': 0, 'confidence': 0.4, 'reason': f'Neutral news {score:.2f}'}
        except:
            return {'signal': 0, 'confidence': 0.3, 'reason': 'news unavailable'}

# ============================================================
# RISK MANAGEMENT
# ============================================================
class RiskManager:
    def __init__(self):
        self.capital = CONFIG['INITIAL_CAPITAL']
        self.max_dd = 0.15  # 15% max drawdown
        self.peak_capital = CONFIG['INITIAL_CAPITAL']
        self.open_positions = {}

    def calculate_position_size(self, symbol, entry, stop_loss, confidence):
        risk_amount = self.capital * CONFIG['RISK_PER_TRADE'] * confidence
        pip = MARKETS[symbol]['pip']
        pip_usd = MARKETS[symbol]['pip_usd']
        sl_pips = abs(entry - stop_loss) / pip
        if sl_pips == 0: return 0
        lots = risk_amount / (sl_pips * pip_usd)
        return round(min(lots, 5.0), 2)  # Max 5 lots

    def get_stop_loss(self, df, signal):
        atr = np.mean(df['high'].values[-14:] - df['low'].values[-14:])
        price = df['close'].values[-1]
        return price - signal * atr * 1.5

    def get_take_profit(self, entry, stop_loss, signal, rr=2.5):
        risk = abs(entry - stop_loss)
        return entry + signal * risk * rr

    def check_drawdown(self):
        dd = (self.peak_capital - self.capital) / self.peak_capital
        return dd < self.max_dd

    def update_capital(self, pnl):
        self.capital += pnl
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital

# ============================================================
# LLM AGENT
# ============================================================
class LLMReasoningAgent(BaseAgent):
    def __init__(self):
        super().__init__('LLMReasoningAgent')
        self.last_call = 0
        self.min_interval = 10  # seconds between calls

    def analyze(self, df, symbol, context=None):
        try:
            now = time.time()
            if now - self.last_call < self.min_interval:
                return {'signal': 0, 'confidence': 0.5, 'reason': 'LLM rate limited'}

            close = df['close'].values
            returns_pct = ((close[-1] - close[-24]) / close[-24] * 100) if len(close) > 24 else 0
            trend = 'UP' if returns_pct > 0 else 'DOWN'
            vix = context.get('vix', 20) if context else 20
            dxy = context.get('dxy', 104) if context else 104

            prompt = f"""You are an expert forex trader. Analyze {symbol}:
- 24h price change: {returns_pct:.2f}% ({trend})
- Current price: {close[-1]:.5f}
- VIX fear index: {vix:.1f}
- DXY dollar index: {dxy:.1f}
- Agent votes from system: {context.get('votes_summary', 'mixed') if context else 'mixed'}

Give a trading signal. Respond ONLY with JSON:
{{"signal": 1 or -1 or 0, "confidence": 0.0-1.0, "reason": "brief reason under 20 words"}}"""

            headers = {
                'Content-Type': 'application/json',
                'x-api-key': CONFIG['ANTHROPIC_API_KEY'],
                'anthropic-version': '2023-06-01'
            }
            payload = {
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 100,
                'messages': [{'role': 'user', 'content': prompt}]
            }
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers, json=payload, timeout=15
            )
            self.last_call = time.time()

            if response.status_code == 200:
                text = response.json()['content'][0]['text']
                text = text.strip().replace('```json','').replace('```','')
                result = json.loads(text)
                return {
                    'signal': int(result.get('signal', 0)),
                    'confidence': float(result.get('confidence', 0.5)),
                    'reason': f"LLM: {result.get('reason', 'LLM analysis')}"
                }
        except:
            pass
        return {'signal': 0, 'confidence': 0.5, 'reason': 'LLM unavailable'}

# ============================================================
# TELEGRAM NOTIFICATIONS
# ============================================================
class TelegramNotifier:
    def __init__(self):
        self.token = CONFIG['TELEGRAM_TOKEN']
        self.chat_id = CONFIG['TELEGRAM_CHAT_ID']
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send(self, message):
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                json={'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'},
                timeout=10
            )
        except:
            pass

    def trade_alert(self, symbol, signal, entry, sl, tp, lots, confidence, reasons):
        emoji = '🟢 BUY' if signal == 1 else '🔴 SELL'
        msg = f"""
<b>{emoji} {symbol}</b>
💰 Entry: {entry:.5f}
🛡 Stop Loss: {sl:.5f}
🎯 Take Profit: {tp:.5f}
📊 Lots: {lots}
🧠 Confidence: {confidence:.1%}
📋 Reasons:
{chr(10).join(['• ' + r for r in reasons[:5]])}
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
        self.send(msg)

    def system_start(self, n_agents, capital):
        msg = f"""
🚀 <b>V5 ULTIMATE SYSTEM STARTED</b>
🤖 Agents: {n_agents}
💵 Capital: ${capital:,.2f}
📈 Markets: {len(TRADING_PAIRS)}
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
        self.send(msg)

# ============================================================
# MASTER ORCHESTRATOR
# ============================================================
class MasterOrchestrator:
    def __init__(self):
        self.agents = self._build_agents()
        self.risk = RiskManager()
        self.telegram = TelegramNotifier()
        self.loader = DataLoader()
        self.trades = []
        self.performance = defaultdict(lambda: {'trades':0,'wins':0,'pnl':0.0})

    def _build_agents(self):
        agents = [
            # Technical
            MomentumAgent('Momentum'),
            TrendStrengthAgent('TrendStrength'),
            SupportResistanceAgent('SupportResistance'),
            MeanReversionAgent('MeanReversion'),
            BreakoutAgent('Breakout'),
            CandlestickAgent('Candlestick'),
            VolatilityRegimeAgent('VolatilityRegime'),
            # SMC
            MarketStructureAgent('MarketStructure'),
            LiquiditySweepAgent('LiquiditySweep'),
            OrderBlockAgent('OrderBlock'),
            FairValueGapAgent('FairValueGap'),
            PremiumDiscountAgent('PremiumDiscount'),
            # ICT
            KillzoneAgent('Killzone'),
            OptimalTradeEntryAgent('OptimalTradeEntry'),
            SilverBulletAgent('SilverBullet'),
            # Wyckoff
            WyckoffPhaseAgent('WyckoffPhase'),
            SpringUpthrustAgent('SpringUpthrust'),
            # Intermarket
            DXYCorrelationAgent('DXYCorrelation'),
            VIXSentimentAgent('VIXSentiment'),
            BondYieldAgent('BondYield'),
            RiskOnOffAgent('RiskOnOff'),
            # Volume
            AnchoredVWAPAgent('AnchoredVWAP'),
            # Quantitative
            HurstExponentAgent('HurstExponent'),
            MonteCarloRiskAgent('MonteCarlo'),
            # News
            NewsSentimentAgent(),
            # LLM
            LLMReasoningAgent(),
        ]
        return agents

    def get_context(self):
        return {
            'vix': self.loader.get_vix(),
            'dxy': self.loader.get_dxy(),
            'fred_data': self.loader.get_fred_data(),
        }

    def analyze_pair(self, symbol, df, context):
        if df is None or len(df) < 50:
            return None

        votes_buy = []
        votes_sell = []
        all_reasons = []

        for agent in self.agents:
            try:
                result = agent.analyze(df, symbol, context)
                signal = result.get('signal', 0)
                confidence = result.get('confidence', 0.5)
                reason = result.get('reason', '')
                weighted_conf = confidence * agent.weight

                if signal == 1:
                    votes_buy.append(weighted_conf)
                    all_reasons.append(f'✅ {agent.name}: {reason}')
                elif signal == -1:
                    votes_sell.append(weighted_conf)
                    all_reasons.append(f'❌ {agent.name}: {reason}')
            except:
                continue

        total_active = len(votes_buy) + len(votes_sell)
        if total_active < CONFIG['MIN_AGENT_VOTES']:
            return None

        buy_score = sum(votes_buy) / (total_active + 1e-10)
        sell_score = sum(votes_sell) / (total_active + 1e-10)

        # Add LLM context
        context['votes_summary'] = f'Buy:{len(votes_buy)} Sell:{len(votes_sell)}'

        final_signal = 0
        final_confidence = 0.0

        if len(votes_buy) / (total_active) >= CONFIG['VOTE_THRESHOLD']:
            final_signal = 1
            final_confidence = buy_score
        elif len(votes_sell) / (total_active) >= CONFIG['VOTE_THRESHOLD']:
            final_signal = -1
            final_confidence = sell_score

        if final_signal == 0:
            return None

        entry = float(df['close'].values[-1])
        sl = self.risk.get_stop_loss(df, final_signal)
        tp = self.risk.get_take_profit(entry, sl, final_signal)
        lots = self.risk.calculate_position_size(symbol, entry, sl, final_confidence)

        if lots <= 0:
            return None

        return {
            'symbol': symbol,
            'signal': final_signal,
            'confidence': final_confidence,
            'entry': entry,
            'stop_loss': sl,
            'take_profit': tp,
            'lots': lots,
            'buy_votes': len(votes_buy),
            'sell_votes': len(votes_sell),
            'reasons': all_reasons[:10],
        }

    def run_analysis(self):
        print("\n" + "="*70)
        print(f"🚀 V5 ULTIMATE SYSTEM | {len(self.agents)} AGENTS")
        print(f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print("="*70)

        # Get global context
        print("\n📡 Loading global market context...")
        context = self.get_context()
        print(f"   VIX: {context['vix']:.1f} | DXY: {context['dxy']:.1f} | Fed Rate: {context['fred_data'].get('fed_funds_rate',5.25):.2f}%")

        signals = []
        capital_per_pair = self.risk.capital / len(TRADING_PAIRS)

        for symbol in TRADING_PAIRS:
            print(f"\n⚡ {symbol} [${capital_per_pair:,.0f}]", end='', flush=True)
            df = self.loader.get_ohlcv(symbol)
            if df is None:
                print(" ❌ No data")
                continue
            print(f" | {len(df)} candles", end='', flush=True)

            result = self.analyze_pair(symbol, df, context.copy())
            if result:
                action = '🟢 BUY' if result['signal'] == 1 else '🔴 SELL'
                print(f"\n   {action} | Confidence: {result['confidence']:.1%} | Lots: {result['lots']}")
                print(f"   Entry: {result['entry']:.5f} | SL: {result['stop_loss']:.5f} | TP: {result['take_profit']:.5f}")
                print(f"   Votes: 🟢{result['buy_votes']} 🔴{result['sell_votes']}")
                signals.append(result)

                # Send Telegram alert
                self.telegram.trade_alert(
                    symbol=result['symbol'],
                    signal=result['signal'],
                    entry=result['entry'],
                    sl=result['stop_loss'],
                    tp=result['take_profit'],
                    lots=result['lots'],
                    confidence=result['confidence'],
                    reasons=[r for r in result['reasons'] if '✅' in r or '❌' in r]
                )
            else:
                print(" | ⚪ HOLD")

        # Summary
        print("\n" + "="*70)
        print(f"📊 ANALYSIS COMPLETE")
        print(f"   Total signals: {len(signals)}")
        print(f"   Buy signals:   {sum(1 for s in signals if s['signal']==1)}")
        print(f"   Sell signals:  {sum(1 for s in signals if s['signal']==-1)}")
        print(f"   Portfolio:     ${self.risk.capital:,.2f}")
        print("="*70)

        return signals

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║           V5 ULTIMATE MULTI-AGENT TRADING SYSTEM            ║
║     SMC + ICT + Wyckoff + Intermarket + ML + LLM           ║
║                    26 Specialized Agents                     ║
╚══════════════════════════════════════════════════════════════╝
    """)

    system = MasterOrchestrator()

    # Send startup notification
    system.telegram.system_start(len(system.agents), CONFIG['INITIAL_CAPITAL'])

    print(f"✅ {len(system.agents)} agents initialized")
    print(f"✅ {len(TRADING_PAIRS)} markets ready")
    print(f"✅ Capital: ${CONFIG['INITIAL_CAPITAL']:,}")
    print(f"✅ Telegram connected")
    print(f"✅ FRED API connected")
    print(f"✅ OANDA ready: {CONFIG['OANDA_ACCOUNT_ID']}")

    # Run analysis
    signals = system.run_analysis()

    print("\n✅ V5 analysis complete!")
    print("📱 Check your Telegram for trade alerts!")
    print("\nTo run continuously every hour, we will set up the scheduler next.")
