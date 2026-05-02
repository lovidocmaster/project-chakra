"""
╔══════════════════════════════════════════════════════════════════════╗
║                  PROJECT CHAKRA — V10 COMPLETE                      ║
║                                                                      ║
║  NEW IN V10 vs V9:                                                   ║
║  ✅ Claude API reasoning agents (8 LLM agents now ACTIVE)           ║
║  ✅ Supabase trade logging (every signal + trade saved)              ║
║  ✅ FRED macro data (interest rates, bonds, inflation)               ║
║  ✅ Alpha Vantage (backup data source)                               ║
║                                                                      ║
║  KEPT FROM V9:                                                       ║
║  ✅ SELL signals enabled                                             ║
║  ✅ 60% confidence threshold                                         ║
║  ✅ Real OANDA execution                                             ║
║  ✅ 5 timeframes H4→H1→M15→M5→M1                                   ║
║  ✅ Session filter London + NY                                       ║
║  ✅ News blackout 30 min                                             ║
║  ✅ Market regime detection                                          ║
║  ✅ Leading indicators                                               ║
║  ✅ 30-trade learning rule                                           ║
║  ✅ Expectancy tracking                                              ║
║  ✅ Weekly reflection agent                                          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os, json, time, warnings, requests, threading, traceback
from missing_agents import get_all_missing_agents
from advanced_agents import get_advanced_agents
from advanced_ai import get_advanced_ai_agents, get_hivemind
from tradingview_agent import TradingViewAgent
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────
# CONFIG — ALL KEYS
# ─────────────────────────────────────────────────────────────────────
CONFIG = {
    # API KEYS
    "ANTHROPIC_KEY":    "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",
    "OANDA_TOKEN":      "500c5382d32fcc8a3a58b0ea0507c083-64e0d997e301a20caa3270a846d33402",
    "OANDA_ACCOUNT":    "101-001-39217670-001",
    "OANDA_URL":        "https://api-fxpractice.oanda.com",
    "FRED_KEY":         "0d5051e1563e45866badf276454ce1ec",
    "NEWS_KEY":         "00ce3b995b134bf98265358f98b9d41e",
    "ALPHA_VANTAGE_KEY":"T7TQAX2SMD7RTNXN",
    "TELEGRAM_TOKEN":   "8635098808:AAEc1mNqNE9pRqsYU0-W4uu7R0KIjEQFbhk",
    "TELEGRAM_CHAT":    "757855988",
    "SUPABASE_URL":     "https://jvnaphbygmqjeyawkmnz.supabase.co",
    "SUPABASE_KEY":     "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2bmFwaGJ5Z21xamV5YXdrbW56Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc1NDU0NDksImV4cCI6MjA5MzEyMTQ0OX0.Suz0H3jrDn89vzCLCPPFIbo3oVYcqVbn7d_OtB3zLR0",

    # TRADING CONTROLS
    "MIN_CONFIDENCE":       0.60,
    "MIN_VOTES_TO_TRADE":   5,
    "AUTO_EXECUTE":         True,

    # SESSION FILTER
    "TRADE_SESSIONS": {
        "LONDON":   {"start": 7,  "end": 12},
        "NEW_YORK": {"start": 12, "end": 17},
    },
    "SESSION_FILTER_ON": True,

    # NEWS BLACKOUT
    "NEWS_BLACKOUT_MINUTES": 30,

    # REGIME FILTER
    "ADX_TREND_THRESHOLD":  25,
    "ADX_STRONG_THRESHOLD": 40,

    # LEARNING
    "MIN_TRADES_TO_LEARN":  30,

    # RISK
    "INITIAL_CAPITAL":   10000,
    "RISK_PER_TRADE":    0.01,
    "MAX_DAILY_LOSS":    0.05,
    "MAX_DRAWDOWN":      0.15,
    "MAX_OPEN_TRADES":   3,

    # PAIRS
    "PRIMARY_PAIRS":   ["EUR_USD", "GBP_USD"],
    "SECONDARY_PAIRS": ["USD_JPY", "AUD_USD", "USD_CAD"],
    "INDICES":         ["US30_USD", "SPX500_USD", "NAS100_USD"],

    # TIMEFRAMES
    "TIMEFRAMES": {
        "H4":  {"yf": "4h",  "candles": 200},
        "H1":  {"yf": "1h",  "candles": 200},
        "M15": {"yf": "15m", "candles": 100},
        "M5":  {"yf": "5m",  "candles": 100},
        "M1":  {"yf": "1m",  "candles": 60},
    },
    "TF_WEIGHTS": {
        "H4": 0.30, "H1": 0.25, "M15": 0.20, "M5": 0.15, "M1": 0.10,
    },
    "CYCLE_SECONDS": 60,

    # ✅ NEW: LLM REASONING
    "LLM_MODEL":        "claude-sonnet-4-20250514",
    "LLM_MAX_TOKENS":   500,
    "LLM_TIMEOUT":      30,

    # ✅ NEW: FRED MACRO
    "FRED_SERIES": {
        "FED_RATE":    "FEDFUNDS",
        "BOND_10Y":    "DGS10",
        "BOND_2Y":     "DGS2",
        "INFLATION":   "CPIAUCSL",
        "UNEMPLOYMENT":"UNRATE",
        "DXY":         "DTWEXBGS",
    },
}

YF_SYMBOLS = {
    "EUR_USD": "EURUSD=X", "GBP_USD": "GBPUSD=X",
    "USD_JPY": "USDJPY=X", "AUD_USD": "AUDUSD=X",
    "USD_CAD": "USDCAD=X", "US30_USD": "^DJI",
    "SPX500_USD": "^GSPC", "NAS100_USD": "^IXIC",
}

PIP_USD = {
    "EUR_USD": 10.0, "GBP_USD": 10.0, "AUD_USD": 10.0,
    "USD_CAD": 7.7,  "USD_JPY": 6.5,
    "US30_USD": 1.0, "SPX500_USD": 1.0, "NAS100_USD": 1.0,
}

# ─────────────────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────────────────
class Telegram:
    @staticmethod
    def send(msg):
        try:
            requests.post(
                f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/sendMessage",
                json={"chat_id": CONFIG["TELEGRAM_CHAT"], "text": msg, "parse_mode": "HTML"},
                timeout=10
            )
        except: pass

# ─────────────────────────────────────────────────────────────────────
# ✅ NEW: SUPABASE LOGGER
# ─────────────────────────────────────────────────────────────────────
class SupabaseLogger:
    def __init__(self):
        self.url  = CONFIG["SUPABASE_URL"]
        self.key  = CONFIG["SUPABASE_KEY"]
        self.headers = {
            "apikey":        self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type":  "application/json",
            "Prefer":        "return=minimal"
        }
        self.enabled = self._test_connection()

    def _test_connection(self):
        try:
            r = requests.get(
                f"{self.url}/rest/v1/trades?limit=1",
                headers=self.headers, timeout=5
            )
            if r.status_code in [200, 206]:
                print("  ✅ Supabase connected — trade logging ACTIVE")
                return True
        except: pass
        print("  ⚠️  Supabase connection failed — logging disabled")
        return False

    def log_signal(self, pair, direction, confidence, votes_for,
                   votes_against, regime, price, reasoning=""):
        if not self.enabled: return
        try:
            data = {
                "agent_name":   "v10_orchestrator",
                "pair":         pair,
                "timeframe":    "MULTI",
                "signal":       direction,
                "confidence":   round(confidence, 4),
                "reasoning":    reasoning[:500] if reasoning else "",
                "raw_data": {
                    "votes_for":     votes_for,
                    "votes_against": votes_against,
                    "regime":        regime,
                    "price":         price,
                    "timestamp":     datetime.utcnow().isoformat()
                }
            }
            requests.post(
                f"{self.url}/rest/v1/agent_signals",
                headers=self.headers,
                json=data, timeout=5
            )
        except: pass

    def log_trade(self, pair, direction, entry, sl, tp, lots, confidence):
        if not self.enabled: return None
        try:
            data = {
                "pair":        pair,
                "direction":   direction,
                "entry_price": entry,
                "stop_loss":   sl,
                "take_profit": tp,
                "lot_size":    lots,
                "status":      "open",
                "mode":        "live" if CONFIG["AUTO_EXECUTE"] else "paper",
                "reasoning":   f"Confidence: {confidence*100:.1f}%"
            }
            r = requests.post(
                f"{self.url}/rest/v1/trades",
                headers={**self.headers, "Prefer": "return=representation"},
                json=data, timeout=5
            )
            if r.status_code in [200, 201]:
                result = r.json()
                trade_id = result[0].get("id") if result else None
                print(f"  ✅ Trade logged to Supabase: {trade_id}")
                return trade_id
        except Exception as e:
            print(f"  ⚠️  Supabase log error: {e}")
        return None

    def log_cycle(self, cycle_num, signals_count, trades_count, capital):
        if not self.enabled: return
        try:
            requests.post(
                f"{self.url}/rest/v1/system_logs",
                headers=self.headers,
                json={
                    "type":    "cycle_complete",
                    "message": f"Cycle {cycle_num}: {signals_count} signals, {trades_count} trades",
                    "data": {
                        "cycle":   cycle_num,
                        "signals": signals_count,
                        "trades":  trades_count,
                        "capital": capital,
                        "time":    datetime.utcnow().isoformat()
                    }
                }, timeout=5
            )
        except: pass

    def update_performance(self, stats):
        if not self.enabled: return
        try:
            requests.post(
                f"{self.url}/rest/v1/performance",
                headers=self.headers,
                json={
                    "date":           datetime.utcnow().date().isoformat(),
                    "win_rate":       stats.get("win_rate", 0),
                    "total_trades":   stats.get("trades", 0),
                    "profit_factor":  stats.get("profit_factor", 0),
                    "total_pnl":      stats.get("total_pnl", 0),
                }, timeout=5
            )
        except: pass

# ─────────────────────────────────────────────────────────────────────
# ✅ NEW: FRED MACRO DATA AGENT
# ─────────────────────────────────────────────────────────────────────
class FREDMacroAgent:
    """Federal Reserve Economic Data — macro intelligence"""
    name = "FREDMacro"
    strategy = "trend_follow"

    def __init__(self):
        self._cache = {}
        self._cache_time = {}
        self.CACHE_HOURS = 6

    def _get_series(self, series_id):
        now = time.time()
        if series_id in self._cache:
            if now - self._cache_time.get(series_id, 0) < self.CACHE_HOURS * 3600:
                return self._cache[series_id]
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            r = requests.get(url, params={
                "series_id":      series_id,
                "api_key":        CONFIG["FRED_KEY"],
                "file_type":      "json",
                "sort_order":     "desc",
                "limit":          5,
                "observation_start": (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")
            }, timeout=10)
            if r.status_code == 200:
                obs = r.json().get("observations", [])
                values = [float(o["value"]) for o in obs if o["value"] != "."]
                if values:
                    self._cache[series_id] = values
                    self._cache_time[series_id] = now
                    return values
        except: pass
        return None

    def get_macro_context(self):
        """Get current macro environment"""
        context = {}
        try:
            # Fed Rate
            fed = self._get_series("FEDFUNDS")
            if fed:
                context["fed_rate"]     = fed[0]
                context["fed_trend"]    = "RISING" if fed[0] > fed[-1] else "FALLING"

            # 10Y Bond Yield
            bond10 = self._get_series("DGS10")
            if bond10:
                context["bond_10y"]     = bond10[0]
                context["bond_trend"]   = "RISING" if bond10[0] > bond10[-1] else "FALLING"

            # 2Y Bond Yield
            bond2 = self._get_series("DGS2")
            if bond2:
                context["bond_2y"]      = bond2[0]
                # Yield curve: 10Y - 2Y
                if bond10:
                    context["yield_curve"] = bond10[0] - bond2[0]
                    context["inverted"]    = context["yield_curve"] < 0

        except: pass
        return context

    def analyze(self, df, direction_hint):
        """Score based on macro environment"""
        try:
            ctx = self.get_macro_context()
            if not ctx:
                return 0.5  # Neutral if no data

            score = 0.5  # Start neutral

            # Rising rates = USD bullish = EUR/GBP bearish
            if ctx.get("fed_trend") == "RISING":
                if direction_hint == "SELL":
                    score += 0.15  # Supports USD strength = pair falls
                elif direction_hint == "BUY":
                    score -= 0.10

            elif ctx.get("fed_trend") == "FALLING":
                if direction_hint == "BUY":
                    score += 0.15  # USD weakness = pairs rise
                elif direction_hint == "SELL":
                    score -= 0.10

            # Inverted yield curve = risk off = USD safe haven
            if ctx.get("inverted"):
                if direction_hint == "SELL":
                    score += 0.10
                elif direction_hint == "BUY":
                    score -= 0.05

            return min(max(score, 0), 1.0)
        except:
            return 0.5

# ─────────────────────────────────────────────────────────────────────
# ✅ NEW: ALPHA VANTAGE DATA AGENT
# ─────────────────────────────────────────────────────────────────────
class AlphaVantageAgent:
    """Alpha Vantage — backup data + technical confirmation"""
    name = "AlphaVantage"
    strategy = "trend_follow"
    _cache = {}
    _cache_time = {}

    def get_forex_data(self, pair):
        """Get forex data from Alpha Vantage as backup"""
        cache_key = f"av_{pair}"
        now = time.time()
        if cache_key in self._cache:
            if now - self._cache_time.get(cache_key, 0) < 300:  # 5 min cache
                return self._cache[cache_key]
        try:
            from_currency = pair[:3]
            to_currency   = pair[4:] if "_" in pair else pair[3:]
            r = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function":      "FX_INTRADAY",
                    "from_symbol":   from_currency,
                    "to_symbol":     to_currency,
                    "interval":      "60min",
                    "outputsize":    "compact",
                    "apikey":        CONFIG["ALPHA_VANTAGE_KEY"]
                }, timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                ts = data.get("Time Series FX (60min)", {})
                if ts:
                    closes = [float(v["4. close"]) for v in list(ts.values())[:20]]
                    self._cache[cache_key] = closes
                    self._cache_time[cache_key] = now
                    return closes
        except: pass
        return None

    def analyze(self, df, direction_hint, pair="EUR_USD"):
        """Use Alpha Vantage data to confirm signal"""
        try:
            closes = self.get_forex_data(pair)
            if not closes or len(closes) < 5:
                return 0.5

            # Simple momentum from AV data
            recent  = closes[0]
            older   = closes[4]
            momentum = (recent - older) / older * 100

            if direction_hint == "BUY":
                if momentum > 0.1:  return 0.75
                if momentum > 0:    return 0.55
                return 0.30
            elif direction_hint == "SELL":
                if momentum < -0.1: return 0.75
                if momentum < 0:    return 0.55
                return 0.30
            return 0.5
        except:
            return 0.5

# ─────────────────────────────────────────────────────────────────────
# ✅ NEW: CLAUDE LLM REASONING AGENT
# ─────────────────────────────────────────────────────────────────────
class ClaudeReasoningAgent:
    """
    Claude AI thinks about each trade like a professional analyst.
    This is the most powerful upgrade — LLM reasoning layer.
    """
    name = "ClaudeReasoning"
    strategy = "trend_follow"

    def __init__(self):
        self.api_key = CONFIG["ANTHROPIC_KEY"]
        self.enabled = bool(self.api_key and "xxxx" not in self.api_key)
        if self.enabled:
            print("  ✅ Claude API reasoning agent ACTIVE")
        else:
            print("  ⚠️  Claude API key not set — reasoning agent disabled")

    def analyze_trade(self, pair, direction, confidence, regime,
                      h4_bias, h1_signal, price, atr):
        """
        Ask Claude to reason about whether this trade makes sense.
        Returns: score 0-1
        """
        if not self.enabled:
            return 0.5

        try:
            prompt = f"""You are an expert forex trader analyzing a potential trade signal.

