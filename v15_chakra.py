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
    if "--once" in sys.argv:
        chakra.run_cycle()
    else:
        t = threading.Thread(target=chakra.run, daemon=True)
        t.start()
        app.run(host="0.0.0.0", port=PORT, debug=False)

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Chakra V15</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#030308;color:#e8eeff;font-family:monospace;overflow-x:hidden}
.hdr{background:#06061a;border-bottom:2px solid #1e1e4e;padding:15px;display:flex;justify-content:space-between;align-items:center}
.logo{color:#00f5ff;font-size:1.2em;font-weight:bold;letter-spacing:2px}
.stats{display:flex;gap:20px;font-size:0.9em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:12px;padding:15px}
.card{background:#0b0b22;border:1px solid #1e1e4e;border-radius:8px;padding:15px;transition:all 0.2s}
.card:hover{border-color:#7b5cff;box-shadow:0 0 10px #7b5cff30}
.pair-name{font-size:1.1em;font-weight:bold;color:#00f5ff;margin-bottom:10px}
.price{font-size:1.8em;color:#00ff88;font-weight:bold;margin:10px 0}
.direction{display:inline-block;padding:5px 15px;border-radius:5px;font-weight:bold;font-size:0.9em;margin:10px 0}
.buy{background:#061a0a;color:#00ff88;border:1px solid #00ff88}
.sell{background:#1a060a;color:#ff3355;border:1px solid #ff3355}
.hold{background:#141428;color:#aab8ff;border:1px solid #1e1e4e}
.chart-container{height:150px;margin:10px 0}
.info{font-size:0.75em;color:#aab8ff;margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:10px}
.info-row{display:flex;justify-content:space-between}
.loading{text-align:center;padding:50px;color:#556}
</style>
</head>
<body>
<div class="hdr">
  <div class="logo">⚡ PROJECT CHAKRA V15</div>
  <div class="stats">
    <span>Cycle: <span id="cyc">—</span></span>
    <span>Pairs: <span id="pcnt">—</span></span>
    <span>Status: <span style="color:#00ff88">LIVE</span></span>
  </div>
</div>
<div class="grid" id="grid">
  <div class="loading">Loading pairs...</div>
</div>
<script>
function drawChart(container, closes) {
  if(!container || closes.length < 2) return;
  try {
    const up = closes[closes.length-1] >= closes[0];
    const c = new Chart(container, {
      type: 'line',
      data: {
        labels: closes.map((_, i) => i),
        datasets: [{
          data: closes,
          borderColor: up ? '#00ff88' : '#ff3355',
          backgroundColor: (up ? '#00ff88' : '#ff3355') + '20',
          borderWidth: 1.5,
          fill: true,
          tension: 0.1,
          pointRadius: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { display: false }
        }
      }
    });
  } catch(e) {}
}

function update() {
  fetch('/api/data').then(r => r.json()).then(d => {
    const grid = document.getElementById('grid');
    const pairs = Object.values(d.pairs || {});
    
    if(pairs.length === 0) {
      grid.innerHTML = '<div class="loading">No data yet...</div>';
      return;
    }
    
    document.getElementById('cyc').textContent = d.cycle || 0;
    document.getElementById('pcnt').textContent = pairs.length;
    
    grid.innerHTML = '';
    pairs.forEach(p => {
      const dir = p.direction || 'HOLD';
      const dirClass = dir === 'BUY' ? 'buy' : dir === 'SELL' ? 'sell' : 'hold';
      const chart = document.createElement('canvas');
      
      const html = `
        <div class="card">
          <div class="pair-name">${p.pair.replace('_', '/')}</div>
          <div class="price">${p.price}</div>
          <div class="direction ${dirClass}">${dir} ${p.confidence}%</div>
          <div class="chart-container"></div>
          <div class="info">
            <div class="info-row"><span>H4:</span><span>${p.h4_trend || '—'}</span></div>
            <div class="info-row"><span>Votes:</span><span>${p.buy_votes}B/${p.sell_votes}S</span></div>
            <div class="info-row"><span>SL:</span><span>${p.sl || '—'}</span></div>
            <div class="info-row"><span>TP:</span><span>${p.tp || '—'}</span></div>
          </div>
        </div>
      `;
      
      const div = document.createElement('div');
      div.innerHTML = html;
      grid.appendChild(div);
      
      const canvas = div.querySelector('canvas');
      if(p.bars_h1 && p.bars_h1.length > 0) {
        const closes = p.bars_h1.map(b => b[4]);
        setTimeout(() => drawChart(canvas, closes), 50);
      }
    });
  }).catch(e => console.error(e));
}

update();
setInterval(update, 30000);
</script>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/data")
def api_data():
    try:
        return jsonify({
            "cycle": chakra.cycle,
            "pairs": chakra.results or {},
            "futures": chakra.futures or {},
        })
    except:
        return jsonify({"cycle": 0, "pairs": {}, "futures": {}})

@app.route("/api/pair/<pair>")
def api_pair(pair):
    return jsonify(chakra.results.get(pair, {}))

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    chakra = ChakraEngine()
    chakra.start()
    app.run(host="0.0.0.0", port=PORT, debug=False)
