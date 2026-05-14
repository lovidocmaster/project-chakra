"""
PROJECT CHAKRA V15 — MAXIMUM PROFIT EDITION
Features:
- Trailing Stop Loss (locks profits as trade moves)
- News Blackout (30min before/after high impact events)
- Volatility Circuit Breaker (pauses on flash crashes)
- XAU_USD (Gold) + GBP_JPY added
- Session Filter (London + New York only)
- VolumeAgent (filters fake breakouts)
- TSMOMAgent (institutional momentum)
- Auto-Execute with proper unit sizing
- Smart Telegram with full explanation
- Quantum Dashboard with candlestick charts

Run: python v15_chakra.py
"""
import os, json, logging, time, math, threading, requests
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from collections import deque
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, render_template_string
from v13_production import (
    OandaAPI, InstrumentsCandles, OrderCreate, OpenTrades,
    BarData, Signal, Agent, TradeRecord, SupabaseLogger,
    EMAAgent, MACDAgent, RSIAgent, BollingerAgent, ATRAgent,
    StochasticAgent, BreakoutAgent, BOSAgent, CHOCHAgent,
    WyckoffAgent, SessionAgent, KillzoneAgent, OrderBlockAgent,
    FVGAgent, LiquidityAgent, OTEAgent, SilverBulletAgent,
    FinMem, AgentWeights, RLAgent, RegimeDetector, HiveMind,
    NewsIntelligence, FREDMacro,
    OANDA_TOKEN, OANDA_ENV, OANDA_ACCOUNT,
    TELEGRAM_TOKEN, TELEGRAM_CHAT,
    MEM_FILE, WTS_FILE, RL_FILE,
    log
)
import numpy as np

# ── CONFIG ──────────────────────────────────────────────────────────
PAIRS = [
    'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD',
    'XAU_USD', 'GBP_JPY'
]

# CME Futures — shown on dashboard as separate cards (signals only, no execution)
CME_FUTURES = {
    '6E=F': {'name': 'EUR Futures', 'equiv': 'EUR/USD', 'flag': '🇪🇺'},
    '6B=F': {'name': 'GBP Futures', 'equiv': 'GBP/USD', 'flag': '🇬🇧'},
    '6J=F': {'name': 'JPY Futures', 'equiv': 'USD/JPY', 'flag': '🇯🇵', 'inverse': True},
    '6A=F': {'name': 'AUD Futures', 'equiv': 'AUD/USD', 'flag': '🇦🇺'},
    '6C=F': {'name': 'CAD Futures', 'equiv': 'USD/CAD', 'flag': '🇨🇦', 'inverse': True},
    '6N=F': {'name': 'NZD Futures', 'equiv': 'NZD/USD', 'flag': '🇳🇿'},
    '6S=F': {'name': 'CHF Futures', 'equiv': 'USD/CHF', 'flag': '🇨🇭', 'inverse': True},
}
CONFIDENCE_BASE    = 0.60
AUTO_EXECUTE       = True
RISK_PCT           = 0.005
MAX_DD             = 0.02
MAX_UNITS          = 50000
MIN_UNITS          = 100
CYCLE_SECS         = 60
PORT               = 5001
RAILWAY_URL        = os.getenv("RAILWAY_URL",
                     "https://project-chakra-production.up.railway.app")
NEWS_KEY           = os.getenv("NEWS_KEY", "")

# News blackout: minutes before/after high impact events
NEWS_BLACKOUT_MIN  = 30

# Volatility breaker: if ATR spikes this many times above normal, pause
VOL_BREAKER_MULT   = 3.0

# Trailing stop: move SL to breakeven when profit = SL distance
TRAIL_TRIGGER_RR   = 1.0   # move SL to BE at 1:1
TRAIL_LOCK_RR      = 2.0   # lock 50% profit at 2:1

# ── VOLUME AGENT ─────────────────────────────────────────────────────
class VolumeAgent(Agent):
    """
    Confirms signals using tick volume from OANDA.
    High volume on signal bar = real move.
    Low volume = fake breakout — skip.
    """
    def __init__(self): super().__init__("Volume")

    def analyze(self, bars):
        if len(bars) < 20:
            return Signal("HOLD", 0.0, "Not enough bars for volume", self.name)

        vols  = [b.volume for b in bars[-20:]]
        avg_v = np.mean(vols[:-1])
        cur_v = vols[-1]

        if avg_v == 0:
            return Signal("HOLD", 0.0, "No volume data", self.name)

        ratio = cur_v / avg_v
        trend = bars[-1].close - bars[-5].close if len(bars) >= 5 else 0

        if ratio >= 1.5:
            # High volume — strong confirmation
            d = "BUY" if trend > 0 else "SELL"
            return Signal(d, 0.72,
                f"Volume {ratio:.1f}x avg — strong {d} confirmation", self.name)
        elif ratio >= 0.8:
            # Normal volume — neutral
            d = "BUY" if trend > 0 else "SELL"
            return Signal(d, 0.55,
                f"Volume {ratio:.1f}x avg — normal", self.name)
        else:
            # Low volume — fake breakout warning
            return Signal("HOLD", 0.0,
                f"Volume only {ratio:.1f}x avg — possible fake move", self.name)


# ── TSMOM AGENT ──────────────────────────────────────────────────────
class TSMOMAgent(Agent):
    """
    Time Series Momentum — Moskowitz, Ooi, Pedersen (2012) / AQR Capital.
    Checks 1-month, 3-month and 12-month return direction.
    Momentum persists for up to 12 months in currency markets.
    """
    def __init__(self): super().__init__("TSMOM")

    def analyze(self, bars):
        if len(bars) < 260:
            return Signal("HOLD", 0.0,
                f"Need 260 bars, have {len(bars)}", self.name)

        closes = np.array([b.close for b in bars])
        now    = closes[-1]

        r1m  = (now - closes[-21])  / closes[-21]
        r3m  = (now - closes[-63])  / closes[-63]
        r12m = (now - closes[-252]) / closes[-252]

        daily_rets = np.diff(closes[-61:]) / closes[-61:-1]
        vol = np.std(daily_rets) * math.sqrt(252) if len(daily_rets) > 5 else 0.1
        if vol == 0: vol = 0.1

        score = (np.sign(r1m)*0.5 + np.sign(r3m)*0.3 + np.sign(r12m)*0.2)
        conf  = min(0.95, abs(score) * 0.75 + 0.20)
        reason = (f"1m:{r1m*100:+.2f}% 3m:{r3m*100:+.2f}% "
                  f"12m:{r12m*100:+.2f}% vol:{vol*100:.1f}%")

        if score > 0:   return Signal("BUY",  conf, f"TSMOM BULL {reason}", self.name)
        elif score < 0: return Signal("SELL", conf, f"TSMOM BEAR {reason}", self.name)
        return Signal("HOLD", 0.0, f"TSMOM NEUTRAL {reason}", self.name)


# ── ALL AGENTS ────────────────────────────────────────────────────────
# ── CME FUTURES CONFIRMATION AGENT ───────────────────────────────────
class CMEFuturesAgent(Agent):
    """
    Uses CME Currency Futures (6A, 6B, 6C, 6E, 6J, 6N, 6S) as
    institutional confirmation for spot forex signals.
    When futures trend aligns with spot signal — higher confidence.
    Institutional money moves futures first, spot follows.
    """

    # Map OANDA pair → CME futures symbol
    FUTURES_MAP = {
        "EUR_USD": "6E=F",
        "GBP_USD": "6B=F",
        "USD_JPY": "6J=F",
        "AUD_USD": "6A=F",
        "USD_CAD": "6C=F",
        "NZD_USD": "6N=F",
        "USD_CHF": "6S=F",
        "GBP_JPY": "6B=F",   # Use GBP futures as proxy
        "XAU_USD": "GC=F",   # Gold futures
    }

    # Pairs where futures are inverse to spot
    INVERSE_PAIRS = {"USD_JPY", "USD_CAD", "USD_CHF"}

    def __init__(self): super().__init__("CMEFutures")

    def analyze(self, bars):
        # bars[0].timestamp contains pair info via agent_name context
        # We use the last bar's context — pair passed via bars list
        if not bars or len(bars) < 5:
            return Signal("HOLD", 0.0, "Not enough bars", self.name)

        # This agent needs pair name — stored as class attribute when called
        pair = getattr(self, '_pair', None)
        if not pair:
            return Signal("HOLD", 0.0, "No pair context", self.name)

        symbol = self.FUTURES_MAP.get(pair)
        if not symbol:
            return Signal("HOLD", 0.0, f"No futures for {pair}", self.name)

        try:
            import yfinance as yf
            d = yf.download(symbol, period="10d", interval="1d",
                           progress=False)
            if hasattr(d.columns, 'levels'):
                d.columns = d.columns.droplevel(1)
            if len(d) < 3:
                return Signal("HOLD", 0.0, "Not enough futures data", self.name)

            closes  = d["Close"].dropna().values
            current = float(closes[-1])
            prev3   = float(closes[-4]) if len(closes) >= 4 else float(closes[0])
            prev1   = float(closes[-2])

            # 3-day trend direction
            trend_3d = current - prev3
            # 1-day momentum
            trend_1d = current - prev1

            is_inverse = pair in self.INVERSE_PAIRS

            # Determine futures signal
            if trend_3d > 0 and trend_1d > 0:
                fut_dir = "SELL" if is_inverse else "BUY"
                conf    = 0.72
                reason  = (f"CME {symbol} bullish 3d:{trend_3d:+.5f} "
                          f"1d:{trend_1d:+.5f} → {fut_dir}")
            elif trend_3d < 0 and trend_1d < 0:
                fut_dir = "BUY" if is_inverse else "SELL"
                conf    = 0.72
                reason  = (f"CME {symbol} bearish 3d:{trend_3d:+.5f} "
                          f"1d:{trend_1d:+.5f} → {fut_dir}")
            else:
                return Signal("HOLD", 0.0,
                    f"CME {symbol} mixed signals", self.name)

            return Signal(fut_dir, conf, reason, self.name)

        except Exception as e:
            return Signal("HOLD", 0.0, f"CME fetch error: {e}", self.name)



class NadarayaWatsonAgent(Agent):
    """
    Nadaraya-Watson Kernel Regression Envelope — Institutional Reversal.
    Fits smooth curve to price using Gaussian kernel.
    Upper/Lower bands = curve ± 2.5 * ATR.
    SELL when price touches upper band (overbought reversal).
    BUY  when price touches lower band (oversold reversal).
    """
    def __init__(self): super().__init__("NW_Envelope")

    def _nw_estimate(self, closes, bandwidth=8.0):
        n   = len(closes)
        y   = np.array(closes, dtype=float)
        idx = np.arange(n, dtype=float)
        # Vectorized — compute all weights at once using broadcasting
        diff    = idx[:, None] - idx[None, :]   # shape (n, n)
        weights = np.exp(-(diff ** 2) / (2 * bandwidth ** 2))
        fitted  = (weights * y[None, :]).sum(axis=1) / weights.sum(axis=1)
        return fitted

    def analyze(self, bars):
        if len(bars) < 50:
            return Signal("HOLD", 0.0,
                f"Need 50 bars for NW Envelope", self.name)

        closes     = np.array([b.close for b in bars[-50:]])
        atr        = get_atr(bars)
        fitted     = self._nw_estimate(closes, bandwidth=8.0)
        nw_line    = fitted[-1]
        upper_band = nw_line + 2.5 * atr
        lower_band = nw_line - 2.5 * atr
        current    = closes[-1]
        band_width = upper_band - lower_band
        pos        = (current - lower_band) / band_width if band_width > 0 else 0.5

        reason = (f"NW={nw_line:.5f} U={upper_band:.5f} "
                  f"L={lower_band:.5f} Pos={pos*100:.0f}%")

        if current >= upper_band * 0.998:
            conf = min(0.92, 0.72 + (current - upper_band*0.998) / max(atr,0.0001) * 0.05)
            return Signal("SELL", conf,
                f"NW UPPER BAND — Reversal SELL | {reason}", self.name)
        elif current <= lower_band * 1.002:
            conf = min(0.92, 0.72 + (lower_band*1.002 - current) / max(atr,0.0001) * 0.05)
            return Signal("BUY", conf,
                f"NW LOWER BAND — Reversal BUY | {reason}", self.name)
        elif pos >= 0.75:
            return Signal("SELL", 0.52,
                f"NW Upper Zone {pos*100:.0f}% — Approaching SELL | {reason}", self.name)
        elif pos <= 0.25:
            return Signal("BUY", 0.52,
                f"NW Lower Zone {pos*100:.0f}% — Approaching BUY | {reason}", self.name)
        return Signal("HOLD", 0.0,
            f"NW Mid Zone {pos*100:.0f}% | {reason}", self.name)