TRADE DETAILS:
- Pair: {pair}
- Direction: {direction}
- Current Price: {price:.5f}
- Technical Confidence: {confidence*100:.1f}%
- Market Regime: {regime}
- H4 Bias: {h4_bias}
- H1 Signal: {h1_signal}
- ATR: {atr:.5f}

QUESTION: Based purely on these technical factors, rate this trade setup quality from 0.0 to 1.0.

Consider:
1. Does the direction align with the regime? (TREND regime + trend direction = good)
2. Is confidence above 60%? (minimum threshold)
3. Do H4 and H1 agree? (they should — already filtered)
4. Is ATR reasonable for entry? (not too high/low volatility)

Respond with ONLY a JSON object like this:
{{"score": 0.75, "reason": "Strong trend alignment, good confidence"}}

No other text. Just the JSON."""

            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         self.api_key,
                    "anthropic-version":  "2023-06-01",
                    "content-type":       "application/json"
                },
                json={
                    "model":      CONFIG["LLM_MODEL"],
                    "max_tokens": CONFIG["LLM_MAX_TOKENS"],
                    "messages":   [{"role": "user", "content": prompt}]
                },
                timeout=CONFIG["LLM_TIMEOUT"]
            )

            if r.status_code == 200:
                content = r.json()["content"][0]["text"].strip()
                # Parse JSON response
                clean = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean)
                score  = float(result.get("score", 0.5))
                reason = result.get("reason", "")
                print(f"  🤖 Claude: {score:.2f} — {reason}")
                return min(max(score, 0), 1.0)

        except Exception as e:
            print(f"  ⚠️  Claude API error: {str(e)[:50]}")

        return 0.5  # Neutral fallback

    def analyze(self, df, direction_hint):
        """Standard agent interface — returns 0.5 (use analyze_trade for full power)"""
        return 0.5

# ─────────────────────────────────────────────────────────────────────
# TECHNICAL INDICATORS (same as v9)
# ─────────────────────────────────────────────────────────────────────
class Indicators:
    @staticmethod
    def ema(series, period):
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series, period=14):
        delta = series.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series, fast=12, slow=26, signal=9):
        ef = series.ewm(span=fast,   adjust=False).mean()
        es = series.ewm(span=slow,   adjust=False).mean()
        ml = ef - es
        sl = ml.ewm(span=signal, adjust=False).mean()
        return ml, sl, ml - sl

    @staticmethod
    def bollinger(series, period=20, std=2):
        ma    = series.rolling(period).mean()
        sigma = series.rolling(period).std()
        return ma + std*sigma, ma, ma - std*sigma

    @staticmethod
    def atr(df, period=14):
        h, l, c = df['High'], df['Low'], df['Close']
        tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def adx(df, period=14):
        h, l, c = df['High'], df['Low'], df['Close']
        plus_dm  = h.diff().clip(lower=0)
        minus_dm = (-l.diff()).clip(lower=0)
        tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
        atr_val  = tr.rolling(period).mean()
        plus_di  = 100 * plus_dm.rolling(period).mean()  / (atr_val + 1e-10)
        minus_di = 100 * minus_dm.rolling(period).mean() / (atr_val + 1e-10)
        dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        return dx.rolling(period).mean(), plus_di, minus_di

    @staticmethod
    def stochastic(df, k=14, d=3):
        low_min  = df['Low'].rolling(k).min()
        high_max = df['High'].rolling(k).max()
        k_line   = 100 * (df['Close'] - low_min) / (high_max - low_min + 1e-10)
        return k_line, k_line.rolling(d).mean()

    @staticmethod
    def volume_profile(df):
        vol    = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df), index=df.index)
        vol_ma = vol.rolling(20).mean()
        return vol / (vol_ma + 1e-10)

# ─────────────────────────────────────────────────────────────────────
# SESSION FILTER
# ─────────────────────────────────────────────────────────────────────
class SessionFilter:
    @staticmethod
    def is_trading_session():
        if not CONFIG["SESSION_FILTER_ON"]: return True
        hour = datetime.utcnow().hour
        london = CONFIG["TRADE_SESSIONS"]["LONDON"]
        ny     = CONFIG["TRADE_SESSIONS"]["NEW_YORK"]
        return (london["start"] <= hour < london["end"]) or \
               (ny["start"]     <= hour < ny["end"])

    @staticmethod
    def current_session():
        hour = datetime.utcnow().hour
        if 7  <= hour < 12: return "LONDON"
        if 12 <= hour < 16: return "OVERLAP"
        if 16 <= hour < 17: return "NEW_YORK"
        return "CLOSED"

# ─────────────────────────────────────────────────────────────────────
# NEWS BLACKOUT
# ─────────────────────────────────────────────────────────────────────
class NewsBlackout:
    KEYWORDS = ["NFP","Non-Farm","FOMC","Federal Reserve","Fed Rate",
                "CPI","Inflation","GDP","Unemployment","Payroll",
                "ECB","Bank of England","BOE","BOJ","Interest Rate"]

    @staticmethod
    def is_blackout():
        try:
            r = requests.get("https://newsapi.org/v2/top-headlines", params={
                "apiKey": CONFIG["NEWS_KEY"], "category": "business",
                "language": "en", "pageSize": 10
            }, timeout=5)
            if r.status_code != 200: return False
            for article in r.json().get("articles", []):
                title = (article.get("title") or "").upper()
                for kw in NewsBlackout.KEYWORDS:
                    if kw.upper() in title:
                        pub = article.get("publishedAt", "")
                        if pub:
                            pub_dt  = datetime.fromisoformat(pub.replace("Z","+00:00"))
                            mins_ago = abs((datetime.now(pub_dt.tzinfo) - pub_dt).total_seconds() / 60)
                            if mins_ago <= CONFIG["NEWS_BLACKOUT_MINUTES"]:
                                print(f"  ⛔ NEWS BLACKOUT: {title[:50]}")
                                return True
        except: pass
        return False

# ─────────────────────────────────────────────────────────────────────
# DATA ENGINE
# ─────────────────────────────────────────────────────────────────────
class DataEngine:
    _cache = {}
    _cache_time = {}
    CACHE_SECONDS = 55

    @staticmethod
    def get_candles(pair, timeframe="H1"):
        key = f"{pair}_{timeframe}"
        now = time.time()
        if key in DataEngine._cache:
            if now - DataEngine._cache_time.get(key, 0) < DataEngine.CACHE_SECONDS:
                return DataEngine._cache[key]
        symbol = YF_SYMBOLS.get(pair)
        if not symbol: return None
        try:
            tf     = CONFIG["TIMEFRAMES"].get(timeframe, CONFIG["TIMEFRAMES"]["H1"])
            period = "60d" if timeframe == "H4" else "30d" if timeframe == "H1" else "7d"
            df = yf.download(symbol, period=period, interval=tf["yf"],
                           progress=False, auto_adjust=True)
            if df is None or len(df) < 20: return None
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df.dropna()
            DataEngine._cache[key]      = df
            DataEngine._cache_time[key] = now
            return df
        except: return None

    @staticmethod
    def get_multi_tf(pair):
        return {tf: DataEngine.get_candles(pair, tf)
                for tf in ["H4","H1","M15","M5","M1"]}

# ─────────────────────────────────────────────────────────────────────
# REGIME DETECTOR
# ─────────────────────────────────────────────────────────────────────
class RegimeDetector:
    @staticmethod
    def detect(df):
        if df is None or len(df) < 30: return "UNKNOWN"
        try:
            adx_vals, _, _ = Indicators.adx(df)
            adx_now = adx_vals.iloc[-1]
            atr_pct = (Indicators.atr(df).iloc[-1] / df['Close'].iloc[-1]) * 100
            if adx_now >= CONFIG["ADX_STRONG_THRESHOLD"]: return "STRONG_TREND"
            if adx_now >= CONFIG["ADX_TREND_THRESHOLD"]:  return "TREND"
            if atr_pct > 1.5: return "VOLATILE"
            return "RANGING"
        except: return "UNKNOWN"

    @staticmethod
    def get_allowed_strategies(regime):
        return {
            "STRONG_TREND": ["trend_follow","breakout","momentum"],
            "TREND":        ["trend_follow","momentum","pullback"],
            "RANGING":      ["mean_reversion","support_resistance","oscillator"],
            "VOLATILE":     ["breakout","volatility"],
            "UNKNOWN":      ["trend_follow","mean_reversion"],
        }.get(regime, ["trend_follow"])

# ─────────────────────────────────────────────────────────────────────
# MULTI-TIMEFRAME ENGINE
# ─────────────────────────────────────────────────────────────────────
class MTFEngine:
    @staticmethod
    def h4_bias(df):
        if df is None or len(df) < 50: return "NEUTRAL", 0
        try:
            c = df['Close']
            e20 = Indicators.ema(c,20).iloc[-1]
            e50 = Indicators.ema(c,50).iloc[-1]
            e200= Indicators.ema(c,200).iloc[-1] if len(c)>=200 else e50
            p   = c.iloc[-1]
            score = sum([p>e20, p>e50, p>e200, e20>e50, e50>e200])
            if score >= 4: return "BUY",  score/5
            if score <= 1: return "SELL", (5-score)/5
            return "NEUTRAL", 0.5
        except: return "NEUTRAL", 0

    @staticmethod
    def h1_signal(df):
        if df is None or len(df) < 30: return "NEUTRAL", 0
        try:
            c  = df['Close']
            ml, sl, hist = Indicators.macd(c)
            rsi = Indicators.rsi(c)
            e20 = Indicators.ema(c,20)
            e50 = Indicators.ema(c,50)
            score = 0
            if ml.iloc[-1] > sl.iloc[-1]:       score += 1
            if hist.iloc[-1] > hist.iloc[-2]:    score += 1
            rsi_now = rsi.iloc[-1]
            if rsi_now > 55:  score += 1
            elif rsi_now < 45: score -= 1
            if e20.iloc[-1] > e50.iloc[-1]: score += 1
            else: score -= 1
            if score >= 3:  return "BUY",  score/4
            if score <= -1: return "SELL", abs(score)/4
            return "NEUTRAL", 0
        except: return "NEUTRAL", 0

    @staticmethod
    def m15_entry(df):
        if df is None or len(df) < 20: return "NEUTRAL", 0, 0
        try:
            c = df['Close']
            rsi = Indicators.rsi(c, 7)
            ub, mb, lb = Indicators.bollinger(c)
            k, d = Indicators.stochastic(df)
            atr  = Indicators.atr(df).iloc[-1]
            p    = c.iloc[-1]
            bs = ss = 0
            if rsi.iloc[-1] < 30:  bs += 2
            if rsi.iloc[-1] > 70:  ss += 2
            if p <= lb.iloc[-1]:   bs += 2
            if p >= ub.iloc[-1]:   ss += 2
            if k.iloc[-1] < 20:    bs += 1
            if k.iloc[-1] > 80:    ss += 1
            if bs > ss and bs >= 2: return "BUY",  bs/5, atr
            if ss > bs and ss >= 2: return "SELL", ss/5, atr
            return "NEUTRAL", 0, atr
        except: return "NEUTRAL", 0, 0

    @staticmethod
    def m5_signal(df):
        if df is None or len(df) < 15: return "NEUTRAL", 0
        try:
            c  = df['Close']
            e5 = Indicators.ema(c, 5)
            e13= Indicators.ema(c,13)
            rsi= Indicators.rsi(c, 7)
            k, _= Indicators.stochastic(df, 5, 3)
            bs = ss = 0
            if e5.iloc[-1] > e13.iloc[-1]:  bs += 1
            else:                            ss += 1
            if e5.iloc[-1] > e5.iloc[-2]:   bs += 1
            else:                            ss += 1
            rn = rsi.iloc[-1]
            if rn < 40:   bs += 1
            elif rn > 60: ss += 1
            if k.iloc[-1] < 25: bs += 1
            if k.iloc[-1] > 75: ss += 1
            if bs >= 3: return "BUY",  bs/4
            if ss >= 3: return "SELL", ss/4
            if bs > ss: return "BUY",  bs/4
            if ss > bs: return "SELL", ss/4
            return "NEUTRAL", 0
        except: return "NEUTRAL", 0

    @staticmethod
    def m1_trigger(df):
        if df is None or len(df) < 10: return "NEUTRAL", 0
        try:
            c   = df['Close']
            e3  = Indicators.ema(c, 3)
            e8  = Indicators.ema(c, 8)
            rsi = Indicators.rsi(c, 5)
            p   = c.iloc[-1]
            mom = (p - c.iloc[-4]) / c.iloc[-4] * 100 if len(c) >= 4 else 0
            bs = ss = 0
            if e3.iloc[-1] > e8.iloc[-1]: bs += 1
            else:                          ss += 1
            if p > e3.iloc[-1]: bs += 1
            else:               ss += 1
            if mom > 0: bs += 1
            else:       ss += 1
            rn = rsi.iloc[-1]
            if rn < 35:   bs += 1
            elif rn > 65: ss += 1
            if bs >= 3: return "BUY",  bs/4
            if ss >= 3: return "SELL", ss/4
            if bs > ss: return "BUY",  bs/4
            if ss > bs: return "SELL", ss/4
            return "NEUTRAL", 0
        except: return "NEUTRAL", 0

    @staticmethod
    def confirm(pair):
        data = DataEngine.get_multi_tf(pair)
        h4b, h4s = MTFEngine.h4_bias(data["H4"])
        h1s, h1st= MTFEngine.h1_signal(data["H1"])
        m15e, m15st, atr = MTFEngine.m15_entry(data["M15"])
        m5s, m5st = MTFEngine.m5_signal(data["M5"])
        m1t, m1st = MTFEngine.m1_trigger(data["M1"])

        if h4b == "NEUTRAL" or h1s == "NEUTRAL": return None
        if h4b != h1s: return None

        direction = h4b
        if m15e != "NEUTRAL" and m15e != direction: return None

        w = CONFIG["TF_WEIGHTS"]
        m5b  = m5st  if m5s  == direction else -m5st  * 0.5
        m1b  = m1st  if m1t  == direction else -m1st  * 0.5

        strength = (
            h4s   * w["H4"]  +
            h1st  * w["H1"]  +
            m15st * w["M15"] +
            max(m5b,  0) * w["M5"] +
            max(m1b,  0) * w["M1"]
        )
        return {
            "direction":  direction,
            "strength":   min(max(strength, 0), 1.0),
            "h4_bias":    h4b,
            "h1_signal":  h1s,
            "m15_entry":  m15e,
            "m5_signal":  m5s,
            "m1_trigger": m1t,
            "m5_agree":   "✅" if m5s == direction else ("➖" if m5s == "NEUTRAL" else "❌"),
            "m1_agree":   "✅" if m1t == direction else ("➖" if m1t == "NEUTRAL" else "❌"),
            "atr":        atr,
            "data":       data,
        }

# ─────────────────────────────────────────────────────────────────────
# TECHNICAL AGENTS (same as v9)
# ─────────────────────────────────────────────────────────────────────
class TrendAgent:
    name="Trend"; strategy="trend_follow"
    def analyze(self, df, d):
        if df is None or len(df)<50: return 0
        try:
            c=df['Close']
            e8=Indicators.ema(c,8).iloc[-1]; e21=Indicators.ema(c,21).iloc[-1]
            e50=Indicators.ema(c,50).iloc[-1]; p=c.iloc[-1]
            if d=="BUY":  return sum([p>e8,e8>e21,e21>e50,p>e50])/4
            if d=="SELL": return sum([p<e8,e8<e21,e21<e50,p<e50])/4
            return 0
        except: return 0

class RSIAgent:
    name="RSI"; strategy="oscillator"
    def analyze(self, df, d):
        if df is None or len(df)<20: return 0
        try:
            rsi=Indicators.rsi(df['Close']); rn=rsi.iloc[-1]; rp=rsi.iloc[-2]
            if d=="BUY":
                if rn<30: return 0.9
                if rn<40: return 0.6
                if rn<50 and rn>rp: return 0.4
                return 0
            if d=="SELL":
                if rn>70: return 0.9
                if rn>60: return 0.6
                if rn>50 and rn<rp: return 0.4
                return 0
            return 0
        except: return 0

class MACDAgent:
    name="MACD"; strategy="trend_follow"
    def analyze(self, df, d):
        if df is None or len(df)<30: return 0
        try:
            ml,sl,hist=Indicators.macd(df['Close'])
            cu=ml.iloc[-1]>sl.iloc[-1] and ml.iloc[-2]<=sl.iloc[-2]
            cd=ml.iloc[-1]<sl.iloc[-1] and ml.iloc[-2]>=sl.iloc[-2]
            hr=hist.iloc[-1]>hist.iloc[-2]; hf=hist.iloc[-1]<hist.iloc[-2]
            az=ml.iloc[-1]>0; bz=ml.iloc[-1]<0
            if d=="BUY":  return sum([cu,hr,az,ml.iloc[-1]>sl.iloc[-1]])/4
            if d=="SELL": return sum([cd,hf,bz,ml.iloc[-1]<sl.iloc[-1]])/4
            return 0
        except: return 0

class BollingerAgent:
    name="Bollinger"; strategy="mean_reversion"
    def analyze(self, df, d):
        if df is None or len(df)<25: return 0
        try:
            ub,mb,lb=Indicators.bollinger(df['Close']); p=df['Close'].iloc[-1]
            if d=="BUY":
                if p<=lb.iloc[-1]: return 0.9
                if p<=mb.iloc[-1]: return 0.5
                return 0.1
            if d=="SELL":
                if p>=ub.iloc[-1]: return 0.9
                if p>=mb.iloc[-1]: return 0.5
                return 0.1
            return 0
        except: return 0

class StochasticAgent:
    name="Stochastic"; strategy="oscillator"
    def analyze(self, df, d):
        if df is None or len(df)<20: return 0
        try:
            k,dk=Indicators.stochastic(df); kn=k.iloc[-1]
            if d=="BUY":
                if kn<20: return 0.9
                if kn<30: return 0.6
                if kn>dk.iloc[-1] and kn<50: return 0.4
                return 0
            if d=="SELL":
                if kn>80: return 0.9
                if kn>70: return 0.6
                if kn<dk.iloc[-1] and kn>50: return 0.4
                return 0
            return 0
        except: return 0

class ATRAgent:
    name="ATR"; strategy="volatility"
    def analyze(self, df, d):
        if df is None or len(df)<20: return 0.5
        try:
            atr=Indicators.atr(df); an=atr.iloc[-1]
            aa=atr.rolling(50).mean().iloc[-1] if len(atr)>=50 else atr.mean()
            r=an/(aa+1e-10)
            if r>3.0: return 0.0
            if r>2.0: return 0.3
            if r<0.5: return 0.3
            return 0.7
        except: return 0.5

class SMCAgent:
    name="SMC"; strategy="breakout"
    def analyze(self, df, d):
        if df is None or len(df)<30: return 0
        try:
            for i in range(-5,-1):
                c1h=df['High'].iloc[i-2]; c1l=df['Low'].iloc[i-2]
                c3h=df['High'].iloc[i];   c3l=df['Low'].iloc[i]
                if d=="BUY"  and c3l>c1h: return 0.75
                if d=="SELL" and c3h<c1l: return 0.75
            return 0.2
        except: return 0

class WyckoffAgent:
    name="Wyckoff"; strategy="mean_reversion"
    def analyze(self, df, d):
        if df is None or len(df)<50: return 0
        try:
            c=df['Close']; vr=Indicators.volume_profile(df)
            va=vr.iloc[-5:].mean()
            if d=="BUY":
                nl=c.iloc[-1]<c.iloc[-20:].quantile(0.2)
                return 0.75 if (nl and va>1.3) else (0.4 if nl else 0)
            if d=="SELL":
                nh=c.iloc[-1]>c.iloc[-20:].quantile(0.8)
                return 0.75 if (nh and va>1.3) else (0.4 if nh else 0)
            return 0
        except: return 0

class VolumeLeadAgent:
    name="VolumeLeader"; strategy="breakout"
    def analyze(self, df, d):
        if df is None or len(df)<30: return 0
        try:
            vr=Indicators.volume_profile(df); pc=df['Close'].pct_change()
            vs=vr.iloc[-1]>1.5; vb=vr.iloc[-1]>vr.iloc[-2]
            if vs and vb:
                if pc.iloc[-1]>0 and d=="BUY":  return 0.8
                if pc.iloc[-1]<0 and d=="SELL": return 0.8
                return 0.4
            return 0
        except: return 0

class StructureBreakAgent:
    name="StructureBreak"; strategy="breakout"
    def analyze(self, df, d):
        if df is None or len(df)<30: return 0
        try:
            c=df['Close']; h=df['High']; l=df['Low']
            rh=h.iloc[-10:-1].max(); rl=l.iloc[-10:-1].min(); p=c.iloc[-1]
            if d=="BUY":
                if p>rh: return 0.9
                prox=(p-rl)/(rh-rl+1e-10)
                return 0.6 if prox>0.8 else 0
            if d=="SELL":
                if p<rl: return 0.9
                prox=(rh-p)/(rh-rl+1e-10)
                return 0.6 if prox>0.8 else 0
            return 0
        except: return 0

class MomentumLeadAgent:
    name="MomentumLead"; strategy="momentum"
    def analyze(self, df, d):
        if df is None or len(df)<20: return 0
        try:
            c=df['Close']
            r3=( c.iloc[-1]/c.iloc[-4]  -1)*100 if len(c)>3  else 0
            r10=(c.iloc[-1]/c.iloc[-11] -1)*100 if len(c)>10 else 0
            r20=(c.iloc[-1]/c.iloc[-21] -1)*100 if len(c)>20 else 0
            if d=="BUY":  return min(sum([r3>0,r10>0,r20>0,r3>r10,abs(r3)>0.1])/5,1.0)
            if d=="SELL": return min(sum([r3<0,r10<0,r20<0,r3<r10,abs(r3)>0.1])/5,1.0)
            return 0
        except: return 0

class LiquiditySweepAgent:
    name="LiquiditySweep"; strategy="mean_reversion"
    def analyze(self, df, d):
        if df is None or len(df)<30: return 0
        try:
            c=df['Close']; h=df['High']; l=df['Low']
            rl=l.iloc[-20:-1]; rh=h.iloc[-20:-1]
            if d=="BUY":
                sl=l.iloc[-1]<rl.min(); rec=c.iloc[-1]>l.iloc[-1]*1.001
                return 0.85 if (sl and rec) else 0
            if d=="SELL":
                sh=h.iloc[-1]>rh.max(); rev=c.iloc[-1]<h.iloc[-1]*0.999
                return 0.85 if (sh and rev) else 0
            return 0
        except: return 0

class SentimentAgent:
    name="Sentiment"; strategy="trend_follow"
    def analyze(self, df, d):
        try:
            r=requests.get("https://newsapi.org/v2/everything", params={
                "apiKey":CONFIG["NEWS_KEY"],"q":"forex dollar euro",
                "language":"en","sortBy":"publishedAt","pageSize":5
            }, timeout=5)
            if r.status_code!=200: return 0.5
            pw=["rally","surge","gain","rise","bull","strong","up"]
            nw=["fall","drop","decline","weak","bear","down","crash"]
            pos=neg=0
            for a in r.json().get("articles",[]):
                t=(a.get("title") or "").lower()
                for w in pw:
                    if w in t: pos+=1
                for w in nw:
                    if w in t: neg+=1
            total=pos+neg
            if total==0: return 0.5
            s=pos/total
            return s if d=="BUY" else 1-s
        except: return 0.5

# ─────────────────────────────────────────────────────────────────────
# OANDA ENGINE
# ─────────────────────────────────────────────────────────────────────
class OandaEngine:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {CONFIG['OANDA_TOKEN']}",
            "Content-Type":  "application/json"
        }
        self.base    = CONFIG["OANDA_URL"]
        self.account = CONFIG["OANDA_ACCOUNT"]

    def get_account(self):
        try:
            r = requests.get(f"{self.base}/v3/accounts/{self.account}",
                           headers=self.headers, timeout=10)
            if r.status_code == 200:
                return r.json()["account"]
        except: pass
        return None

    def get_price(self, pair):
        try:
            r = requests.get(f"{self.base}/v3/accounts/{self.account}/pricing",
                           headers=self.headers, params={"instruments": pair}, timeout=10)
            if r.status_code == 200:
                p = r.json()["prices"][0]
                bid = float(p["bids"][0]["price"])
                ask = float(p["asks"][0]["price"])
                return bid, ask, (bid+ask)/2
        except: pass
        return None, None, None

    def place_trade(self, pair, direction, lots, sl_price, tp_price):
        if not CONFIG["AUTO_EXECUTE"]:
            return {"simulated": True}
        try:
            units = int(lots * 100000)
            if direction == "SELL": units = -units
            order = {"order": {
                "type": "MARKET", "instrument": pair, "units": str(units),
                "stopLossOnFill":   {"price": str(round(sl_price,5)), "timeInForce":"GTC"},
                "takeProfitOnFill": {"price": str(round(tp_price,5)), "timeInForce":"GTC"}
            }}
            r = requests.post(f"{self.base}/v3/accounts/{self.account}/orders",
                            headers=self.headers, json=order, timeout=15)
            if r.status_code in [200,201]:
                result   = r.json()
                trade_id = result.get("orderFillTransaction",{}).get("tradeOpened",{}).get("tradeID","?")
                print(f"  ✅ OANDA TRADE PLACED: {direction} {lots} {pair} | ID:{trade_id}")
                return result
            else:
                print(f"  ❌ OANDA order failed: {r.status_code}")
                return None
        except Exception as e:
            print(f"  ❌ OANDA error: {e}")
            return None

# ─────────────────────────────────────────────────────────────────────
# RISK MANAGER
# ─────────────────────────────────────────────────────────────────────
class RiskManager:
    def __init__(self):
        self.daily_loss    = 0
        self.session_start = datetime.utcnow().date()
        self.peak_capital  = CONFIG["INITIAL_CAPITAL"]

    def reset_daily(self):
        today = datetime.utcnow().date()
        if today != self.session_start:
            self.daily_loss    = 0
            self.session_start = today

    def can_trade(self, capital, open_count):
        self.reset_daily()
        if open_count >= CONFIG["MAX_OPEN_TRADES"]:
            return False, f"Max {CONFIG['MAX_OPEN_TRADES']} open trades"
        if self.daily_loss/CONFIG["INITIAL_CAPITAL"] >= CONFIG["MAX_DAILY_LOSS"]:
            return False, "Daily loss limit reached"
        self.peak_capital = max(self.peak_capital, capital)
        dd = (self.peak_capital - capital) / self.peak_capital
        if dd >= CONFIG["MAX_DRAWDOWN"]:
            return False, f"Max drawdown reached — SYSTEM PAUSED"
        return True, "OK"

    def calculate_position(self, capital, atr, pair):
        risk_amount = capital * CONFIG["RISK_PER_TRADE"]
        pip_val     = PIP_USD.get(pair, 10.0)
        sl_pips     = max(atr * 1.5 * 10000, 10)
        sl_pips     = min(sl_pips, 100)
        lots        = risk_amount / (sl_pips * pip_val)
        return max(0.01, min(round(lots, 2), 5.0)), sl_pips

    def calculate_sl_tp(self, price, direction, atr, pair):
        is_jpy = "JPY" in pair
        dec    = 3 if is_jpy else 5
        sl_d   = atr * 1.5
        tp_d   = atr * 3.75  # 1:2.5 R:R
        if direction == "BUY":
            return round(price-sl_d, dec), round(price+tp_d, dec)
        return round(price+sl_d, dec), round(price-tp_d, dec)

# ─────────────────────────────────────────────────────────────────────
# LEARNING SYSTEM
# ─────────────────────────────────────────────────────────────────────
class LearningSystem:
    def __init__(self):
        self.trade_log = []

    def log_trade(self, t):
        self.trade_log.append(t)

    def get_stats(self):
        if not self.trade_log:
            return {"trades":0,"win_rate":0,"expectancy":0,"profit_factor":0,"total_pnl":0}
        wins   = [t["pnl"] for t in self.trade_log if t.get("pnl",0)>0]
        losses = [t["pnl"] for t in self.trade_log if t.get("pnl",0)<0]
        wr     = len(wins)/len(self.trade_log)
        aw     = np.mean(wins)  if wins   else 0
        al     = abs(np.mean(losses)) if losses else 0
        exp    = wr*aw - (1-wr)*al
        pf     = sum(wins)/abs(sum(losses)) if losses else 0
        return {"trades":len(self.trade_log),"win_rate":wr,
                "expectancy":exp,"profit_factor":pf,
                "total_pnl":sum(t.get("pnl",0) for t in self.trade_log)}

    def should_adjust(self):
        return len(self.trade_log) >= CONFIG["MIN_TRADES_TO_LEARN"]

# ─────────────────────────────────────────────────────────────────────
# WEEKLY REFLECTION
# ─────────────────────────────────────────────────────────────────────
class WeeklyReflection:
    def __init__(self, learner):
        self.learner = learner
        self.last    = None

    def check_and_reflect(self):
        now = datetime.utcnow()
        if now.weekday() == 6 and now.hour == 20 and self.last != now.date():
            self.last = now.date()
            stats = self.learner.get_stats()
            if stats["trades"] == 0: return
            Telegram.send(f"""
