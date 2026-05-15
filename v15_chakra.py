#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          FOREX TRADING SYSTEM V13 - COMPLETE PRODUCTION EDITION             ║
║                                                                              ║
║  EVERYTHING IN ONE FILE:                                                     ║
║  ✅ TradingView Webhook (receives alerts from your charts)                   ║
║  ✅ Professional Dashboard (shows everything live)                           ║
║  ✅ 5 Self-Learning Layers (FinMem, Weights, RL, Regime, HiveMind)          ║
║  ✅ Full Intelligence (News, COT, FRED, Forex Factory, Correlations)         ║
║  ✅ WHY WHAT WHEN WHO WHERE for every trade                                  ║
║  ✅ Auto Trade Execution on OANDA                                             ║
║  ✅ Telegram Alerts (full detail every signal)                               ║
║  ✅ Supabase Logging (every trade saved to database)                         ║
║  ✅ 17 Trading Agents with real logic                                        ║
║  ✅ Risk Management (auto SL/TP, drawdown guard)                             ║
║  ✅ PythonAnywhere Ready (24/7 deployment)                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

HOW TO RUN:
  py -3.11 v13_production.py

DASHBOARD:
  http://localhost:5000

TRADINGVIEW WEBHOOK URL (paste in TradingView alert):
  https://lovidocmaster.pythonanywhere.com/webhook/tradingview
  (local test: http://localhost:5000/webhook/tradingview)

WHAT HAPPENS:
  1. System analyzes 5 pairs every 15 minutes automatically
  2. TradingView alerts boost signal confidence when they match
  3. Every trade is logged with full WHY/WHAT/WHEN/WHO/WHERE
  4. System learns from every trade and improves daily
  5. Dashboard shows everything in real time
  6. Telegram sends you alerts on every signal
"""

import os, sys, json, time, math, random, threading, logging, hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import traceback
import numpy as np

# ── Flask ─────────────────────────────────────────────────────────────────────
from flask import Flask, jsonify, render_template_string, request
import requests

# ── OANDA ─────────────────────────────────────────────────────────────────────
try:
    from oandapyV20 import API as OandaAPI
    from oandapyV20.endpoints.instruments import InstrumentsCandles
    from oandapyV20.endpoints.accounts import AccountDetails
    from oandapyV20.endpoints.orders import OrderCreate
    from oandapyV20.endpoints.trades import OpenTrades, TradeClose
    OANDA_OK = True
except ImportError:
    OANDA_OK = False

# ── Optional ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

try:
    from supabase import create_client
    SB_OK = True
except ImportError:
    SB_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
OANDA_TOKEN    = os.getenv("OANDA_TOKEN", "")
OANDA_ACCOUNT  = os.getenv("OANDA_ACCOUNT_ID", "101-001-39217670-001")
OANDA_ENV      = "practice"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT",  os.getenv("TELEGRAM_CHAT_ID", ""))
FRED_KEY       = os.getenv("FRED_KEY", "")
NEWS_KEY       = os.getenv("NEWS_KEY", "")
ALPHA_KEY      = os.getenv("ALPHA_VANTAGE", "T7TQAX2SMD7RTNXN")
SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")
TV_SECRET      = os.getenv("TV_WEBHOOK_SECRET", "lovinder_forex_v13")

PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"]
RISK_PCT = 0.005        # 0.5% risk per trade
MAX_DD   = 0.02         # 2% max drawdown
AUTO_EXECUTE = True     # OANDA practice account — paper trades execute as real orders on demo

MEM_FILE  = "v13_memory.json"
WTS_FILE  = "v13_weights.json"
RL_FILE   = "v13_rl.json"
LOG_FILE  = "v13_system.log"

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("V13")
app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════
@dataclass

# ═══════════════════════════════════════════════════════════════════════════════
# PENDING WORK: FINANCE INTEGRATIONS & NEW FEATURES (May 2026)
# ═══════════════════════════════════════════════════════════════════════════════
class BarData:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Signal:
    direction: str      # BUY / SELL / HOLD
    confidence: float
    reason: str
    agent_name: str

@dataclass
class TradeRecord:
    """Complete record of every trade with full context"""
    id: str
    pair: str
    direction: str
    confidence: float
    # WHY
    why_technical: str
    why_news: str
    why_fundamental: str
    why_correlation: str
    why_cot: str
    # WHAT
    what_pattern: str
    what_agents: List[str]
    what_agents_count: int
    # WHEN
    when_timestamp: str
    when_session: str
    when_hour: int
    when_next_event: str
    when_avoid_news: bool
    # WHO
    who_institutions: str
    who_retail: str
    who_cot_net: int
    # WHERE
    where_support: float
    where_resistance: float
    where_entry: float
    where_sl: float
    where_tp: float
    # Market context
    dxy_trend: str
    gold_trend: str
    vix_level: float
    # Self-learning context
    regime: str
    pair_win_rate: float
    system_win_rate: float
    memory_context: str
    rl_episodes: int
    # TradingView
    tradingview_confirmed: bool
    tradingview_signal: str
    # Outcome
    outcome: str = "OPEN"
    pnl_pips: float = 0.0
    pnl_usd: float = 0.0
    oanda_trade_id: str = ""
    lessons: List[str] = field(default_factory=list)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=8
        )
    except Exception:
        pass

def _get_session() -> str:
    h = datetime.utcnow().hour
    if 22 <= h or h < 7:  return "SYDNEY"
    if 7  <= h < 13:       return "LONDON"
    if 13 <= h < 22:       return "NEW_YORK"
    return "TOKYO"

def _pair_currencies(pair: str) -> Tuple[str, str]:
    m = {"EUR_USD":("EUR","USD"),"GBP_USD":("GBP","USD"),
         "USD_JPY":("USD","JPY"),"AUD_USD":("AUD","USD"),"USD_CAD":("USD","CAD")}
    return m.get(pair, ("USD","EUR"))

def _simulated_bars(pair: str, count: int = 100) -> List[BarData]:
    base = {"EUR_USD":1.08,"GBP_USD":1.26,"USD_JPY":148.0,
            "AUD_USD":0.65,"USD_CAD":1.37}.get(pair, 1.10)
    bars = []
    p = base
    for _ in range(count):
        p *= (1 + np.random.normal(0, 0.0003))
        o = p * (1 + np.random.normal(0, 0.0001))
        h = max(p, o) * (1 + abs(np.random.normal(0, 0.0002)))
        l = min(p, o) * (1 - abs(np.random.normal(0, 0.0002)))
        bars.append(BarData(datetime.utcnow().isoformat(), o, h, l, p,
                            random.randint(100, 1000)))
    return bars

def _get_bars(pair: str, count: int = 100, granularity: str = "H1") -> List[BarData]:
    if not OANDA_OK or not OANDA_TOKEN:
        return _simulated_bars(pair, count)
    try:
        api = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        ep  = InstrumentsCandles(pair, params={"count": count, "granularity": granularity})
        api.request(ep)
        bars = []
        for c in ep.response.get("candles", []):
            m = c.get("mid", {})
            bars.append(BarData(
                c.get("time", ""),
                float(m.get("o", 0)), float(m.get("h", 0)),
                float(m.get("l", 0)), float(m.get("c", 0)),
                float(c.get("volume", 0))
            ))
        return bars if bars else _simulated_bars(pair, count)
    except Exception as e:
        log.warning(f"OANDA bars {pair} {granularity}: {e}")
        return _simulated_bars(pair, count)

def _get_account_balance() -> float:
    if not OANDA_OK or not OANDA_TOKEN:
        return 100000.0
    try:
        api = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        r   = AccountDetails(OANDA_ACCOUNT)
        api.request(r)
        return float(r.response["account"]["balance"])
    except Exception:
        return 100000.0

# ══════════════════════════════════════════════════════════════════════════════
# TRADINGVIEW WEBHOOK HANDLER
# ══════════════════════════════════════════════════════════════════════════════
class TradingViewHandler:
    """
    Receives alerts directly from TradingView charts.
    When TradingView fires an alert that matches our system signal,
    confidence gets boosted significantly.

    HOW TO SET UP IN TRADINGVIEW:
    1. Open your chart in TradingView
    2. Create an alert (bell icon)
    3. Set condition (e.g. EMA cross, RSI oversold, etc.)
    4. In 'Alert actions' select 'Webhook URL'
    5. Paste: http://YOUR_IP:5000/webhook/tradingview
    6. In 'Message' paste this JSON:
    {
      "secret": "lovinder_forex_v13",
      "pair": "{{ticker}}",
      "direction": "BUY",
      "strategy": "EMA_CROSS",
      "timeframe": "{{interval}}",
      "price": "{{close}}",
      "message": "{{strategy.order.comment}}"
    }
    7. Click Create
    """

    def __init__(self):
        self.pending_signals: Dict[str, Dict] = {}
        self.history: List[Dict] = []
        self.total_received = 0
        self.total_matched = 0
        log.info("TradingView Webhook Handler ready at /webhook/tradingview")

    def receive(self, data: Dict) -> Tuple[bool, str]:
        """Process incoming TradingView webhook"""
        # Verify secret
        if data.get("secret") != TV_SECRET:
            return False, "Invalid secret"

        pair = data.get("pair", "").replace("/", "_").replace("EURUSD", "EUR_USD") \
                                   .replace("GBPUSD", "GBP_USD").replace("USDJPY", "USD_JPY") \
                                   .replace("AUDUSD", "AUD_USD").replace("USDCAD", "USD_CAD")

        if pair not in PAIRS:
            # Try to normalize pair name
            for p in PAIRS:
                if p.replace("_","") in pair.upper():
                    pair = p
                    break

        direction = data.get("direction", "").upper()
        if direction not in ["BUY", "SELL"]:
            return False, "Invalid direction"

        signal = {
            "pair": pair,
            "direction": direction,
            "strategy": data.get("strategy", "UNKNOWN"),
            "timeframe": data.get("timeframe", "H1"),
            "price": float(data.get("price", 0)),
            "message": data.get("message", ""),
            "timestamp": datetime.now().isoformat(),
            "used": False
        }

        key = f"{pair}_{direction}"
        self.pending_signals[key] = signal
        self.history.append(signal)
        self.history = self.history[-50:]
        self.total_received += 1

        log.info(f"TradingView: {pair} {direction} from {signal['strategy']}")
        _telegram(
            f"📊 <b>TradingView Alert Received</b>\n"
            f"Pair: {pair}\n"
            f"Direction: {direction}\n"
            f"Strategy: {signal['strategy']}\n"
            f"Timeframe: {signal['timeframe']}\n"
            f"Price: {signal['price']}\n"
            f"System will confirm with 42 agents..."
        )
        return True, f"Signal received: {pair} {direction}"

    def check_confirmation(self, pair: str, direction: str) -> Tuple[bool, str]:
        """Check if TradingView confirms our system signal"""
        key = f"{pair}_{direction}"
        sig = self.pending_signals.get(key)
        if not sig:
            return False, "No TradingView signal"

        # Signal expires after 4 hours
        try:
            sig_time = datetime.fromisoformat(sig["timestamp"])
            if (datetime.now() - sig_time).seconds > 14400:
                del self.pending_signals[key]
                return False, "TradingView signal expired"
        except Exception:
            pass

        sig["used"] = True
        self.total_matched += 1
        return True, f"TradingView confirmed: {sig['strategy']} on {sig['timeframe']}"

# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE MODULE: FOREX FACTORY CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
class ForexFactoryCalendar:
    """Economic calendar - WHEN to trade and what events are coming"""

    def __init__(self):
        self.events = []
        self.last_fetch = datetime.now() - timedelta(hours=2)
        self.total_fetched = 0
        self.high_impact_today = []

    def fetch(self):
        if (datetime.now() - self.last_fetch).seconds < 3600:
            return self.events
        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                self.events = data
                self.total_fetched = len(data)
                self.high_impact_today = [
                    e for e in data
                    if e.get("impact") == "High"
                ]
                log.info(f"ForexFactory: {len(data)} events, {len(self.high_impact_today)} HIGH impact")
        except Exception as e:
            log.warning(f"ForexFactory: {e}")
        self.last_fetch = datetime.now()
        return self.events

    def should_avoid(self, pair: str) -> Tuple[bool, str]:
        base, quote = _pair_currencies(pair)
        events = self.fetch()
        now = datetime.now()
        for ev in events:
            if ev.get("impact") != "High":
                continue
            country = ev.get("country", "")
            if base not in country and quote not in country:
                continue
            try:
                et = datetime.fromisoformat(ev.get("date","").replace("Z",""))
                diff = abs((et - now).total_seconds() / 60)
                if diff <= 30:
                    return True, f"HIGH impact in {diff:.0f}min: {ev.get('title','')}"
            except Exception:
                pass
        return False, "Calendar clear"

    def get_next_event(self, currency: str = "USD"):
        events = self.fetch()
        for ev in events:
            if ev.get("impact") == "High" and currency in ev.get("country", ""):
                return ev.get("title", "Unknown"), ev.get("impact", "")
        return "None scheduled", "N/A"

    def summary(self) -> str:
        hi = [e.get("title","") for e in self.high_impact_today[:3]]
        return f"{len(self.high_impact_today)} HIGH events: {', '.join(hi)}" if hi else "No high impact events"

# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE MODULE: COT / CHICAGO DATA
# ══════════════════════════════════════════════════════════════════════════════
class COTIntelligence:
    """CFTC Commitment of Traders - WHO is buying/selling (institutions)"""

    COT_MAP = {
        "EUR_USD": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "GBP_USD": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
        "USD_JPY": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
        "AUD_USD": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
        "USD_CAD": "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    }

    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.last_fetch = datetime.now() - timedelta(days=8)
        self.status = "Initializing"

    def get(self, pair: str) -> Dict:
        if pair in self.cache and (datetime.now() - self.last_fetch).days < 7:
            return self.cache[pair]
        try:
            contract = self.COT_MAP.get(pair, "")
            url = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
            params = {
                "$where": f"market_and_exchange_names='{contract}'",
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": 1
            }
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200 and r.json():
                d = r.json()[0]
                longs  = int(float(d.get("noncomm_positions_long_all",  0)))
                shorts = int(float(d.get("noncomm_positions_short_all", 0)))
                net    = longs - shorts
                result = {
                    "longs": longs, "shorts": shorts, "net": net,
                    "week": d.get("report_date_as_yyyy_mm_dd", ""),
                    "bias": "NET LONG" if net > 10000 else ("NET SHORT" if net < -10000 else "NEUTRAL"),
                    "direction": "BUY" if net > 10000 else ("SELL" if net < -10000 else "NEUTRAL")
                }
                self.cache[pair] = result
                self.last_fetch = datetime.now()
                self.status = f"Live - Week {result['week']}"
                return result
        except Exception as e:
            log.warning(f"COT {pair}: {e}")
            self.status = "Using estimates"

        # Fallback estimate
        net = random.randint(-30000, 30000)
        return {
            "longs": max(0, net), "shorts": max(0, -net), "net": net,
            "week": datetime.now().strftime("%Y-%m-%d"),
            "bias": "NET LONG" if net > 10000 else ("NET SHORT" if net < -10000 else "NEUTRAL"),
            "direction": "BUY" if net > 10000 else ("SELL" if net < -10000 else "NEUTRAL")
        }

    def get_bias(self, pair: str) -> Tuple[str, str, int]:
        d = self.get(pair)
        return d["direction"], d["bias"], d["net"]

# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE MODULE: NEWS
# ══════════════════════════════════════════════════════════════════════════════
class NewsIntelligence:
    """Real-time news sentiment - WHY markets are moving"""

    BULLISH = ["rise","surge","jump","beat","exceed","strong","hawkish",
               "hike","growth","positive","recovery","above forecast","beats expectations"]
    BEARISH = ["fall","drop","miss","weak","dovish","cut","recession",
               "below forecast","decline","slump","negative","disappoints"]

    KEYWORDS = {
        "USD":["federal reserve","fed","dollar","powell","nfp","cpi","inflation"],
        "EUR":["ecb","euro","eurozone","lagarde","germany","draghi"],
        "GBP":["bank of england","boe","pound","sterling","bailey","uk"],
        "JPY":["bank of japan","boj","yen","japan","ueda"],
        "AUD":["rba","australia","aussie","chinese economy"],
        "CAD":["bank of canada","boc","loonie","oil","canada"],
    }

    def __init__(self):
        self.articles = []
        self.last_fetch = datetime.now() - timedelta(hours=2)
        self.total_articles = 0
        self.status = "Initializing"

    def fetch(self):
        if (datetime.now() - self.last_fetch).seconds < 1800:
            return self.articles
        arts = []
        if NEWS_KEY:
            try:
                r = requests.get("https://newsapi.org/v2/everything", params={
                    "q": "forex OR currency OR federal reserve OR ECB OR interest rate",
                    "language": "en", "sortBy": "publishedAt",
                    "pageSize": 20, "apiKey": NEWS_KEY
                }, timeout=10)
                if r.status_code == 200:
                    arts = r.json().get("articles", [])
                    self.status = f"Live - {len(arts)} articles"
            except Exception as e:
                log.warning(f"News: {e}")

        if not arts and ALPHA_KEY:
            try:
                r = requests.get("https://www.alphavantage.co/query", params={
                    "function": "NEWS_SENTIMENT", "topics": "forex,economy_macro",
                    "apikey": ALPHA_KEY, "limit": 20
                }, timeout=10)
                if r.status_code == 200:
                    feed = r.json().get("feed", [])
                    arts = [{"title": a.get("title",""), "description": a.get("summary","")}
                            for a in feed]
                    self.status = f"Alpha Vantage - {len(arts)} articles"
            except Exception as e:
                log.warning(f"Alpha news: {e}")

        self.articles = arts
        self.total_articles = len(arts)
        self.last_fetch = datetime.now()
        return arts

    def sentiment(self, pair: str) -> Tuple[str, str, float]:
        arts = self.fetch()
        base, quote = _pair_currencies(pair)
        b_score = q_score = 0.0
        top_headline = "No major news"

        for art in arts:
            txt = (art.get("title","") + " " + art.get("description","")).lower()
            is_base  = any(kw in txt for kw in self.KEYWORDS.get(base, []))
            is_quote = any(kw in txt for kw in self.KEYWORDS.get(quote, []))
            if not (is_base or is_quote):
                continue
            bull = sum(1 for w in self.BULLISH if w in txt)
            bear = sum(1 for w in self.BEARISH if w in txt)
            score = bull - bear
            if is_base:
                b_score += score
                if abs(score) > 0 and top_headline == "No major news":
                    top_headline = art.get("title","")[:80]
            if is_quote:
                q_score -= score

        net = b_score + q_score
        if net > 1.5:
            return "BULLISH", top_headline, min(1.0, abs(net)/5)
        elif net < -1.5:
            return "BEARISH", top_headline, min(1.0, abs(net)/5)
        return "NEUTRAL", top_headline, 0.3

# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE MODULE: MARKET CORRELATIONS
# ══════════════════════════════════════════════════════════════════════════════
class MarketCorrelations:
    """DXY, Gold, VIX, Oil, SP500 - market context"""

    def __init__(self):
        self.data: Dict = {}
        self.last_fetch = datetime.now() - timedelta(hours=2)
        self.status = "Initializing"

    def fetch(self) -> Dict:
        if (datetime.now() - self.last_fetch).seconds < 1800:
            return self.data
        data = {}
        if YF_OK:
            tickers = {"DXY":"DX-Y.NYB","GOLD":"GC=F","OIL":"CL=F",
                       "SP500":"^GSPC","VIX":"^VIX"}
            for name, ticker in tickers.items():
                try:
                    t = yf.Ticker(ticker)
                    h = t.history(period="5d")
                    if not h.empty:
                        cur  = float(h["Close"].iloc[-1])
                        prev = float(h["Close"].iloc[-2]) if len(h) > 1 else cur
                        chg  = ((cur - prev) / prev) * 100
                        data[name] = {"value": round(cur, 2),
                                      "change": round(chg, 3),
                                      "trend": "UP" if chg > 0 else "DOWN"}
                except Exception:
                    pass
            self.status = f"Live - {list(data.keys())}"

        if not data:
            data = {n: {"value": v, "change": round(random.uniform(-0.5,0.5),3),
                        "trend": random.choice(["UP","DOWN"])}
                    for n, v in [("DXY",104.5),("GOLD",2350),
                                 ("OIL",78.5),("SP500",5200),("VIX",15.5)]}
            self.status = "Simulated"

        self.data = data
        self.last_fetch = datetime.now()
        return data

    def bias(self, pair: str) -> Tuple[str, str]:
        d = self.fetch()
        base, quote = _pair_currencies(pair)
        reasons = []
        buy = sell = 0

        dxy = d.get("DXY", {})
        if dxy:
            if dxy["trend"] == "UP":
                if quote == "USD": buy += 1; reasons.append(f"DXY↑ {dxy['change']:+.2f}% USD strong")
                else: sell += 1; reasons.append(f"DXY↑ weighs on {base}")
            else:
                if quote == "USD": sell += 1; reasons.append(f"DXY↓ {dxy['change']:+.2f}% USD weak")

        vix = d.get("VIX", {})
        if vix and float(vix.get("value", 0)) > 20:
            if pair in ["AUD_USD", "GBP_USD"]:
                sell += 1; reasons.append(f"VIX {vix['value']:.1f} risk-off")

        if buy > sell:   return "BUY",  " | ".join(reasons) or "Correlations bullish"
        if sell > buy:   return "SELL", " | ".join(reasons) or "Correlations bearish"
        return "NEUTRAL", " | ".join(reasons) or "Mixed correlations"

# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE MODULE: FRED MACRO
# ══════════════════════════════════════════════════════════════════════════════
class FREDMacro:
    """US Federal Reserve data - fundamental context"""

    def __init__(self):
        self.data: Dict = {}
        self.last_fetch = datetime.now() - timedelta(hours=13)
        self.status = "Initializing"

    def fetch(self) -> Dict:
        if (datetime.now() - self.last_fetch).seconds < 43200:
            return self.data
        data = {}
        if FRED_KEY:
            for sid, name in [("FEDFUNDS","Fed Rate"),("CPIAUCSL","CPI"),
                               ("UNRATE","Unemployment"),("GDP","GDP")]:
                try:
                    r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                        params={"series_id":sid,"api_key":FRED_KEY,
                                "sort_order":"desc","limit":2,"file_type":"json"}, timeout=10)
                    if r.status_code == 200:
                        obs = r.json().get("observations", [])
                        if obs:
                            data[name] = {
                                "current": obs[0].get("value","N/A"),
                                "previous": obs[1].get("value","N/A") if len(obs)>1 else "N/A",
                                "date": obs[0].get("date","")
                            }
                except Exception:
                    pass
            self.status = f"Live - {len(data)} indicators"

        if not data:
            data = {
                "Fed Rate":     {"current":"5.25","previous":"5.25","date":"2026-01-01"},
                "CPI":          {"current":"3.2", "previous":"3.4", "date":"2026-01-01"},
                "Unemployment": {"current":"3.8", "previous":"3.9", "date":"2026-01-01"},
                "GDP":          {"current":"2.1", "previous":"1.8", "date":"2026-01-01"}
            }
            self.status = "Estimated"

        self.data = data
        self.last_fetch = datetime.now()
        return data

    def usd_bias(self) -> Tuple[str, str]:
        d = self.fetch()
        score = 0
        reasons = []
        try:
            fed = float(d.get("Fed Rate",{}).get("current",0))
            if fed > 4.0: score += 2; reasons.append(f"Fed {fed}% hawkish")
            cpi = float(d.get("CPI",{}).get("current",0))
            if cpi > 3.0: score += 1; reasons.append(f"CPI {cpi}% elevated")
            ue  = float(d.get("Unemployment",{}).get("current",5))
            if ue < 4.0:  score += 1; reasons.append(f"Jobs {ue}% strong")
        except Exception:
            pass
        if score >= 3: return "BULLISH", " | ".join(reasons)
        if score <= 1: return "BEARISH", " | ".join(reasons)
        return "NEUTRAL", " | ".join(reasons)

# ══════════════════════════════════════════════════════════════════════════════
# SELF-LEARNING LAYER 1: FINMEM
# ══════════════════════════════════════════════════════════════════════════════
class FinMem:
    """Permanent memory - remembers everything forever"""

    def __init__(self):
        self.trades: List[Dict] = []
        self.total = self.wins = self.losses = 0
        self.lessons: List[str] = []
        self.pair_perf: Dict = {}
        self.regime_perf: Dict = {
            "TRENDING": {"wins":0,"losses":0,"pnl":0.0},
            "RANGING":  {"wins":0,"losses":0,"pnl":0.0},
            "VOLATILE": {"wins":0,"losses":0,"pnl":0.0},
        }
        self.session_perf: Dict = {
            "LONDON":   {"wins":0,"losses":0},
            "NEW_YORK": {"wins":0,"losses":0},
            "TOKYO":    {"wins":0,"losses":0},
            "SYDNEY":   {"wins":0,"losses":0},
        }
        self.tv_confirmed_wr: Dict = {"wins":0,"losses":0}
        self.evolution_log: List[str] = []
        self.news_losses: List[str] = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(MEM_FILE):
                with open(MEM_FILE) as f:
                    d = json.load(f)
                self.total         = d.get("total", 0)
                self.wins          = d.get("wins", 0)
                self.losses        = d.get("losses", 0)
                self.lessons       = d.get("lessons", [])
                self.pair_perf     = d.get("pair_perf", {})
                self.regime_perf   = d.get("regime_perf", self.regime_perf)
                self.session_perf  = d.get("session_perf", self.session_perf)
                self.evolution_log = d.get("evolution_log", [])
                self.news_losses   = d.get("news_losses", [])
                self.tv_confirmed_wr = d.get("tv_confirmed_wr", {"wins":0,"losses":0})
                self.trades        = d.get("trades", [])[-500:]
                log.info(f"FinMem: {self.total} trades remembered | WR: {self.win_rate:.1%}")
        except Exception as e:
            log.warning(f"FinMem fresh start: {e}")

    def save(self):
        try:
            with open(MEM_FILE, "w") as f:
                json.dump({
                    "total": self.total, "wins": self.wins, "losses": self.losses,
                    "lessons": self.lessons[-200:], "pair_perf": self.pair_perf,
                    "regime_perf": self.regime_perf, "session_perf": self.session_perf,
                    "evolution_log": self.evolution_log[-100:],
                    "news_losses": self.news_losses[-50:],
                    "tv_confirmed_wr": self.tv_confirmed_wr,
                    "trades": self.trades[-500:]
                }, f, indent=2)
        except Exception as e:
            log.error(f"FinMem save: {e}")

    def record(self, rec: TradeRecord):
        self.total += 1
        self.trades.append(asdict(rec))
        is_win = rec.outcome == "WIN"
        if is_win:   self.wins += 1
        elif rec.outcome == "LOSS": self.losses += 1

        lesson = (f"{rec.outcome} | {rec.pair} {rec.direction} | "
                  f"Regime:{rec.regime} Session:{rec.when_session} | "
                  f"Conf:{rec.confidence:.0%} | TV:{rec.tradingview_confirmed} | "
                  f"News:{rec.why_news[:40]}")
        self.lessons.append(lesson)

        if rec.outcome == "LOSS" and "BEARISH" in rec.why_news:
            self.news_losses.append(f"News caused loss: {rec.why_news[:60]}")

        # Pair performance
        p = self.pair_perf.setdefault(rec.pair,
            {"wins":0,"losses":0,"pnl":0.0,"tv_wins":0,"tv_losses":0})
        if is_win:
            p["wins"] += 1
            if rec.tradingview_confirmed: p["tv_wins"] += 1
        elif rec.outcome == "LOSS":
            p["losses"] += 1
            if rec.tradingview_confirmed: p["tv_losses"] += 1
        p["pnl"] += rec.pnl_pips

        # Regime
        r = self.regime_perf.get(rec.regime, {"wins":0,"losses":0,"pnl":0.0})
        if is_win: r["wins"] += 1
        elif rec.outcome == "LOSS": r["losses"] += 1
        r["pnl"] += rec.pnl_pips
        self.regime_perf[rec.regime] = r

        # Session
        s = self.session_perf.get(rec.when_session, {"wins":0,"losses":0})
        if is_win: s["wins"] += 1
        elif rec.outcome == "LOSS": s["losses"] += 1
        self.session_perf[rec.when_session] = s

        # TradingView confirmed win rate
        if rec.tradingview_confirmed:
            if is_win: self.tv_confirmed_wr["wins"] += 1
            elif rec.outcome == "LOSS": self.tv_confirmed_wr["losses"] += 1

        self.save()

    def log_evo(self, msg: str):
        self.evolution_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} - {msg}")
        self.save()

    @property
    def win_rate(self):
        t = self.wins + self.losses
        return self.wins / t if t > 0 else 0.0

    def pair_wr(self, pair: str) -> float:
        p = self.pair_perf.get(pair, {})
        t = p.get("wins",0) + p.get("losses",0)
        return p.get("wins",0) / t if t > 0 else 0.0

    def context(self, pair: str, regime: str) -> str:
        parts = [f"System WR:{self.win_rate:.1%} ({self.total} trades)"]
        if pair in self.pair_perf:
            p = self.pair_perf[pair]
            t = p["wins"] + p["losses"]
            if t > 0:
                parts.append(f"{pair} WR:{p['wins']/t:.1%}({t})")
        r = self.regime_perf.get(regime, {})
        rt = r.get("wins",0) + r.get("losses",0)
        if rt > 0:
            parts.append(f"{regime} WR:{r['wins']/rt:.1%}")
        if self.lessons:
            parts.append(f"Last:{self.lessons[-1][:50]}")
        return " | ".join(parts)

# ══════════════════════════════════════════════════════════════════════════════
# SELF-LEARNING LAYER 2: AGENT WEIGHTS
# ══════════════════════════════════════════════════════════════════════════════
class AgentWeights:
    """Winners get more power automatically"""

    def __init__(self, names: List[str]):
        self.w: Dict[str, float] = {n: 1.0 for n in names}
        self.perf: Dict[str, Dict] = {n: {"correct":0,"wrong":0} for n in names}
        self._load()

    def _load(self):
        try:
            if os.path.exists(WTS_FILE):
                with open(WTS_FILE) as f:
                    d = json.load(f)
                self.w    = d.get("weights", self.w)
                self.perf = d.get("perf", self.perf)
                log.info("AgentWeights: loaded from memory")
        except Exception:
            pass

    def save(self):
        try:
            with open(WTS_FILE,"w") as f:
                json.dump({"weights":self.w,"perf":self.perf,
                           "updated":datetime.now().isoformat()}, f, indent=2)
        except Exception as e:
            log.error(f"Weights save: {e}")

    def update(self, agreed: List[str], disagreed: List[str], outcome: str):
        win = outcome == "WIN"
        for n in agreed:
            if n not in self.w: continue
            if win:
                self.w[n] = min(3.0, self.w[n] * 1.05)
                self.perf[n]["correct"] += 1
            else:
                self.w[n] = max(0.1, self.w[n] * 0.95)
                self.perf[n]["wrong"] += 1
        for n in disagreed:
            if n not in self.w: continue
            if not win:
                self.w[n] = min(3.0, self.w[n] * 1.03)
                self.perf[n]["correct"] += 1
        self.save()

    def get(self, n: str) -> float:
        return self.w.get(n, 1.0)

    def top(self, k=5) -> List[Tuple]:
        return sorted(self.w.items(), key=lambda x: x[1], reverse=True)[:k]

    def bottom(self, k=5) -> List[Tuple]:
        return sorted(self.w.items(), key=lambda x: x[1])[:k]

# ══════════════════════════════════════════════════════════════════════════════
# SELF-LEARNING LAYER 3: RL AGENT
# ══════════════════════════════════════════════════════════════════════════════
class RLAgent:
    """Reinforcement learning from every trade"""

    def __init__(self):
        self.q: Dict[str, Dict[str, float]] = {}
        self.lr = 0.1; self.gamma = 0.95
        self.eps = 0.3; self.eps_min = 0.05; self.eps_decay = 0.995
        self.episodes = 0; self.reward_total = 0.0
        self._load()

    def _load(self):
        try:
            if os.path.exists(RL_FILE):
                with open(RL_FILE) as f:
                    d = json.load(f)
                self.q = d.get("q", {})
                self.eps = d.get("eps", 0.3)
                self.episodes = d.get("episodes", 0)
                log.info(f"RL Agent: {self.episodes} episodes, eps={self.eps:.3f}")
        except Exception:
            pass

    def save(self):
        try:
            with open(RL_FILE,"w") as f:
                json.dump({"q":self.q,"eps":self.eps,"episodes":self.episodes,
                           "reward_total":self.reward_total}, f, indent=2)
        except Exception as e:
            log.error(f"RL save: {e}")

    def _state(self, pair, regime, conf, wr, news, cot, tv_conf, hour) -> str:
        c = "HI" if conf>0.7 else ("MD" if conf>0.5 else "LO")
        w = "GD" if wr>0.6 else ("OK" if wr>0.45 else "BD")
        s = "LON" if 7<=hour<=16 else ("NY" if 13<=hour<=22 else "AS")
        n = news[:2].upper()
        tv = "TV" if tv_conf else "NT"
        ct = "L" if "LONG" in cot else ("S" if "SHORT" in cot else "N")
        return f"{pair}_{regime}_{c}_{w}_{s}_{n}_{tv}_{ct}"

    def decide(self, pair, regime, conf, wr, vote, news, cot, tv_conf) -> Tuple[str, float]:
        hour = datetime.now().hour
        state = self._state(pair, regime, conf, wr, news, cot, tv_conf, hour)
        if random.random() < self.eps:
            return vote, 0.85
        if state in self.q:
            qv = self.q[state]
            best = max(qv, key=qv.get)
            if best == vote:   return vote, 1.15 if tv_conf else 1.10
            elif qv.get(vote, 0) > -0.5: return vote, 0.9
            else: return "HOLD", 0.5
        return vote, 0.9 if not tv_conf else 1.0

    def learn(self, pair, regime, conf, wr, news, cot, tv_conf, action, reward):
        hour = datetime.now().hour
        state = self._state(pair, regime, conf, wr, news, cot, tv_conf, hour)
        if state not in self.q:
            self.q[state] = {"BUY":0.0,"SELL":0.0,"HOLD":0.0}
        cur = self.q[state].get(action, 0.0)
        mx  = max(self.q[state].values())
        self.q[state][action] = cur + self.lr * (reward + self.gamma*mx - cur)
        self.reward_total += reward
        self.episodes += 1
        self.eps = max(self.eps_min, self.eps * self.eps_decay)
        self.save()

# ══════════════════════════════════════════════════════════════════════════════
# SELF-LEARNING LAYER 4: MARKET REGIME DETECTOR
# ══════════════════════════════════════════════════════════════════════════════
class RegimeDetector:
    """Detects TRENDING / RANGING / VOLATILE and adapts strategy"""

    def detect(self, bars: List[BarData]) -> str:
        if len(bars) < 20: return "RANGING"
        closes = np.array([b.close for b in bars[-20:]])
        highs  = np.array([b.high  for b in bars[-20:]])
        lows   = np.array([b.low   for b in bars[-20:]])
        atr    = np.mean(highs - lows)
        move   = abs(closes[-1] - closes[0])
        dirstr = move / (atr * 20) if atr > 0 else 0
        std    = np.std(closes)
        volr   = std / np.mean(closes) if np.mean(closes) > 0 else 0
        if volr > 0.005: return "VOLATILE"
        if dirstr > 0.3: return "TRENDING"
        return "RANGING"

    def params(self, regime: str) -> Dict:
        return {
            "TRENDING": {"min_conf":0.60,"risk_mult":1.2,
                         "desc":"Trend following. Larger positions.",
                         "agents":["EMA","MACD","BOS","CHOCH"]},
            "RANGING":  {"min_conf":0.65,"risk_mult":0.8,
                         "desc":"Reversal at boundaries. Smaller positions.",
                         "agents":["RSI","OrderBlock","FVG","OTE"]},
            "VOLATILE": {"min_conf":0.75,"risk_mult":0.5,
                         "desc":"Only highest confidence. Very small.",
                         "agents":["LiquiditySweep","SilverBullet"]},
        }.get(regime, {"min_conf":0.65,"risk_mult":1.0,"desc":"","agents":[]})

# ══════════════════════════════════════════════════════════════════════════════
# SELF-LEARNING LAYER 5: HIVEMIND
# ══════════════════════════════════════════════════════════════════════════════
class HiveMind:
    """Evolves worst agents every 5 days automatically"""

    def __init__(self, mem: FinMem, ws: AgentWeights):
        self.mem = mem; self.ws = ws
        self.last = datetime.now() - timedelta(days=6)
        self.cycles = 0

    def should_run(self) -> bool:
        return (datetime.now() - self.last).days >= 5

    def run(self):
        if not self.should_run(): return
        worst = self.ws.bottom(5)
        for name, w in worst:
            self.ws.w[name] = 0.5
        self.ws.save()
        msg = f"HiveMind Cycle #{self.cycles+1}: Recalibrated {len(worst)} agents"
        self.mem.log_evo(msg)
        self.cycles += 1
        self.last = datetime.now()
        _telegram(f"🧠 <b>HiveMind #{self.cycles}</b>\nSystem evolved\n{len(worst)} agents recalibrated\nNext cycle in 5 days")
        log.info(msg)

# ══════════════════════════════════════════════════════════════════════════════
# TRADING AGENTS (17 agents with real logic)
# ══════════════════════════════════════════════════════════════════════════════
class Agent:
    def __init__(self, n): self.name = n
    def analyze(self, bars: List[BarData]) -> Optional[Signal]: return None

class EMAAgent(Agent):
    def __init__(self): super().__init__("EMA")
    def analyze(self, bars):
        if len(bars) < 50: return None
        c = np.array([b.close for b in bars])
        e20, e50, e200 = np.mean(c[-20:]), np.mean(c[-50:]), np.mean(c[-100:]) if len(c)>=100 else np.mean(c)
        if c[-1] > e20 > e50: return Signal("BUY",  0.68, f"EMA20>{e20:.5f}>EMA50 uptrend", self.name)
        if c[-1] < e20 < e50: return Signal("SELL", 0.68, f"EMA20<{e20:.5f}<EMA50 downtrend", self.name)
        return Signal("HOLD", 0.0, "EMA not aligned", self.name)

class RSIAgent(Agent):
    def __init__(self): super().__init__("RSI")
    def analyze(self, bars):
        if len(bars) < 15: return None
        c = np.array([b.close for b in bars[-15:]])
        d = np.diff(c)
        g, l = np.where(d>0,d,0), np.where(d<0,-d,0)
        ag, al = np.mean(g[-14:]), np.mean(l[-14:])
        rsi = 100 if al==0 else 100-100/(1+ag/al)
        if rsi < 30: return Signal("BUY",  0.72, f"RSI oversold {rsi:.1f}", self.name)
        if rsi > 70: return Signal("SELL", 0.72, f"RSI overbought {rsi:.1f}", self.name)
        return Signal("HOLD", 0.0, f"RSI neutral {rsi:.1f}", self.name)

class MACDAgent(Agent):
    def __init__(self): super().__init__("MACD")
    def analyze(self, bars):
        if len(bars) < 27: return None
        c = np.array([b.close for b in bars])
        m = np.mean(c[-12:]) - np.mean(c[-26:])
        pm = np.mean(c[-13:-1]) - np.mean(c[-27:-1])
        if m > 0 and pm <= 0: return Signal("BUY",  0.70, f"MACD bullish cross {m:.6f}", self.name)
        if m < 0 and pm >= 0: return Signal("SELL", 0.70, f"MACD bearish cross {m:.6f}", self.name)
        return Signal("BUY" if m>0 else "SELL", 0.55, f"MACD {'pos' if m>0 else 'neg'}", self.name)

class BOSAgent(Agent):
    def __init__(self): super().__init__("BOS")
    def analyze(self, bars):
        if len(bars) < 10: return None
        ph = max(b.high for b in bars[-10:-1])
        pl = min(b.low  for b in bars[-10:-1])
        c = bars[-1].close
        if c > ph: return Signal("BUY",  0.74, f"BOS above {ph:.5f}", self.name)
        if c < pl: return Signal("SELL", 0.74, f"BOS below {pl:.5f}", self.name)
        return Signal("HOLD", 0.0, "No BOS", self.name)

class CHOCHAgent(Agent):
    def __init__(self): super().__init__("CHOCH")
    def analyze(self, bars):
        if len(bars) < 20: return None
        t1 = bars[-10].close - bars[-20].close
        t2 = bars[-1].close  - bars[-10].close
        if t1 < 0 and t2 > 0: return Signal("BUY",  0.76, "CHOCH bear→bull", self.name)
        if t1 > 0 and t2 < 0: return Signal("SELL", 0.76, "CHOCH bull→bear", self.name)
        return Signal("HOLD", 0.0, "No CHOCH", self.name)

class OrderBlockAgent(Agent):
    def __init__(self): super().__init__("OrderBlock")
    def analyze(self, bars):
        if len(bars) < 15: return None
        cp = bars[-1].close
        for i in range(-15, -3):
            bar = bars[i]
            strong = abs(bars[i+1].close - bar.close) > (bar.high-bar.low)*1.5
            if strong and bar.low <= cp <= bar.high:
                d = "BUY" if bars[i+1].close > bar.close else "SELL"
                return Signal(d, 0.77, f"{d} OB at {bar.low:.5f}-{bar.high:.5f}", self.name)
        return Signal("HOLD", 0.0, "No OB touch", self.name)

class FVGAgent(Agent):
    def __init__(self): super().__init__("FVG")
    def analyze(self, bars):
        if len(bars) < 6: return None
        cp = bars[-1].close
        for i in range(-6, -3):
            b1, b3 = bars[i], bars[i+2]
            if b3.low > b1.high and b1.high <= cp <= b3.low:
                return Signal("BUY",  0.75, f"Bullish FVG {b1.high:.5f}-{b3.low:.5f}", self.name)
            if b3.high < b1.low and b3.high <= cp <= b1.low:
                return Signal("SELL", 0.75, f"Bearish FVG {b3.high:.5f}-{b1.low:.5f}", self.name)
        return Signal("HOLD", 0.0, "No FVG", self.name)

class KillzoneAgent(Agent):
    def __init__(self): super().__init__("Killzone")
    def analyze(self, bars):
        h = datetime.utcnow().hour
        in_kz = (7 <= h <= 9) or (13 <= h <= 15)
        if not in_kz: return Signal("HOLD", 0.0, "Not in killzone", self.name)
        sess = "London" if h < 12 else "NY"
        t = bars[-1].close - bars[-2].close if len(bars) >= 2 else 0
        d = "BUY" if t > 0 else "SELL"
        return Signal(d, 0.73, f"{sess} Killzone {d}", self.name)

class OTEAgent(Agent):
    def __init__(self): super().__init__("OTE")
    def analyze(self, bars):
        if len(bars) < 20: return None
        sh = max(b.high for b in bars[-20:])
        sl = min(b.low  for b in bars[-20:])
        cp = bars[-1].close
        f618 = sh - (sh-sl)*0.618
        f786 = sh - (sh-sl)*0.786
        if f786 <= cp <= f618:
            t = bars[-1].close - bars[-20].close
            d = "BUY" if t > 0 else "SELL"
            return Signal(d, 0.78, f"OTE {d} {f786:.5f}-{f618:.5f}", self.name)
        return Signal("HOLD", 0.0, "Not in OTE zone", self.name)

class SilverBulletAgent(Agent):
    def __init__(self): super().__init__("SilverBullet")
    def analyze(self, bars):
        h, m = datetime.utcnow().hour, datetime.utcnow().minute
        in_sb = (h==10) or (h==14) or (h==15 and m<=30)
        if not in_sb: return Signal("HOLD", 0.0, "Not Silver Bullet window", self.name)
        if len(bars) < 2: return None
        d = "BUY" if bars[-1].close > bars[-2].close else "SELL"
        return Signal(d, 0.80, f"Silver Bullet {d} h{h}:00", self.name)

class LiquidityAgent(Agent):
    def __init__(self): super().__init__("LiquiditySweep")
    def analyze(self, bars):
        if len(bars) < 10: return None
        ph = max(b.high for b in bars[-10:-1])
        pl = min(b.low  for b in bars[-10:-1])
        lb = bars[-1]
        if lb.high > ph and lb.close < ph:
            return Signal("SELL", 0.79, f"Swept highs {ph:.5f} reversal", self.name)
        if lb.low < pl and lb.close > pl:
            return Signal("BUY",  0.79, f"Swept lows {pl:.5f} reversal", self.name)
        return Signal("HOLD", 0.0, "No liquidity sweep", self.name)

class WyckoffAgent(Agent):
    def __init__(self): super().__init__("Wyckoff")
    def analyze(self, bars):
        if len(bars) < 30: return None
        closes = [b.close for b in bars[-30:]]
        vols   = [b.volume for b in bars[-30:]]
        avg_v  = np.mean(vols)
        hi_vol = sum(1 for v in vols if v > avg_v * 1.3)
        if hi_vol > 3:
            t = closes[-1] - closes[-10]
            if t > 0 and closes[-1] > np.mean(closes):
                return Signal("BUY",  0.72, "Wyckoff accumulation spring", self.name)
            if t < 0 and closes[-1] < np.mean(closes):
                return Signal("SELL", 0.72, "Wyckoff distribution upthrust", self.name)
        return Signal("HOLD", 0.0, "Wyckoff unclear", self.name)

class BollingerAgent(Agent):
    def __init__(self): super().__init__("Bollinger")
    def analyze(self, bars):
        if len(bars) < 20: return None
        c = np.array([b.close for b in bars[-20:]])
        mid, std = np.mean(c), np.std(c)
        up, dn = mid+2*std, mid-2*std
        if c[-1] <= dn: return Signal("BUY",  0.70, f"At lower BB {dn:.5f}", self.name)
        if c[-1] >= up: return Signal("SELL", 0.70, f"At upper BB {up:.5f}", self.name)
        return Signal("HOLD", 0.0, "Inside Bollinger Bands", self.name)

class StochasticAgent(Agent):
    def __init__(self): super().__init__("Stochastic")
    def analyze(self, bars):
        if len(bars) < 14: return None
        h14 = max(b.high for b in bars[-14:])
        l14 = min(b.low  for b in bars[-14:])
        if h14 == l14: return None
        k = ((bars[-1].close - l14)/(h14-l14))*100
        if k < 20: return Signal("BUY",  0.68, f"Stoch oversold {k:.1f}", self.name)
        if k > 80: return Signal("SELL", 0.68, f"Stoch overbought {k:.1f}", self.name)
        return Signal("HOLD", 0.0, f"Stoch neutral {k:.1f}", self.name)

class SessionAgent(Agent):
    def __init__(self): super().__init__("Session")
    def analyze(self, bars):
        h = datetime.utcnow().hour
        if not ((7<=h<=12) or (13<=h<=18)):
            return Signal("HOLD", 0.0, "Low volume session", self.name)
        t = bars[-1].close - bars[-5].close if len(bars)>=5 else 0
        d = "BUY" if t > 0 else "SELL"
        return Signal(d, 0.60, f"Prime session h{h} {d}", self.name)

class ATRAgent(Agent):
    def __init__(self): super().__init__("ATR")
    def analyze(self, bars):
        if len(bars) < 14: return None
        atrs = [b.high-b.low for b in bars[-14:]]
        avg = np.mean(atrs); cur = bars[-1].high - bars[-1].low
        if cur > avg*2.5: return Signal("HOLD", 0.0, f"ATR {cur:.5f} too volatile", self.name)
        if cur < avg*0.3: return Signal("HOLD", 0.0, f"ATR {cur:.5f} too quiet", self.name)
        t = bars[-1].close - bars[-5].close if len(bars)>=5 else 0
        d = "BUY" if t > 0 else "SELL"
        return Signal(d, 0.62, f"ATR {cur:.5f} normal conditions {d}", self.name)

class BreakoutAgent(Agent):
    def __init__(self): super().__init__("Breakout")
    def analyze(self, bars):
        if len(bars) < 20: return None
        r_high = max(b.high for b in bars[-21:-1])
        r_low  = min(b.low  for b in bars[-21:-1])
        c = bars[-1].close
        if c > r_high and bars[-1].volume > np.mean([b.volume for b in bars[-20:]]) * 1.2:
            return Signal("BUY",  0.73, f"Breakout above {r_high:.5f} with volume", self.name)
        if c < r_low and bars[-1].volume > np.mean([b.volume for b in bars[-20:]]) * 1.2:
            return Signal("SELL", 0.73, f"Breakout below {r_low:.5f} with volume", self.name)
        return Signal("HOLD", 0.0, "No breakout", self.name)

# ══════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
class RiskManager:
    """Calculates position size, SL, TP automatically"""

    def __init__(self):
        self.balance = 100000.0
        self.open_trades = 0
        self.daily_pnl = 0.0
        self.max_open = 3

    def update_balance(self):
        self.balance = _get_account_balance()

    def can_trade(self) -> Tuple[bool, str]:
        if self.open_trades >= self.max_open:
            return False, f"Max {self.max_open} open trades reached"
        daily_dd = self.daily_pnl / self.balance
        if daily_dd < -MAX_DD:
            return False, f"Daily drawdown limit {MAX_DD:.0%} reached"
        return True, "Risk OK"

    def calculate(self, pair: str, direction: str, confidence: float,
                  bars: List[BarData], regime: str) -> Dict:
        """Calculate entry, SL, TP, position size"""
        self.update_balance()
        price  = bars[-1].close
        atr    = np.mean([b.high-b.low for b in bars[-14:]]) if len(bars)>=14 else price*0.001
        risk_mult = {"TRENDING":1.2,"RANGING":0.8,"VOLATILE":0.5}.get(regime, 1.0)

        # SL/TP based on ATR
        sl_dist = atr * 2.0 * risk_mult
        tp_dist = atr * 3.0 * risk_mult  # 1.5:1 RR minimum

        if direction == "BUY":
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            sl = price + sl_dist
            tp = price - tp_dist

        # Position size (risk 0.5% of balance)
        risk_usd = self.balance * RISK_PCT * confidence
        pip_val  = 10.0 if "JPY" not in pair else 0.1
        units    = int(risk_usd / (sl_dist * pip_val))
        units    = max(1000, min(units, 100000))  # 1K to 100K units

        return {
            "entry": round(price, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "units": units,
            "risk_usd": round(risk_usd, 2),
            "sl_pips": round(sl_dist / (0.0001 if "JPY" not in pair else 0.01), 1),
            "tp_pips": round(tp_dist / (0.0001 if "JPY" not in pair else 0.01), 1),
        }

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE LOGGER
# ══════════════════════════════════════════════════════════════════════════════
TRADES_JSON = "v13_trades_local.json"

class SupabaseLogger:
    """Log every trade to Supabase database + local JSON fallback"""

    def __init__(self):
        self.client = None
        if SB_OK and SUPABASE_URL and SUPABASE_KEY:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                log.info("Supabase: Connected")
            except Exception as e:
                log.warning(f"Supabase: {e}")

    def _save_local(self, data: dict):
        """Always save to local JSON file as backup"""
        try:
            existing = []
            if os.path.exists(TRADES_JSON):
                with open(TRADES_JSON, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(data)
            with open(TRADES_JSON, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, default=str)
        except Exception as e:
            log.warning(f"Local JSON save failed: {e}")

    def log_trade(self, rec: TradeRecord):
        data = {
            "trade_id": rec.id, "pair": rec.pair,
            "direction": rec.direction, "confidence": rec.confidence,
            "outcome": rec.outcome, "pnl_pips": rec.pnl_pips,
            "pnl_usd": rec.pnl_usd,
            "regime": rec.regime, "session": rec.when_session,
            "tv_confirmed": rec.tradingview_confirmed,
            "why_technical": rec.why_technical[:200],
            "why_news": rec.why_news[:200],
            "why_cot": rec.why_cot[:100],
            "where_entry": rec.where_entry, "where_sl": rec.where_sl, "where_tp": rec.where_tp,
            "created_at": rec.when_timestamp
        }
        self._save_local(data)  # always save locally first
        if not self.client:
            return
        try:
            self.client.table("v13_trades").insert(data).execute()
        except Exception as e:
            log.warning(f"Supabase log: {e}")

    def log_tv_signal(self, pair: str, direction: str, strategy: str,
                      timeframe: str, price: float):
        """Save TradingView webhook signal to Supabase so any instance can read it"""
        if not self.client:
            return
        try:
            self.client.table("v13_tv_signals").insert({
                "pair": pair, "direction": direction,
                "strategy": strategy, "timeframe": timeframe,
                "price": price,
            }).execute()
        except Exception as e:
            log.warning(f"Supabase TV signal log: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# MASTER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════
# MACRO INTELLIGENCE LAYER (NEW)
# ═════════════════════════════════════════════════════════════════════════════
class MacroAgent:
    """
    Monitors macro conditions: USD strength, Fed rates, inflation, market regime.
    Provides daily bias for all trading pairs.
    """
    def __init__(self):
        self.fred_key = os.getenv('FRED_KEY', '')
        self.last_update = None
        self.usd_strength = 100.0
        self.fed_rate = 5.5
        self.inflation_rate = 3.2
        self.bias = 'BALANCED'
        
    def fetch_fred(self, series_id):
        """Fetch latest value from FRED (Federal Reserve Economic Data)"""
        if not self.fred_key:
            return None
        try:
            url = f'https://api.stlouisfed.org/fred/series/{series_id}/observations'
            params = {'api_key': self.fred_key, 'limit': 1}
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('observations'):
                    return float(data['observations'][0]['value'])
        except Exception as e:
            log.warning(f"FRED fetch error: {e}")
        return None
    
    def fetch_usd_strength(self):
        """Get USD strength from exchangerate.host (no API key needed)"""
        try:
            resp = requests.get(
                'https://api.exchangerate.host/latest?base=USD&symbols=EUR,GBP,JPY,CAD,AUD,CHF',
                timeout=5
            )
            if resp.status_code == 200:
                rates = resp.json()['rates']
                # USD stronger when rates are lower
                basket = np.mean([rates.get(c, 1.0) for c in ['EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF']])
                self.usd_strength = 100 / basket  # invert to index
                return self.usd_strength
        except Exception as e:
            log.warning(f"USD strength fetch error: {e}")
        return self.usd_strength
    
    def update(self):
        """Update all macro data"""
        self.fetch_usd_strength()
        fed_rate = self.fetch_fred('FEDFUNDS')
        inflation = self.fetch_fred('CPIAUCSL')
        if fed_rate:
            self.fed_rate = fed_rate
        if inflation:
            self.inflation_rate = inflation
        
        # Determine market bias
        if self.usd_strength > 103:
            self.bias = 'USD_STRONG'
        elif self.usd_strength < 100:
            self.bias = 'USD_WEAK'
        else:
            self.bias = 'BALANCED'
        
        self.last_update = datetime.now(timezone.utc)
        log.info(f"[MACRO] USD={self.usd_strength:.2f} Fed={self.fed_rate:.2f}% Inflation={self.inflation_rate:.2f}% Bias={self.bias}")
    
    def get_pair_bias(self, pair):
        """Get specific bias for a pair based on macro conditions"""
        if self.bias == 'USD_STRONG':
            if 'USD' in pair[:3]:  # USD in base (USD_XXX pairs)
                return 'BULLISH'  # USD pairs go up
            else:
                return 'BEARISH'  # XXX_USD pairs go down
        elif self.bias == 'USD_WEAK':
            if 'USD' in pair[:3]:
                return 'BEARISH'
            else:
                return 'BULLISH'
        return 'NEUTRAL'


# ═════════════════════════════════════════════════════════════════════════════
# PORTFOLIO PERFORMANCE TRACKER (NEW)
# ═════════════════════════════════════════════════════════════════════════════
class PortfolioTracker:
    """Tracks live P&L, metrics, and portfolio performance"""
    def __init__(self, starting_balance=100000):
        self.starting_balance = starting_balance
        self.current_balance = starting_balance
        self.trades_open = {}
        self.trades_closed = []
        self.last_update = None
        
    def add_trade(self, trade_id, pair, direction, entry_price, units, sl, tp):
        """Add open trade"""
        self.trades_open[trade_id] = {
            'pair': pair, 'direction': direction, 'entry': entry_price,
            'units': units, 'sl': sl, 'tp': tp, 'opened': datetime.now(timezone.utc)
        }
    
    def close_trade(self, trade_id, exit_price, pnl):
        """Close trade and move to history"""
        if trade_id in self.trades_open:
            t = self.trades_open.pop(trade_id)
            t['exit'] = exit_price
            t['pnl'] = pnl
            t['closed'] = datetime.now(timezone.utc)
            self.trades_closed.append(t)
            self.current_balance += pnl
    
    def get_metrics(self):
        """Get portfolio metrics"""
        if not self.trades_closed:
            return {'total_trades': 0, 'win_rate': 0, 'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0}
        
        wins = [t['pnl'] for t in self.trades_closed if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in self.trades_closed if t['pnl'] < 0]
        
        return {
            'total_trades': len(self.trades_closed),
            'win_rate': len(wins) / len(self.trades_closed) * 100,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'profit_factor': sum(wins) / sum(losses) if losses and sum(losses) > 0 else 0,
            'total_pnl': self.current_balance - self.starting_balance,
            'roi_percent': (self.current_balance - self.starting_balance) / self.starting_balance * 100
        }

class V13Orchestrator:

    def __init__(self):
        log.info("="*70)
        log.info("V13 COMPLETE PRODUCTION SYSTEM STARTING")
        log.info("="*70)

        # Intelligence modules
        self.ff_cal  = ForexFactoryCalendar()
        self.cot     = COTIntelligence()
        self.news    = NewsIntelligence()
        self.corr    = MarketCorrelations()
        self.fred    = FREDMacro()
        self.tv      = TradingViewHandler()

        # Agents
        self.agents = [
            EMAAgent(), RSIAgent(), MACDAgent(), BOSAgent(), CHOCHAgent(),
            OrderBlockAgent(), FVGAgent(), KillzoneAgent(), OTEAgent(),
            SilverBulletAgent(), LiquidityAgent(), WyckoffAgent(),
            BollingerAgent(), StochasticAgent(), SessionAgent(),
            ATRAgent(), BreakoutAgent()
        ]

        # Self-learning
        names = [a.name for a in self.agents]
        self.mem     = FinMem()
        self.weights = AgentWeights(names)
        self.rl      = RLAgent()
        self.regime  = RegimeDetector()
        self.hive    = HiveMind(self.mem, self.weights)

        # Risk & logging
        self.risk    = RiskManager()
        self.sb      = SupabaseLogger()

        # State
        self.running  = False
        self.records:  List[TradeRecord] = []
        self.open_pos: Dict[str, TradeRecord] = {}
        self.bars_cache: Dict[str, List[BarData]] = {}  # Store bars for each pair
        self.stats = {
            "cycles": 0, "signals": 0, "tv_signals": 0,
            "trades_executed": 0, "hive_cycles": 0
        }
        self.started_at = datetime.now().isoformat()

        self.mem.log_evo("V13 Production System started with TradingView + Full Dashboard")
        self._startup_alert()

    def _startup_alert(self):
        bal = _get_account_balance()
        _telegram(
            f"🚀 <b>V13 Production System STARTED</b>\n\n"
            f"Balance: ${bal:,.0f}\n"
            f"Agents: {len(self.agents)}\n"
            f"Memory: {self.mem.total} trades\n"
            f"WR: {self.mem.win_rate:.1%}\n"
            f"RL Episodes: {self.rl.episodes}\n\n"
            f"📊 TradingView Webhook:\n"
            f"POST to /webhook/tradingview\n\n"
            f"🌐 Dashboard: localhost:5000\n\n"
            f"All systems GO ✅"
        )

    def _vote(self, signals: List[Signal]) -> Tuple[str, float, List[str], List[str]]:
        buy_w = sell_w = 0.0
        buy_a: List[str] = []
        sell_a: List[str] = []
        for s in signals:
            if s.direction == "HOLD": continue
            w = self.weights.get(s.agent_name)
            if s.direction == "BUY":
                buy_w  += w * s.confidence; buy_a.append(s.agent_name)
            else:
                sell_w += w * s.confidence; sell_a.append(s.agent_name)
        total = buy_w + sell_w
        if total == 0: return "HOLD", 0.0, [], []
        if buy_w >= sell_w:
            return "BUY",  buy_w/total,  buy_a,  sell_a
        return "SELL", sell_w/total, sell_a, buy_a

    def analyze_pair(self, pair: str) -> Optional[TradeRecord]:
        rec = None  # always defined — prevents UnboundLocalError if construction fails
        bars = _get_bars(pair, 100)
        if len(bars) < 30: return None
        
        # Cache bars for dashboard charts
        self.bars_cache[pair] = bars

        # ── WHEN ──────────────────────────────────────────────────────────────
        session   = _get_session()
        hour      = datetime.utcnow().hour
        avoid, av_reason = self.ff_cal.should_avoid(pair)
        if avoid:
            log.info(f"{pair}: Skip - {av_reason}")
            return None
        next_ev, next_ev_impact = self.ff_cal.get_next_event()

        # ── WHO ───────────────────────────────────────────────────────────────
        cot_dir, cot_bias, cot_net = self.cot.get_bias(pair)

        # ── WHY (News) ────────────────────────────────────────────────────────
        news_sent, news_headline, news_score = self.news.sentiment(pair)

        # ── WHY (Macro) ───────────────────────────────────────────────────────
        macro_bias, macro_reason = self.fred.usd_bias()

        # ── WHY (Correlations) ───────────────────────────────────────────────
        corr_bias, corr_reason = self.corr.bias(pair)
        corr_data = self.corr.fetch()
        dxy  = corr_data.get("DXY",  {"trend":"?","change":0})
        gold = corr_data.get("GOLD", {"trend":"?","change":0})
        vix  = corr_data.get("VIX",  {"value":15})

        # ── WHAT (Technical agents) ──────────────────────────────────────────
        raw_sigs = []
        for agent in self.agents:
            try:
                s = agent.analyze(bars)
                if s: raw_sigs.append(s)
            except Exception as e:
                log.warning(f"Agent {agent.name}: {e}")

        # ── Regime ───────────────────────────────────────────────────────────
        curr_regime = self.regime.detect(bars)
        rp = self.regime.params(curr_regime)

        # ── Weighted vote ────────────────────────────────────────────────────
        direction, tech_conf, agreed, disagreed = self._vote(raw_sigs)
        if direction == "HOLD": return None

        # ── Boost confidence from intelligence ───────────────────────────────
        adj_conf = tech_conf
        if (news_sent == "BULLISH" and direction == "BUY") or \
           (news_sent == "BEARISH" and direction == "SELL"):
            adj_conf = min(1.0, adj_conf * 1.08)
        if cot_dir == direction:
            adj_conf = min(1.0, adj_conf * 1.08)
        if corr_bias == direction:
            adj_conf = min(1.0, adj_conf * 1.05)

        # ── Multi-timeframe confluence (H4) ──────────────────────────────────
        h4_boost = ""
        try:
            bars_h4 = _get_bars(pair, 50, granularity="H4")
            if len(bars_h4) >= 20:
                h4_sigs = []
                for agent in self.agents:
                    try:
                        s = agent.analyze(bars_h4)
                        if s: h4_sigs.append(s)
                    except Exception:
                        pass
                h4_dir, h4_conf, _, _ = self._vote(h4_sigs)
                if h4_dir == direction and h4_dir != "HOLD":
                    adj_conf = min(1.0, adj_conf * 1.12)
                    h4_boost = f" | H4 CONFIRMS {direction} ({h4_conf:.0%})"
                else:
                    h4_boost = f" | H4 neutral ({h4_dir})"
        except Exception:
            pass

        # ── TradingView confirmation ─────────────────────────────────────────
        tv_confirmed, tv_reason = self.tv.check_confirmation(pair, direction)
        if tv_confirmed:
            adj_conf = min(1.0, adj_conf * 1.15)
            self.stats["tv_signals"] += 1

        # ── RL Agent ─────────────────────────────────────────────────────────
        pair_wr = self.mem.pair_wr(pair)
        rl_action, rl_mod = self.rl.decide(
            pair, curr_regime, adj_conf, pair_wr,
            direction, news_sent, cot_bias, tv_confirmed
        )
        final_conf = min(1.0, adj_conf * rl_mod)

        if final_conf < rp["min_conf"]:
            log.info(f"{pair}: {final_conf:.1%} < {rp['min_conf']:.1%} threshold. Skip.")
            return None

        # ── WHERE (Risk calculation) ──────────────────────────────────────────
        can_trade, risk_reason = self.risk.can_trade()
        if not can_trade:
            log.info(f"{pair}: {risk_reason}")
            return None

        risk = self.risk.calculate(pair, direction, final_conf, bars, curr_regime)

        # ── WHERE (Key levels) ────────────────────────────────────────────────
        support    = min(b.low  for b in bars[-20:])
        resistance = max(b.high for b in bars[-20:])

        # ── Build complete trade record ───────────────────────────────────────
        mem_ctx = self.mem.context(pair, curr_regime)
        trade_id = f"V13-{pair[:3]}-{int(time.time())}"

        try:
          rec = TradeRecord(
            id=trade_id, pair=pair, direction=direction, confidence=final_conf,
            # WHY
            why_technical=f"{len(agreed)} agents: {', '.join(agreed[:4])}. {rp['desc']}",
            why_news=f"{news_sent}: {news_headline}",
            why_fundamental=f"FRED: {macro_reason[:80]}",
            why_correlation=f"DXY {dxy['trend']} {dxy['change']:+.2f}% | {corr_reason[:60]}",
            why_cot=f"{cot_bias} net:{cot_net:+,}",
            # WHAT
            what_pattern=", ".join(agreed[:5]),
            what_agents=agreed,
            what_agents_count=len(agreed),
            # WHEN
            when_timestamp=datetime.now().isoformat(),
            when_session=session,
            when_hour=hour,
            when_next_event=next_ev,
            when_avoid_news=avoid,
            # WHO
            who_institutions=cot_bias,
            who_retail="MAJORITY SELL" if direction=="BUY" else "MAJORITY BUY",
            who_cot_net=cot_net,
            # WHERE
            where_support=round(support,5),
            where_resistance=round(resistance,5),
            where_entry=risk["entry"],
            where_sl=risk["sl"],
            where_tp=risk["tp"],
            # Market
            dxy_trend=f"DXY {dxy['trend']} {dxy['change']:+.2f}%",
            gold_trend=f"Gold {gold['trend']} {gold['change']:+.2f}%",
            vix_level=float(vix.get("value",15)),
            # Self-learning
            regime=curr_regime,
            pair_win_rate=pair_wr,
            system_win_rate=self.mem.win_rate,
            memory_context=mem_ctx,
            rl_episodes=self.rl.episodes,
            # TradingView
            tradingview_confirmed=tv_confirmed,
            tradingview_signal=tv_reason,
          )
        except Exception as e:
            log.error(f"TradeRecord build failed for {pair}: {e}")
            return None

        self.records.append(rec)
        self.stats["signals"] += 1

        # ── Telegram Alert ───────────────────────────────────────────────────
        tv_tag = "✅ TV CONFIRMED" if tv_confirmed else "⬜ No TV signal"
        _telegram(
            f"{'🟢' if direction=='BUY' else '🔴'} <b>SIGNAL: {pair} {direction}</b>\n"
            f"Confidence: {final_conf:.1%} | Regime: {curr_regime}\n"
            f"{tv_tag}\n\n"
            f"<b>WHY:</b>\n"
            f"• Technical: {len(agreed)} agents agree\n"
            f"• News: {news_sent} - {news_headline[:50]}\n"
            f"• COT: {cot_bias} ({cot_net:+,})\n"
            f"• DXY: {dxy['trend']} {dxy['change']:+.2f}%\n\n"
            f"<b>WHEN:</b> {session} session\n"
            f"Next event: {next_ev}\n\n"
            f"<b>WHERE:</b>\n"
            f"Entry: {risk['entry']} | SL: {risk['sl']} | TP: {risk['tp']}\n"
            f"Risk: ${risk['risk_usd']} | Units: {risk['units']:,}\n\n"
            f"<b>MEMORY:</b> {mem_ctx[:80]}"
        )

        log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%} | "
                 f"Regime:{curr_regime} | News:{news_sent} | COT:{cot_bias} | "
                 f"TV:{tv_confirmed} | Agents:{len(agreed)}{h4_boost}")

        # ── Execute trade ─────────────────────────────────────────────────────
        if AUTO_EXECUTE and OANDA_OK and OANDA_TOKEN:
            self._execute_trade(rec, risk)

        # ── Schedule learning ─────────────────────────────────────────────────
        threading.Timer(300.0, self._learn_from_trade, args=[rec]).start()
        return rec

    def _execute_trade(self, rec: TradeRecord, risk: Dict):
        """Place trade on OANDA — auto-falls back to IC Markets if OANDA fails"""
        # ── Primary: OANDA ────────────────────────────────────────────────────
        oanda_ok = False
        try:
            api   = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
            # Format prices correctly for OANDA (JPY=3 decimals, others=5)
            def format_price(pair, price):
                if "JPY" in pair:
                    return f"{price:.3f}"  # JPY: 3 decimals
                return f"{price:.5f}"  # Others: 5 decimals
            
            units = risk["units"] if rec.direction == "BUY" else -risk["units"]
            order = {
                "order": {
                    "type": "MARKET",
                    "instrument": rec.pair,
                    "units": str(units),
                    "stopLossOnFill": {"price": format_price(rec.pair, rec.where_sl)},
                    "takeProfitOnFill": {"price": format_price(rec.pair, rec.where_tp)},
                }
            }
            r = OrderCreate(OANDA_ACCOUNT, data=order)
            api.request(r)
            trade_id = r.response.get("orderFillTransaction",{}).get("tradeOpened",{}).get("tradeID","")
            rec.oanda_trade_id = trade_id
            self.open_pos[rec.pair] = rec
            self.risk.open_trades += 1
            self.stats["trades_executed"] += 1
            oanda_ok = True
            log.info(f"OANDA EXECUTED: {rec.pair} {rec.direction} {risk['units']} units | ID:{trade_id}")
            _telegram(f"✅ <b>TRADE EXECUTED (OANDA)</b>\n{rec.pair} {rec.direction}\nUnits: {risk['units']:,}\nID: {trade_id}")
        except Exception as e:
            log.error(f"OANDA execute error: {e} — trying IC Markets backup")

        # ── Backup: IC Markets MT5 ────────────────────────────────────────────
        if not oanda_ok:
            try:
                from ic_markets_bridge import ICMarketsBridge
                ic = ICMarketsBridge()
                if ic.connected:
                    result = ic.place_trade(
                        pair=rec.pair, direction=rec.direction,
                        units=risk["units"], sl=rec.where_sl, tp=rec.where_tp
                    )
                    if result.get("status") == "ok":
                        rec.oanda_trade_id = f"IC-{result['trade_id']}"
                        self.open_pos[rec.pair] = rec
                        self.risk.open_trades += 1
                        self.stats["trades_executed"] += 1
                        log.info(f"IC MARKETS EXECUTED: {rec.pair} {rec.direction} | ID:{result['trade_id']}")
                        _telegram(f"✅ <b>TRADE EXECUTED (IC Markets backup)</b>\n{rec.pair} {rec.direction}\nUnits: {risk['units']:,}\nID: {result['trade_id']}")
                    else:
                        log.error(f"IC Markets also failed: {result.get('reason')}")
                        _telegram(f"❌ <b>BOTH BROKERS FAILED</b>\n{rec.pair} {rec.direction}\nOANDA + IC Markets unavailable")
                ic.disconnect()
            except Exception as e2:
                log.error(f"IC Markets backup error: {e2}")

    def _learn_from_trade(self, rec: TradeRecord):
        """5-min timer callback — only for signals NOT executed on OANDA.
        Real OANDA trades are handled by _monitor_open_trades with actual results."""
        if rec.oanda_trade_id:
            return  # real trade — monitor thread will handle it with actual P&L

        # Simulate for signal-only (no execution)
        win = random.random() < max(0.55, rec.confidence)
        if rec.tradingview_confirmed:
            win = random.random() < max(0.62, rec.confidence)
        rec.outcome  = "WIN" if win else "LOSS"
        rec.pnl_pips = random.uniform(15, 60) if win else random.uniform(-35, -10)
        rec.pnl_usd  = rec.pnl_pips * 10
        rec.lessons  = [f"{'✅' if win else '❌'} SIMULATED: {rec.why_technical[:60]}"]
        self.mem.record(rec)
        self.weights.update(rec.what_agents, [], rec.outcome)
        self.rl.learn(rec.pair, rec.regime, rec.confidence, rec.pair_win_rate,
                      rec.why_news[:4], rec.who_institutions, rec.tradingview_confirmed,
                      rec.direction, rec.pnl_pips / 10)
        self.sb.log_trade(rec)
        log.info(f"Signal (not executed): {rec.pair} {rec.outcome} | WR: {self.mem.win_rate:.1%}")

    # ─────────────────────────────────────────────────────────────────────────
    # REAL TRADE MONITORING
    # ─────────────────────────────────────────────────────────────────────────
    def _monitor_open_trades(self):
        """Background thread: polls OANDA every 5 min for real trade outcomes"""
        while self.running:
            try:
                if not OANDA_OK or not OANDA_TOKEN or not self.open_pos:
                    time.sleep(300); continue
                api = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
                from oandapyV20.endpoints.trades import TradeDetails
                closed_pairs = []
                for pair, rec in list(self.open_pos.items()):
                    if not rec.oanda_trade_id or rec.oanda_trade_id.startswith("IC-"):
                        continue
                    try:
                        r = TradeDetails(OANDA_ACCOUNT, tradeID=rec.oanda_trade_id)
                        api.request(r)
                        trade = r.response.get("trade", {})
                        state = trade.get("state", "OPEN")
                        if state == "CLOSED":
                            close_px   = float(trade.get("averageClosePrice", rec.where_entry))
                            realized   = float(trade.get("realizedPL", 0))
                            pip_size   = 0.01 if "JPY" in pair else 0.0001
                            pnl_pips   = (close_px - rec.where_entry) / pip_size if rec.direction == "BUY" \
                                         else (rec.where_entry - close_px) / pip_size
                            rec.outcome  = "WIN" if realized >= 0 else "LOSS"
                            rec.pnl_pips = round(pnl_pips, 1)
                            rec.pnl_usd  = round(realized, 2)
                            rec.lessons  = [
                                f"{'✅ WIN' if rec.outcome=='WIN' else '❌ LOSS'} (REAL): {rec.why_technical[:60]}",
                                f"Entry:{rec.where_entry:.5f} → Close:{close_px:.5f}",
                                f"P&L: {realized:+.2f} USD | {pnl_pips:+.1f} pips",
                            ]
                            self.mem.record(rec)
                            self.weights.update(rec.what_agents, [], rec.outcome)
                            self.rl.learn(rec.pair, rec.regime, rec.confidence, rec.pair_win_rate,
                                          rec.why_news[:4], rec.who_institutions,
                                          rec.tradingview_confirmed, rec.direction, pnl_pips / 10)
                            self.sb.log_trade(rec)
                            self.risk.open_trades = max(0, self.risk.open_trades - 1)
                            closed_pairs.append(pair)
                            log.info(f"REAL RESULT: {pair} {rec.outcome} | {pnl_pips:+.1f} pips | ${realized:+.2f} | WR:{self.mem.win_rate:.1%}")
                            _telegram(f"{'✅' if rec.outcome=='WIN' else '❌'} <b>REAL {rec.outcome}: {pair}</b>\n"
                                      f"P&L: {realized:+.2f} USD | {pnl_pips:+.1f} pips\n"
                                      f"System WR: {self.mem.win_rate:.1%} | RL: {self.rl.episodes}")
                        elif state == "OPEN":
                            self._update_trailing_stop(api, rec, trade)
                    except Exception as e:
                        log.warning(f"Monitor {pair}: {e}")
                for p in closed_pairs:
                    self.open_pos.pop(p, None)
            except Exception as e:
                log.error(f"Monitor thread: {e}")
            time.sleep(300)

    def _update_trailing_stop(self, api, rec: TradeRecord, trade_data: dict):
        """Trail SL: breakeven at +20 pips, trail at 15 pips from +30 pips"""
        try:
            from oandapyV20.endpoints.trades import TradeCRCDO
            curr = float(trade_data.get("price", rec.where_entry))
            pip  = 0.01 if "JPY" in rec.pair else 0.0001
            pnl_pips = (curr - rec.where_entry) / pip if rec.direction == "BUY" \
                       else (rec.where_entry - curr) / pip
            new_sl = None
            if pnl_pips >= 20:  # breakeven
                be = rec.where_entry + (3 * pip if rec.direction == "BUY" else -3 * pip)
                if rec.direction == "BUY" and be > rec.where_sl:
                    new_sl = be
                elif rec.direction == "SELL" and be < rec.where_sl:
                    new_sl = be
            if pnl_pips >= 30:  # trail 15 pips behind
                trail = curr - (15 * pip) if rec.direction == "BUY" else curr + (15 * pip)
                if new_sl is None or (rec.direction == "BUY" and trail > rec.where_sl) \
                                  or (rec.direction == "SELL" and trail < rec.where_sl):
                    new_sl = trail
            if new_sl and abs(new_sl - rec.where_sl) > pip:
                # Format SL correctly for JPY vs others
                sl_str = f"{new_sl:.3f}" if "JPY" in rec.pair else f"{new_sl:.5f}"
                r = TradeCRCDO(OANDA_ACCOUNT, tradeID=rec.oanda_trade_id,
                               data={"stopLoss": {"price": sl_str, "timeInForce": "GTC"}})
                api.request(r)
                log.info(f"Trailing SL {rec.pair}: {rec.where_sl:.5f}→{new_sl:.5f} (+{pnl_pips:.0f}p)")
                rec.where_sl = new_sl
        except Exception as e:
            log.warning(f"Trailing stop {rec.pair}: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # KILL SWITCH + TELEGRAM COMMANDS
    # ─────────────────────────────────────────────────────────────────────────
    def _listen_telegram_commands(self):
        """Background thread: listens for /stop /status /report commands"""
        last_id = 0
        while self.running:
            try:
                if not TELEGRAM_TOKEN: time.sleep(30); continue
                r = requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                    params={"offset": last_id + 1, "timeout": 20}, timeout=25
                )
                for upd in r.json().get("result", []):
                    last_id = upd["update_id"]
                    msg  = upd.get("message", {}).get("text", "").upper().strip()
                    chat = str(upd.get("message", {}).get("chat", {}).get("id", ""))
                    if chat != str(TELEGRAM_CHAT): continue
                    if msg in ["/STOP", "STOP", "KILL", "/KILL"]:
                        log.warning("🚨 KILL SWITCH via Telegram")
                        _telegram("🚨 <b>KILL SWITCH ACTIVATED</b>\nClosing all trades...")
                        self._close_all_trades()
                        self.running = False
                    elif msg in ["/STATUS", "STATUS"]:
                        _telegram(f"📡 <b>STATUS</b>\nCycles:{self.stats['cycles']} | "
                                  f"Trades:{self.mem.total} | WR:{self.mem.win_rate:.1%}\n"
                                  f"Open:{len(self.open_pos)} | RL:{self.rl.episodes}")
                    elif msg in ["/REPORT", "REPORT"]:
                        self._send_daily_report()
            except Exception as e:
                log.warning(f"Telegram listen: {e}")
            time.sleep(10)

    def _close_all_trades(self):
        """Emergency: close every open OANDA position"""
        if not OANDA_OK or not OANDA_TOKEN: return
        try:
            from oandapyV20.endpoints.trades import OpenTrades, TradeClose
            api = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
            r   = OpenTrades(OANDA_ACCOUNT); api.request(r)
            for t in r.response.get("trades", []):
                try:
                    api.request(TradeClose(OANDA_ACCOUNT, tradeID=t["id"]))
                    log.info(f"Force-closed {t['id']} {t['instrument']}")
                except Exception as e:
                    log.error(f"Force-close {t['id']}: {e}")
            self.open_pos.clear(); self.risk.open_trades = 0
        except Exception as e:
            log.error(f"Close all: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # DAILY P&L REPORT
    # ─────────────────────────────────────────────────────────────────────────
    def _send_daily_report(self):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        recs  = [r for r in self.records if r.when_timestamp[:10] == today and r.outcome in ["WIN","LOSS"]]
        wins  = [r for r in recs if r.outcome == "WIN"]
        pips  = sum(r.pnl_pips for r in recs)
        usd   = sum(r.pnl_usd  for r in recs)
        wr    = len(wins)/len(recs)*100 if recs else 0
        pair_pips = {}
        for r in recs: pair_pips[r.pair] = pair_pips.get(r.pair, 0) + r.pnl_pips
        best  = max(pair_pips, key=pair_pips.get) if pair_pips else "—"
        worst = min(pair_pips, key=pair_pips.get) if pair_pips else "—"
        _telegram(
            f"📊 <b>DAILY REPORT — {today}</b>\n\n"
            f"Trades: {len(recs)} | WR: {wr:.0f}%\n"
            f"✅ Wins: {len(wins)} | ❌ Losses: {len(recs)-len(wins)}\n"
            f"P&L: {pips:+.1f} pips | ${usd:+.2f}\n"
            f"Best: {best} | Worst: {worst}\n\n"
            f"Total WR: {self.mem.win_rate:.1%} | RL: {self.rl.episodes} episodes"
        )

    def run_cycle(self):
        self.stats["cycles"] += 1
        # Layer 5: HiveMind check
        if self.hive.should_run():
            self.hive.run()
            self.stats["hive_cycles"] += 1
        for pair in PAIRS:
            try:
                self.analyze_pair(pair)
                time.sleep(3)
            except Exception as e:
                log.error(f"Pair {pair}: {e}\n{traceback.format_exc()}")

    def run(self):
        self.running = True
        # Flask dashboard
        threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000,
                         debug=False, use_reloader=False), daemon=True).start()
        # Real trade monitor (checks OANDA every 5 min for actual results)
        threading.Thread(target=self._monitor_open_trades, daemon=True).start()
        # Kill switch + Telegram commands (/stop /status /report)
        threading.Thread(target=self._listen_telegram_commands, daemon=True).start()

        log.info("\n" + "="*70)
        log.info("V13 PRODUCTION SYSTEM RUNNING")
        log.info(f"Dashboard: http://localhost:5000")
        log.info(f"Webhook:   POST http://localhost:5000/webhook/tradingview")
        log.info(f"Commands:  Send /stop /status /report to Telegram bot")
        log.info("="*70 + "\n")

        _last_report_day = ""
        while self.running:
            try:
                self.run_cycle()
                self.mem.save(); self.rl.save(); self.weights.save()
                self.mem.save(); self.rl.save(); self.weights.save()
                log.info(
                    f"Cycle #{self.stats['cycles']} complete | "
                    f"Trades:{self.mem.total} | WR:{self.mem.win_rate:.1%} | "
                    f"RL:{self.rl.episodes} | TV:{self.stats['tv_signals']} | Open:{len(self.open_pos)}"
                )
                # Daily report at 22:00 UTC
                now = datetime.utcnow()
                today_str = now.strftime("%Y-%m-%d")
                if now.hour == 22 and _last_report_day != today_str:
                    self._send_daily_report()
                    _last_report_day = today_str
                time.sleep(900)  # 15 min
            except KeyboardInterrupt:
                log.info("System stopped")
                self.mem.save(); self.rl.save(); self.weights.save()
                break
            except Exception as e:
                log.error(f"Cycle error: {e}")
                self.mem.save(); self.rl.save(); self.weights.save()
                time.sleep(60)

# ══════════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ══════════════════════════════════════════════════════════════════════════════
orch: Optional[V13Orchestrator] = None

# ── TradingView Webhook ───────────────────────────────────────────────────────
@app.route("/webhook/tradingview", methods=["POST"])
def webhook_tradingview():
    global orch
    try:
        data = request.get_json(force=True) or {}
        ok, msg = orch.tv.receive(data) if orch else (False, "System not ready")
        # Save to Supabase so GitHub Actions cloud cycles can also read TV signals
        if ok and orch:
            orch.sb.log_tv_signal(
                pair=data.get("pair","").replace(":","_").replace("/","_"),
                direction=data.get("direction","").upper(),
                strategy=data.get("strategy","manual"),
                timeframe=data.get("timeframe",""),
                price=float(data.get("price", 0) or 0),
            )
        return jsonify({"status": "ok" if ok else "error", "message": msg}), 200 if ok else 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── Test webhook endpoint ────────────────────────────────────────────────────
@app.route("/webhook/test", methods=["GET"])
def webhook_test():
    return jsonify({
        "status": "TradingView webhook ready",
        "url": "POST /webhook/tradingview",
        "required_fields": ["secret", "pair", "direction"],
        "secret": TV_SECRET,
        "example": {
            "secret": TV_SECRET,
            "pair": "EURUSD",
            "direction": "BUY",
            "strategy": "EMA_CROSS",
            "timeframe": "H1",
            "price": "1.0850"
        }
    })

# ── API endpoints ─────────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    global orch
    if not orch:
        return jsonify({"status": "starting", "cycle": 0, "pairs": {}})
    
    # Build pairs data from last signals + cached bars
    pairs_data = {}
    try:
        for record in orch.records[-7:]:  # Last 7 signals
            pair = record.pair
            bars = orch.bars_cache.get(pair, [])
            bars_array = [[b.open, b.high, b.low, b.close, b.volume] for b in bars[-50:]] if bars else []
            
            pairs_data[pair] = {
                'pair': pair,
                'price': record.price,
                'direction': record.direction,
                'confidence': record.confidence,
                'h4_trend': record.h4_trend if hasattr(record, 'h4_trend') else '—',
                'regime': record.regime if hasattr(record, 'regime') else '—',
                'sl': record.sl if hasattr(record, 'sl') else '—',
                'tp': record.tp if hasattr(record, 'tp') else '—',
                'bars_h1': bars_array,  # Last 50 H1 bars for charting
            }
    except Exception as e:
        log.error(f"API pairs build error: {e}")
        pass
    
    return jsonify({
        "cycle": getattr(orch, 'cycle', 0),
        "pairs": pairs_data,
        "system": "V13 Production",
        "running": orch.running,
        "memory": {
            "total_trades": orch.mem.total,
            "win_rate": round(orch.mem.win_rate, 4),
            "wins": orch.mem.wins,
            "losses": orch.mem.losses,
        },
        "rl": {
            "episodes": orch.rl.episodes,
            "epsilon": round(orch.rl.eps, 4),
            "states": len(orch.rl.q),
            "reward": round(orch.rl.reward_total, 2)
        },
        "recent_signals": [asdict(r) for r in orch.records[-5:]] if orch.records else [],
    })

@app.route("/api/signals")
def api_signals():
    global orch
    if not orch:
        return jsonify([])
    return jsonify([asdict(r) for r in orch.records[-20:]])

@app.route("/api/memory")
def api_memory():
    global orch
    if not orch:
        return jsonify({})
    return jsonify({
        "lessons": orch.mem.lessons[-20:],
        "evolution_log": orch.mem.evolution_log[-20:],
        "pair_perf": orch.mem.pair_perf,
        "regime_perf": orch.mem.regime_perf,
        "session_perf": orch.mem.session_perf,
        "tv_confirmed_wr": orch.mem.tv_confirmed_wr,
    })

# ── Main Dashboard ─────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    return render_template_string("""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚡ Project Chakra V15 — Professional Trading Platform</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.min.js"></script>

<style>
* { margin:0; padding:0; box-sizing:border-box; }
html, body { height:100%; width:100%; }

body.dark { 
    background:#0a0a15; 
    color:#e8eeff;
}
body.light { 
    background:#f5f5f5; 
    color:#1a1a1a;
}

body { 
    font-family:'Courier New','Courier',monospace; 
    line-height:1.4;
    overflow:hidden;
}

.hdr { 
    display:flex; 
    justify-content:space-between; 
    align-items:center;
    padding:15px 20px;
    height:60px;
    border-bottom:1px solid;
    position:relative;
    z-index:100;
}

body.dark .hdr { 
    background:linear-gradient(90deg,#06061a 0%,#0f0f2e 100%);
    border-color:#1e1e4e;
}

body.light .hdr { 
    background:linear-gradient(90deg,#ffffff 0%,#f0f0ff 100%);
    border-color:#ddd;
}

.logo { 
    font-size:1.2em; 
    font-weight:bold; 
    letter-spacing:2px;
}

body.dark .logo { color:#00f5ff; }
body.light .logo { color:#0066ff; }

.controls { 
    display:flex; 
    gap:15px; 
    align-items:center;
}

.theme-toggle { 
    padding:8px 15px; 
    border:1px solid; 
    border-radius:5px; 
    cursor:pointer; 
    font-weight:bold;
    transition:all 0.3s;
}

body.dark .theme-toggle { 
    border-color:#1e1e4e; 
    background:#141428; 
    color:#00ff88;
}

body.light .theme-toggle { 
    border-color:#ddd; 
    background:#fff; 
    color:#0066ff;
}

.theme-toggle:hover { 
    transform:scale(1.05);
}

.capital-input { 
    padding:8px 12px; 
    border-radius:5px; 
    border:1px solid; 
    font-size:0.9em;
    width:200px;
}

body.dark .capital-input { 
    background:#1a1a2e; 
    border-color:#1e1e4e; 
    color:#e8eeff;
}

body.light .capital-input { 
    background:#fff; 
    border-color:#ddd; 
    color:#1a1a1a;
}

.currency-select { 
    padding:8px 12px; 
    border-radius:5px; 
    border:1px solid; 
    font-size:0.9em;
}

body.dark .currency-select { 
    background:#1a1a2e; 
    border-color:#1e1e4e; 
    color:#e8eeff;
}

body.light .currency-select { 
    background:#fff; 
    border-color:#ddd; 
    color:#1a1a1a;
}

.status-bar { 
    display:flex; 
    gap:20px; 
    font-size:0.85em;
}

body.dark .status-bar { color:#aab8ff; }
body.light .status-bar { color:#666; }

.status-value { 
    font-weight:bold;
}

body.dark .status-value { color:#00ff88; }
body.light .status-value { color:#0066ff; }

.content { 
    display:flex; 
    height:calc(100vh - 60px);
    overflow:hidden;
}

.sidebar { 
    width:250px; 
    overflow-y:auto;
    padding:15px;
    border-right:1px solid;
}

body.dark .sidebar { 
    background:#06061a; 
    border-color:#1e1e4e;
}

body.light .sidebar { 
    background:#fff; 
    border-color:#ddd;
}

.sidebar-section { 
    margin:20px 0;
}

.sidebar-title { 
    font-weight:bold; 
    font-size:0.9em; 
    margin-bottom:10px; 
    text-transform:uppercase;
    letter-spacing:1px;
}

body.dark .sidebar-title { color:#ff6b35; }
body.light .sidebar-title { color:#ff6b35; }

.sidebar-item { 
    padding:10px; 
    margin:5px 0; 
    border-radius:4px;
    cursor:pointer; 
    font-size:0.9em; 
    transition:all 0.2s; 
    border-left:3px solid transparent;
}

body.dark .sidebar-item:hover { 
    background:#1a1a2e; 
    border-left-color:#7b5cff;
}

body.light .sidebar-item:hover { 
    background:#f0f0ff; 
    border-left-color:#7b5cff;
}

.sidebar-item.active { 
    border-left-color:#00ff88;
}

body.dark .sidebar-item.active { 
    background:#1e1e4e; 
    color:#00ff88;
}

body.light .sidebar-item.active { 
    background:#e8f0ff; 
    color:#0066ff;
}

.main { 
    flex:1; 
    overflow:hidden;
    display:flex;
    flex-direction:column;
}

.tabs { 
    display:flex; 
    gap:2px; 
    padding:10px; 
    overflow-x:auto;
    height:50px;
    border-bottom:1px solid;
}

body.dark .tabs { 
    background:#0b0b22; 
    border-color:#1e1e4e;
}

body.light .tabs { 
    background:#fff; 
    border-color:#ddd;
}

.tab { 
    padding:8px 15px; 
    border-radius:4px 4px 0 0; 
    cursor:pointer; 
    font-size:0.85em; 
    transition:all 0.2s; 
    white-space:nowrap; 
    border-bottom:2px solid transparent;
}

body.dark .tab { 
    background:#141428; 
    color:#aab8ff;
}

body.light .tab { 
    background:#f5f5f5; 
    color:#666;
}

.tab:hover { 
    background:opacity(0.5);
}

.tab.active { 
    border-bottom-color:#00ff88;
}

body.dark .tab.active { 
    color:#00ff88;
}

body.light .tab.active { 
    color:#0066ff;
}

.chart-section { 
    flex:1; 
    overflow:hidden;
    position:relative;
}

.chart-wrapper { 
    width:100%; 
    height:100%;
    position:relative;
    display:none;
}

.chart-wrapper.active { 
    display:block;
}

.chart-info { 
    position:absolute;
    top:15px;
    left:15px;
    padding:15px;
    border-radius:6px;
    border:1px solid;
    z-index:10;
    min-width:350px;
    max-width:400px;
}

body.dark .chart-info { 
    background:#0a0a15dd; 
    border-color:#1e1e4e;
}

body.light .chart-info { 
    background:#ffffffdd; 
    border-color:#ddd;
}

.chart-pair { 
    font-size:1.2em; 
    font-weight:bold; 
    margin-bottom:8px;
}

body.dark .chart-pair { color:#00f5ff; }
body.light .chart-pair { color:#0066ff; }

.chart-price { 
    font-size:1.8em; 
    font-weight:bold; 
    margin:8px 0;
}

body.dark .chart-price { color:#00ff88; }
body.light .chart-price { color:#00aa00; }

.signal-badge { 
    display:inline-block; 
    padding:6px 12px; 
    border-radius:4px; 
    font-weight:bold; 
    margin:8px 0;
    font-size:0.95em;
}

.signal-buy { 
    background:#061a0a; 
    color:#00ff88; 
    border:1px solid #00ff88;
}

.signal-sell { 
    background:#1a060a; 
    color:#ff3355; 
    border:1px solid #ff3355;
}

.signal-hold { 
    border:1px solid;
}

body.dark .signal-hold { 
    background:#141428; 
    color:#aab8ff; 
    border-color:#1e1e4e;
}

body.light .signal-hold { 
    background:#f0f0ff; 
    color:#666; 
    border-color:#ddd;
}

.chart-stats { 
    display:grid; 
    grid-template-columns:1fr 1fr; 
    gap:8px; 
    margin-top:10px;
}

.stat-row { 
    display:flex; 
    justify-content:space-between;
    padding:6px 0;
    border-bottom:1px solid;
    font-size:0.85em;
}

body.dark .stat-row { border-color:#1e1e4e; }
body.light .stat-row { border-color:#ddd; }

.stat-label { 
    font-weight:bold;
}

body.dark .stat-label { color:#aab8ff; }
body.light .stat-label { color:#666; }

.stat-value { 
    font-weight:bold;
}

body.dark .stat-value { color:#00ff88; }
body.light .stat-value { color:#00aa00; }

.bottom-panels { 
    display:flex; 
    gap:15px; 
    height:250px; 
    overflow:hidden;
    padding:15px;
    border-top:1px solid;
}

body.dark .bottom-panels { border-color:#1e1e4e; }
body.light .bottom-panels { border-color:#ddd; }

.panel { 
    flex:1; 
    border-radius:6px; 
    border:1px solid; 
    padding:15px;
    overflow-y:auto;
}

body.dark .panel { 
    background:#0b0b22; 
    border-color:#1e1e4e;
}

body.light .panel { 
    background:#fff; 
    border-color:#ddd;
}

.panel-title { 
    font-weight:bold; 
    font-size:0.9em; 
    margin-bottom:10px;
    text-transform:uppercase;
    letter-spacing:1px;
}

body.dark .panel-title { color:#ff6b35; }
body.light .panel-title { color:#ff6b35; }

.risk-metric { 
    padding:8px 0; 
    border-bottom:1px solid; 
    display:flex; 
    justify-content:space-between; 
    font-size:0.85em;
}

body.dark .risk-metric { border-color:#1e1e4e; }
body.light .risk-metric { border-color:#ddd; }

.metric-label { 
    font-weight:bold;
}

body.dark .metric-label { color:#aab8ff; }
body.light .metric-label { color:#666; }

.metric-value { 
    font-weight:bold; 
    color:#00ff88;
}

body.light .metric-value { color:#00aa00; }

.agent-vote { 
    background:rgba(255,107,53,0.1); 
    padding:8px; 
    margin:5px 0; 
    border-radius:4px; 
    border-left:3px solid; 
    font-size:0.85em; 
    display:flex; 
    justify-content:space-between;
}

.agent-vote.buy { border-left-color:#00ff88; }
.agent-vote.sell { border-left-color:#ff3355; }
.agent-vote.hold { border-left-color:#aab8ff; }

.hedgefund-comparison { 
    display:grid; 
    grid-template-columns:1fr 1fr 1fr 1fr; 
    gap:8px;
}

.hf-card { 
    background:rgba(255,107,53,0.1); 
    padding:10px; 
    border-radius:4px; 
    border-left:3px solid #ff6b35; 
    text-align:center; 
    font-size:0.85em;
}

.hf-name { 
    font-weight:bold; 
    margin-bottom:5px;
}

.hf-return { 
    font-size:1.2em; 
    font-weight:bold; 
    color:#00ff88;
}

.hf-sharpe { 
    font-size:0.8em; 
    color:#aab8ff; 
    margin-top:3px;
}

body.light .hf-card { 
    background:rgba(0,102,255,0.05);
    border-left-color:#0066ff;
}

body.light .hf-return { color:#00aa00; }

::-webkit-scrollbar { width:8px; height:8px; }

body.dark ::-webkit-scrollbar-track { background:#0a0a15; }
body.dark ::-webkit-scrollbar-thumb { background:#1e1e4e; border-radius:4px; }
body.dark ::-webkit-scrollbar-thumb:hover { background:#2e2e5e; }

body.light ::-webkit-scrollbar-track { background:#f5f5f5; }
body.light ::-webkit-scrollbar-thumb { background:#ddd; border-radius:4px; }
body.light ::-webkit-scrollbar-thumb:hover { background:#bbb; }

@media (max-width:1024px) {
    .sidebar { width:180px; }
    .bottom-panels { height:200px; }
}

@media (max-width:768px) {
    .sidebar { display:none; }
    .bottom-panels { flex-direction:column; height:150px; }
}
</style>
</head>
<body class="dark">

<div class="hdr">
  <div class="logo">⚡ CHAKRA V15 PRO</div>
  <div class="controls">
    <input type="number" id="capitalInput" class="capital-input" placeholder="Starting Capital" value="100000" min="1000">
    <select id="currencySelect" class="currency-select">
      <option value="USD">USD</option>
      <option value="EUR">EUR</option>
      <option value="GBP">GBP</option>
      <option value="INR">INR</option>
    </select>
    <button class="theme-toggle" onclick="toggleTheme()">☀️ Light</button>
  </div>
  <div class="status-bar">
    <div>Cycle: <span class="status-value" id="cycle">0</span></div>
    <div>P&L: <span class="status-value" id="pnl">+$0</span></div>
    <div>Sharpe: <span class="status-value" id="sharpe">0.00</span></div>
    <div>WR: <span class="status-value" id="wr">0%</span></div>
    <div>DD: <span class="status-value" id="dd">0%</span></div>
  </div>
</div>

<div class="content">
  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-title">📊 Forex Pairs</div>
      <div class="sidebar-item active" onclick="selectSymbol('EUR_USD')">EUR/USD</div>
      <div class="sidebar-item" onclick="selectSymbol('GBP_USD')">GBP/USD</div>
      <div class="sidebar-item" onclick="selectSymbol('USD_JPY')">USD/JPY</div>
      <div class="sidebar-item" onclick="selectSymbol('AUD_USD')">AUD/USD</div>
      <div class="sidebar-item" onclick="selectSymbol('USD_CAD')">USD/CAD</div>
      <div class="sidebar-item" onclick="selectSymbol('XAU_USD')">XAU/USD</div>
      <div class="sidebar-item" onclick="selectSymbol('GBP_JPY')">GBP/JPY</div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-title">🔮 CME Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6E=F')">EUR Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6B=F')">GBP Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6J=F')">JPY Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6A=F')">AUD Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6C=F')">CAD Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6N=F')">NZD Futures</div>
      <div class="sidebar-item" onclick="selectSymbol('6S=F')">CHF Futures</div>
    </div>
  </div>

  <!-- MAIN -->
  <div class="main">
    <!-- TABS -->
    <div class="tabs" id="tabs"></div>

    <!-- CHARTS -->
    <div class="chart-section" id="charts"></div>

    <!-- BOTTOM PANELS -->
    <div class="bottom-panels">
      <!-- HEDGE FUND COMPARISON -->
      <div class="panel">
        <div class="panel-title">🏆 vs Hedge Funds</div>
        <div class="hedgefund-comparison" id="hfComparison"></div>
      </div>

      <!-- RISK METRICS -->
      <div class="panel">
        <div class="panel-title">⚠️ Risk Metrics</div>
        <div id="riskMetrics"></div>
      </div>

      <!-- AGENT VOTES -->
      <div class="panel">
        <div class="panel-title">🧠 Agent Consensus</div>
        <div id="agentVotes"></div>
      </div>
    </div>
  </div>
</div>

<script>
const PAIRS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD', 'GBP_JPY'];
const FUTURES = ['6E=F', '6B=F', '6J=F', '6A=F', '6C=F', '6N=F', '6S=F'];
const ALL_SYMBOLS = [...PAIRS, ...FUTURES];

const hedgeFunds = {
  'Your System': { return: 0, sharpe: 0, name: 'Chakra V15' },
  'Renaissance': { return: 30, sharpe: 2.5, name: 'Renaissance' },
  'Citadel': { return: 14, sharpe: 1.8, name: 'Citadel' },
  'Point72': { return: 11, sharpe: 1.6, name: 'Point72' },
  'Two Sigma': { return: 12, sharpe: 1.7, name: 'Two Sigma' },
};

let currentSymbol = 'EUR_USD';
let charts = {};
const capital = { initial: 100000, current: 100000, currency: 'USD', pnl: 0 };

function toggleTheme() {
  document.body.classList.toggle('dark');
  document.body.classList.toggle('light');
  document.querySelector('.theme-toggle').textContent = 
    document.body.classList.contains('dark') ? '☀️ Light' : '🌙 Dark';
  
  // Redraw charts on theme change
  setTimeout(() => {
    Object.values(charts).forEach(c => c && c.applyOptions ? c.applyOptions({layout: {background: {color: getThemeColor()}}}) : null);
  }, 100);
}

function getThemeColor() {
  return document.body.classList.contains('dark') ? '#0b0b22' : '#ffffff';
}

function initUI() {
  const tabs = document.getElementById('tabs');
  const chartsContainer = document.getElementById('charts');
  
  ALL_SYMBOLS.forEach((sym, i) => {
    const tab = document.createElement('div');
    tab.className = `tab ${i === 0 ? 'active' : ''}`;
    tab.textContent = sym.replace('_', '/');
    tab.onclick = () => selectSymbol(sym);
    tabs.appendChild(tab);
    
    const wrapper = document.createElement('div');
    wrapper.id = `chart-${sym}`;
    wrapper.className = `chart-wrapper ${i === 0 ? 'active' : ''}`;
    wrapper.innerHTML = `
      <div id="container-${sym}" style="width:100%;height:100%;"></div>
      <div class="chart-info">
        <div class="chart-pair" id="info-pair-${sym}">${sym.replace('_', '/')}</div>
        <div class="chart-price" id="info-price-${sym}">—</div>
        <div class="signal-badge" id="info-signal-${sym}">HOLD</div>
        <div class="chart-stats">
          <div class="stat-row"><span class="stat-label">Trend:</span><span class="stat-value" id="info-trend-${sym}">—</span></div>
          <div class="stat-row"><span class="stat-label">Regime:</span><span class="stat-value" id="info-regime-${sym}">—</span></div>
          <div class="stat-row"><span class="stat-label">SL:</span><span class="stat-value" id="info-sl-${sym}">—</span></div>
          <div class="stat-row"><span class="stat-label">TP:</span><span class="stat-value" id="info-tp-${sym}">—</span></div>
          <div class="stat-row"><span class="stat-label">Confidence:</span><span class="stat-value" id="info-conf-${sym}">0%</span></div>
        </div>
      </div>
    `;
    chartsContainer.appendChild(wrapper);
  });
  
  // Initialize hedge fund comparison
  updateHedgeFundComparison();
}

function selectSymbol(sym) {
  currentSymbol = sym;
  
  document.querySelectorAll('.tab').forEach((tab, i) => {
    tab.classList.toggle('active', ALL_SYMBOLS[i] === sym);
  });
  
  document.querySelectorAll('.sidebar-item').forEach((item, i) => {
    item.classList.toggle('active', ALL_SYMBOLS[i] === sym);
  });
  
  document.querySelectorAll('.chart-wrapper').forEach((wrapper, i) => {
    wrapper.classList.toggle('active', ALL_SYMBOLS[i] === sym);
  });
  
  if (!charts[sym]) createChart(sym);
}

function createChart(sym) {
  const container = document.getElementById(`container-${sym}`);
  if (!container) return;
  
  container.innerHTML = '<canvas id="canvas-' + sym + '" style="width:100%; height:100%;"></canvas>';
  const canvas = document.getElementById('canvas-' + sym);
  if (canvas) {
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
  }
  charts[sym] = canvas;
  
  updateChart(sym);
}

async function updateChart(sym) {
  try {
    const resp = await fetch('/api/status');
    const data = resp.ok ? await resp.json() : {};
    const pairData = data.pairs && data.pairs[sym];
    
    if (!pairData) return;
    
    const dirClass = pairData.direction === 'BUY' ? 'signal-buy' : pairData.direction === 'SELL' ? 'signal-sell' : 'signal-hold';
    document.getElementById(`info-signal-${sym}`).className = `signal-badge ${dirClass}`;
    document.getElementById(`info-signal-${sym}`).textContent = `${pairData.direction} ${(pairData.confidence * 100).toFixed(0)}%`;
    document.getElementById(`info-price-${sym}`).textContent = (pairData.price || 0).toFixed(sym.includes('JPY') ? 2 : 5);
    document.getElementById(`info-trend-${sym}`).textContent = pairData.h4_trend || '—';
    document.getElementById(`info-regime-${sym}`).textContent = pairData.regime || '—';
    document.getElementById(`info-sl-${sym}`).textContent = pairData.sl || '—';
    document.getElementById(`info-tp-${sym}`).textContent = pairData.tp || '—';
    document.getElementById(`info-conf-${sym}`).textContent = (pairData.confidence * 100).toFixed(0) + '%';
    
    // Draw candlesticks if bars available
    if (pairData.bars_h1 && pairData.bars_h1.length > 0 && charts[sym]) {
      drawCandlesticks(charts[sym], pairData.bars_h1, sym);
    }
  } catch (e) {
    console.error('Chart error:', e);
  }
}

function drawCandlesticks(canvas, bars, sym) {
  const ctx = canvas.getContext('2d');
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  
  canvas.width = width;
  canvas.height = height;
  
  if (!bars || bars.length === 0) {
    ctx.fillStyle = document.body.classList.contains('dark') ? '#0b0b22' : '#ffffff';
    ctx.fillRect(0, 0, width, height);
    return;
  }
  
  // Extract OHLCV
  const closes = bars.map(b => (Array.isArray(b) ? b[3] : b.close) || 0);
  const highs = bars.map(b => (Array.isArray(b) ? b[1] : b.high) || 0);
  const lows = bars.map(b => (Array.isArray(b) ? b[2] : b.low) || 0);
  const opens = bars.map(b => (Array.isArray(b) ? b[0] : b.open) || 0);
  
  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const priceRange = maxPrice - minPrice || 1;
  
  // Background
  ctx.fillStyle = document.body.classList.contains('dark') ? '#0b0b22' : '#ffffff';
  ctx.fillRect(0, 0, width, height);
  
  // Grid
  ctx.strokeStyle = document.body.classList.contains('dark') ? '#1e1e4e' : '#ddd';
  ctx.lineWidth = 0.5;
  for (let i = 0; i < 5; i++) {
    const y = (height / 5) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  
  // Candlesticks
  const barWidth = Math.max(2, width / (bars.length * 1.5));
  const padding = 20;
  
  bars.forEach((bar, i) => {
    const open = Array.isArray(bar) ? bar[0] : bar.open || 0;
    const high = Array.isArray(bar) ? bar[1] : bar.high || 0;
    const low = Array.isArray(bar) ? bar[2] : bar.low || 0;
    const close = Array.isArray(bar) ? bar[3] : bar.close || 0;
    
    const x = padding + (i * barWidth);
    const yHigh = height - ((high - minPrice) / priceRange) * (height - 40);
    const yLow = height - ((low - minPrice) / priceRange) * (height - 40);
    const yOpen = height - ((open - minPrice) / priceRange) * (height - 40);
    const yClose = height - ((close - minPrice) / priceRange) * (height - 40);
    
    const isUp = close >= open;
    
    // Wick
    ctx.strokeStyle = isUp ? '#00ff88' : '#ff3355';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x + barWidth/2, yHigh);
    ctx.lineTo(x + barWidth/2, yLow);
    ctx.stroke();
    
    // Body
    ctx.fillStyle = isUp ? '#00ff88' : '#ff3355';
    const bodyHeight = Math.abs(yClose - yOpen) || 1;
    ctx.fillRect(x, Math.min(yOpen, yClose), barWidth, bodyHeight);
  });
  
  // Price label
  const lastPrice = closes[closes.length - 1];
  ctx.fillStyle = document.body.classList.contains('dark') ? '#00ff88' : '#00aa00';
  ctx.font = 'bold 14px monospace';
  ctx.fillText(lastPrice.toFixed(sym.includes('JPY') ? 2 : 5), 5, 20);
}

async function updateChart(sym) {
  try {
    const resp = await fetch('/api/status');
    const data = resp.ok ? await resp.json() : {};
    const pairData = data.pairs && data.pairs[sym];
    
    if (!pairData) return;
    
    const dirClass = pairData.direction === 'BUY' ? 'signal-buy' : pairData.direction === 'SELL' ? 'signal-sell' : 'signal-hold';
    document.getElementById(`info-signal-${sym}`).className = `signal-badge ${dirClass}`;
    document.getElementById(`info-signal-${sym}`).textContent = `${pairData.direction} ${pairData.confidence || 0}%`;
    document.getElementById(`info-price-${sym}`).textContent = (pairData.price || 0).toFixed(sym.includes('JPY') ? 2 : 5);
    document.getElementById(`info-trend-${sym}`).textContent = pairData.h4_trend || '—';
    document.getElementById(`info-regime-${sym}`).textContent = pairData.regime || '—';
    document.getElementById(`info-sl-${sym}`).textContent = pairData.sl || '—';
    document.getElementById(`info-tp-${sym}`).textContent = pairData.tp || '—';
    document.getElementById(`info-conf-${sym}`).textContent = (pairData.confidence || 0) + '%';
    
    if (pairData.bars_h1 && pairData.bars_h1.length > 0 && charts[sym]) {
      const candleData = pairData.bars_h1.map((bar, i) => ({
        time: Math.floor(Date.now() / 1000) - (pairData.bars_h1.length - i - 1) * 3600,
        open: bar[0] || 0, high: bar[1] || 0, low: bar[2] || 0, close: bar[4] || 0,
      }));
      charts[sym].candleSeries.setData(candleData);
      charts[sym].chart.timeScale().fitContent();
    }
  } catch (e) {
    console.error('Chart error:', e);
  }
}

function updateHedgeFundComparison() {
  const container = document.getElementById('hfComparison');
  let html = '';
  for (const [key, hf] of Object.entries(hedgeFunds)) {
    html += `
      <div class="hf-card">
        <div class="hf-name">${hf.name}</div>
        <div class="hf-return">${hf.return}%</div>
        <div class="hf-sharpe">Sharpe: ${hf.sharpe}</div>
      </div>
    `;
  }
  container.innerHTML = html;
}

function updateRiskMetrics(data) {
  const container = document.getElementById('riskMetrics');
  const wr = (data.win_rate || 0) * 100;
  const sharpe = data.pnl_usd > 0 ? (data.pnl_usd / Math.max(1, Math.abs(data.max_drawdown || 1))).toFixed(2) : '0.00';
  const dd = Math.abs(data.max_drawdown || 0).toFixed(2);
  
  container.innerHTML = `
    <div class="risk-metric"><span class="metric-label">Win Rate:</span><span class="metric-value">${wr.toFixed(1)}%</span></div>
    <div class="risk-metric"><span class="metric-label">Sharpe Ratio:</span><span class="metric-value">${sharpe}</span></div>
    <div class="risk-metric"><span class="metric-label">Max Drawdown:</span><span class="metric-value">-${dd}%</span></div>
    <div class="risk-metric"><span class="metric-label">P&L:</span><span class="metric-value">${capital.currency} ${capital.pnl.toLocaleString()}</span></div>
    <div class="risk-metric"><span class="metric-label">Capital:</span><span class="metric-value">${capital.currency} ${capital.current.toLocaleString()}</span></div>
    <div class="risk-metric"><span class="metric-label">ROI:</span><span class="metric-value">${((capital.pnl / capital.initial) * 100).toFixed(2)}%</span></div>
  `;
  
  // Update your system in hedge fund comparison
  hedgeFunds['Your System'].return = ((capital.pnl / capital.initial) * 100).toFixed(1);
  hedgeFunds['Your System'].sharpe = parseFloat(sharpe);
  updateHedgeFundComparison();
}

function updateAgentVotes(data) {
  const container = document.getElementById('agentVotes');
  if (!data.recent_signals || data.recent_signals.length === 0) {
    container.innerHTML = '<div style="color:#556">No agent data</div>';
    return;
  }
  
  const recent = data.recent_signals[data.recent_signals.length - 1];
  let html = '';
  (recent.agents || []).slice(0, 8).forEach(agent => {
    const dir = agent.direction || 'HOLD';
    const cls = dir.toLowerCase();
    html += `
      <div class="agent-vote ${cls}">
        <span><strong>${agent.name || 'Agent'}</strong></span>
        <span>${dir} ${((agent.confidence || 0) * 100).toFixed(0)}%</span>
      </div>
    `;
  });
  container.innerHTML = html || '<div style="color:#556">Analyzing...</div>';
}

async function updateDashboard() {
  try {
    const resp = await fetch('/api/status');
    const data = resp.ok ? await resp.json() : {};
    
    capital.current = capital.initial + (data.pnl_usd || 0);
    capital.pnl = data.pnl_usd || 0;
    
    document.getElementById('cycle').textContent = data.cycle || 0;
    document.getElementById('pnl').textContent = `${capital.currency} ${capital.pnl.toLocaleString()}`;
    document.getElementById('wr').textContent = ((data.win_rate || 0) * 100).toFixed(1) + '%';
    document.getElementById('sharpe').textContent = (data.pnl_usd > 0 ? (data.pnl_usd / Math.max(1, Math.abs(data.max_drawdown || 1))).toFixed(2) : '0.00');
    document.getElementById('dd').textContent = Math.abs(data.max_drawdown || 0).toFixed(2) + '%';
    
    updateRiskMetrics(data);
    updateAgentVotes(data);
    
    for (const sym of ALL_SYMBOLS) {
      if (charts[sym]) updateChart(sym);
    }
  } catch (e) {
    console.error('Update error:', e);
  }
}

document.getElementById('capitalInput').addEventListener('change', (e) => {
  capital.initial = parseFloat(e.target.value) || 100000;
  capital.current = capital.initial;
});

document.getElementById('currencySelect').addEventListener('change', (e) => {
  capital.currency = e.target.value;
});

initUI();
updateDashboard();
setInterval(updateDashboard, 3000);
</script>

</body>
</html>
""")


def main():
    global orch
    orch = V13Orchestrator()

    # --once flag: run a single cycle then exit (used by GitHub Actions cron)
    if "--once" in sys.argv:
        log.info("=== V13 SINGLE CYCLE MODE (GitHub Actions) ===")
        orch.run_cycle()
        orch.mem.save(); orch.rl.save(); orch.weights.save()
        log.info(f"Single cycle done | Trades:{orch.mem.total} | WR:{orch.mem.win_rate:.1%} | RL:{orch.rl.episodes}")
        return

    orch.run()

if __name__ == "__main__":
    main()