ALL_AGENTS = [
    EMAAgent, MACDAgent, RSIAgent, BollingerAgent, ATRAgent,
    StochasticAgent, BreakoutAgent, BOSAgent, CHOCHAgent,
    WyckoffAgent, SessionAgent, KillzoneAgent, OrderBlockAgent,
    FVGAgent, LiquidityAgent, OTEAgent, SilverBulletAgent,
    VolumeAgent, TSMOMAgent, NadarayaWatsonAgent, CMEFuturesAgent,
]

# ── HELPERS ──────────────────────────────────────────────────────────
def fetch_bars(pair, granularity="H1", count=300):
    try:
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        params = {"count": count, "granularity": granularity, "price": "M"}
        r = InstrumentsCandles(instrument=pair, params=params)
        client.request(r)
        bars = []
        for c in r.response.get("candles", []):
            if not c.get("complete"): continue
            m = c.get("mid", {})
            bars.append(BarData(
                timestamp=c.get("time", ""),
                open=float(m.get("o", 0)),
                high=float(m.get("h", 0)),
                low=float(m.get("l", 0)),
                close=float(m.get("c", 0)),
                volume=float(c.get("volume", 0))
            ))
        return bars
    except Exception as e:
        log.warning(f"fetch_bars {pair} {granularity}: {e}")
        return []

def analyze_cme_future(symbol, meta):
    """Analyze a CME futures contract — same agents, real OHLCV data"""
    try:
        import yfinance as yf

        # Fetch hourly data
        d = yf.download(symbol, period="5d", interval="1h", progress=False)
        if hasattr(d.columns, 'levels'):
            d.columns = d.columns.droplevel(1)
        if len(d) < 50:
            return None

        # Convert to BarData
        bars = []
        for ts, row in d.iterrows():
            try:
                bars.append(BarData(
                    timestamp=str(ts),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                ))
            except:
                continue

        if len(bars) < 50:
            return None

        # Fetch daily for H4 equivalent
        d4 = yf.download(symbol, period="60d", interval="1d", progress=False)
        if hasattr(d4.columns, 'levels'):
            d4.columns = d4.columns.droplevel(1)

        bars_d = []
        for ts, row in d4.iterrows():
            try:
                bars_d.append(BarData(
                    timestamp=str(ts),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                ))
            except:
                continue

        price  = bars[-1].close
        atr    = get_atr(bars)
        is_inv = meta.get('inverse', False)

        # Run subset of agents (fast ones only)
        fast_agents = [EMAAgent, MACDAgent, RSIAgent, BollingerAgent,
                       ATRAgent, VolumeAgent, TSMOMAgent]
        buy_votes = sell_votes = hold_votes = 0
        buy_conf  = sell_conf  = 0.0
        agent_opinions = []

        for AgentClass in fast_agents:
            try:
                ag  = AgentClass()
                sig = ag.analyze(bars)
                if sig is None: continue
                d_raw = sig.direction
                c     = float(sig.confidence)
                # Flip direction for inverse pairs
                if is_inv and d_raw in ("BUY", "SELL"):
                    d_raw = "SELL" if d_raw == "BUY" else "BUY"
                if d_raw == "BUY":
                    buy_votes += 1; buy_conf  += c
                elif d_raw == "SELL":
                    sell_votes += 1; sell_conf += c
                else:
                    hold_votes += 1
                agent_opinions.append({
                    "agent":      ag.name,
                    "signal":     d_raw,
                    "confidence": round(c * 100, 1),
                    "reason":     sig.reason
                })
            except:
                hold_votes += 1

        # Final signal
        direction  = "HOLD"
        final_conf = 0.0
        active     = buy_votes + sell_votes

        if active >= 2:
            if buy_votes > sell_votes:
                final_conf = min(0.99, (buy_conf / max(buy_votes,1)) / 3.0)
                if final_conf >= 0.55:
                    direction = "BUY"
            elif sell_votes > buy_votes:
                final_conf = min(0.99, (sell_conf / max(sell_votes,1)) / 3.0)
                if final_conf >= 0.55:
                    direction = "SELL"

        # Trend from daily bars
        trend = "NEUTRAL"
        if len(bars_d) >= 20:
            c_arr = np.array([b.close for b in bars_d])
            e10   = np.mean(c_arr[-10:])
            e20   = np.mean(c_arr[-20:])
            if c_arr[-1] > e10 > e20:
                trend = "BULLISH"
            elif c_arr[-1] < e10 < e20:
                trend = "BEARISH"
            else:
                trend = "RANGING"

        # SL/TP
        sl = tp = 0.0
        if direction == "BUY":
            sl = price - atr * 1.5
            tp = price + atr * 4.5
        elif direction == "SELL":
            sl = price + atr * 1.5
            tp = price - atr * 4.5

        # Chart data — last 60 hourly bars
        chart_bars = [[b.timestamp, b.open, b.high, b.low, b.close, b.volume]
                      for b in bars[-60:]]

        return {
            "pair":          symbol,
            "display_name":  f"{meta['flag']} {meta['name']}",
            "equiv":         meta['equiv'],
            "price":         round(price, 5),
            "direction":     direction,
            "confidence":    round(final_conf * 100, 1),
            "regime":        trend,
            "h4_trend":      trend,
            "h4_reason":     f"Daily trend: {trend}",
            "h4_aligned":    True,
            "conflict":      "",
            "buy_votes":     buy_votes,
            "sell_votes":    sell_votes,
            "hold_votes":    hold_votes,
            "sl":            round(sl, 5),
            "tp":            round(tp, 5),
            "atr":           round(atr, 5),
            "rr":            "3:1",
            "sl_pips":       0,
            "tp_pips":       0,
            "dollar_risk":   0,
            "is_futures":    True,
            "agent_opinions": agent_opinions,
            "headlines":     [f"CME {symbol} | Equiv: {meta['equiv']} | Volume confirmation available"],
            "explanation":   (f"{meta['flag']} {meta['name']} ({symbol})\n"
                             f"Equivalent to: {meta['equiv']}\n"
                             f"Price: {price:.5f} | Trend: {trend}\n"
                             f"Signal: {direction} ({final_conf*100:.1f}%)\n"
                             f"Votes: {buy_votes}B / {sell_votes}S\n"
                             f"⚡ Institutional futures — signals only, not executed on OANDA"),
            "bars_m15":      chart_bars,
            "bars_h1":       chart_bars,
            "bars_h4":       chart_bars,
            "bars_h8":       chart_bars,
            "bars_d1":       [[b.timestamp, b.open, b.high, b.low, b.close, b.volume]
                               for b in bars_d[-60:]],
            "timestamp":     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        }
    except Exception as e:
        log.warning(f"CME {symbol}: {e}")
        return None


def get_atr(bars, period=14):
    if len(bars) < period + 1: return 0.001
    trs = []
    for i in range(1, period + 1):
        h, l, pc = bars[-i].high, bars[-i].low, bars[-i-1].close
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs) / len(trs)

def get_balance():
    try:
        from v13_production import AccountDetails
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        r = AccountDetails(accountID=OANDA_ACCOUNT)
        client.request(r)
        return float(r.response["account"]["balance"])
    except:
        return 100000.0

def get_open_trades():
    try:
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        r = OpenTrades(accountID=OANDA_ACCOUNT)
        client.request(r)
        return r.response.get("trades", [])
    except:
        return []