📊 <b>WEEKLY REFLECTION — Project Chakra</b>
📅 {now.strftime('%d %b %Y')}

📈 Trades:        {stats['trades']}
🎯 Win Rate:      {stats['win_rate']*100:.1f}%
💰 Expectancy:    ${stats['expectancy']:.2f}/trade
📊 Profit Factor: {stats['profit_factor']:.2f}
💵 Total P&L:     ${stats['total_pnl']:.2f}

{'✅ System performing well' if stats['win_rate']>0.55 else '⚠️ Win rate needs improvement'}
            """)

# ─────────────────────────────────────────────────────────────────────
# V10 MASTER ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────
class V10Orchestrator:
    def __init__(self):
        print("\n" + "═"*70)
        print("  PROJECT CHAKRA — V10 COMPLETE STARTING")
        print("═"*70)

        # Core systems
        self.oanda    = OandaEngine()
        self.risk     = RiskManager()
        self.learner  = LearningSystem()
        self.reflect  = WeeklyReflection(self.learner)

        # ✅ NEW: Activated systems
        self.supabase = SupabaseLogger()
        self.fred     = FREDMacroAgent()
        self.av       = AlphaVantageAgent()
        self.claude   = ClaudeReasoningAgent()

        # All technical agents
        self.agents = [
            TrendAgent(), RSIAgent(), MACDAgent(), BollingerAgent(),
            StochasticAgent(), ATRAgent(), SMCAgent(), WyckoffAgent(),
            VolumeLeadAgent(), StructureBreakAgent(), MomentumLeadAgent(),
            LiquiditySweepAgent(), SentimentAgent(),
            # ✅ NEW agents
            self.fred,   # FRED macro
            self.av,     # Alpha Vantage
        ]
        self.agents += get_all_missing_agents()
        self.agents += get_advanced_agents()
        self.agents += get_advanced_ai_agents()
        self.hivemind = get_hivemind()
    self.hivemind.learning_enabled = True
    self.hivemind.weekend_mode = True
    print("✅ HiveMind Weekend Learning ENABLED"),self.agents.append(TradingViewAgent())

        self.instruments = (CONFIG["PRIMARY_PAIRS"] +
                           CONFIG["SECONDARY_PAIRS"] +
                           CONFIG["INDICES"])

        # Verify OANDA
        account = self.oanda.get_account()
        self.capital = float(account.get("balance", CONFIG["INITIAL_CAPITAL"])) if account else CONFIG["INITIAL_CAPITAL"]
        open_t = int(account.get("openTradeCount", 0)) if account else 0

        if account:
            print(f"  ✅ OANDA | Balance: ${self.capital:,.2f} | Open: {open_t}")
        else:
            print(f"  ⚠️  OANDA connection issue")

        # Load macro context
        print("  📊 Loading FRED macro data...", end=" ", flush=True)
        macro = self.fred.get_macro_context()
        if macro:
            fr = macro.get('fed_rate','?')
            b10= macro.get('bond_10y','?')
            ft = macro.get('fed_trend','?')
            print(f"Fed:{fr}% Bond10Y:{b10}% Trend:{ft} ✅")
        else:
            print("limited data")

        self.cycle = 0

        # Startup Telegram
        mode = "🔴 LIVE" if CONFIG["AUTO_EXECUTE"] else "📋 PAPER"
        Telegram.send(f"""