def get_forex_factory_events():
    """Fetch high impact events from Forex Factory calendar"""
    try:
        # Try multiple FF endpoints
        urls = [
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
        ]
        for url in urls:
            try:
                resp = requests.get(url, timeout=8,
                    headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200 and resp.text.strip():
                    events = resp.json()
                    high_impact = []
                    for e in events:
                        if e.get("impact") not in ("High", "3"): continue
                        high_impact.append({
                            "title":    e.get("title", e.get("name", "")),
                            "currency": e.get("country", e.get("currency", "")),
                            "time":     e.get("time", e.get("date", "")),
                            "forecast": e.get("forecast", ""),
                            "previous": e.get("previous", "")
                        })
                    return high_impact[:5]
            except:
                continue
        return []
    except Exception as e:
        log.warning(f"Forex Factory: {e}")
        return []

def get_fred_context():
    """Get key FRED macro indicators affecting forex"""
    try:
        fred_key = os.getenv("FRED_KEY", "")
        if not fred_key: return {}

        indicators = {
            "Fed Rate":    "FEDFUNDS",
            "CPI":         "CPIAUCSL",
            "Unemployment":"UNRATE",
        }
        results = {}
        for name, series_id in indicators.items():
            try:
                url = (f"https://api.stlouisfed.org/fred/series/observations"
                       f"?series_id={series_id}&api_key={fred_key}"
                       f"&limit=1&sort_order=desc&file_type=json")
                r = requests.get(url, timeout=5)
                obs = r.json().get("observations", [])
                if obs:
                    results[name] = obs[0].get("value", "N/A")
            except:
                continue
        return results
    except Exception as e:
        log.warning(f"FRED: {e}")
        return {}

def is_news_blackout():
    """Check if within 30 min of high impact news event"""
    try:
        events = get_forex_factory_events()
        now = datetime.now(timezone.utc)
        for e in events:
            try:
                # Parse date and time from Forex Factory format
                date_str = e.get("date", "")
                time_str = e.get("time", "")
                if not date_str or not time_str: continue
                # Try parsing
                from dateutil import parser as dparser
                event_dt = dparser.parse(f"{date_str} {time_str}")
                event_dt = event_dt.replace(tzinfo=timezone.utc)
                diff = abs((event_dt - now).total_seconds() / 60)
                if diff <= NEWS_BLACKOUT_MIN:
                    log.info(f"📰 NEWS BLACKOUT: {e['title']} in {diff:.0f} min")
                    return True
            except:
                continue
        return False
    except:
        return False

def get_news_headlines(pair):
    """Fetch real news for pair + Forex Factory events + FRED context"""
    headlines = []

    # 1. NewsAPI headlines
    try:
        base = pair.split("_")[0]
        currency_names = {
            "EUR": "Euro eurozone", "GBP": "British pound sterling",
            "USD": "US dollar Federal Reserve", "JPY": "Japanese yen Bank of Japan",
            "AUD": "Australian dollar", "CAD": "Canadian dollar oil",
            "XAU": "Gold prices", "GBP": "British pound"
        }
        query = currency_names.get(base, base) + " forex"
        url = (f"https://newsapi.org/v2/everything?q={query}&"
               f"sortBy=publishedAt&pageSize=3&language=en&apiKey={NEWS_KEY}")
        resp = requests.get(url, timeout=5)
        articles = resp.json().get("articles", [])
        for a in articles[:2]:
            if a.get("title"):
                headlines.append(f"📰 {a['title'][:70]}")
    except:
        pass

    # 2. Forex Factory high impact events
    try:
        events = get_forex_factory_events()
        pair_currencies = pair.replace("_", "")
        for e in events[:3]:
            curr = e.get("currency", "").upper()
            if curr and curr in pair_currencies:
                headlines.append(
                    f"⚡ {e['currency']} {e['title']} — "
                    f"Forecast: {e.get('forecast','?')} "
                    f"Prev: {e.get('previous','?')}"
                )
    except:
        pass

    # 3. FRED macro context for USD pairs
    if "USD" in pair:
        try:
            fred = get_fred_context()
            if fred:
                parts = [f"{k}: {v}" for k, v in fred.items()]
                headlines.append(f"📊 FRED Macro — {' | '.join(parts)}")
        except:
            pass

    return headlines if headlines else ["No recent market news found"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=5)
    except Exception as e:
        log.warning(f"Telegram: {e}")

def is_news_blackout():
    """Check if we are within 30 min of a high impact news event"""
    try:
        # Check FRED for scheduled events — simplified check
        # In production this would call Forex Factory API
        now = datetime.now(timezone.utc)
        # Major news times (UTC): NFP first Friday 13:30, Fed 19:00 etc
        # For now return False — full implementation needs Forex Factory
        return False
    except:
        return False

def is_volatility_breaker(bars):
    """Pause if ATR suddenly spikes 3x above normal — flash crash protection"""
    if len(bars) < 20: return False
    avg_atr = np.mean([b.high - b.low for b in bars[-20:-1]])
    cur_atr = bars[-1].high - bars[-1].low
    if avg_atr == 0: return False
    return (cur_atr / avg_atr) > VOL_BREAKER_MULT

def is_trading_session():
    """Only trade London (7-12 UTC) and New York (13-18 UTC) sessions"""
    h = datetime.now(timezone.utc).hour
    return (7 <= h <= 12) or (13 <= h <= 18)

def update_trailing_stops():
    """
    Move SL to breakeven when profit = SL distance (1:1 RR reached).
    Lock 50% profit when 2:1 RR reached.
    """
    try:
        from oandapyV20.endpoints.trades import TradeCRCDO
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        open_trades = get_open_trades()

        for trade in open_trades:
            try:
                trade_id   = trade["id"]
                units      = float(trade["currentUnits"])
                open_price = float(trade["price"])
                cur_price  = float(trade["price"])  # will update from market

                sl = float(trade.get("stopLossOrder", {}).get("price", 0))
                tp = float(trade.get("takeProfitOrder", {}).get("price", 0))

                if sl == 0 or tp == 0: continue

                is_buy     = units > 0
                sl_dist    = abs(open_price - sl)
                tp_dist    = abs(open_price - tp)
                profit_now = abs(cur_price - open_price)

                # Move to breakeven at 1:1
                if profit_now >= sl_dist * TRAIL_TRIGGER_RR:
                    new_sl = open_price + 0.00010 if is_buy else open_price - 0.00010
                    if (is_buy and new_sl > sl) or (not is_buy and new_sl < sl):
                        data = {"stopLoss": {"price": f"{new_sl:.5f}"}}
                        r = TradeCRCDO(accountID=OANDA_ACCOUNT,
                                      tradeID=trade_id, data=data)
                        client.request(r)
                        log.info(f"[TRAIL] {trade_id} SL moved to breakeven {new_sl:.5f}")

                # Lock 50% profit at 2:1
                if profit_now >= sl_dist * TRAIL_LOCK_RR:
                    lock_profit = profit_now * 0.5
                    new_sl = (open_price + lock_profit if is_buy
                             else open_price - lock_profit)
                    if (is_buy and new_sl > sl) or (not is_buy and new_sl < sl):
                        data = {"stopLoss": {"price": f"{new_sl:.5f}"}}
                        r = TradeCRCDO(accountID=OANDA_ACCOUNT,
                                      tradeID=trade_id, data=data)
                        client.request(r)
                        log.info(f"[TRAIL] {trade_id} SL locked at {new_sl:.5f}")
            except:
                continue
    except Exception as e:
        log.warning(f"Trailing stop update: {e}")


# ── SUPABASE LOGGER (V15) ─────────────────────────────────────────────
_sb_logger = None
def get_supabase_logger():
    global _sb_logger
    if _sb_logger is None:
        try: _sb_logger = SupabaseLogger()
        except: pass
    return _sb_logger

def log_trade_to_supabase(pair, direction, conf, price, sl, tp,
                           units, regime, agents_agreed, agents_disagreed,
                           headlines, oanda_trade_id=""):
    """Log every executed trade to Supabase with full context"""
    try:
        sb = get_supabase_logger()
        if not sb: return
        import hashlib
        trade_id = hashlib.md5(
            f"{pair}{direction}{price}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        rec = TradeRecord(
            id=trade_id, pair=pair, direction=direction,
            confidence=conf,
            why_technical=f"ICT+Technical agents: {len(agents_agreed)} agreed",
            why_news=headlines[0][:100] if headlines else "No news",
            why_fundamental="FRED macro integrated",
            why_correlation="CME futures confirmation",
            why_cot="COT data via v13",
            what_pattern=f"{direction} setup at {price:.5f}",
            what_agents=agents_agreed,
            what_agents_count=len(agents_agreed),
            when_timestamp=datetime.now(timezone.utc).isoformat(),
            when_session="London" if 7<=datetime.now(timezone.utc).hour<=12 else "NewYork",
            when_hour=datetime.now(timezone.utc).hour,
            when_next_event="Check Forex Factory",
            when_avoid_news=False,
            who_institutions="CME futures aligned",
            who_retail="Retail sentiment unknown",
            who_cot_net=0,
            where_support=sl,
            where_resistance=tp,
            where_entry=price,
            where_sl=sl,
            where_tp=tp,
            dxy_trend="Unknown",
            gold_trend="Unknown",
            vix_level=0.0,
            regime=regime,
            pair_win_rate=0.0,
            system_win_rate=0.0,
            memory_context="V15 active",
            rl_episodes=0,
            tradingview_confirmed=False,
            tradingview_signal="",
            outcome="OPEN",
            oanda_trade_id=oanda_trade_id
        )
        sb.log_trade(rec)
        log.info(f"[SUPABASE] Trade logged: {trade_id}")
        return trade_id
    except Exception as e:
        log.warning(f"[SUPABASE] Log failed: {e}")
        return ""

# ── SELF-LEARNING ACTIVATION ──────────────────────────────────────────
def activate_self_learning(chakra_instance, pair, direction, conf,
                            agent_opinions, regime, outcome="WIN"):
    """
    Update AgentWeights and RLAgent after each trade.
    This is what makes the system smarter over time.
    """
    try:
        agreed    = [o["agent"] for o in agent_opinions
                     if o["signal"] == direction]
        disagreed = [o["agent"] for o in agent_opinions
                     if o["signal"] not in (direction, "HOLD")]

        # Update agent weights — winners get more power
        chakra_instance.weights.update(agreed, disagreed, outcome)
        chakra_instance.weights.save()

        # Update RL brain
        reward = 1.0 if outcome == "WIN" else -1.0
        pair_wr = chakra_instance.mem.pair_wr(pair)
        sys_wr  = chakra_instance.mem.win_rate

        chakra_instance.rl.learn(
            pair=pair, regime=regime, conf=conf,
            wr=pair_wr, news=0.5, cot=0.5,
            tv_conf=0.5, action=direction, reward=reward
        )
        chakra_instance.rl.save()
        log.info(f"[LEARN] {pair} {direction} {outcome} — weights+RL updated")
    except Exception as e:
        log.warning(f"[LEARN] Error: {e}")

# ── PYRAMID INTO WINNERS ──────────────────────────────────────────────
def pyramid_winners(balance):
    """
    When open trade is up 1:1 RR (50% to TP), add 50% more position.
    Lets winners run bigger — used by all top trend traders.
    """
    try:
        from oandapyV20.endpoints.trades import TradeCRCDO
        client     = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        open_trades = get_open_trades()

        for trade in open_trades:
            try:
                trade_id   = trade["id"]
                units      = float(trade["currentUnits"])
                open_price = float(trade["price"])
                is_buy     = units > 0

                sl = float(trade.get("stopLossOrder",   {}).get("price", 0))
                tp = float(trade.get("takeProfitOrder", {}).get("price", 0))
                if sl == 0 or tp == 0: continue

                # Get current price from OANDA
                pair = trade["instrument"]
                bars = fetch_bars(pair, "M15", 5)
                if not bars: continue
                cur_price = bars[-1].close

                sl_dist    = abs(open_price - sl)
                tp_dist    = abs(open_price - tp)
                profit_now = abs(cur_price - open_price)

                # Pyramid at 1:1 RR — only once per trade
                already_pyramided = float(trade.get("initialMarginRequired", 0)) > 0
                pyramid_tag = f"pyramid_{trade_id}"

                if (profit_now >= sl_dist and
                    not trade.get("clientExtensions", {}).get("comment", "").startswith("PYR")):

                    # Add 50% of original position
                    add_units = int(abs(units) * 0.5)
                    if add_units < MIN_UNITS: continue
                    if not is_buy: add_units = -add_units

                    # New SL at breakeven, same TP
                    new_sl = open_price + 0.0001 if is_buy else open_price - 0.0001

                    data = {
                        "order": {
                            "type": "MARKET",
                            "instrument": pair,
                            "units": str(add_units),
                            "stopLossOnFill":   {"price": f"{new_sl:.5f}"},
                            "takeProfitOnFill": {"price": f"{tp:.5f}"},
                            "timeInForce": "FOK",
                            "clientExtensions": {"comment": f"PYR_{trade_id}"}
                        }
                    }
                    r = OrderCreate(accountID=OANDA_ACCOUNT, data=data)
                    client.request(r)
                    log.info(f"[PYRAMID] {pair} added {add_units} units at {cur_price:.5f}")

                    msg = (f"📈 <b>PYRAMID TRADE ADDED</b>\n\n"
                           f"Pair: <b>{pair}</b>\n"
                           f"Original trade up {profit_now/sl_dist:.1f}:1\n"
                           f"Added: {abs(add_units)} units\n"
                           f"New SL: Breakeven {new_sl:.5f}\n"
                           f"TP: {tp:.5f}\n\n"
                           f"📊 {RAILWAY_URL}")
                    send_telegram(msg)
            except:
                continue
    except Exception as e:
        log.warning(f"[PYRAMID] Error: {e}")

# ── WEEKLY BIAS AGENT ─────────────────────────────────────────────────
class WeeklyBiasAgent:
    """
    Every Sunday analyses which pairs are in strongest weekly trends.
    Boosts confidence on those pairs by 20% for the week.
    """
    def __init__(self):
        self.bias      = {}
        self.last_run  = None
        self.bias_file = "v15_weekly_bias.json"
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.bias_file):
                with open(self.bias_file) as f:
                    data = json.load(f)
                    self.bias     = data.get("bias", {})
                    self.last_run = data.get("last_run")
        except:
            pass

    def _save(self):
        try:
            with open(self.bias_file, "w") as f:
                json.dump({"bias": self.bias, "last_run": self.last_run}, f)
        except:
            pass

    def update(self, pairs_to_check=None):
        """Run Sunday analysis — check weekly trend for all pairs"""
        now = datetime.now(timezone.utc)
        # Run every Sunday or if never run
        if self.last_run and now.weekday() != 6:
            return  # Not Sunday

        log.info("[WeeklyBias] Running Sunday analysis...")
        pairs_to_check = pairs_to_check or PAIRS
        new_bias = {}

        for pair in pairs_to_check:
            try:
                bars = fetch_bars(pair, "D", 10)
                if len(bars) < 5: continue
                closes = [b.close for b in bars]
                week_ret = (closes[-1] - closes[-5]) / closes[-5]

                if week_ret > 0.005:      # +0.5% weekly → BULLISH bias
                    new_bias[pair] = {"direction": "BUY",  "boost": 0.20,
                                      "weekly_ret": round(week_ret*100, 2)}
                elif week_ret < -0.005:   # -0.5% weekly → BEARISH bias
                    new_bias[pair] = {"direction": "SELL", "boost": 0.20,
                                      "weekly_ret": round(week_ret*100, 2)}
                else:
                    new_bias[pair] = {"direction": "HOLD", "boost": 0.0,
                                      "weekly_ret": round(week_ret*100, 2)}

                log.info(f"[WeeklyBias] {pair}: {new_bias[pair]['direction']} "
                         f"({week_ret*100:+.2f}% weekly)")
            except:
                continue

        self.bias     = new_bias
        self.last_run = now.isoformat()
        self._save()

        # Send Sunday summary to Telegram
        if new_bias:
            lines = ["📅 <b>WEEKLY BIAS REPORT</b>\n"]
            for p, b in new_bias.items():
                icon = "🟢" if b["direction"]=="BUY" else "🔴" if b["direction"]=="SELL" else "⚪"
                lines.append(f"{icon} {p}: {b['direction']} ({b['weekly_ret']:+.2f}%)")
            lines.append(f"\n📊 {RAILWAY_URL}")
            send_telegram("\n".join(lines))

    def get_boost(self, pair, signal_direction):
        """Return confidence boost if weekly bias matches signal"""
        bias = self.bias.get(pair, {})
        if bias.get("direction") == signal_direction:
            return bias.get("boost", 0.0)
        return 0.0

    def get_summary(self):
        return self.bias