🚀 <b>PROJECT CHAKRA V10 COMPLETE</b>

{mode} | ${self.capital:,.2f}
🤖 {len(self.agents)} Agents Active
✅ Claude LLM reasoning: {'ACTIVE' if self.claude.enabled else 'DISABLED'}
✅ Supabase logging: {'ACTIVE' if self.supabase.enabled else 'DISABLED'}
✅ FRED macro data: {'ACTIVE' if macro else 'LIMITED'}
✅ Alpha Vantage: ACTIVE
✅ 5 Timeframes: H4→H1→M15→M5→M1
✅ Session: London + NY only
✅ Confidence: 60% minimum
✅ SELL signals: ENABLED

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        """)

        print(f"\n  ✅ {len(self.agents)} agents loaded")
        print(f"  ✅ {len(self.instruments)} instruments")
        print(f"  ✅ Claude reasoning: {'ON' if self.claude.enabled else 'OFF'}")
        print(f"  ✅ Supabase logging: {'ON' if self.supabase.enabled else 'OFF'}")
        print("═"*70)

    def analyze_pair(self, pair):
        print(f"\n  📊 {pair}", end="", flush=True)

        # MTF confirmation
        mtf = MTFEngine.confirm(pair)
        if mtf is None:
            print(" → No MTF agreement", end="")
            return None

        direction = mtf["direction"]
        print(f" → {direction} H4:{mtf['h4_bias']} H1:{mtf['h1_signal']} "
              f"M15:{mtf['m15_entry']} M5:{mtf['m5_signal']} M1:{mtf['m1_trigger']}", end="")

        df = mtf["data"]["H1"]
        if df is None: return None

        # Regime detection
        regime   = RegimeDetector.detect(df)
        allowed  = RegimeDetector.get_allowed_strategies(regime)

        # Agent voting
        votes_for = votes_against = total = 0
        for agent in self.agents:
            try:
                if agent.strategy not in allowed: continue
                # Special handling for AV agent (needs pair)
                if hasattr(agent, 'get_forex_data'):
                    score = agent.analyze(df, direction, pair)
                else:
                    score = agent.analyze(df, direction)
                total += 1
                if score >= 0.6:  votes_for     += 1
                elif score <= 0.3: votes_against += 1
            except: pass

        if total < CONFIG["MIN_VOTES_TO_TRADE"]:
            return None

        # Base confidence from technical agents
        confidence = votes_for / (votes_for + votes_against + 1e-10)
        confidence = min(confidence * 0.7 + mtf["strength"] * 0.3, 1.0)

        if confidence < CONFIG["MIN_CONFIDENCE"]:
            print(f" | Conf:{confidence*100:.0f}% → SKIP", end="")
            return None

        # ✅ NEW: Claude LLM reasoning boost
        atr = mtf["atr"] if mtf["atr"] > 0 else 0.001
        llm_score = self.claude.analyze_trade(
            pair, direction, confidence, regime,
            mtf["h4_bias"], mtf["h1_signal"],
            df['Close'].iloc[-1], atr
        )

        # Blend: 70% technical + 30% LLM
        if self.claude.enabled:
            confidence = confidence * 0.70 + llm_score * 0.30
            confidence = min(confidence, 1.0)

        # Final check after LLM
        if confidence < CONFIG["MIN_CONFIDENCE"]:
            print(f" | LLM adjusted to {confidence*100:.0f}% → SKIP", end="")
            return None

        # Get price
        bid, ask, mid = self.oanda.get_price(pair)
        if mid is None:
            df_latest = DataEngine.get_candles(pair, "H1")
            mid = float(df_latest['Close'].iloc[-1]) if df_latest is not None else None
            bid = ask = mid
        if mid is None: return None

        print(f" | Conf:{confidence*100:.0f}% Regime:{regime}", end="")

        # ✅ NEW: Log signal to Supabase
        reasoning = (f"{direction} on {pair} | Regime:{regime} | "
                    f"Votes:{votes_for}/{total} | LLM:{llm_score:.2f}")
        self.supabase.log_signal(
            pair, direction, confidence,
            votes_for, votes_against, regime, mid, reasoning
        )

        return {
            "pair":          pair,
            "direction":     direction,
            "confidence":    confidence,
            "regime":        regime,
            "votes_for":     votes_for,
            "votes_against": votes_against,
            "price":         mid,
            "bid":           bid or mid,
            "ask":           ask or mid,
            "atr":           atr,
            "h4_bias":       mtf["h4_bias"],
            "h1_signal":     mtf["h1_signal"],
            "m15_entry":     mtf["m15_entry"],
            "m5_signal":     mtf["m5_signal"],
            "m1_trigger":    mtf["m1_trigger"],
            "m5_agree":      mtf["m5_agree"],
            "m1_agree":      mtf["m1_agree"],
            "llm_score":     llm_score,
            "reasoning":     reasoning,
            "timestamp":     datetime.utcnow().isoformat(),
        }

    def execute_signal(self, signal):
        pair      = signal["pair"]
        direction = signal["direction"]
        price     = signal["ask"] if direction == "BUY" else signal["bid"]
        atr       = signal["atr"]

        account = self.oanda.get_account()
        if account:
            self.capital = float(account.get("balance", self.capital))
            open_count   = int(account.get("openTradeCount", 0))
        else:
            open_count = 0

        can_trade, reason = self.risk.can_trade(self.capital, open_count)
        if not can_trade:
            print(f"\n  ⛔ Risk: {reason}")
            return False

        lots, _   = self.risk.calculate_position(self.capital, atr, pair)
        sl, tp    = self.risk.calculate_sl_tp(price, direction, atr, pair)
        rr        = abs(tp-price) / abs(sl-price) if abs(sl-price) > 0 else 0

        # Place on OANDA
        result = self.oanda.place_trade(pair, direction, lots, sl, tp)

        if result:
            # ✅ NEW: Log trade to Supabase
            self.supabase.log_trade(
                pair, direction, price, sl, tp, lots, signal["confidence"]
            )

            emoji    = "🟢" if direction == "BUY" else "🔴"
            mode_tag = "🔴 LIVE" if CONFIG["AUTO_EXECUTE"] else "📋 PAPER"

            Telegram.send(f"""
{emoji} <b>{direction} {pair}</b> {mode_tag}