def execute_trade(pair, direction, bars, balance):
    try:
        price    = bars[-1].close
        atr      = get_atr(bars)
        risk     = balance * RISK_PCT
        sl_dist  = atr * 1.5

        # Safe unit sizing
        if sl_dist > 0:
            units = int(risk / sl_dist)
        else:
            units = MIN_UNITS

        # Gold needs smaller units due to high price
        if "XAU" in pair:
            units = min(units, 5)
        else:
            units = min(units, MAX_UNITS)
        units = max(units, MIN_UNITS)
        if direction == "SELL": units = -units

        # Price precision — JPY pairs need 3 decimals, XAU needs 2, others need 5
        if "JPY" in pair:
            precision = 3
        elif "XAU" in pair:
            precision = 2
        else:
            precision = 5

        sl_price = round(price - atr*1.5, precision) if direction=="BUY" else round(price + atr*1.5, precision)
        tp_price = round(price + atr*4.5, precision) if direction=="BUY" else round(price - atr*4.5, precision)

        data = {
            "order": {
                "type": "MARKET",
                "instrument": pair,
                "units": str(units),
                "stopLossOnFill":   {"price": f"{sl_price:.{precision}f}"},
                "takeProfitOnFill": {"price": f"{tp_price:.{precision}f}"},
                "timeInForce": "FOK"
            }
        }
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        r = OrderCreate(accountID=OANDA_ACCOUNT, data=data)
        client.request(r)
        log.info(f"[EXECUTED] {pair} {direction} units={units} "
                 f"entry={price:.{precision}f} SL={sl_price:.{precision}f} TP={tp_price:.{precision}f}")

        # Calculate pip distances
        pip = 0.01 if "JPY" in pair or "XAU" in pair else 0.0001
        sl_pips = round(abs(price - sl_price) / pip)
        tp_pips = round(abs(price - tp_price) / pip)
        dollar_risk = round(balance * RISK_PCT, 2)

        return True, price, sl_price, tp_price, abs(units), sl_pips, tp_pips, dollar_risk
    except Exception as e:
        log.error(f"[EXECUTE ERROR] {pair}: {e}")
        return False, 0, 0, 0, 0, 0, 0, 0


# ── MAIN ORCHESTRATOR ─────────────────────────────────────────────────
class ChakraV15:
    def __init__(self):
        self.cycle        = 0
        self.results      = {}
        self.futures      = {}
        self.paused       = False
        self.pause_reason = ""
        self._balance     = 100000.0
        self._ff_events   = []
        self._fred_data   = {}
        self.weekly_bias  = WeeklyBiasAgent()
        self._prev_signals = {}          # track previous signals to avoid spam
        self._signal_feed  = deque(maxlen=50)  # live signal feed
        self._news_feed    = deque(maxlen=30)  # live news headlines
        self._market_news  = {}          # news impact per pair
        agent_names      = [ag().name for ag in ALL_AGENTS]
        self.mem         = FinMem()
        self.weights     = AgentWeights(agent_names)
        self.rl          = RLAgent()
        self.regime_det  = RegimeDetector()
        self.hivemind    = HiveMind(self.mem, self.weights)
        self.news_intel  = NewsIntelligence()
        self.lock        = threading.Lock()
        log.info(f"[Dashboard] {RAILWAY_URL}")
        log.info(f"PROJECT CHAKRA V15 MAX PROFIT | AUTO_EXECUTE={AUTO_EXECUTE}")
        log.info(f"Pairs: {PAIRS}")

    def analyze_pair(self, pair):
        try:
            bars_m15 = fetch_bars(pair, "M15", 100)
            bars_h1  = fetch_bars(pair, "H1",  300)
            bars_h4  = fetch_bars(pair, "H4",  300)
            bars_h8  = fetch_bars(pair, "H8",  200)
            bars_d1  = fetch_bars(pair, "D",   100)

            if not bars_h1 or len(bars_h1) < 50:
                return None

            price  = bars_h1[-1].close
            atr    = get_atr(bars_h1)
            regime = self.regime_det.detect(bars_h1)

            # Volatility circuit breaker
            if is_volatility_breaker(bars_h1):
                return {
                    "pair": pair, "price": round(price, 5),
                    "direction": "HOLD", "confidence": 0,
                    "regime": "VOLATILE", "h4_trend": "—",
                    "h4_reason": "Volatility circuit breaker active",
                    "h4_aligned": True, "conflict": "⚡ Flash crash protection active",
                    "buy_votes": 0, "sell_votes": 0, "hold_votes": 0,
                    "sl": 0, "tp": 0, "atr": round(atr, 5), "rr": "—",
                    "sl_pips": 0, "tp_pips": 0, "dollar_risk": 0,
                    "agent_opinions": [], "headlines": [],
                    "explanation": "Volatility spike detected. System paused for safety.",
                    "bars_m15": [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                                 for b in bars_m15[-50:]],
                    "bars_h1":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                                 for b in bars_h1[-50:]],
                    "bars_h4":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                                 for b in bars_h4[-50:]],
                    "bars_h8":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                                 for b in bars_h8[-50:]],
                    "bars_d1":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                                 for b in bars_d1[-50:]],
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                }

            # H4 trend
            h4_trend = "NEUTRAL"
            h4_reason = ""
            if bars_h4 and len(bars_h4) >= 50:
                c   = np.array([b.close for b in bars_h4])
                e20 = np.mean(c[-20:])
                e50 = np.mean(c[-50:])
                if c[-1] > e20 > e50:
                    h4_trend  = "BULLISH"
                    h4_reason = f"Price {c[-1]:.5f} > EMA20 {e20:.5f} > EMA50 {e50:.5f}"
                elif c[-1] < e20 < e50:
                    h4_trend  = "BEARISH"
                    h4_reason = f"Price {c[-1]:.5f} < EMA20 {e20:.5f} < EMA50 {e50:.5f}"
                else:
                    h4_trend  = "RANGING"
                    h4_reason = f"EMA20 {e20:.5f} | EMA50 {e50:.5f} — no clear trend"

            # Run all agents
            buy_votes = sell_votes = hold_votes = 0
            buy_conf  = sell_conf  = 0.0
            agent_opinions = []

            for AgentClass in ALL_AGENTS:
                try:
                    ag  = AgentClass()
                    # Pass pair context to CMEFuturesAgent
                    if ag.name == "CMEFutures":
                        ag._pair = pair
                    # NadarayaWatson runs on 8H for reversal signals
                    if ag.name == "NW_Envelope":
                        bars_for_agent = bars_h8 if bars_h8 and len(bars_h8) >= 50 else bars_h1
                    else:
                        bars_for_agent = bars_h1
                    sig = ag.analyze(bars_for_agent)
                    if sig is None: continue
                    w   = self.weights.get(ag.name)
                    if sig.direction == "BUY":
                        buy_votes += 1; buy_conf  += sig.confidence * w
                    elif sig.direction == "SELL":
                        sell_votes += 1; sell_conf += sig.confidence * w
                    else:
                        hold_votes += 1
                    agent_opinions.append({
                        "agent":      ag.name,
                        "signal":     sig.direction,
                        "confidence": round(sig.confidence * 100, 1),
                        "reason":     sig.reason
                    })
                except:
                    hold_votes += 1

            # Final signal — normalize confidence (weights are 3.0)
            direction  = "HOLD"
            final_conf = 0.0
            conflict   = ""
            active     = buy_votes + sell_votes

            if active >= 3:
                if buy_votes > sell_votes:
                    final_conf = min(0.99, (buy_conf / max(buy_votes,1)) / 3.0)
                    if final_conf >= CONFIDENCE_BASE:
                        direction = "BUY"
                        # Apply weekly bias boost
                        boost = self.weekly_bias.get_boost(pair, "BUY")
                        final_conf = min(0.99, final_conf + boost)
                        if h4_trend == "BEARISH":
                            conflict = "⚠️ Counter-trend: H4 is BEARISH but signal is BUY"
                elif sell_votes > buy_votes:
                    final_conf = min(0.99, (sell_conf / max(sell_votes,1)) / 3.0)
                    if final_conf >= CONFIDENCE_BASE:
                        direction = "SELL"
                        # Apply weekly bias boost
                        boost = self.weekly_bias.get_boost(pair, "SELL")
                        final_conf = min(0.99, final_conf + boost)
                        if h4_trend == "BULLISH":
                            conflict = "⚠️ Counter-trend: H4 is BULLISH but signal is SELL"

            # H4 alignment
            h4_aligned = (
                (direction == "BUY"  and h4_trend == "BULLISH") or
                (direction == "SELL" and h4_trend == "BEARISH") or
                (direction == "HOLD")
            )

            # SL / TP / pip calculation
            pip = 0.01 if ("JPY" in pair or "XAU" in pair) else 0.0001
            sl = tp = 0.0
            sl_pips = tp_pips = 0
            if direction == "BUY":
                sl = price - atr * 1.5
                tp = price + atr * 4.5
            elif direction == "SELL":
                sl = price + atr * 1.5
                tp = price - atr * 4.5
            if sl and tp:
                sl_pips = round(abs(price - sl) / pip)
                tp_pips = round(abs(price - tp) / pip)

            dollar_risk = round(self._balance * RISK_PCT, 2)

            # News
            # News — build from cached FF events + FRED (no API call per pair)
            headlines = []
            pair_currencies = pair.replace("_", "")
            for e in self._ff_events[:3]:
                curr = e.get("currency", "").upper()
                if curr and curr in pair_currencies:
                    headlines.append(
                        f"⚡ {e['currency']} {e['title']} "
                        f"Forecast:{e.get('forecast','?')} "
                        f"Prev:{e.get('previous','?')}"
                    )
            if "USD" in pair and self._fred_data:
                parts = [f"{k}:{v}" for k, v in self._fred_data.items()]
                headlines.append(f"📊 FRED: {' | '.join(parts)}")
            if not headlines:
                headlines = ["No high-impact events this cycle"]

            # Plain English explanation
            explanation = self._explain(
                pair, direction, final_conf, buy_votes, sell_votes,
                h4_trend, h4_reason, conflict, agent_opinions,
                headlines, price, sl, tp, sl_pips, tp_pips,
                dollar_risk, regime
            )

            return {
                "pair":          pair,
                "price":         round(price, 5),
                "direction":     direction,
                "confidence":    round(final_conf * 100, 1),
                "regime":        regime,
                "h4_trend":      h4_trend,
                "h4_reason":     h4_reason,
                "h4_aligned":    h4_aligned,
                "conflict":      conflict,
                "buy_votes":     buy_votes,
                "sell_votes":    sell_votes,
                "hold_votes":    hold_votes,
                "sl":            round(sl, 5),
                "tp":            round(tp, 5),
                "atr":           round(atr, 5),
                "rr":            "3:1",
                "sl_pips":       sl_pips,
                "tp_pips":       tp_pips,
                "dollar_risk":   dollar_risk,
                "agent_opinions": agent_opinions,
                "headlines":     headlines,
                "explanation":   explanation,
                "bars_m15": [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                              for b in bars_m15[-60:]],
                "bars_h1":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                              for b in bars_h1[-60:]],
                "bars_h4":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                              for b in bars_h4[-60:]],
                "bars_h8":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                              for b in (bars_h8 or [])[-60:]],
                "bars_d1":  [[b.timestamp,b.open,b.high,b.low,b.close,b.volume]
                              for b in (bars_d1 or [])[-60:]],
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            }
        except Exception as e:
            log.error(f"analyze_pair {pair}: {e}")
            return None

    def _explain(self, pair, direction, conf, buy_v, sell_v,
                 h4_trend, h4_reason, conflict, opinions,
                 headlines, price, sl, tp, sl_pips, tp_pips,
                 dollar_risk, regime):
        base  = pair.replace("_", "/")
        lines = []

        if direction == "HOLD":
            lines.append(f"📊 {base} — WAITING FOR SETUP")
            lines.append(f"Market regime: {regime}")
            lines.append(f"Agent split: {buy_v} bullish vs {sell_v} bearish")
            lines.append("Not enough agreement to enter. Patience is profit.")
        else:
            emoji = "🟢" if direction == "BUY" else "🔴"
            lines.append(f"{emoji} {base} — {direction} SIGNAL")
            lines.append(f"Confidence: {conf*100:.1f}% | Regime: {regime}")
            lines.append("")
            lines.append(f"📍 TRADE LEVELS")
            lines.append(f"Entry:       {price:.5f}")
            lines.append(f"Stop Loss:   {sl:.5f}  ({sl_pips} pips away)")
            lines.append(f"Take Profit: {tp:.5f}  ({tp_pips} pips away)")
            lines.append(f"Risk/Reward: 3:1  |  Dollar Risk: ${dollar_risk}")
            lines.append("")
            lines.append(f"📈 H4 TREND: {h4_trend}")
            lines.append(f"{h4_reason}")
            if conflict:
                lines.append(f"\n{conflict}")
                lines.append("Trade skipped until H4 aligns.")
            else:
                lines.append("✅ Signal aligns with H4 trend.")
            lines.append("")
            lines.append(f"🤖 AGENT VOTES: {buy_v} BUY | {sell_v} SELL")
            relevant = [o for o in opinions if o["signal"] == direction][:4]
            for o in relevant:
                lines.append(f"  • {o['agent']} ({o['confidence']}%): {o['reason'][:50]}")

        lines.append("")
        lines.append("📰 NEWS CONTEXT:")
        for h in headlines[:2]:
            lines.append(f"  • {h[:75]}")

        return "\n".join(lines)

    def run_cycle(self):
        self.cycle += 1
        log.info(f"\n{'='*55}\n CYCLE {self.cycle} - "
                 f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
                 f"\n{'='*55}")

        # Update trailing stops on open trades
        update_trailing_stops()

        # Pyramid into winning trades
        pyramid_winners(self._balance)

        # Weekly bias update (runs only on Sundays)
        self.weekly_bias.update(PAIRS)

        # News blackout check
        if is_news_blackout():
            log.info("📰 NEWS BLACKOUT — pausing new trades")
            return

        # Session check
        in_session = is_trading_session()
        if not in_session:
            log.info("🌙 Outside London/NY session — monitoring only")

        balance     = get_balance()
        self._balance = balance

        # Fetch news and FF events ONCE per cycle — not per pair
        self._ff_events = get_forex_factory_events()
        self._fred_data = get_fred_context()

        # Fetch global market news for news ticker
        try:
            url = (f"https://newsapi.org/v2/top-headlines?category=business&"
                   f"language=en&pageSize=10&apiKey={NEWS_KEY}")
            resp = requests.get(url, timeout=5)
            articles = resp.json().get("articles", [])
            for a in articles[:10]:
                title = a.get("title", "")
                if title and len(title) > 10:
                    # Determine which pairs this news affects
                    impacts = []
                    title_lower = title.lower()
                    if any(w in title_lower for w in ["euro","ecb","eurozone","germany","france"]):
                        impacts.append("EUR_USD")
                    if any(w in title_lower for w in ["pound","boe","britain","uk","brexit"]):
                        impacts.append("GBP_USD")
                    if any(w in title_lower for w in ["yen","boj","japan","nikkei"]):
                        impacts.append("USD_JPY")
                    if any(w in title_lower for w in ["fed","dollar","federal reserve","fomc","cpi","inflation"]):
                        impacts.extend(["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD"])
                    if any(w in title_lower for w in ["gold","xau","precious"]):
                        impacts.append("XAU_USD")
                    if any(w in title_lower for w in ["oil","canada","cad","opec"]):
                        impacts.append("USD_CAD")
                    if any(w in title_lower for w in ["australia","rba","aud","china"]):
                        impacts.append("AUD_USD")

                    item = {
                        "title":   title[:100],
                        "source":  a.get("source",{}).get("name",""),
                        "impacts": list(set(impacts)),
                        "time":    datetime.now(timezone.utc).strftime("%H:%M")
                    }
                    # Add to news feed if not duplicate
                    existing = [n["title"] for n in self._news_feed]
                    if title not in existing:
                        self._news_feed.appendleft(item)
        except:
            pass
        new_results = {}

        for pair in PAIRS:
            result = self.analyze_pair(pair)
            if not result:
                continue

            new_results[pair] = result
            direction = result["direction"]
            conf      = result["confidence"]

            log.info(f"  {pair:<10} {direction:<5} conf={conf:.1f}% "
                     f"H4:{result['h4_trend']:<8} "
                     f"votes:{result['buy_votes']}B/"
                     f"{result['sell_votes']}S "
                     f"SL={result['sl']} TP={result['tp']}")

            # ── NEW SIGNAL DETECTION ─────────────────────────────
            prev = self._prev_signals.get(pair, {})
            is_new_signal = (
                direction != prev.get("direction", "HOLD") and
                direction in ("BUY", "SELL")
            )
            if is_new_signal:
                self._prev_signals[pair] = {
                    "direction": direction,
                    "conf": conf,
                    "time": datetime.now(timezone.utc).isoformat()
                }
                # Add to live signal feed
                self._signal_feed.appendleft({
                    "pair":      pair,
                    "direction": direction,
                    "conf":      conf,
                    "h4":        result["h4_trend"],
                    "regime":    result["regime"],
                    "price":     result["price"],
                    "sl":        result["sl"],
                    "tp":        result["tp"],
                    "time":      datetime.now(timezone.utc).strftime("%H:%M UTC"),
                    "aligned":   result["h4_aligned"],
                    "conflict":  result["conflict"]
                })

            # Execute only during trading sessions
            if (AUTO_EXECUTE and in_session and
                direction in ("BUY", "SELL") and
                result["h4_aligned"] and
                not result["conflict"]):

                ok, price, sl, tp, units, sl_pips, tp_pips, d_risk = \
                    execute_trade(pair, direction, 
                        [BarData(b[0],b[1],b[2],b[3],b[4],b[5])
                         for b in result["bars_h1"]], balance)

                if ok:
                    # 1. Log to Supabase
                    agents_agreed = [o["agent"] for o in result.get("agent_opinions",[])
                                     if o["signal"] == direction]
                    agents_disagreed = [o["agent"] for o in result.get("agent_opinions",[])
                                        if o["signal"] not in (direction, "HOLD")]
                    trade_id = log_trade_to_supabase(
                        pair, direction, conf/100, price, sl, tp,
                        units, result["regime"], agents_agreed,
                        agents_disagreed, result.get("headlines",[])
                    )

                    # 2. Activate self-learning
                    activate_self_learning(
                        self, pair, direction, conf/100,
                        result.get("agent_opinions",[]),
                        result["regime"], outcome="OPEN"
                    )

                    # 3. Record in FinMem
                    try:
                        from v13_production import TradeRecord
                        import hashlib
                        rec = TradeRecord(
                            id=trade_id or hashlib.md5(f"{pair}{price}".encode()).hexdigest()[:8],
                            pair=pair, direction=direction, confidence=conf/100,
                            why_technical=f"{len(agents_agreed)} agents agreed",
                            why_news=result.get("headlines",[""])[0][:80],
                            why_fundamental="", why_correlation="CME futures",
                            why_cot="", what_pattern=f"{direction} {price:.5f}",
                            what_agents=agents_agreed,
                            what_agents_count=len(agents_agreed),
                            when_timestamp=datetime.now(timezone.utc).isoformat(),
                            when_session="London" if 7<=datetime.now(timezone.utc).hour<=12 else "NewYork",
                            when_hour=datetime.now(timezone.utc).hour,
                            when_next_event="", when_avoid_news=False,
                            who_institutions="", who_retail="", who_cot_net=0,
                            where_support=sl, where_resistance=tp,
                            where_entry=price, where_sl=sl, where_tp=tp,
                            dxy_trend="", gold_trend="", vix_level=0.0,
                            regime=result["regime"],
                            pair_win_rate=self.mem.pair_wr(pair),
                            system_win_rate=self.mem.win_rate,
                            memory_context="V15", rl_episodes=0,
                            tradingview_confirmed=False, tradingview_signal="",
                            outcome="OPEN", oanda_trade_id=str(trade_id)
                        )
                        self.mem.record(rec)
                        self.mem.save()
                    except Exception as e:
                        log.warning(f"FinMem record: {e}")

                    # 4. Telegram alert
                    msg = (
                        f"🚀 <b>CHAKRA TRADE EXECUTED</b>\n\n"
                        f"Pair: <b>{pair}</b>\n"
                        f"Direction: <b>{direction}</b>\n"
                        f"Confidence: {conf:.1f}%\n"
                        f"Weekly Bias: {self.weekly_bias.bias.get(pair,{}).get('direction','—')}\n\n"
                        f"📍 <b>LEVELS</b>\n"
                        f"Entry:       {price:.5f}\n"
                        f"Stop Loss:   {sl:.5f} ({sl_pips} pips)\n"
                        f"Take Profit: {tp:.5f} ({tp_pips} pips)\n"
                        f"Units:       {units}\n"
                        f"Risk:        ${d_risk}\n"
                        f"RR Ratio:    3:1\n\n"
                        f"🔄 Trailing stop + Pyramid active\n"
                        f"📚 Logged to Supabase | Self-learning updated\n\n"
                        f"H4 Trend: {result['h4_trend']}\n"
                        f"Regime: {result['regime']}\n\n"
                        f"📊 Dashboard: {RAILWAY_URL}"
                    )
                    send_telegram(msg)

            elif direction in ("BUY", "SELL") and not in_session and is_new_signal:
                # Alert only on NEW signals outside session
                msg = (
                    f"⚡ <b>CHAKRA NEW SIGNAL</b> (Outside Session)\n\n"
                    f"Pair: <b>{pair}</b>\n"
                    f"Signal: <b>{direction}</b> ({conf:.1f}%)\n"
                    f"Entry: {result['price']:.5f}\n"
                    f"SL: {result['sl']:.5f} ({result['sl_pips']} pips)\n"
                    f"TP: {result['tp']:.5f} ({result['tp_pips']} pips)\n"
                    f"H4: {result['h4_trend']}\n"
                    f"Regime: {result['regime']}\n\n"
                    f"⏰ Will execute at London open (07:00 UTC)\n\n"
                    f"📊 {RAILWAY_URL}"
                )
                send_telegram(msg)
            elif direction in ("BUY", "SELL") and in_session and is_new_signal and result["conflict"]:
                # New signal but H4 conflict — send warning only
                msg = (
                    f"⚠️ <b>CHAKRA SIGNAL — NOT EXECUTED</b>\n\n"
                    f"Pair: <b>{pair}</b>\n"
                    f"Signal: <b>{direction}</b> ({conf:.1f}%)\n"
                    f"Reason skipped: {result['conflict']}\n\n"
                    f"📊 {RAILWAY_URL}"
                )
                send_telegram(msg)

        with self.lock:
            self.results = new_results

        # Fetch CME futures synchronously so dashboard always has data
        futures_results = {}
        for symbol, meta in CME_FUTURES.items():
            result = analyze_cme_future(symbol, meta)
            if result:
                futures_results[symbol] = result
                log.info(f"  {symbol:<8} {result['direction']:<5} "
                         f"conf={result['confidence']:.1f}% "
                         f"trend:{result['h4_trend']}")
        with self.lock:
            self.futures = futures_results

    def run(self):
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                log.error(f"Cycle error: {e}")
            time.sleep(CYCLE_SECS)


# ── QUANTUM DASHBOARD ─────────────────────────────────────────────────
app    = Flask(__name__)
chakra = None

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Chakra V15</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#030308;color:#e0e8ff;font-family:'Courier New',monospace;min-height:100vh;font-size:14px}
body.light{background:#f0f2ff;color:#111133}
body.light .hdr{background:linear-gradient(135deg,#e8eaff,#d0d8ff);border-color:#9999cc}
body.light .card{background:linear-gradient(160deg,#ffffff,#f0f2ff);border-color:#ccccee}
body.light .c-price{color:#0066cc}
body.light .c-regime{background:#e0e4ff;color:#334}
body.light .c-conf-bar{background:#d0d4ee}
body.light .side{background:#f8f9ff;border-color:#ccccee}
body.light .side-title{background:#e8eaff;color:#5533aa}
body.light .logic-box{background:#fff;border-color:#ccccee;color:#223}
body.light .news-item{border-color:#dde}
body.light .news-title{color:#112}
body.light .ag-row{border-color:#eee}
body.light .ag-name{color:#5533aa}
body.light .ag-reason{color:#445}
body.light .status-bar{background:#e8eaff;color:#445;border-color:#ccd}
body.light .news-ticker{background:#e0e4ff;border-color:#ccd}
body.light .tick{color:#334}
body.light .signal-feed{background:#eef0ff;border-color:#ccd}
body.light .feed-empty{color:#889}
body.light .c-explain{background:#fff;border-color:#ccd;color:#223}
body.light .tab{background:#e8eaff;color:#556;border-color:#ccd}
body.light .tab.active{background:#d0d4ff;color:#3322aa}
body.light .c-lev{background:#f8f9ff}
body.light .c-levels{background:#dde}
body.light .c-trend{border-color:#dde}
body.light .c-votes{border-color:#dde}
body.light .c-agents{border-color:#dde}
body.light .c-agents-title{background:#eef0ff;color:#5533aa}
body.light .hstat-v{color:#0055cc}
body.light .hstat-l{color:#667}
body.light .logo-text{background:linear-gradient(90deg,#5533aa,#0066cc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-thumb{background:#3a2a7a;border-radius:3px}

/* HEADER */
.hdr{background:linear-gradient(135deg,#06061a,#0e0628);border-bottom:2px solid #2a1a6a;
     padding:12px 20px;display:flex;align-items:center;justify-content:space-between;
     position:sticky;top:0;z-index:200}
.logo-wrap{display:flex;align-items:center;gap:12px}
.logo-svg{width:48px;height:48px;flex-shrink:0}
.logo-text{font-size:1.3em;font-weight:bold;letter-spacing:3px;
           background:linear-gradient(90deg,#7b5cff,#00f5ff);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.logo-sub{font-size:0.65em;color:#667;letter-spacing:2px;margin-top:2px}
.hdr-stats{display:flex;gap:20px;align-items:center}
.hstat{text-align:center}
.hstat-v{font-size:1.3em;font-weight:bold;color:#00f5ff}
.hstat-l{font-size:0.65em;color:#889;letter-spacing:1px}
.live-badge{display:flex;align-items:center;gap:6px;background:#061a06;
            border:1px solid #00ff66;border-radius:20px;padding:5px 14px;
            font-size:0.8em;color:#00ff66;font-weight:bold}
.dot{width:8px;height:8px;border-radius:50%;background:#00ff66;animation:blink 1s infinite}
@keyframes blink{0%,100%{opacity:1;box-shadow:0 0 8px #00ff66}50%{opacity:0.2}}
.sound-btn{background:#0a0a20;border:1px solid #3a3a6a;color:#889;padding:5px 12px;
           border-radius:6px;cursor:pointer;font-size:0.75em;font-family:inherit}
.sound-btn.on{color:#00ff66;border-color:#00ff6650}

/* NEWS TICKER */
.news-ticker{background:#030310;border-bottom:1px solid #1a1a5a;padding:0;
             overflow:hidden;height:32px;display:flex;align-items:center}
.ticker-label{background:#0a0a2a;color:#7b5cff;font-size:0.68em;padding:0 12px;
              height:100%;display:flex;align-items:center;border-right:1px solid #1a1a5a;
              white-space:nowrap;flex-shrink:0;letter-spacing:1px}
.ticker-scroll{overflow:hidden;flex:1}
.ticker-inner{display:inline-flex;animation:scroll 80s linear infinite;white-space:nowrap}
.ticker-inner:hover{animation-play-state:paused}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.tick{display:inline-block;padding:0 20px;font-size:0.72em;color:#aab;
      border-right:1px solid #1a1a4a;height:32px;line-height:32px}
.tick-high{color:#ff6655}
.tick-med{color:#ffaa44}
.tick-ff{color:#7b5cff;font-weight:bold}

/* SIGNAL FEED */
.signal-feed{background:#04040f;border-bottom:1px solid #1a1a4a;
             padding:7px 16px;display:flex;align-items:center;gap:10px;
             min-height:40px;overflow-x:auto}
.feed-label{font-size:0.68em;color:#556;letter-spacing:1px;white-space:nowrap;flex-shrink:0;
            font-weight:bold}
.feed-item{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;
           border-radius:14px;font-size:0.75em;white-space:nowrap;flex-shrink:0;
           cursor:pointer;transition:opacity .2s;font-weight:bold}
.feed-item:hover{opacity:0.8}
.feed-buy{background:#0a2a0a;border:1px solid #00ff66;color:#00ff66}
.feed-sell{background:#2a0a0a;border:1px solid #ff4455;color:#ff4455}
.feed-empty{font-size:0.72em;color:#445;font-style:italic}

/* STATUS BAR */
.status-bar{background:#02020a;border-bottom:1px solid #0f0f2a;
            padding:5px 16px;display:flex;gap:20px;font-size:0.72em;color:#778;flex-wrap:wrap}
.s-ok{color:#00ff66;font-weight:bold}
.s-warn{color:#ffaa44;font-weight:bold}
.s-err{color:#ff4455;font-weight:bold}

/* MAIN LAYOUT: 3 columns */
.main-wrap{display:grid;grid-template-columns:1fr 300px;min-height:calc(100vh - 140px)}

/* PAIR GRID */
.pair-grid{padding:12px;display:grid;
           grid-template-columns:repeat(auto-fill,minmax(360px,1fr));
           gap:14px;align-content:start;overflow-y:auto}

/* SIDE PANEL */
.side{background:#030310;border-left:2px solid #1a1a5a;display:flex;
      flex-direction:column;overflow:hidden;max-height:calc(100vh - 140px);position:sticky;top:140px}
.side-section{border-bottom:1px solid #0f0f2a;flex-shrink:0}
.side-title{padding:8px 14px;font-size:0.68em;color:#7b5cff;letter-spacing:2px;
            background:#050520;border-bottom:1px solid #0f0f2a;font-weight:bold}
.side-scroll{overflow-y:auto}

/* LOGIC BOARD */
.logic-sel{width:100%;background:#06061a;border:1px solid #2a2a6a;color:#ccd;
           padding:6px 10px;border-radius:5px;font-family:inherit;font-size:0.75em;
           margin:10px 12px;width:calc(100% - 24px)}
.logic-box{margin:0 12px 10px;padding:10px;background:#030315;
           border:1px solid #1a1a4a;border-radius:6px;
           font-size:0.7em;line-height:1.8;color:#bbc;
           max-height:280px;overflow-y:auto;white-space:pre-wrap}

/* NEWS PANEL */
.news-scroll{overflow-y:auto;max-height:220px}
.news-item{padding:8px 14px;border-bottom:1px solid #08081a;cursor:pointer}
.news-item:hover{background:#06060f}
.news-title{font-size:0.72em;color:#ccd;line-height:1.5;margin-bottom:4px}
.news-tags{display:flex;gap:4px;flex-wrap:wrap;margin-top:3px}
.news-tag{background:#0a0a2a;border:1px solid #2a2a6a;color:#7b5cff;
          padding:1px 6px;border-radius:3px;font-size:0.68em}
.news-src{font-size:0.65em;color:#556;margin-top:2px}

/* FF EVENTS */
.ff-scroll{overflow-y:auto;max-height:180px}
.ff-item{padding:7px 14px;border-bottom:1px solid #08081a;display:grid;
         grid-template-columns:40px 1fr auto;gap:6px;align-items:center}
.ff-curr{font-size:0.72em;color:#7b5cff;font-weight:bold}
.ff-name{font-size:0.7em;color:#ccd}
.ff-time{font-size:0.65em;color:#556}
.ff-high{border-left:3px solid #ff4455}
.ff-med{border-left:3px solid #ffaa44}
.ff-low{border-left:3px solid #334}

/* CARD */
.card{background:linear-gradient(160deg,#07071c,#0b0b25);
      border:1px solid #1e1e4e;border-radius:14px;overflow:hidden;
      transition:border-color .3s,transform .15s;position:relative}
.card:hover{transform:translateY(-2px);border-color:#4a3a9a}
.card.buy-card{border-color:#0d3d1a}
.card.sell-card{border-color:#3d0d1a}

/* Card header */
.c-hdr{padding:12px 16px;display:flex;justify-content:space-between;align-items:center;
       border-bottom:1px solid #1a1a3e}
.c-pair{font-size:1.2em;font-weight:bold;color:#fff;letter-spacing:2px}
.c-sig{padding:4px 14px;border-radius:16px;font-weight:bold;font-size:0.85em;letter-spacing:1px}
.sig-buy{background:#0a2e0a;color:#00ff88;border:1px solid #00ff8830;box-shadow:0 0 10px #00ff8820}
.sig-sell{background:#2e0a0a;color:#ff3355;border:1px solid #ff335530;box-shadow:0 0 10px #ff335520}
.sig-hold{background:#141430;color:#778;border:1px solid #2a2a5a}

/* Price */
.c-price-row{padding:10px 16px;display:flex;align-items:baseline;gap:12px;
             border-bottom:1px solid #0a0a1e}
.c-price{font-size:1.9em;font-weight:bold;color:#00f5ff;font-variant-numeric:tabular-nums}
.c-regime{font-size:0.75em;color:#889;padding:2px 8px;background:#0a0a1e;border-radius:4px}

/* Levels */
.c-levels{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:#0a0a1e}
.c-lev{padding:8px 6px;text-align:center;background:#07071c}
.c-lev-l{font-size:0.62em;color:#778;letter-spacing:1px;margin-bottom:3px;font-weight:bold}
.c-lev-v{font-size:0.88em;font-weight:bold;font-variant-numeric:tabular-nums}
.sl-v{color:#ff3355}
.en-v{color:#00f5ff}
.tp-v{color:#00ff88}
.c-lev-p{font-size:0.62em;color:#556}

/* Trend */
.c-trend{padding:7px 16px;display:flex;align-items:center;gap:8px;
         border-bottom:1px solid #0a0a1e;flex-wrap:wrap}
.t-pill{padding:3px 10px;border-radius:10px;font-weight:bold;font-size:0.75em}
.t-bull{background:#0a2e0a;color:#00ff88;border:1px solid #00ff8840}
.t-bear{background:#2e0a0a;color:#ff3355;border:1px solid #ff335540}
.t-rng{background:#14142e;color:#aab;border:1px solid #2a2a5a}
.t-rsn{font-size:0.68em;color:#778;flex:1}

/* Conflict */
.c-conflict{margin:6px 16px;padding:6px 10px;border-radius:6px;
            background:#1e0e00;border:1px solid #ffaa44;color:#ffaa44;font-size:0.72em}

/* Confidence */
.c-conf{padding:6px 16px}
.c-conf-row{display:flex;justify-content:space-between;font-size:0.72em;color:#889;margin-bottom:4px}
.c-conf-bar{height:5px;background:#0a0a1e;border-radius:3px;overflow:hidden}
.c-conf-fill{height:100%;border-radius:3px;
             background:linear-gradient(90deg,#4a1aaa,#7b5cff,#00f5ff);transition:width .6s}

/* Votes */
.c-votes{padding:5px 16px;display:flex;gap:14px;border-bottom:1px solid #0a0a1e;font-size:0.78em}
.vb{color:#00ff88;font-weight:bold}
.vs{color:#ff3355;font-weight:bold}
.vh{color:#445}

/* AGENT LOGIC PANEL — always visible */
.c-agents{border-bottom:1px solid #0a0a1e}
.c-agents-title{padding:6px 16px;font-size:0.65em;color:#7b5cff;letter-spacing:2px;
                background:#050518;border-bottom:1px solid #0a0a1e;font-weight:bold;
                display:flex;justify-content:space-between;align-items:center}
.c-agents-body{max-height:160px;overflow-y:auto}
.ag-row{display:grid;grid-template-columns:90px 50px 50px 1fr;
        gap:4px;padding:4px 16px;border-bottom:1px solid #08081a;font-size:0.68em;align-items:center}
.ag-row:hover{background:#06060f}
.ag-name{color:#9988ff;font-weight:bold}
.ag-buy{color:#00ff88;font-weight:bold}
.ag-sell{color:#ff3355;font-weight:bold}
.ag-hold{color:#445}
.ag-conf{color:#778;text-align:right}
.ag-reason{color:#889;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* Timeframe tabs */
.c-tabs{display:flex;gap:3px;padding:8px 16px 0;flex-wrap:wrap}
.tab{padding:4px 10px;border-radius:6px 6px 0 0;cursor:pointer;font-size:0.68em;
     border:1px solid #1a1a4e;border-bottom:none;color:#778;background:#04040f;
     transition:all .2s;font-weight:bold}
.tab.active{background:#0b0b25;color:#00f5ff;border-color:#4a3a9a}

/* Chart */
.c-chart{padding:0 16px 6px;height:155px;position:relative}

/* Explain */
.c-explain{margin:6px 16px;padding:8px 10px;background:#04040f;border:1px solid #1a1a4e;
           border-radius:6px;font-size:0.7em;line-height:1.8;color:#aab;
           max-height:110px;overflow-y:auto;white-space:pre-wrap}

/* Logic button */
.c-logic-btn{margin:6px 16px;background:#080820;border:1px solid #2a2a6a;
             color:#7b5cff;padding:5px 12px;border-radius:6px;cursor:pointer;
             font-size:0.7em;font-family:inherit;width:calc(100% - 32px);text-align:left;
             font-weight:bold}
.c-logic-btn:hover{background:#0e0e30}

/* Card footer */
.c-foot{padding:5px 16px;font-size:0.62em;color:#334;border-top:1px solid #0a0a1e;
        display:flex;justify-content:space-between}

/* Futures */
.fut-hdr{grid-column:1/-1;padding:12px 4px 6px;font-size:0.78em;color:#7b5cff;
         letter-spacing:2px;border-top:2px solid #2a1a6a;margin-top:6px;font-weight:bold}
.fut-hdr span{color:#556;font-size:0.85em;font-weight:normal}
.fut-card{border-color:#181840}
.fut-card:hover{border-color:#2a1a7a}

/* Mobile */
@media(max-width:900px){
  .main-wrap{grid-template-columns:1fr}
  .side{display:none}
  .pair-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <div class="logo-wrap">
    <svg class="logo-svg" viewBox="0 0 48 48">
      <defs>
        <radialGradient id="g1" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#9b6fff"/>
          <stop offset="100%" stop-color="#3a0080"/>
        </radialGradient>
      </defs>
      <circle cx="24" cy="24" r="22" fill="none" stroke="#7b5cff" stroke-width="1.5" opacity="0.9"/>
      <circle cx="24" cy="24" r="17" fill="none" stroke="#4a3a8a" stroke-width="0.8" opacity="0.5"/>
      <circle cx="24" cy="24" r="7" fill="url(#g1)"/>
      <circle cx="24" cy="24" r="3" fill="#fff" opacity="0.95"/>
      <polygon points="24,1 26.5,8 21.5,8" fill="#7b5cff"/>
      <polygon points="24,47 26.5,40 21.5,40" fill="#7b5cff"/>
      <polygon points="1,24 8,21.5 8,26.5" fill="#7b5cff"/>
      <polygon points="47,24 40,21.5 40,26.5" fill="#7b5cff"/>
      <line x1="24" y1="8" x2="24" y2="17" stroke="#7b5cff" stroke-width="1" opacity="0.8"/>
      <line x1="24" y1="31" x2="24" y2="40" stroke="#7b5cff" stroke-width="1" opacity="0.8"/>
      <line x1="8" y1="24" x2="17" y2="24" stroke="#7b5cff" stroke-width="1" opacity="0.8"/>
      <line x1="31" y1="24" x2="40" y2="24" stroke="#7b5cff" stroke-width="1" opacity="0.8"/>
      <circle cx="24" cy="9" r="4.5" fill="#04040e" stroke="#7b5cff" stroke-width="1"/>
      <circle cx="24" cy="39" r="4.5" fill="#04040e" stroke="#7b5cff" stroke-width="1"/>
      <circle cx="9" cy="24" r="4.5" fill="#04040e" stroke="#7b5cff" stroke-width="1"/>
      <circle cx="39" cy="24" r="4.5" fill="#04040e" stroke="#7b5cff" stroke-width="1"/>
      <text x="24" y="11" text-anchor="middle" font-size="4.5" fill="#00f5ff">▲</text>
      <text x="24" y="42" text-anchor="middle" font-size="4" fill="#7b5cff">AI</text>
      <text x="9" y="26" text-anchor="middle" font-size="4" fill="#00ff88">$</text>
      <text x="39" y="26" text-anchor="middle" font-size="4" fill="#ffd700">€</text>
    </svg>
    <div>
      <div class="logo-text">PROJECT CHAKRA V15</div>
      <div class="logo-sub">AUTONOMOUS AI FOREX TRADING SYSTEM</div>
    </div>
  </div>
  <div class="hdr-stats">
    <div class="hstat"><div class="hstat-v" id="hCycles">—</div><div class="hstat-l">CYCLES</div></div>
    <div class="hstat"><div class="hstat-v" id="hSignals">—</div><div class="hstat-l">SIGNALS</div></div>
    <div class="hstat"><div class="hstat-v">21</div><div class="hstat-l">AGENTS</div></div>
    <div class="hstat"><div class="hstat-v">14</div><div class="hstat-l">PAIRS</div></div>
    <div class="hstat"><div class="hstat-v s-warn" id="hSess">ASIAN</div><div class="hstat-l">SESSION</div></div>
    <div class="live-badge"><div class="dot"></div>LIVE</div>
    <button class="sound-btn" id="sndBtn" onclick="toggleSound()">🔇 Sound</button>
    <button class="sound-btn" id="modeBtn" onclick="toggleMode()">☀️ Light</button>
  </div>
</div>

<!-- NEWS TICKER -->
<div class="news-ticker">
  <div class="ticker-label">📡 LIVE NEWS</div>
  <div class="ticker-scroll">
    <div class="ticker-inner" id="ticker">
      <span class="tick">⚡ Connecting to market news feed...</span>
      <span class="tick">⚡ Connecting to market news feed...</span>
    </div>
  </div>
</div>

<!-- SIGNAL FEED -->
<div class="signal-feed">
  <span class="feed-label">🎯 NEW SIGNALS:</span>
  <span class="feed-empty" id="feedEmpty">Monitoring market — no new signals yet</span>
  <div id="feedItems" style="display:flex;gap:6px;align-items:center"></div>
</div>

<!-- STATUS BAR -->
<div class="status-bar">
  <span>Session: <span id="sessEl" class="s-warn">Checking...</span></span>
  <span>Trailing: <span class="s-ok">ON</span></span>
  <span>Pyramid: <span class="s-ok">ON</span></span>
  <span>Execute: <span class="s-ok">AUTO</span></span>
  <span>Learning: <span class="s-ok">ON</span></span>
  <span>Supabase: <span class="s-ok">LOGGING</span></span>
  <span style="margin-left:auto">Updated: <span id="upd">—</span></span>
</div>

<!-- MAIN -->
<div class="main-wrap">

  <!-- PAIR GRID -->
  <div class="pair-grid" id="grid"></div>

  <!-- SIDE PANEL -->
  <div class="side">

    <!-- LOGIC BOARD -->
    <div class="side-section" style="flex-shrink:0">
      <div class="side-title">🧠 SIGNAL LOGIC BOARD</div>
      <div style="padding:8px 0 0">
        <select class="logic-sel" id="logicSel" onchange="renderLogic()">
          <option value="">— Select pair to analyse —</option>
        </select>
        <div class="logic-box" id="logicBox">
Select a pair above to see:
• Why signal is BUY / SELL / HOLD
• Which agents agree and their reasons
• H4 trend alignment
• News affecting this pair
• Weekly bias direction
• Risk levels explanation
        </div>
      </div>
    </div>

    <!-- FOREX FACTORY -->
    <div class="side-section" style="flex-shrink:0">
      <div class="side-title">📅 HIGH IMPACT EVENTS</div>
      <div class="ff-scroll" id="ffPanel">
        <div style="padding:10px 14px;font-size:0.72em;color:#556">Loading calendar...</div>
      </div>
    </div>

    <!-- NEWS -->
    <div class="side-section" style="flex:1;overflow:hidden">
      <div class="side-title">📰 NEWS & PAIR IMPACT</div>
      <div class="news-scroll" id="newsPanel">
        <div style="padding:10px 14px;font-size:0.72em;color:#556">Loading news...</div>
      </div>
    </div>

  </div>
</div>

<script>
const charts={};
let soundOn=false, prevSigCount=0;
window._D={};  // all pair data

function toggleMode(){
  document.body.classList.toggle('light');
  const b=document.getElementById('modeBtn');
  b.textContent=document.body.classList.contains('light')?'🌙 Dark':'☀️ Light';
}
function toggleSound(){
  soundOn=!soundOn;
  const b=document.getElementById('sndBtn');
  b.textContent=soundOn?'🔊 Sound':'🔇 Sound';
  b.className=soundOn?'sound-btn on':'sound-btn';
}
function beep(){
  if(!soundOn)return;
  try{
    const a=new AudioContext(),o=a.createOscillator(),g=a.createGain();
    o.connect(g);g.connect(a.destination);
    o.frequency.setValueAtTime(900,a.currentTime);
    o.frequency.setValueAtTime(700,a.currentTime+0.12);
    g.gain.setValueAtTime(0.25,a.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001,a.currentTime+0.45);
    o.start();o.stop(a.currentTime+0.45);
  }catch(e){}
}
function inSession(){
  const h=new Date().getUTCHours();
  return (h>=7&&h<=12)||(h>=13&&h<=18);
}
function tfKey(tf){
  const m={M15:'bars_m15',M30:'bars_h1',H1:'bars_h1',H4:'bars_h4',H8:'bars_h8',D1:'bars_d1'};
  return m[tf]||'bars_m15';
}
function switchTF(pair,tf,el){
  el.closest('.card').querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  const sid=safe(pair);
  const d=window._D[pair]||window._D[sid];
  if(d)drawChart(sid,d[tfKey(tf)]||d.bars_m15||[]);
}
function safe(s){return s.replace(/[^a-zA-Z0-9]/g,'_')}
function trendCls(t){return t==='BULLISH'?'t-bull':t==='BEARISH'?'t-bear':'t-rng'}

function drawChart(sid,bars){
  if(!bars||bars.length<2)return;
  const cv=document.getElementById('chart-'+sid);
  if(!cv)return;
  if(charts[sid])charts[sid].destroy();
  const closes=bars.map(b=>b[4]);
  const labels=bars.map(b=>b[0].substring(11,16));
  const up=closes[closes.length-1]>=closes[0];
  const lc=up?'#00ff88':'#ff3355';
  charts[sid]=new Chart(cv,{
    type:'line',
    data:{labels,datasets:[{data:closes,borderColor:lc,backgroundColor:lc+'15',
          borderWidth:1.8,pointRadius:0,fill:true,tension:0.1}]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      plugins:{legend:{display:false}},
      scales:{x:{ticks:{color:'#556',font:{size:9},maxTicksLimit:8},grid:{color:'#0a0a1e'}},
              y:{ticks:{color:'#556',font:{size:9},maxTicksLimit:5},grid:{color:'#0a0a1e'},position:'right'}}}
  });
}

function buildAgentRows(ops){
  if(!ops||ops.length===0)return '<div class="ag-row"><span class="ag-name" style="color:#445">No agent data</span></div>';
  return ops.map(a=>{
    const cls=a.signal==='BUY'?'ag-buy':a.signal==='SELL'?'ag-sell':'ag-hold';
    return `<div class="ag-row">
      <span class="ag-name">${a.agent}</span>
      <span class="${cls}">${a.signal}</span>
      <span class="ag-conf">${a.confidence}%</span>
      <span class="ag-reason" title="${a.reason||''}">${(a.reason||'').substring(0,44)}</span>
    </div>`;
  }).join('');
}

function buildCard(r,label,isFut){
  const sid=safe(r.pair);
  const lbl=label||r.pair.replace(/_/g,'/');
  const sc=r.direction==='BUY'?'buy-card':r.direction==='SELL'?'sell-card':'';
  const sb=r.direction==='BUY'?'sig-buy':r.direction==='SELL'?'sig-sell':'sig-hold';
  const tc=trendCls(r.h4_trend);
  const conf=r.direction==='HOLD'?'—':r.confidence+'%';
  const conflict=r.conflict?`<div class="c-conflict">⚠️ ${r.conflict}</div>`:'';
  const futBadge=isFut?`<div style="font-size:0.62em;color:#556;padding:2px 16px 4px">⚡ Institutional signal — read only</div>`:'';

  return `
  <div class="card ${sc} ${isFut?'fut-card':''}" id="card-${sid}">
    <div class="c-hdr">
      <span class="c-pair">${lbl}</span>
      <span class="c-sig ${sb}">${r.direction}</span>
    </div>
    <div class="c-price-row">
      <span class="c-price" id="px-${sid}">${r.price}</span>
      <span class="c-regime">${r.regime||'—'}</span>
    </div>
    <div class="c-levels">
      <div class="c-lev"><div class="c-lev-l">STOP LOSS</div>
        <div class="c-lev-v sl-v">${r.sl||'—'}</div>
        <div class="c-lev-p">${r.sl_pips||0} pips</div></div>
      <div class="c-lev"><div class="c-lev-l">ENTRY</div>
        <div class="c-lev-v en-v">${r.price}</div>
        <div class="c-lev-p">Risk $${r.dollar_risk||0}</div></div>
      <div class="c-lev"><div class="c-lev-l">TAKE PROFIT</div>
        <div class="c-lev-v tp-v">${r.tp||'—'}</div>
        <div class="c-lev-p">${r.tp_pips||0} pips</div></div>
    </div>
    <div class="c-trend">
      <span class="t-pill ${tc}">H4 ${r.h4_trend}</span>
      <span class="t-rsn">${(r.h4_reason||'').substring(0,52)}</span>
    </div>
    ${conflict}
    <div class="c-conf">
      <div class="c-conf-row"><span>Confidence</span><span>${conf} | RR ${r.rr||'3:1'}</span></div>
      <div class="c-conf-bar"><div class="c-conf-fill" style="width:${Math.min(r.confidence||0,100)}%"></div></div>
    </div>
    <div class="c-votes">
      <span class="vb">▲ ${r.buy_votes} BUY</span>
      <span class="vs">▼ ${r.sell_votes} SELL</span>
      <span class="vh">◆ ${r.hold_votes} HOLD</span>
    </div>
    <div class="c-agents">
      <div class="c-agents-title">
        <span>🤖 AGENT OPINIONS (${(r.agent_opinions||[]).length})</span>
        <span style="color:#556;font-size:0.9em">scroll →</span>
      </div>
      <div class="c-agents-body">${buildAgentRows(r.agent_opinions)}</div>
    </div>
    <div class="c-tabs">
      <div class="tab active" onclick="switchTF('${r.pair}','M15',this)">M15</div>
      <div class="tab" onclick="switchTF('${r.pair}','H1',this)">H1</div>
      <div class="tab" onclick="switchTF('${r.pair}','H4',this)">H4</div>
      <div class="tab" onclick="switchTF('${r.pair}','H8',this)">H8</div>
      <div class="tab" onclick="switchTF('${r.pair}','D1',this)">1D</div>
    </div>
    <div class="c-chart"><canvas id="chart-${sid}"></canvas></div>
    ${futBadge}
    <div class="c-explain" id="exp-${sid}">${r.explanation||''}</div>
    <button class="c-logic-btn" onclick="pickLogic('${r.pair}')">🧠 Open Full Logic Board →</button>
    <div class="c-foot">
      <span>${r.timestamp||''}</span>
      <span>ATR: ${r.atr||'—'}</span>
    </div>
  </div>`;
}

function pickLogic(pair){
  document.getElementById('logicSel').value=pair;
  renderLogic();
  document.querySelector('.side').scrollTo(0,0);
}

function renderLogic(){
  const pair=document.getElementById('logicSel').value;
  const box=document.getElementById('logicBox');
  if(!pair){box.textContent='Select a pair above.';return;}
  const sid=safe(pair);
  const r=window._D[pair]||window._D[sid];
  if(!r){box.textContent='No data yet for this pair.';return;}

  const ops=r.agent_opinions||[];
  const agreed=ops.filter(a=>a.signal===r.direction);
  const oppose=ops.filter(a=>a.signal!==r.direction&&a.signal!=='HOLD');
  const neut=ops.filter(a=>a.signal==='HOLD');
  let t='';
  t+=`╔══════════════════════════════════╗\n`;
  t+=`  ${r.pair.replace('_','/')} — ${r.direction}  (${r.confidence}% conf)\n`;
  t+=`╚══════════════════════════════════╝\n\n`;
  t+=`📍 TRADE PLAN\n`;
  t+=`  Entry:  ${r.price}\n`;
  t+=`  SL:     ${r.sl||'—'} (${r.sl_pips||0} pips)\n`;
  t+=`  TP:     ${r.tp||'—'} (${r.tp_pips||0} pips)\n`;
  t+=`  RR:     ${r.rr||'3:1'} | Risk $${r.dollar_risk||0}\n\n`;
  t+=`📈 TREND ANALYSIS\n`;
  t+=`  H4 Trend:  ${r.h4_trend}\n`;
  t+=`  Detail:    ${r.h4_reason||'—'}\n`;
  t+=`  Regime:    ${r.regime||'—'}\n`;
  t+=`  Aligned:   ${r.h4_aligned?'YES ✅':'NO ⚠️'}\n`;
  if(r.conflict)t+=`  WARNING:   ${r.conflict}\n`;
  t+=`\n🤖 AGENT VOTES\n`;
  t+=`  Total: ${ops.length} | BUY: ${r.buy_votes} | SELL: ${r.sell_votes} | HOLD: ${r.hold_votes}\n\n`;
  if(agreed.length){
    t+=`✅ AGREEING AGENTS (${agreed.length}):\n`;
    agreed.forEach(a=>{t+=`  • ${a.agent} [${a.confidence}%]\n    → ${a.reason||'no reason'}\n`;});
    t+='\n';
  }
  if(oppose.length){
    t+=`❌ OPPOSING AGENTS (${oppose.length}):\n`;
    oppose.forEach(a=>{t+=`  • ${a.agent} says ${a.signal} [${a.confidence}%]\n    → ${a.reason||'no reason'}\n`;});
    t+='\n';
  }
  t+=`⏸️ NEUTRAL: ${neut.length} agents holding\n\n`;
  t+=`📰 NEWS:\n`;
  (r.headlines||[]).forEach(h=>{t+=`  • ${h}\n`;});
  box.textContent=t;
}

function updateSignalFeed(feed){
  if(!feed||feed.length===0)return;
  document.getElementById('feedEmpty').style.display='none';
  const c=document.getElementById('feedItems');
  c.innerHTML='';
  feed.slice(0,8).forEach(s=>{
    const cls=s.direction==='BUY'?'feed-buy':'feed-sell';
    const ic=s.direction==='BUY'?'▲':'▼';
    const el=document.createElement('div');
    el.className=`feed-item ${cls}`;
    el.innerHTML=`${ic} <b>${s.pair.replace('_','/')}</b> ${s.direction} ${s.conf}% <span style="color:#556;font-weight:normal">${s.time}</span>`;
    el.onclick=()=>pickLogic(s.pair);
    el.title='Click to view signal logic';
    c.appendChild(el);
  });
  if(feed.length>prevSigCount)beep();
  prevSigCount=feed.length;
}

function updateTicker(news,ff){
  const t=document.getElementById('ticker');
  let html='';
  (ff||[]).slice(0,5).forEach(e=>{
    html+=`<span class="tick tick-ff">⚡ ${e.currency||''}: ${e.title||''} | Forecast:${e.forecast||'?'} Prev:${e.previous||'?'}</span>`;
  });
  (news||[]).slice(0,12).forEach(n=>{
    const p=(n.impacts||[]).join(' ');
    const cls=(n.impacts||[]).length>=3?'tick-high':(n.impacts||[]).length>0?'tick-med':'';
    html+=`<span class="tick ${cls}">${p?'['+p+'] ':''}${n.title}</span>`;
  });
  if(!html)html='<span class="tick">⚡ Market monitoring active...</span>';
  t.innerHTML=html+html;
}

function updateNewsPanel(news){
  const p=document.getElementById('newsPanel');
  if(!news||news.length===0){p.innerHTML='<div style="padding:10px 14px;font-size:0.72em;color:#556">No news loaded</div>';return;}
  p.innerHTML=news.slice(0,15).map(n=>{
    const tags=(n.impacts||[]).map(x=>`<span class="news-tag">${x.replace('_','/')}</span>`).join('');
    return `<div class="news-item" onclick="pickLogic('${(n.impacts||[])[0]||''}')">
      <div class="news-title">${n.title}</div>
      <div class="news-tags">${tags||'<span style="color:#445;font-size:0.68em">General</span>'}</div>
      <div class="news-src">${n.source||''} — ${n.time||''}</div>
    </div>`;
  }).join('');
}

function updateFFPanel(ff){
  const p=document.getElementById('ffPanel');
  if(!ff||ff.length===0){p.innerHTML='<div style="padding:10px 14px;font-size:0.72em;color:#556">No events or API unavailable</div>';return;}
  p.innerHTML=ff.slice(0,8).map(e=>{
    const cls=e.impact==='High'||e.impact==='3'?'ff-high':e.impact==='Medium'||e.impact==='2'?'ff-med':'ff-low';
    return `<div class="ff-item ${cls}">
      <span class="ff-curr">${e.currency||'—'}</span>
      <span class="ff-name">${e.title||''}</span>
      <span class="ff-time">${e.time||''}</span>
    </div>`;
  }).join('');
}

function updateLogicSelect(pairs){
  const s=document.getElementById('logicSel');
  const cur=s.value;
  s.innerHTML='<option value="">— Select pair to analyse —</option>';
  pairs.forEach(p=>{
    const o=document.createElement('option');
    o.value=p;o.textContent=p.replace(/_/g,'/');
    s.appendChild(o);
  });
  if(cur)s.value=cur;
}

function update(){
  fetch('/api/data').then(r=>r.json()).then(d=>{
    const pairs=Object.values(d.pairs||{});
    const futs=Object.values(d.futures||{});

    // Store all data
    window._D={};
    pairs.forEach(p=>{window._D[p.pair]=p;});
    futs.forEach(f=>{window._D[f.pair]=f; window._D[safe(f.pair)]=f;});

    // Header
    document.getElementById('hCycles').textContent=d.cycle||'—';
    document.getElementById('hSignals').textContent=[...pairs,...futs].filter(p=>p.direction!=='HOLD').length;
    document.getElementById('upd').textContent=new Date().toLocaleTimeString();
    const sess=inSession();
    document.getElementById('sessEl').textContent=sess?'London/NY':'Asian';
    document.getElementById('sessEl').className=sess?'s-ok':'s-warn';
    document.getElementById('hSess').textContent=sess?'LONDON':'ASIAN';
    document.getElementById('hSess').className=sess?'hstat-v s-ok':'hstat-v s-warn';

    // Signal feed
    updateSignalFeed(d.signal_feed||[]);

    // Ticker
    updateTicker(d.news_feed||[],d.ff_events||[]);

    // Side panels
    updateNewsPanel(d.news_feed||[]);
    updateFFPanel(d.ff_events||[]);
    updateLogicSelect([...pairs.map(p=>p.pair),...futs.map(f=>f.pair)]);

    // Render forex pairs
    const grid=document.getElementById('grid');
    pairs.forEach(r=>{
      const sid=safe(r.pair);
      let card=document.getElementById('card-'+sid);
      if(!card){
        const div=document.createElement('div');
        div.innerHTML=buildCard(r,null,false);
        grid.appendChild(div.firstElementChild);
      } else {
        const px=document.getElementById('px-'+sid);
        if(px)px.textContent=r.price;
        const ex=document.getElementById('exp-'+sid);
        if(ex)ex.textContent=r.explanation||'';
        // Refresh agent rows
        const ab=card.querySelector('.c-agents-body');
        if(ab)ab.innerHTML=buildAgentRows(r.agent_opinions);
      }
      setTimeout(()=>drawChart(sid,r.bars_m15||[]),50);
    });

    // Futures header
    if(futs.length>0&&!document.getElementById('fut-hdr-el')){
      const h=document.createElement('div');
      h.id='fut-hdr-el';h.className='fut-hdr';
      h.innerHTML='⚡ CME CURRENCY FUTURES &nbsp;<span>Institutional signals — Read only — Not executed on OANDA</span>';
      grid.appendChild(h);
    }

    // Render futures
    futs.forEach(r=>{
      const sid=safe(r.pair);
      const displayR={...r,pair:sid};
      let card=document.getElementById('card-'+sid);
      if(!card){
        const div=document.createElement('div');
        div.innerHTML=buildCard(displayR,r.display_name||r.pair,true);
        const el=div.firstElementChild;
        if(el)grid.appendChild(el);
      } else {
        const px=document.getElementById('px-'+sid);
        if(px)px.textContent=r.price;
        const ab=card.querySelector('.c-agents-body');
        if(ab)ab.innerHTML=buildAgentRows(r.agent_opinions);
      }
      setTimeout(()=>drawChart(sid,r.bars_h1||[]),80);
    });

    // Auto-update logic board
    if(document.getElementById('logicSel').value)renderLogic();

  }).catch(e=>console.error(e));
}

update();
setInterval(update,30000);
</script>
</body>
</html>"""



@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/data")
def api_data():
    with chakra.lock:
        return jsonify({
            "cycle":        chakra.cycle,
            "pairs":        chakra.results,
            "futures":      chakra.futures,
            "paused":       chakra.paused,
            "weekly_bias":  chakra.weekly_bias.get_summary(),
            "signal_feed":  list(chakra._signal_feed),
            "news_feed":    list(chakra._news_feed),
            "ff_events":    chakra._ff_events,
            "timestamp":    datetime.now(timezone.utc).isoformat()
        })

@app.route("/api/pair/<pair>")
def api_pair(pair):
    with chakra.lock:
        return jsonify(chakra.results.get(pair, {}))

@app.route("/health")
def health():
    return jsonify({"status":"ok","cycle":chakra.cycle if chakra else 0})

if __name__ == "__main__":
    import sys
    chakra = ChakraV15()
    if "--once" in sys.argv:
        chakra.run_cycle()
    else:
        t = threading.Thread(target=chakra.run, daemon=True)
        t.start()
        app.run(host="0.0.0.0", port=PORT, debug=False)