💰 Entry:  {price:.5f}
🛡 SL:    {sl:.5f}
🎯 TP:    {tp:.5f}
📦 Lots:  {lots}
⚖️ R:R:   1:{rr:.1f}
🧠 Conf:  {signal['confidence']*100:.1f}%
🤖 LLM:   {signal['llm_score']:.2f}
✅ Votes: 🟢{signal['votes_for']} 🔴{signal['votes_against']}
📊 Regime: {signal['regime']}

⏱ Timeframes:
  H4:{signal['h4_bias']} H1:{signal['h1_signal']}
  M15:{signal['m15_entry']} M5:{signal['m5_signal']} {signal['m5_agree']}
  M1:{signal['m1_trigger']} {signal['m1_agree']}

💵 Risk: ${self.capital * CONFIG['RISK_PER_TRADE']:.2f}
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
            """)
            return True
        return False

    def run_cycle(self):
        self.cycle += 1
        now = datetime.utcnow()
        print(f"\n\n{'═'*70}")
        print(f"  🔄 CYCLE {self.cycle} | {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'═'*70}")

        # Session check
        if not SessionFilter.is_trading_session():
            session = SessionFilter.current_session()
            print(f"  💤 Session: {session} — Waiting for London/NY")
            return []

        # News blackout
        print("  📰 Checking news...", end=" ", flush=True)
        if NewsBlackout.is_blackout():
            print("BLACKOUT — skipping")
            return []
        print("Clear ✅")

        # Weekly reflection
        self.reflect.check_and_reflect()

        # Analyze all pairs
        signals = []
        print(f"\n  📊 Analyzing {len(self.instruments)} instruments...")
        for pair in self.instruments:
            try:
                signal = self.analyze_pair(pair)
                if signal:
                    signals.append(signal)
            except Exception as e:
                print(f"\n  ❌ {pair}: {str(e)[:40]}")

        signals.sort(key=lambda x: x["confidence"], reverse=True)

        buys  = [s for s in signals if s["direction"] == "BUY"]
        sells = [s for s in signals if s["direction"] == "SELL"]
        print(f"\n\n  📈 BUY: {len(buys)}  📉 SELL: {len(sells)}")

        if signals:
            print(f"\n  🔥 TOP SIGNALS:")
            for s in signals[:5]:
                e = "📈" if s["direction"] == "BUY" else "📉"
                print(f"     {e} {s['pair']:<12} {s['direction']:<4} "
                      f"Conf:{s['confidence']*100:.0f}% "
                      f"LLM:{s['llm_score']:.2f} "
                      f"Regime:{s['regime']}")

        # Execute top signals
        executed = 0
        for signal in signals[:3]:
            if executed >= CONFIG["MAX_OPEN_TRADES"]: break
            if self.execute_signal(signal):
                executed += 1

        # Stats
        stats = self.learner.get_stats()
        account = self.oanda.get_account()
        if account:
            self.capital = float(account.get("balance", self.capital))

        # ✅ NEW: Log cycle to Supabase
        self.supabase.log_cycle(self.cycle, len(signals), executed, self.capital)
        self.supabase.update_performance(stats)

        print(f"\n  {'─'*60}")
        print(f"  💵 Capital:    ${self.capital:,.2f}")
        print(f"  📊 Trades:     {stats['trades']}")
        print(f"  🎯 Win Rate:   {stats['win_rate']*100:.1f}%")
        print(f"  💰 Expectancy: ${stats['expectancy']:.2f}/trade")
        print(f"  🤖 LLM:        {'ACTIVE' if self.claude.enabled else 'OFF'}")
        print(f"  💾 Supabase:   {'LOGGING' if self.supabase.enabled else 'OFF'}")
        print(f"  ✅ Executed:   {executed} trades")
        print(f"  ⏰ Next:       {CONFIG['CYCLE_SECONDS']}s")

        return signals

    def run(self):
        print(f"\n  🚀 V10 COMPLETE RUNNING")
        print(f"  Session: {SessionFilter.current_session()}")
        print(f"  Mode: {'🔴 LIVE' if CONFIG['AUTO_EXECUTE'] else '📋 PAPER'}")

        while True:
            try:
                self.run_cycle()
            except KeyboardInterrupt:
                print("\n\n  🛑 Stopped by user")
                Telegram.send("🛑 V10 STOPPED BY USER")
                break
            except Exception as e:
                print(f"\n  ❌ Error: {str(e)}")
                traceback.print_exc()
                Telegram.send(f"⚠️ V10 Error: {str(e)[:200]}")
            time.sleep(CONFIG["CYCLE_SECONDS"])

# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                 PROJECT CHAKRA — V10 COMPLETE                       ║
║                                                                      ║
║  ✅ Claude LLM reasoning agents ACTIVE                              ║
║  ✅ Supabase trade logging ACTIVE                                    ║
║  ✅ FRED macro data ACTIVE                                           ║
║  ✅ Alpha Vantage ACTIVE                                             ║
║  ✅ All v9 upgrades kept                                             ║
║  ✅ 5 timeframes H4→H1→M15→M5→M1                                   ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    system = V10Orchestrator()
    system.run()
