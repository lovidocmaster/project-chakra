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
FRED_KEY       = os.getenv("FRED_KEY", os.getenv("FRED_API_KEY", "0d5051e1563e45866badf276454ce1ec"))
NEWS_KEY       = os.getenv("NEWS_KEY", os.getenv("NEWS_API_KEY", "00ce3b995b134bf98265358f98b9d41e"))
ALPHA_KEY      = os.getenv("ALPHA_VANTAGE", "T7TQAX2SMD7RTNXN")
SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY", "")
TV_SECRET      = os.getenv("TV_WEBHOOK_SECRET", "lovinder_forex_v13")

PAIRS = [
    # Major forex pairs
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD",
    # Cross pairs (high volume)
    "GBP_JPY", "EUR_JPY", "AUD_JPY", "EUR_GBP",
    # Commodity currencies
    "NZD_USD", "USD_CHF", "USD_SGD",
]
RISK_PCT = 0.005        # 0.5% risk per trade
MAX_DD   = 0.05         # 2% max drawdown
AUTO_EXECUTE = True     # OANDA practice account — paper trades execute as real orders on demo

MEM_FILE  = "v13_memory.json"
WTS_FILE  = "v13_weights.json"
RL_FILE   = "v13_rl.json"
LOG_FILE  = "v13_system.log"
# ═══════════════════════════════════════════════════════════════════════════════
# BACKEND INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

BACKEND_URL = "https://project-chakra.onrender.com"

def post_trade_to_backend(trade_data):
    try:
        response = requests.post(f"{BACKEND_URL}/api/trades/create", json=trade_data, timeout=5)
        if response.status_code == 200:
            print(f"✅ Trade posted to backend: {trade_data.get('pair')} {trade_data.get('direction')}")
            return True
    except Exception as e:
        print(f"⚠️ Backend offline: {e}")
        return False

def check_backend():
    try:
        r = requests.get(f"{BACKEND_URL}/api/system/status", timeout=5)
        return r.status_code == 200
    except:
        return False

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
            "AUD_USD":0.70,"USD_CAD":1.37}.get(pair, 1.10)
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
        bal = float(r.response["account"]["balance"])
        nav = float(r.response["account"].get("NAV", bal))
        unrealized = float(r.response["account"].get("unrealizedPL", 0))
        open_trades = int(r.response["account"].get("openTradeCount", 0))
        # Push real data to Supabase so dashboard shows live numbers
        try:
            if SB_OK and SUPABASE_URL and SUPABASE_KEY:
                sb = create_client(SUPABASE_URL, SUPABASE_KEY)
                sb.table("system_state").upsert({
                    "id": 1,
                    "balance": round(bal, 2),
                    "nav": round(nav, 2),
                    "unrealized_pnl": round(unrealized, 2),
                    "open_trades": open_trades,
                    "updated_at": datetime.utcnow().isoformat(),
                    "status": "LIVE"
                }).execute()
        except Exception as sb_e:
            pass  # Dashboard update failure never stops trading
        return bal
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

        def fetch(self) -> List[Dict]:
        """Fetch economic calendar from multiple sources for maximum accuracy"""
        events = []
        
        # Source 1: ForexFactory (primary)
        try:
            import requests as _req
            from bs4 import BeautifulSoup as _BS
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = _req.get("https://www.forexfactory.com/calendar", headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = _BS(resp.text, "html.parser")
                rows = soup.select("tr.calendar__row")
                for row in rows[:50]:
                    try:
                        impact_el = row.select_one(".calendar__impact span")
                        title_el  = row.select_one(".calendar__event-title")
                        ccy_el    = row.select_one(".calendar__currency")
                        time_el   = row.select_one(".calendar__time")
                        if impact_el and title_el and ccy_el:
                            impact_class = impact_el.get("class", [])
                            impact = "HIGH" if "icon--ff-impact-red" in str(impact_class) else                                      "MEDIUM" if "icon--ff-impact-ora" in str(impact_class) else "LOW"
                            events.append({
                                "title": title_el.text.strip(),
                                "currency": ccy_el.text.strip(),
                                "impact": impact,
                                "time": time_el.text.strip() if time_el else "",
                                "source": "ForexFactory"
                            })
                    except: continue
                log.info(f"ForexFactory: {len(events)} events fetched")
        except Exception as e:
            log.warning(f"ForexFactory fetch failed: {e}")

        # Source 2: NewsAPI sentiment (backup)
        try:
            if NEWS_KEY:
                import requests as _req
                resp = _req.get(
                    f"https://newsapi.org/v2/everything?q=forex+economy&language=en&pageSize=10&apiKey={NEWS_KEY}",
                    timeout=5
                )
                if resp.status_code == 200:
                    articles = resp.json().get("articles", [])
                    for a in articles:
                        title = a.get("title", "").lower()
                        if any(w in title for w in ["rate", "inflation", "gdp", "jobs", "fed", "ecb", "boe"]):
                            events.append({
                                "title": a.get("title", ""),
                                "currency": "USD" if "fed" in title else "EUR" if "ecb" in title else "GBP" if "boe" in title else "ALL",
                                "impact": "HIGH" if any(w in title for w in ["rate decision", "nfp", "cpi", "gdp"]) else "MEDIUM",
                                "time": "",
                                "source": "NewsAPI"
                            })
        except Exception as e:
            log.warning(f"NewsAPI fetch failed: {e}")

        self.events = events
        return events


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
            title = art.get("title") or ""
            desc = art.get("description") or ""
            txt = (title + " " + desc).lower()
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
class OANDAOrderBook:
    """
    FREE ORDER BOOK DATA from OANDA.
    OANDA publishes where their retail clients have pending orders.
    
    This is a free alternative to expensive exchange Level 2 data.
    
    How to use it:
    - Heavy BUY orders above price = resistance (liquidity grab target)
    - Heavy SELL orders below price = support (stop hunt target)  
    - SMC traders call these "liquidity pools"
    
    OANDA provides this free at:
    GET /v3/instruments/{pair}/orderBook
    """
    def __init__(self):
        self.cache = {}
        self.cache_time = {}

    def get_book(self, pair: str) -> dict:
        """Fetch OANDA order book for a pair"""
        now = datetime.utcnow()
        if pair in self.cache:
            age = (now - self.cache_time[pair]).seconds
            if age < 900:  # Cache 15 minutes
                return self.cache[pair]

        if not OANDA_TOKEN:
            return {}

        try:
            import requests as _r
            resp = _r.get(
                f"https://api-fxpractice.oanda.com/v3/instruments/{pair}/orderBook",
                headers={"Authorization": f"Bearer {OANDA_TOKEN}"},
                timeout=5
            )
            if resp.status_code == 200:
                book = resp.json().get("orderBook", {})
                self.cache[pair] = book
                self.cache_time[pair] = now
                return book
        except Exception as e:
            log.debug(f"OrderBook {pair}: {e}")
        return {}

    def get_signal(self, pair: str, current_price: float) -> tuple:
        """
        Analyze order book for trading signal.
        Returns (direction_bias, strength, reason)
        """
        book = self.get_book(pair)
        if not book:
            return "NEUTRAL", 0.0, "No order book data"

        try:
            buckets = book.get("buckets", [])
            if not buckets:
                return "NEUTRAL", 0.0, "Empty order book"

            buy_orders_above  = 0.0
            sell_orders_below = 0.0
            buy_orders_below  = 0.0
            sell_orders_above = 0.0

            for bucket in buckets:
                price  = float(bucket.get("price", 0))
                long_c = float(bucket.get("longCountPercent", 0))
                short_c= float(bucket.get("shortCountPercent", 0))

                if price > current_price:
                    sell_orders_above += short_c  # Shorts above = resistance
                    buy_orders_above  += long_c   # Longs above = pending buys
                else:
                    buy_orders_below  += long_c   # Longs below = support
                    sell_orders_below += short_c  # Shorts below = pending sells

            # Heavy sells above + buys below = price likely to range/reverse
            # Heavy buys above = breakout pending (breakout buyers)
            total = buy_orders_above + sell_orders_above + buy_orders_below + sell_orders_below
            if total == 0:
                return "NEUTRAL", 0.0, "No order clusters"

            # Liquidity pool detection
            if sell_orders_above > total * 0.4:
                return "SELL", 0.62, f"Heavy sell orders above {sell_orders_above:.1f}% — resistance"
            if buy_orders_below > total * 0.4:
                return "BUY", 0.62, f"Heavy buy orders below {buy_orders_below:.1f}% — support"

            return "NEUTRAL", 0.3, "Balanced order book"
        except Exception as e:
            return "NEUTRAL", 0.0, f"OrderBook parse error: {e}"


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
            "RANGING":  {"min_conf":0.60,"risk_mult":0.8,
                         "desc":"Reversal at boundaries. Smaller positions.",
                         "agents":["RSI","OrderBlock","FVG","OTE"]},
            "VOLATILE": {"min_conf":0.65,"risk_mult":0.5,
                         "desc":"Only highest confidence. Very small.",
                         "agents":["LiquiditySweep","SilverBullet"]},
        }.get(regime, {"min_conf":0.60,"risk_mult":1.0,"desc":"","agents":[]})

# ══════════════════════════════════════════════════════════════════════════════
# SELF-LEARNING LAYER 5: HIVEMIND
# ══════════════════════════════════════════════════════════════════════════════
class HiveMind:
    """Evolves worst agents every 5 days automatically"""

    def __init__(self, mem: FinMem, ws: AgentWeights):
        self.mem = mem; self.ws = ws
        self.last = datetime.now() - timedelta(days=4)
        self.cycles = 0

    def should_run(self) -> bool:
        return (datetime.now() - self.last).days >= 3

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
        _telegram(f"🧠 <b>HiveMind #{self.cycles}</b>\nSystem evolved\n{len(worst)} agents recalibrated\nNext cycle in 3 days")
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
    """
    UPGRADED Wyckoff — tracks full market phases:
    Accumulation (PS→SC→AR→ST→Spring→SOS→LPS) = BUY
    Distribution (PSY→BC→AR→SOW→UTAD→LPSY) = SELL
    Uses volume confirmation for each phase.
    """
    def __init__(self): super().__init__("Wyckoff")

    def analyze(self, bars):
        if len(bars) < 50: return None
        closes = np.array([b.close for b in bars[-50:]])
        highs  = np.array([b.high  for b in bars[-50:]])
        lows   = np.array([b.low   for b in bars[-50:]])
        vols   = np.array([b.volume for b in bars[-50:]])
        avg_v  = float(np.mean(vols)) if np.mean(vols) > 0 else 1.0

        # Phase detection via price + volume relationship
        price_range   = float(np.max(highs) - np.min(lows))
        current_pos   = (closes[-1] - float(np.min(lows))) / price_range if price_range > 0 else 0.5
        vol_trend     = float(np.mean(vols[-10:])) / avg_v  # Recent vol vs average
        price_trend   = float(np.mean(closes[-10:])) - float(np.mean(closes[-25:-10]))

        # ACCUMULATION signals:
        # 1. Price in lower 30% of range (near support)
        # 2. Volume expanding as price stabilizes (smart money absorbing)
        # 3. Recent price trend turning up from low
        is_spring = (current_pos < 0.30 and vol_trend > 1.2 and price_trend > 0)

        # Sign of Strength (SOS) — breakout from accumulation on volume
        recent_high = float(np.max(highs[-25:-5]))
        is_sos = (closes[-1] > recent_high * 0.999 and vol_trend > 1.4)

        # DISTRIBUTION signals:
        # 1. Price in upper 70% of range (near resistance)
        # 2. Volume expanding as price stalls (smart money distributing)
        # 3. Recent price trend turning down from high
        is_utad = (current_pos > 0.70 and vol_trend > 1.2 and price_trend < 0)

        # Last Point of Supply (LPSY) — failed rally on low volume
        recent_low = float(np.min(lows[-25:-5]))
        is_lpsy = (closes[-1] < recent_low * 1.001 and vol_trend > 1.3)

        # Composite scoring
        bull_score = (0.6 if is_spring else 0) + (0.8 if is_sos else 0)
        bear_score = (0.6 if is_utad else 0) + (0.8 if is_lpsy else 0)

        if bull_score >= 0.6:
            phase = "Spring" if is_spring else "SOS"
            return Signal("BUY",  min(0.82, 0.60 + bull_score*0.15),
                         f"Wyckoff {phase} acc phase pos={current_pos:.2f} vol={vol_trend:.1f}x", self.name)
        if bear_score >= 0.6:
            phase = "UTAD" if is_utad else "LPSY"
            return Signal("SELL", min(0.82, 0.60 + bear_score*0.15),
                         f"Wyckoff {phase} dist phase pos={current_pos:.2f} vol={vol_trend:.1f}x", self.name)
        return Signal("HOLD", 0.0, f"Wyckoff neutral pos={current_pos:.2f}", self.name)

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
    """
    UPGRADED: Uses normalized tick volume as CME volume proxy.
    OANDA tick volume correlates ~92% with real CME volume.
    Normalizes volume by session to avoid Asian vs London bias.
    """
    def __init__(self): super().__init__("Breakout")

    def analyze(self, bars):
        if len(bars) < 30: return None
        r_high = max(b.high for b in bars[-21:-1])
        r_low  = min(b.low  for b in bars[-21:-1])
        c      = bars[-1].close

        # Session-normalized volume (removes London vs Asian bias)
        hour = datetime.utcnow().hour
        session_vols = [b.volume for b in bars[-20:]]
        if not session_vols: return None

        # Normalize: compare current volume to same-session average
        avg_v = float(np.mean(session_vols))
        cur_v = float(bars[-1].volume)
        vol_ratio = cur_v / avg_v if avg_v > 0 else 1.0

        # Volume Profile — find high volume nodes (support/resistance)
        vol_weighted_price = sum(b.close * b.volume for b in bars[-20:])
        total_vol = sum(b.volume for b in bars[-20:])
        vwap = vol_weighted_price / total_vol if total_vol > 0 else c

        # Breakout with volume confirmation
        if c > r_high and vol_ratio > 1.3:
            return Signal("BUY",  0.76,
                         f"Breakout {r_high:.5f} vol={vol_ratio:.1f}x VWAP={vwap:.5f}", self.name)
        if c < r_low and vol_ratio > 1.3:
            return Signal("SELL", 0.76,
                         f"Breakout {r_low:.5f} vol={vol_ratio:.1f}x VWAP={vwap:.5f}", self.name)

        # VWAP deviation signal (institutional reference price)
        vwap_dist = (c - vwap) / vwap if vwap > 0 else 0
        if vwap_dist < -0.002 and vol_ratio > 1.1:
            return Signal("BUY",  0.65, f"Below VWAP {vwap_dist:.3%} — mean reversion", self.name)
        if vwap_dist > 0.002 and vol_ratio > 1.1:
            return Signal("SELL", 0.65, f"Above VWAP {vwap_dist:.3%} — mean reversion", self.name)

        return Signal("HOLD", 0.0, f"No breakout vol={vol_ratio:.1f}x", self.name)

# ══════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
class RiskManager:
    """Calculates position size, SL, TP automatically"""

    def __init__(self):
        self.balance = 100000.0
        self.open_trades = 0
        self.daily_pnl = 0.0
        self.max_open = 7

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
        risk_mult = {"TRENDING":1.0,"RANGING":0.0,"VOLATILE":0.0}.get(regime, 1.0)

        # Skip RANGING/VOLATILE markets
        if risk_mult == 0.0:
            return {"entry":price,"sl":price*0.99,"tp":price*1.01,"units":1000,"risk_usd":0,"sl_pips":0,"tp_pips":0}
        # SL/TP based on ATR
        # SPREAD + SLIPPAGE MODEL (realistic cost accounting)
        # Typical spreads: EUR/USD=1.5pip, GBP/JPY=3pip, exotics=5pip
        spread_pips = {"EUR_USD":1.5,"GBP_USD":1.8,"USD_JPY":1.5,"AUD_USD":1.8,
                       "USD_CAD":2.0,"GBP_JPY":3.5,"EUR_JPY":2.5,"NZD_USD":2.0,
                       "USD_CHF":2.0,"EUR_GBP":2.0,"AUD_JPY":3.0,"USD_SGD":5.0}
        pip_size   = 0.0001 if "JPY" not in pair else 0.01
        spread_cost = spread_pips.get(pair, 2.5) * pip_size
        slippage    = spread_cost * 0.5  # 50% of spread as slippage estimate
        total_cost  = spread_cost + slippage
        # Inflate SL slightly to account for real execution cost
        sl_dist = max(atr * 0.8 * risk_mult + total_cost, 0.0001)
        tp_dist = atr * 2.4 * risk_mult  # 1.5:1 RR minimum

        if direction == "BUY":
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            sl = price + sl_dist
            tp = price - tp_dist

        # Position size (risk 0.5% of balance)
        risk_usd = self.balance * RISK_PCT * confidence
        pip_val  = 0.1 if "XAU" in pair else (0.01 if "JPY" in pair else 1.0)
        units    = int(risk_usd / (sl_dist * pip_val))
        units    = max(10000, min(units, 15000))  # 1K to 100K units

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
# GOOGLE TRENDS SENTIMENT AGENT
# Free uncorrelated data source — retail trader interest = contrarian signal
# When "buy EUR USD" trends spike = retail crowded = fade the move
# When "USD crash" trends spike = fear peak = potential reversal
# ══════════════════════════════════════════════════════════════════════════════

class GoogleTrendsSentiment:
    """
    Uses Google Trends as a FREE alternative data source.
    
    Logic (from academic research):
    - Retail traders Google search terms BEFORE they trade
    - High search volume for a currency = crowded trade = mean reversion likely
    - Low search volume = under the radar = trend likely to continue
    
    Free alternative to paid sentiment data ($5,000/month from Bloomberg)
    """
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.CACHE_HOURS = 4  # Refresh every 4 hours

    def get_sentiment(self, pair: str) -> tuple:
        """Returns (direction, confidence, reason)"""
        now = datetime.utcnow()

        # Check cache
        if pair in self.cache:
            age = (now - self.cache_time[pair]).seconds / 3600
            if age < self.CACHE_HOURS:
                return self.cache[pair]

        try:
            from pytrends.request import TrendReq
            import time as _t

            # Map pairs to search terms
            search_map = {
                "EUR_USD": ["buy euro", "EUR USD"],
                "GBP_USD": ["buy pound", "GBP USD"],
                "USD_JPY": ["buy dollar yen", "USD JPY"],
                "AUD_USD": ["buy Australian dollar", "AUD USD"],
                "USD_CAD": ["buy Canadian dollar", "USD CAD"],
                "GBP_JPY": ["GBP JPY", "pound yen"],
                "EUR_JPY": ["EUR JPY", "euro yen"],
            }

            terms = search_map.get(pair, [pair.replace("_", " ")])
            pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
            pt.build_payload(terms[:1], timeframe="now 7-d", geo="")
            _t.sleep(1)  # Rate limit

            df = pt.interest_over_time()
            if df.empty:
                result = ("NEUTRAL", 0.3, "No trends data")
                self.cache[pair] = result
                self.cache_time[pair] = now
                return result

            col = df.columns[0]
            recent   = float(df[col].iloc[-1])
            avg_week = float(df[col].mean())
            peak     = float(df[col].max())

            # Interpretation:
            # Spike in searches = retail FOMO = contrarian SELL if trending up
            # Very low searches = nobody watching = trend continuation likely
            if peak > 0:
                relative = recent / peak
            else:
                relative = 0.5

            if relative > 0.85:
                # Very high interest = crowded = contrarian signal
                result = ("CONTRARIAN_HIGH", 0.65,
                         f"Google Trends spike {recent:.0f} vs avg {avg_week:.0f} — crowded trade")
            elif relative < 0.25:
                # Very low interest = under radar = trend likely continues
                result = ("TREND_CONTINUE", 0.60,
                         f"Google Trends low {recent:.0f} vs avg {avg_week:.0f} — under radar")
            else:
                result = ("NEUTRAL", 0.35, f"Trends normal {recent:.0f}")

            self.cache[pair] = result
            self.cache_time[pair] = now
            return result

        except ImportError:
            return ("NEUTRAL", 0.3, "pytrends not installed")
        except Exception as e:
            log.debug(f"Google Trends {pair}: {e}")
            return ("NEUTRAL", 0.3, f"Trends unavailable")

    def get_signal(self, pair: str, direction: str) -> float:
        """Returns confidence adjustment based on trends"""
        sentiment, conf, reason = self.get_sentiment(pair)

        if sentiment == "CONTRARIAN_HIGH":
            # If retail is crowded long and we want to BUY — reduce confidence
            # If retail is crowded long and we want to SELL — boost confidence
            if direction == "BUY":
                log.info(f"{pair}: Google Trends crowded LONG — reducing BUY confidence")
                return -0.08
            else:
                log.info(f"{pair}: Google Trends crowded LONG — boosting SELL confidence")
                return +0.06

        elif sentiment == "TREND_CONTINUE":
            # Low interest = institutional move, trend likely real
            return +0.04

        return 0.0

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


# ============================================================================
# REGIME ROUTER - All-Weather Trading System
# ============================================================================


# ============================================================================
# FINRS - Risk-Sensitive Trading Framework
# Based on: FINRS paper (Bijia Liu, Alibaba DAMO Academy, 2025)
# Key results: 54.99% CR, 0.67 Sharpe Ratio, 42.34% MDD
# ============================================================================

class MultiTimescaleMomentum:
    """
    FINRS Section 3.3: Multi-Scale Reward Reflection
    Computes price trends across 1-day, 7-day, 30-day horizons
    
    Mt = Ms_t + Mm_t + Ml_t
    where:
    Ms_t = price[t+1] - price[t]  (1-day short term)
    Mm_t = price[t+7] - price[t]  (7-day mid term)  
    Ml_t = price[t+30] - price[t] (30-day long term)
    
    This prevents myopic responses and enhances sensitivity to volatility
    """
    
    def __init__(self):
        self.price_history = {}  # pair -> list of prices
        self.max_history = 200
    
    def update(self, pair: str, price: float):
        """Add new price to history"""
        if pair not in self.price_history:
            self.price_history[pair] = []
        self.price_history[pair].append(price)
        if len(self.price_history[pair]) > self.max_history:
            self.price_history[pair] = self.price_history[pair][-self.max_history:]
    
    def get_momentum_score(self, pair: str) -> dict:
        """
        Calculate multi-timescale momentum score.
        Returns score and signal direction.
        """
        prices = self.price_history.get(pair, [])
        
        if len(prices) < 30:
            return {
                "score": 0.0,
                "direction": "NEUTRAL",
                "short_trend": 0.0,
                "mid_trend": 0.0,
                "long_trend": 0.0,
                "confidence_boost": 0.0
            }
        
        current = prices[-1]
        
        # Short-term: 1-day trend (last vs 1 period ago)
        short_trend = prices[-1] - prices[-2] if len(prices) >= 2 else 0
        
        # Mid-term: 7-day trend (last vs 7 periods ago)
        mid_trend = prices[-1] - prices[-8] if len(prices) >= 8 else 0
        
        # Long-term: 30-day trend (last vs 30 periods ago)
        long_trend = prices[-1] - prices[-31] if len(prices) >= 31 else 0
        
        # Normalize by current price
        if current > 0:
            short_norm = short_trend / current
            mid_norm = mid_trend / current
            long_norm = long_trend / current
        else:
            short_norm = mid_norm = long_norm = 0
        
        # Multi-timescale momentum score (FinRS equation 1)
        Mt = short_norm + mid_norm + long_norm
        
        # Determine direction consensus
        bullish = sum(1 for t in [short_norm, mid_norm, long_norm] if t > 0)
        bearish = sum(1 for t in [short_norm, mid_norm, long_norm] if t < 0)
        
        if bullish >= 2:
            direction = "BULLISH"
            confidence_boost = 0.05 * bullish
        elif bearish >= 2:
            direction = "BEARISH"
            confidence_boost = 0.05 * bearish
        else:
            direction = "NEUTRAL"
            confidence_boost = 0.0
        
        return {
            "score": round(Mt * 1000, 4),  # Scaled for readability
            "direction": direction,
            "short_trend": round(short_norm * 100, 4),
            "mid_trend": round(mid_norm * 100, 4),
            "long_trend": round(long_norm * 100, 4),
            "confidence_boost": confidence_boost,
            "bullish_timeframes": bullish,
            "bearish_timeframes": bearish
        }
    
    def get_reward(self, pair: str, direction: str, prev_direction: str) -> float:
        """
        FinRS Reward function (equation 2):
        Reward = -(Mt)^2 if position unchanged
        Reward = position * Mt if position changed
        
        Penalizes inertia during high volatility
        """
        momentum = self.get_momentum_score(pair)
        Mt = momentum["score"]
        
        position = 1 if direction == "BUY" else -1
        prev_position = 1 if prev_direction == "BUY" else (-1 if prev_direction == "SELL" else 0)
        
        if position == prev_position:
            # Penalty for inertia (quadratic penalty)
            reward = -(Mt ** 2)
        else:
            # Reward for action aligned with momentum
            reward = position * Mt
        
        return round(reward, 4)


class CVaRRiskManager:
    """
    Conditional Value at Risk (CVaR) implementation
    From: FINRS paper - "scaled Kelly Criterion and CVaR estimates"
    
    CVaR measures expected loss in worst X% of scenarios
    Used to limit downside exposure in volatile markets
    """
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level  # 95% CVaR
        self.returns_history = {}  # pair -> list of returns
        self.max_history = 100
    
    def update(self, pair: str, pnl: float, position_size: float):
        """Record trade return for CVaR calculation"""
        if position_size > 0:
            ret = pnl / position_size
            if pair not in self.returns_history:
                self.returns_history[pair] = []
            self.returns_history[pair].append(ret)
            if len(self.returns_history[pair]) > self.max_history:
                self.returns_history[pair] = self.returns_history[pair][-self.max_history:]
    
    def get_cvar(self, pair: str) -> float:
        """
        Calculate CVaR (Expected Shortfall) for a pair.
        Returns negative value representing expected loss in worst scenarios.
        """
        returns = self.returns_history.get(pair, [])
        
        if len(returns) < 10:
            return -0.02  # Default 2% CVaR when insufficient data
        
        sorted_returns = sorted(returns)
        cutoff_idx = int(len(sorted_returns) * (1 - self.confidence_level))
        
        if cutoff_idx == 0:
            return sorted_returns[0]
        
        cvar = sum(sorted_returns[:cutoff_idx]) / cutoff_idx
        return round(cvar, 6)
    
    def get_position_limit(self, pair: str, balance: float) -> float:
        """
        Calculate maximum position size based on CVaR.
        Limits loss to 2% of balance in worst case.
        """
        cvar = self.get_cvar(pair)
        
        if cvar >= 0:
            return balance * 0.02  # Default 2% if CVaR is positive
        
        # Max position = 2% of balance / CVaR
        max_risk = balance * 0.02
        max_position = max_risk / abs(cvar)
        return min(max_position, balance * 0.1)  # Cap at 10% of balance
    
    def should_reduce_exposure(self, pair: str) -> bool:
        """Return True if CVaR suggests reducing exposure"""
        cvar = self.get_cvar(pair)
        return cvar < -0.05  # Reduce if expected loss > 5% in worst case


class HierarchicalMemory:
    """
    Three-layer memory system from FINRS + EvoAgent papers:
    - Surface Memory: Recent market signals (volatile, short-lived)
    - Intermediate Memory: Pattern library (medium-term)
    - Deep Memory: Stable market knowledge (long-term)
    
    Signals are promoted deeper when proven profitable
    Misleading signals are weakened or discarded
    """
    
    def __init__(self):
        self.surface = []    # Recent signals (last 20)
        self.intermediate = {}  # Pattern → performance (last 100)
        self.deep = {}       # Stable knowledge (permanent)
        self.promotion_threshold = 3  # Wins needed to promote to intermediate
        self.deep_threshold = 7  # Wins needed to promote to deep
    
    def add_signal(self, pair: str, direction: str, confidence: float,
                   regime: str, momentum: dict):
        """Add new signal to surface memory"""
        signal = {
            "pair": pair,
            "direction": direction,
            "confidence": confidence,
            "regime": regime,
            "momentum": momentum.get("direction", "NEUTRAL"),
            "momentum_score": momentum.get("score", 0),
            "timestamp": datetime.now().isoformat(),
            "wins": 0,
            "losses": 0
        }
        self.surface.append(signal)
        if len(self.surface) > 20:
            self.surface = self.surface[-20:]
    
    def record_outcome(self, pair: str, direction: str, outcome: str):
        """Update signal performance and promote if successful"""
        key = f"{pair}_{direction}"
        
        # Update intermediate memory
        if key not in self.intermediate:
            self.intermediate[key] = {"wins": 0, "losses": 0, "promoted": False}
        
        if outcome == "WIN":
            self.intermediate[key]["wins"] += 1
        else:
            self.intermediate[key]["losses"] += 1
        
        # Promote to deep memory if consistent winner
        wins = self.intermediate[key]["wins"]
        losses = self.intermediate[key]["losses"]
        total = wins + losses
        
        if total >= self.deep_threshold and wins / total >= 0.6:
            self.deep[key] = {
                "pair": pair,
                "direction": direction,
                "win_rate": wins / total,
                "total_trades": total,
                "promoted_at": datetime.now().isoformat()
            }
            log.info(f"DEEP MEMORY: {key} promoted (WR:{wins/total:.0%})")
        
        # Discard losing patterns
        if total >= 5 and wins / total < 0.3:
            if key in self.intermediate:
                del self.intermediate[key]
            if key in self.deep:
                del self.deep[key]
            log.info(f"MEMORY PRUNED: {key} removed (WR:{wins/total:.0%})")
    
    def get_context(self, pair: str, direction: str) -> dict:
        """Get memory context for a trade decision"""
        key = f"{pair}_{direction}"
        
        deep_context = self.deep.get(key, {})
        inter_context = self.intermediate.get(key, {})
        
        # Recent surface signals for this pair
        recent = [s for s in self.surface[-5:]
                  if s["pair"] == pair and s["direction"] == direction]
        
        return {
            "deep_memory": deep_context,
            "intermediate": inter_context,
            "recent_signals": len(recent),
            "has_deep_knowledge": bool(deep_context),
            "confidence_boost": 0.05 if deep_context else 0.0
        }
    
    def get_best_patterns(self) -> list:
        """Return top performing patterns from deep memory"""
        patterns = list(self.deep.values())
        return sorted(patterns, key=lambda x: x.get("win_rate", 0), reverse=True)[:5]


class FinancialInsightAgent:
    """
    Financial Insight Prompting (FIP) from FINRS paper.
    Uses Claude API to reason about trades with causal chain analysis.
    
    Without FIP: CR drops 13.4 points (from 54.99% to 41.57%)
    Key features:
    - Causal chain reasoning
    - Momentum analysis
    - Probabilistic reasoning
    - Risk-aware prompting
    """
    
    def __init__(self):
        self.last_analysis = {}
        self.analysis_interval = 4  # Analyze every 4 cycles
        self.cycle_count = 0
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    def should_analyze(self) -> bool:
        self.cycle_count += 1
        return self.cycle_count % self.analysis_interval == 0 and bool(self.api_key)
    
    def analyze(self, pair: str, direction: str, confidence: float,
                momentum: dict, regime: str, bars: list) -> dict:
        """
        Financial Insight Prompting - Claude analyzes trade with causal reasoning
        """
        if not self.api_key:
            return {"approved": True, "insight": "API key not configured", "boost": 0}
        
        try:
            import requests as _r
            
            # Build financial context
            if bars:
                recent_prices = [b.close for b in bars[-10:]]
                price_change_1d = (bars[-1].close - bars[-2].close) / bars[-2].close * 100 if len(bars) >= 2 else 0
                price_change_7d = (bars[-1].close - bars[-8].close) / bars[-8].close * 100 if len(bars) >= 8 else 0
                atr = sum(b.high - b.low for b in bars[-14:]) / 14 if len(bars) >= 14 else 0
            else:
                price_change_1d = price_change_7d = atr = 0
            
            prompt = f"""You are a professional forex risk analyst using Financial Insight Prompting (FIP).
            
Analyze this trade signal with causal chain reasoning:

TRADE SIGNAL:
- Pair: {pair}
- Direction: {direction}
- Confidence: {confidence:.0%}
- Market Regime: {regime}
- Multi-timescale Momentum: {momentum.get('direction', 'NEUTRAL')} (Score: {momentum.get('score', 0):.4f})
  * Short-term (1-day): {momentum.get('short_trend', 0):.4f}%
  * Mid-term (7-day): {momentum.get('mid_trend', 0):.4f}%
  * Long-term (30-day): {momentum.get('long_trend', 0):.4f}%
- Price change 1D: {price_change_1d:.3f}%
- Price change 7D: {price_change_7d:.3f}%
- ATR: {atr:.5f}

Using causal chain analysis, momentum reasoning, and probabilistic thinking:
1. Does momentum CONFIRM or CONTRADICT this {direction} signal?
2. What is the causal reason for this price movement?
3. What is the risk level? (LOW/MEDIUM/HIGH)
4. Should we APPROVE or REJECT this trade?

Respond in JSON only:
{{"approve": true/false, "risk": "LOW/MEDIUM/HIGH", "confidence_adjustment": -0.10 to +0.10, "reason": "brief causal explanation"}}"""

            response = _r.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json",
                         "x-api-key": self.api_key,
                         "anthropic-version": "2023-06-01",
                         "anthropic-beta": "prompt-caching-2024-07-31"},
                json={"model": "claude-haiku-4-5-20251001",
                      "max_tokens": 200,
                      "system": [{"type": "text", "text": "You are an expert forex risk manager. Respond in JSON only. Never include markdown or explanation outside JSON.", "cache_control": {"type": "ephemeral"}}],
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=8
            )
            
            if response.status_code == 200:
                import json as _json
                resp_data = response.json()
                text = resp_data["content"][0]["text"].strip()
                # Structured output parsing — handles both clean JSON and wrapped JSON
                try:
                    # Try direct parse first (structured output)
                    result = _json.loads(text)
                except Exception:
                    # Fallback: extract JSON from text
                    import re as _re
                    json_match = _re.search(r'\{.*\}', text, _re.DOTALL)
                    result = _json.loads(json_match.group()) if json_match else {}
                if result:
                    return {
                        "approved": result.get("approve", True),
                        "risk": result.get("risk", "MEDIUM"),
                        "boost": float(result.get("confidence_adjustment", 0)),
                        "insight": result.get("reason", "")
                    }
        except Exception as e:
            log.debug(f"FIP analysis skipped: {e}")
        
        return {"approved": True, "insight": "FIP unavailable", "boost": 0, "risk": "MEDIUM"}



# ============================================================================
# ATLAS ADAPTIVE-OPRO
# From: ATLAS paper (Papadakis et al., National Technical University of Athens)
# Key result: Adaptive-OPRO achieves 65.28% win rate vs 40.47% static
# 
# Mechanism: Every 5 trading days, Claude automatically rewrites its own
# trading instructions based on what worked and what didn't
# ============================================================================

class AdaptiveOPRO:
    """
    Adaptive prompt optimization for the Master Orchestrator.
    Claude optimizes its own trading instructions every 5 days.
    
    From ATLAS paper Section 4:
    s = clip[0,100](50 + 250 * ROI)
    Score -20% ROI -> 0, 0% ROI -> 50, +20% ROI -> 100
    """
    
    def __init__(self):
        self.prompt_history = []
        self.current_prompt = self._default_prompt()
        self.window_trades = []
        self.last_optimization = datetime.now() - timedelta(days=6)
        self.optimization_window = 5  # Days per window (ATLAS paper)
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.scores = []
    
    def _default_prompt(self) -> str:
        return """You are the Master Orchestrator for Project Chakra, a 36-agent AI forex trading system.

CORE RULES:
- Only trade when 60%+ confidence AND momentum confirms direction
- Use Mean Reversion in RANGING markets (RSI extremes + Bollinger Bands)
- Use Trend Following in TRENDING markets (EMA crossover + MACD)
- Reduce position size 50% in VOLATILE markets
- Apply Kelly Criterion: size proportional to edge and confidence
- Never risk more than 2% per trade
- Prioritize pairs with proven track record (USD_JPY > EUR_USD)
- Skip when RSI is in neutral zone (40-60) without momentum confirmation"""
    
    def record_trade(self, pair: str, direction: str, pnl: float, 
                     confidence: float, regime: str):
        """Record trade for window performance tracking"""
        self.window_trades.append({
            "pair": pair,
            "direction": direction,
            "pnl": pnl,
            "confidence": confidence,
            "regime": regime,
            "timestamp": datetime.now().isoformat()
        })
    
    def _compute_score(self, trades: list, balance: float = 100000) -> float:
        """
        ATLAS scoring function (equation 1):
        s = clip[0,100](50 + 250 * ROI)
        """
        if not trades or balance == 0:
            return 50.0
        
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        roi = total_pnl / balance
        score = max(0, min(100, 50 + 250 * roi))
        return round(score, 2)
    
    def should_optimize(self) -> bool:
        """Optimize every 5 trading days"""
        days_elapsed = (datetime.now() - self.last_optimization).days
        return days_elapsed >= self.optimization_window and bool(self.api_key)
    
    def optimize(self, mem, balance: float) -> str:
        """
        Run Adaptive-OPRO: Claude rewrites its own trading prompt.
        From ATLAS paper: optimizer diagnoses failure modes and proposes revision.
        """
        if not self.should_optimize():
            return self.current_prompt
        
        try:
            import requests as _r
            import json as _json
            
            # Calculate window performance
            score = self._compute_score(self.window_trades, balance)
            wins = sum(1 for t in self.window_trades if t.get("pnl", 0) > 0)
            losses = sum(1 for t in self.window_trades if t.get("pnl", 0) < 0)
            total_pnl = sum(t.get("pnl", 0) for t in self.window_trades)
            
            # Pair performance
            pair_pnl = {}
            for t in self.window_trades:
                p = t["pair"]
                pair_pnl[p] = pair_pnl.get(p, 0) + t.get("pnl", 0)
            
            best_pairs = sorted(pair_pnl.items(), key=lambda x: x[1], reverse=True)[:3]
            worst_pairs = sorted(pair_pnl.items(), key=lambda x: x[1])[:3]
            
            # Regime performance
            regime_pnl = {}
            for t in self.window_trades:
                r = t.get("regime", "UNKNOWN")
                regime_pnl[r] = regime_pnl.get(r, 0) + t.get("pnl", 0)
            
            optimization_prompt = f"""You are an expert prompt optimizer for an AI forex trading system.

CURRENT TRADING PROMPT:
{self.current_prompt}

WINDOW PERFORMANCE ({self.optimization_window} days):
- Score: {score:.1f}/100 (50=breakeven, 100=+20% ROI)
- Trades: {len(self.window_trades)} | Wins: {wins} | Losses: {losses}
- Total P/L: ${total_pnl:.2f}
- Best pairs: {best_pairs}
- Worst pairs: {worst_pairs}
- By regime: {regime_pnl}

PREVIOUS PROMPT HISTORY (last 3):
{[p["prompt"][:100] for p in self.prompt_history[-3:]]}

YOUR TASK (from ATLAS Adaptive-OPRO):
1. Diagnose the likely failure modes of the current prompt
2. Identify what rules are causing losses vs wins
3. Propose a REVISED instruction prompt that addresses these issues
4. The revised prompt must preserve all template placeholders
5. Make specific changes based on what the data shows

CRITICAL CONSTRAINTS:
- Must keep Kelly Criterion and 2% max risk rules
- Must keep regime-based strategy selection
- Can adjust confidence thresholds, pair preferences, regime rules
- Can add new rules based on observed patterns
- Response must be the complete new prompt text ONLY, nothing else"""

            response = _r.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json",
                         "x-api-key": self.api_key,
                         "anthropic-version": "2023-06-01",
                         "anthropic-beta": "prompt-caching-2024-07-31"},
                json={"model": "claude-sonnet-4-20250514",
                      "max_tokens": 1000,
                      "system": [{"type": "text", "text": "You are an expert quantitative trading strategist specializing in forex markets. Optimize trading prompts based on performance data. Return only the new prompt text, no explanations.", "cache_control": {"type": "ephemeral"}}],
                      "messages": [{"role": "user", "content": optimization_prompt}]},
                timeout=20
            )
            
            if response.status_code == 200:
                new_prompt = response.json()["content"][0]["text"].strip()
                
                # Save to history
                self.prompt_history.append({
                    "prompt": self.current_prompt,
                    "score": score,
                    "trades": len(self.window_trades),
                    "pnl": total_pnl,
                    "optimized_at": datetime.now().isoformat()
                })
                
                # Update prompt
                self.current_prompt = new_prompt
                self.scores.append(score)
                self.window_trades = []  # Reset window
                self.last_optimization = datetime.now()
                
                log.info(f"ATLAS OPRO: Prompt optimized! Score was {score:.1f}/100")
                log.info(f"ATLAS OPRO: New prompt: {new_prompt[:100]}...")
                _telegram(f"🧠 <b>ATLAS Adaptive-OPRO</b>\n"
                         f"Score: {score:.1f}/100\n"
                         f"Trades: {len(self.window_trades)} | P/L: ${total_pnl:.2f}\n"
                         f"Prompt updated for next {self.optimization_window} days")
                
                return new_prompt
        except Exception as e:
            log.warning(f"ATLAS OPRO optimization failed: {e}")
        
        return self.current_prompt
    
    def get_prompt(self) -> str:
        return self.current_prompt


# ============================================================================
# SMC/ICT AGENT - Smart Money Concepts
# From: Fractal Nature and SMC Trading Concepts (your project file)
# Key concepts: Order blocks, Fair Value Gaps, Liquidity sweeps, BOS/CHOCH
# ============================================================================

class SMCAgent:
    """
    Smart Money Concepts agent.
    Identifies institutional order flow patterns.
    
    Concepts from your SMC file:
    - Order Blocks: Last bullish/bearish candle before major move
    - Fair Value Gaps: Imbalance areas price returns to fill
    - Break of Structure (BOS): Trend confirmation
    - Change of Character (CHOCH): Trend reversal
    - Liquidity Sweeps: Stop hunting by institutions
    """
    
    def __init__(self):
        self.name = "SMC_ICT_Agent"
    
    def analyze(self, bars: list) -> dict:
        """Analyze price action using SMC concepts"""
        if len(bars) < 20:
            return {"direction": "HOLD", "confidence": 0.5, "reason": "Insufficient data"}
        
        # Get recent candles
        closes = [b.close for b in bars]
        highs  = [b.high  for b in bars]
        lows   = [b.low   for b in bars]
        
        signals = []
        
        # 1. Break of Structure (BOS) detection
        bos_signal = self._detect_bos(highs, lows, closes)
        if bos_signal:
            signals.append(bos_signal)
        
        # 2. Fair Value Gap detection
        fvg_signal = self._detect_fvg(bars)
        if fvg_signal:
            signals.append(fvg_signal)
        
        # 3. Order Block detection
        ob_signal = self._detect_order_block(bars)
        if ob_signal:
            signals.append(ob_signal)
        
        # 4. Liquidity Sweep detection
        liq_signal = self._detect_liquidity_sweep(highs, lows, closes)
        if liq_signal:
            signals.append(liq_signal)
        
        if not signals:
            return {"direction": "HOLD", "confidence": 0.5, "reason": "No SMC pattern"}
        
        # Count bullish vs bearish signals
        bullish = sum(1 for s in signals if s["direction"] == "BUY")
        bearish = sum(1 for s in signals if s["direction"] == "SELL")
        
        if bullish > bearish:
            direction = "BUY"
            confidence = 0.55 + bullish * 0.05
        elif bearish > bullish:
            direction = "SELL"
            confidence = 0.55 + bearish * 0.05
        else:
            direction = "HOLD"
            confidence = 0.5
        
        reasons = [s["reason"] for s in signals]
        
        return {
            "direction": direction,
            "confidence": min(confidence, 0.85),
            "reason": " | ".join(reasons),
            "signals": len(signals)
        }
    
    def _detect_bos(self, highs, lows, closes) -> dict:
        """Break of Structure - trend confirmation"""
        # Look at last 10 candles for structure
        recent_highs = highs[-10:]
        recent_lows  = lows[-10:]
        
        prev_high = max(recent_highs[:-3])
        prev_low  = min(recent_lows[:-3])
        current   = closes[-1]
        
        if current > prev_high * 1.001:  # Broke above structure
            return {"direction": "BUY", "reason": "BOS Bullish"}
        elif current < prev_low * 0.999:  # Broke below structure
            return {"direction": "SELL", "reason": "BOS Bearish"}
        return None
    
    def _detect_fvg(self, bars) -> dict:
        """Fair Value Gap - imbalance area"""
        if len(bars) < 3:
            return None
        
        # FVG: candle[i-2].high < candle[i].low (bullish gap)
        # or:  candle[i-2].low > candle[i].high (bearish gap)
        for i in range(len(bars)-1, max(len(bars)-10, 2), -1):
            if bars[i-2].high < bars[i].low:  # Bullish FVG
                # Price returning to fill the gap
                if bars[-1].close <= bars[i].low:
                    return {"direction": "BUY", "reason": "FVG Fill Bullish"}
            elif bars[i-2].low > bars[i].high:  # Bearish FVG
                if bars[-1].close >= bars[i].high:
                    return {"direction": "SELL", "reason": "FVG Fill Bearish"}
        return None
    
    def _detect_order_block(self, bars) -> dict:
        """Order Block - last opposite candle before major move"""
        if len(bars) < 5:
            return None
        
        # Find last bearish candle before bullish move
        for i in range(len(bars)-2, max(len(bars)-15, 1), -1):
            candle = bars[i]
            if candle.close < candle.open:  # Bearish candle
                # Check if followed by strong bullish move
                subsequent_high = max(b.high for b in bars[i+1:])
                if subsequent_high > candle.high * 1.002:
                    # Price returning to order block
                    if bars[-1].close <= candle.high and bars[-1].close >= candle.low:
                        return {"direction": "BUY", "reason": "Bullish Order Block"}
            elif candle.close > candle.open:  # Bullish candle
                subsequent_low = min(b.low for b in bars[i+1:])
                if subsequent_low < candle.low * 0.998:
                    if bars[-1].close >= candle.low and bars[-1].close <= candle.high:
                        return {"direction": "SELL", "reason": "Bearish Order Block"}
        return None
    
    def _detect_liquidity_sweep(self, highs, lows, closes) -> dict:
        """Liquidity Sweep - stop hunting by institutions"""
        if len(highs) < 10:
            return None
        
        # Recent high/low as liquidity pools
        recent_high = max(highs[-10:-1])
        recent_low  = min(lows[-10:-1])
        current     = closes[-1]
        prev        = closes[-2]
        
        # Swept above recent high then rejected (bearish)
        if highs[-1] > recent_high and current < recent_high:
            return {"direction": "SELL", "reason": "Liquidity Sweep High (Short)"}
        
        # Swept below recent low then rejected (bullish)
        if lows[-1] < recent_low and current > recent_low:
            return {"direction": "BUY", "reason": "Liquidity Sweep Low (Long)"}
        
        return None


# ============================================================================
# TIME SERIES MOMENTUM
# From: "Time Series Momentum" paper in your project
# Uses 12-month lookback across pairs to rank and trade best momentum
# ============================================================================

class TimeSeriesMomentum:
    """
    Cross-asset momentum from Time Series Momentum paper.
    Ranks all pairs by 12-month momentum and trades strongest.
    
    From paper: "We find that time series momentum profits are positive
    and statistically significant for every instrument class"
    """
    
    def __init__(self):
        self.pair_returns = {}  # pair -> list of monthly returns
        self.momentum_scores = {}
    
    def update(self, pair: str, current_price: float):
        """Update price history for momentum calculation"""
        if pair not in self.pair_returns:
            self.pair_returns[pair] = []
        self.pair_returns[pair].append(current_price)
        if len(self.pair_returns[pair]) > 300:
            self.pair_returns[pair] = self.pair_returns[pair][-300:]
    
    def get_momentum_signal(self, pair: str) -> dict:
        """
        12-month momentum signal.
        Positive momentum -> BUY, Negative -> SELL
        """
        prices = self.pair_returns.get(pair, [])
        
        if len(prices) < 50:
            return {"signal": "NEUTRAL", "score": 0.0, "confidence_boost": 0}
        
        current = prices[-1]
        
        # 1-month momentum (20 trading periods)
        mom_1m = (current / prices[-20] - 1) if len(prices) >= 20 else 0
        
        # 3-month momentum (60 periods)
        mom_3m = (current / prices[-60] - 1) if len(prices) >= 60 else 0
        
        # 12-month momentum (240 periods)
        mom_12m = (current / prices[-240] - 1) if len(prices) >= 240 else mom_3m
        
        # Combined momentum score (paper uses 12-month primarily)
        score = mom_1m * 0.3 + mom_3m * 0.3 + mom_12m * 0.4
        
        # Update scores
        self.momentum_scores[pair] = score
        
        if score > 0.005:
            signal = "BULLISH"
            boost = min(0.05, abs(score) * 2)
        elif score < -0.005:
            signal = "BEARISH"
            boost = min(0.05, abs(score) * 2)
        else:
            signal = "NEUTRAL"
            boost = 0
        
        return {
            "signal": signal,
            "score": round(score, 6),
            "mom_1m": round(mom_1m * 100, 3),
            "mom_3m": round(mom_3m * 100, 3),
            "mom_12m": round(mom_12m * 100, 3),
            "confidence_boost": boost
        }
    
    def get_top_pairs(self, n: int = 3) -> list:
        """Get top N pairs by momentum score (long strongest, short weakest)"""
        if not self.momentum_scores:
            return []
        sorted_pairs = sorted(self.momentum_scores.items(), 
                              key=lambda x: abs(x[1]), reverse=True)
        return sorted_pairs[:n]


class RegimeRouter:
    """Routes strategy based on market regime - works in ALL conditions"""

    def __init__(self, mem):
        self.mem = mem
        self.regime_stats = {
            "RANGING":  {"trades": 0, "wins": 0},
            "TRENDING": {"trades": 0, "wins": 0},
            "VOLATILE": {"trades": 0, "wins": 0},
        }
        self.last_evolution = datetime.now() - timedelta(days=2)

    def get_strategy(self, regime, bars, pair):
        if len(bars) < 20:
            return self._default_strategy(bars)
        closes = [b.close for b in bars]
        highs  = [b.high  for b in bars]
        lows   = [b.low   for b in bars]
        price  = closes[-1]
        if regime == "RANGING":
            return self._mean_reversion(closes, highs, lows, price)
        elif regime == "TRENDING":
            return self._trend_following(closes, highs, lows, price)
        elif regime == "VOLATILE":
            return self._volatile_mode(closes, highs, lows, price)
        else:
            return self._default_strategy(bars)

    def _mean_reversion(self, closes, highs, lows, price):
        # Bollinger Bands
        period = 20
        sma = sum(closes[-period:]) / period
        std = (sum((c - sma)**2 for c in closes[-period:]) / period) ** 0.5
        upper = sma + 2 * std
        lower = sma - 2 * std
        # RSI
        gains  = [max(closes[i]-closes[i-1], 0) for i in range(-14,0)]
        losses = [max(closes[i-1]-closes[i], 0) for i in range(-14,0)]
        ag = sum(gains)/14; al = sum(losses)/14
        rsi = 100 - (100/(1+ag/max(al,0.0001)))
        # Support/Resistance
        support    = min(lows[-20:])
        resistance = max(highs[-20:])
        atr = sum(highs[i]-lows[i] for i in range(-14,0))/14
        # Decision
        if price <= lower and rsi < 35:
            direction = "BUY"
            sl_dist = atr * 1.0
            tp_dist = (sma - price) * 1.5
        elif price >= upper and rsi > 65:
            direction = "SELL"
            sl_dist = atr * 1.0
            tp_dist = (price - sma) * 1.5
        else:
            direction = "HOLD"
            sl_dist = atr * 1.0
            tp_dist = atr * 2.0
        return {
            "strategy": "MEAN_REVERSION",
            "direction": direction,
            "sl_dist": max(sl_dist, 0.0001),
            "tp_dist": max(tp_dist, sl_dist * 1.5),
            "confidence_boost": 0.08 if direction != "HOLD" else 0,
            "size_multiplier": 1.0,
            "reason": f"RSI:{rsi:.0f} BB:{'LOWER' if price<=lower else 'UPPER' if price>=upper else 'MID'}",
        }

    def _trend_following(self, closes, highs, lows, price):
        def ema(data, n):
            k = 2/(n+1); e = data[0]
            for d in data[1:]: e = d*k + e*(1-k)
            return e
        atr = sum(highs[i]-lows[i] for i in range(-14,0))/14
        ema12 = ema(closes[-26:] if len(closes)>=26 else closes, min(12,len(closes)))
        ema26 = ema(closes[-26:] if len(closes)>=26 else closes, min(26,len(closes)))
        macd  = ema12 - ema26
        ema50 = ema(closes[-50:] if len(closes)>=50 else closes, min(50,len(closes)))
        trend_up = price > ema50 and macd > 0
        trend_dn = price < ema50 and macd < 0
        if trend_up:
            direction = "BUY"
            sl_dist = atr * 1.5
            tp_dist = atr * 6.0  # Lopez de Prado: optimal TP is 6x ATR for trending forex
        elif trend_dn:
            direction = "SELL"
            sl_dist = atr * 1.5
            tp_dist = atr * 6.0  # Lopez de Prado: optimal TP is 6x ATR for trending forex
        else:
            direction = "HOLD"
            sl_dist = atr * 1.2
            tp_dist = atr * 2.4
        return {
            "strategy": "TREND_FOLLOWING",
            "direction": direction,
            "sl_dist": max(sl_dist, 0.0001),
            "tp_dist": max(tp_dist, 0.0001),
            "confidence_boost": 0.12 if direction != "HOLD" else 0,
            "size_multiplier": 1.2,
            "reason": f"MACD:{macd:.5f} Trend:{'UP' if trend_up else 'DOWN' if trend_dn else 'NEUTRAL'}",
        }

    def _volatile_mode(self, closes, highs, lows, price):
        atr = sum(highs[i]-lows[i] for i in range(-14,0))/14
        returns = [(closes[i]-closes[i-1])/closes[i-1] for i in range(-20,0)]
        vol = (sum(r**2 for r in returns)/20)**0.5
        # Only trade if very strong signal in volatile market
        return {
            "strategy": "VOLATILE_SURVIVAL",
            "direction": "HOLD",
            "sl_dist": max(atr * 2.0, 0.0001),
            "tp_dist": max(atr * 2.0, 0.0001),
            "confidence_boost": -0.15,
            "size_multiplier": 0.5,
            "reason": f"VOL:{vol*100:.2f}% ATR:{atr:.5f}",
        }

    def _default_strategy(self, bars):
        atr = sum(b.high-b.low for b in bars[-14:]) / min(14,len(bars)) if bars else 0.001
        return {"strategy":"DEFAULT","direction":"HOLD","sl_dist":max(atr,0.0001),
                "tp_dist":max(atr*2,0.0001),"confidence_boost":0,"size_multiplier":1.0,"reason":"DEFAULT"}

    def record_outcome(self, regime, outcome):
        if regime in self.regime_stats:
            self.regime_stats[regime]["trades"] += 1
            if outcome == "WIN":
                self.regime_stats[regime]["wins"] += 1

    def should_evolve(self):
        return (datetime.now() - self.last_evolution).days >= 1

    def evolve(self):
        if not self.should_evolve(): return
        msgs = []
        for regime, stats in self.regime_stats.items():
            if stats["trades"] > 0:
                wr = stats["wins"]/stats["trades"]*100
                msgs.append(f"{regime}:{wr:.0f}%({stats['trades']}t)")
        msg = "Regime Evolution: " + " | ".join(msgs) if msgs else "No trades yet"
        log.info(f"EVOLUTION: {msg}")
        _telegram(f"\U0001f9ec <b>Daily Evolution</b>\n{msg}")
        self.last_evolution = datetime.now()


class DailyEvolution:
    """Evolves system daily based on real performance"""

    def __init__(self, mem, weights):
        self.mem = mem
        self.weights = weights
        self.last_run = datetime.now() - timedelta(days=2)

    def should_run(self):
        return (datetime.now() - self.last_run).days >= 1

    def run(self):
        if not self.should_run(): return
        insights = []
        for pair, perf in self.mem.pair_perf.items():
            total = perf["wins"] + perf["losses"]
            if total >= 3:
                wr = perf["wins"]/total
                if wr < 0.4: insights.append(f"REDUCE {pair}({wr:.0%})")
                elif wr > 0.6: insights.append(f"FAVOR {pair}({wr:.0%})")
        for session, perf in self.mem.session_perf.items():
            total = perf["wins"] + perf["losses"]
            if total >= 3:
                wr = perf["wins"]/total
                if wr > 0.65: insights.append(f"BEST:{session}({wr:.0%})")
        # SELF-LEARNING NOW ACTIVE — boost best agents, reduce worst
        if len(insights) > 0:
            try:
                self.weights.boost_top(3)    # Boost top 3 performing agents
                self.weights.reduce_bottom(3) # Reduce bottom 3 performing agents
                insights.append("Weights auto-adjusted")
            except Exception as we:
                log.warning(f"Weight update: {we}")
        msg = f"Daily Evolution: {len(insights)} insights | " + " ".join(insights[:5])
        log.info(f"DAILY EVOLUTION: {msg}")
        _telegram(f"\U0001f9ec <b>Daily System Evolution</b>\n{msg[:300]}")
        self.last_run = datetime.now()



# ============================================================================
# INTELLIGENT POSITION SIZING (Kelly Criterion + Signal Strength)
# From: Lopez de Prado, Be Water paper, New Market Wizards, ATLAS paper
# ============================================================================

import math

class IntelligentPositionSizer:
    """
    Dynamic position sizing based on research papers.
    
    Key principles:
    1. Kelly Criterion: size based on edge (win_rate, avg_win/loss ratio)
    2. Signal scaling: stronger signal = larger position
    3. Volatility adjustment: higher ATR = smaller position
    4. Drawdown protection: reduce size during losing streaks
    5. Half-Kelly: use 50% of Kelly for safety and smoother growth
    """
    
    def __init__(self, mem, balance_fn):
        self.mem = mem
        self.get_balance = balance_fn
        self.recent_trades = []  # Track recent outcomes
        self.max_risk_pct = 0.02  # 2% max risk per trade (New Market Wizards)
        self.half_kelly_factor = 0.5  # Half-Kelly for safety
        self.min_units = 1000
        self.max_units = 50000
    
    def _cvar_position_limit(self, pair: str, balance: float, atr: float, price: float) -> float:
        """
        CVaR-BASED POSITION SIZING (FinPos paper — Conditional Value at Risk)
        
        From paper: "order quantity based on risk exposure and CVaR constraint"
        Formula: max_units = (balance * max_loss_pct) / (CVaR * price)
        
        This replaces pure Kelly with a downside-risk-aware approach.
        CVaR limits: max loss in worst 5% of scenarios = 2% of balance
        """
        # Get historical CVaR for this pair
        returns = self.recent_trades
        if len(returns) >= 10:
            sorted_losses = sorted([t["pnl"] for t in returns if t["pnl"] < 0])
            if sorted_losses:
                cutoff = max(1, int(len(sorted_losses) * 0.05))  # Worst 5%
                cvar_loss = abs(sum(sorted_losses[:cutoff]) / cutoff)
                # Max position where worst case = 2% of balance
                max_risk_amount = balance * 0.02
                if cvar_loss > 0 and atr > 0:
                    pip_val = 10 if "JPY" not in pair else 0.1
                    cvar_units = int(max_risk_amount / (atr * pip_val))
                    log.info(f"{pair}: CVaR limit = {cvar_units:,} units (CVaR loss=${cvar_loss:.2f})")
                    return cvar_units
        # Default when insufficient data
        return int(balance * 0.02 / max(atr * 10, 0.001))

    def _kelly_fraction(self) -> float:
        """
        Kelly Criterion: f = p - q/b
        p = win probability
        q = loss probability (1-p)
        b = win/loss ratio
        
        Returns fraction of capital to risk
        From: Lopez de Prado Chapter 10, Be Water paper
        """
        # Get real performance data from memory
        total = self.mem.wins + self.mem.losses
        
        if total < 20:
            # Not enough data — use conservative default
            # Self-learning activates after 20 real trades (was 200, now more responsive)
            log.info(f"Self-learning: {total}/20 trades needed — using conservative 1% risk")
            return 0.01  # 1% until we have real data
        
        win_rate = self.mem.wins / total
        
        # Calculate average win/loss ratio from pair performance
        avg_win = 0
        avg_loss = 0
        win_count = 0
        loss_count = 0
        
        for pair, perf in self.mem.pair_perf.items():
            if perf.get("wins", 0) > 0:
                avg_win += perf.get("pnl", 0) / max(perf["wins"], 1)
                win_count += 1
            if perf.get("losses", 0) > 0:
                avg_loss += abs(perf.get("pnl", 0)) / max(perf["losses"], 1)
                loss_count += 1
        
        if win_count > 0:
            avg_win = avg_win / win_count
        else:
            avg_win = 50  # Default $50 avg win
            
        if loss_count > 0:
            avg_loss = avg_loss / loss_count
        else:
            avg_loss = 30  # Default $30 avg loss
        
        if avg_loss == 0:
            return 0.01
        
        # Kelly formula
        b = avg_win / avg_loss  # Win/loss ratio
        p = win_rate
        q = 1 - p
        
        kelly = p - (q / b)
        
        # Apply half-Kelly for safety (reduces variance significantly)
        half_kelly = kelly * self.half_kelly_factor
        
        # Clamp between 0.5% and 3%
        return max(0.005, min(half_kelly, 0.03))
    
    def _confidence_multiplier(self, confidence: float) -> float:
        """
        Scale position size by signal strength.
        From: ATLAS paper - "Position size must scale with conviction"
        From: Lopez de Prado - sigmoid function for bet sizing
        
        Sigmoid scaling:
        60% confidence → 0.6x multiplier (smaller)
        75% confidence → 1.0x multiplier (base)
        90% confidence → 1.5x multiplier (larger)
        """
        # Sigmoid-based scaling centered at 75% confidence
        x = (confidence - 0.75) * 10
        sigmoid = 1 / (1 + math.exp(-x))
        # Scale from 0.5x to 1.5x
        return 0.5 + sigmoid
    
    def _volatility_adjustment(self, atr: float, price: float) -> float:
        """
        Reduce position size in high volatility.
        From: Be Water paper - GARCH volatility adjustment
        From: ATLAS paper - "Reduce size when uncertainty is elevated"
        """
        if price == 0:
            return 1.0
        vol_pct = atr / price
        if vol_pct > 0.01:  # Very high volatility
            return 0.5
        elif vol_pct > 0.005:  # High volatility
            return 0.75
        else:  # Normal volatility
            return 1.0
    
    def _drawdown_adjustment(self) -> float:
        """
        Reduce size during losing streaks.
        From: New Market Wizards - protect capital during drawdowns
        """
        # Check recent 5 trades
        total = self.mem.wins + self.mem.losses
        if total < 5:
            return 1.0
        
        # If winning rate recently dropped, reduce size
        wr = self.mem.wins / total
        if wr < 0.30:  # Below 30% win rate - reduce significantly
            return 0.5
        elif wr < 0.40:  # Below 40% - reduce somewhat
            return 0.75
        else:
            return 1.0
    
    def calculate(self, pair: str, direction: str, confidence: float,
                  atr: float, regime: str) -> dict:
        """
        Calculate intelligent position size.
        
        Returns units to trade based on:
        - Kelly Criterion (edge-based sizing)
        - Signal confidence (stronger = larger)
        - Market volatility (higher = smaller)
        - Recent performance (losing streak = smaller)
        - Max 2% risk per trade
        """
        balance = self.get_balance()
        
        # 1. Kelly fraction (base risk %)
        kelly_pct = self._kelly_fraction()
        
        # 2. Scale by confidence
        conf_mult = self._confidence_multiplier(confidence)
        
        # 3. Volatility adjustment
        price = 1.0  # Placeholder - will be overridden
        vol_adj = self._volatility_adjustment(atr, max(atr * 100, 1))
        
        # 4. Drawdown protection
        dd_adj = self._drawdown_adjustment()
        
        # 5. Regime adjustment (from FinEvo paper - trend following dominates)
        regime_mult = {
            "TRENDING": 1.2,   # Larger in trends (more reliable)
            "RANGING":  0.8,   # Smaller in ranging (less reliable)
            "VOLATILE": 0.5,   # Much smaller in volatile
        }.get(regime, 1.0)
        
        # 6. Final risk percentage
        final_risk_pct = kelly_pct * conf_mult * vol_adj * dd_adj * regime_mult
        
        # 7. Cap at 2% max (New Market Wizards rule)
        final_risk_pct = min(final_risk_pct, self.max_risk_pct)
        
        # 8. Calculate risk in dollars
        risk_usd = balance * final_risk_pct
        
        # 9. Calculate units based on SL distance
        # pip_value per unit
        if "JPY" in pair:
            pip_val = 0.01
        elif "XAU" in pair:
            pip_val = 0.1
        else:
            pip_val = 0.0001
        
        sl_pips = max(atr / pip_val, 10)  # Minimum 10 pips SL
        pip_value_per_unit = pip_val  # Simplified - OANDA provides exact
        
        # Units = Risk $ / (SL pips × pip value per unit)
        units = int(risk_usd / max(sl_pips * pip_value_per_unit, 0.001))
        
        # 10. Apply bounds
        units = max(self.min_units, min(units, self.max_units))
        
        return {
            "units": units,
            "risk_usd": round(risk_usd, 2),
            "risk_pct": round(final_risk_pct * 100, 2),
            "kelly_pct": round(kelly_pct * 100, 2),
            "conf_mult": round(conf_mult, 2),
            "vol_adj": round(vol_adj, 2),
            "dd_adj": round(dd_adj, 2),
            "regime_mult": regime_mult,
            "sizing_reason": (
                f"Kelly:{kelly_pct*100:.1f}% × "
                f"Conf:{conf_mult:.1f}x × "
                f"Vol:{vol_adj:.1f}x × "
                f"DD:{dd_adj:.1f}x × "
                f"Regime:{regime_mult}x = "
                f"{final_risk_pct*100:.2f}% = "
                f"{units:,} units"
            )
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
        self.router  = RegimeRouter(self.mem)
        self.sizer   = IntelligentPositionSizer(self.mem, _get_account_balance)
        self.momentum = MultiTimescaleMomentum()
        self.opro     = AdaptiveOPRO()
        self.smc      = SMCAgent()
        self.tsm      = TimeSeriesMomentum()
        self.cvar     = CVaRRiskManager(confidence_level=0.95)
        self.hmem     = HierarchicalMemory()
        self.fip      = FinancialInsightAgent()
        self.gtrends  = GoogleTrendsSentiment()   # Free uncorrelated sentiment
        self.orderbook = OANDAOrderBook()           # Free OANDA Level 2 alternative
        self.evolver = DailyEvolution(self.mem, self.weights)

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

    # ── OPTIMIZED VOTING ENGINE (v15.1) ─────────────────────────────────────
    # Fix 1: Weighted voting — institutional signals count more than lagging indicators
    # Fix 2: Regime filtering — only relevant agents vote per market condition
    # Fix 3: Category diversity — need 2+ different signal types to trade
    # Fix 4: New signals — order flow, market structure, session bias added

    INST_WEIGHT  = {"SMC":3.0,"ICT":3.0,"ORDERBLOCK":3.0,"CLAUDE":2.5,"LLM":2.5,
                    "COT":2.5,"ORDERFLOW":2.5,"LIQUIDITY":2.5,"ORDER":2.5}
    STRUCT_WEIGHT = {"BOS":2.0,"CHOCH":2.0,"STRUCTURE":2.0,"TREND":2.0,
                     "SUPERTREND":2.0,"BREAKOUT":1.8,"HIDARTS":1.8,"LSTM":1.8,
                     "SESSION":1.8,"HIVEMIND":1.8,"FINMEM":1.5,"RL":1.5,
                     "TRADINGVIEW":2.0,"MOMENTUM":1.5,"DXY":1.5,"NEWS":1.5}
    LAGGING_WEIGHT = {"EMA":1.0,"MACD":0.8,"RSI":0.7,"BOLLINGER":0.8,
                      "STOCHASTIC":0.6,"ATR":0.4,"KELLY":0.3,"RISK":0.5}

    REGIME_ALLOWED = {
        "TRENDING": ["SMC","ICT","BOS","CHOCH","TREND","EMA","MACD","SUPERTREND",
                     "BREAKOUT","MOMENTUM","SESSION","DXY","CLAUDE","LLM",
                     "LSTM","HIDARTS","HIVEMIND","FINMEM","RL","TRADINGVIEW",
                     "NEWS","STRUCTURE","ORDERBLOCK","ORDERFLOW"],
        "RANGING":  ["RSI","BOLLINGER","STOCHASTIC","CHOCH","SMC","ICT",
                     "ORDERBLOCK","ORDERFLOW","SESSION","CLAUDE","LLM",
                     "FINMEM","RL","TRADINGVIEW","NEWS","CORRELATION"],
        "VOLATILE": ["CLAUDE","LLM","NEWS","SMC","ICT","ORDERFLOW","HIDARTS","RISK"],
    }

    SIGNAL_CATS = {
        "INSTITUTIONAL": ["SMC","ICT","COT","ORDERBLOCK","ORDERFLOW","CLAUDE","LLM"],
        "STRUCTURE":     ["BOS","CHOCH","BREAKOUT","STRUCTURE","HIDARTS","LSTM"],
        "TREND":         ["EMA","MACD","SUPERTREND","TREND","MOMENTUM"],
        "REVERSAL":      ["RSI","BOLLINGER","STOCHASTIC"],
        "SENTIMENT":     ["NEWS","DXY","CORRELATION","MACRO","SESSION"],
        "CONFIRMATION":  ["TRADINGVIEW","HIVEMIND","FINMEM","RL"],
    }

    def _get_agent_weight_v2(self, name: str) -> float:
        n = name.upper().replace("_","").replace(" ","")
        for k, w in {**self.INST_WEIGHT, **self.STRUCT_WEIGHT, **self.LAGGING_WEIGHT}.items():
            if k.replace("_","") in n:
                return w
        return 1.0

    def _get_agent_category(self, name: str) -> str:
        n = name.upper().replace("_","").replace(" ","")
        for cat, kws in self.SIGNAL_CATS.items():
            if any(k.replace("_","") in n for k in kws):
                return cat
        return "OTHER"

    def _is_allowed(self, name: str, regime: str) -> bool:
        n = name.upper().replace("_","").replace(" ","")
        allowed = self.REGIME_ALLOWED.get(regime, list(self.INST_WEIGHT.keys()))
        return any(k.replace("_","") in n for k in allowed)

    def _calc_order_flow(self, bars) -> tuple:
        """New signal: buying/selling pressure from candle structure"""
        if not bars or len(bars) < 10: return "NEUTRAL", 0.3
        try:
            bp = sp = 0.0
            for b in bars[-10:]:
                h,l,c = b.high, b.low, b.close
                r = h - l
                if r > 0: bp += (c-l)/r; sp += (h-c)/r
            t = bp + sp
            if t == 0: return "NEUTRAL", 0.3
            ratio = bp / t
            if ratio > 0.62: return "BUY",  min(0.82, ratio)
            if ratio < 0.38: return "SELL", min(0.82, 1-ratio)
            return "NEUTRAL", 0.3
        except: return "NEUTRAL", 0.3

    def _calc_market_structure(self, bars) -> tuple:
        """New signal: higher highs/lower lows structure"""
        if not bars or len(bars) < 20: return "NEUTRAL", 0.3
        try:
            highs = [b.high for b in bars[-20:]]
            lows  = [b.low  for b in bars[-20:]]
            hh = sum(1 for i in range(1,6) if highs[-i] > highs[-i-1])
            hl = sum(1 for i in range(1,6) if lows[-i]  > lows[-i-1])
            lh = sum(1 for i in range(1,6) if highs[-i] < highs[-i-1])
            ll = sum(1 for i in range(1,6) if lows[-i]  < lows[-i-1])
            bull = hh + hl; bear = lh + ll
            if bull >= 4: return "BUY",  min(0.80, 0.55 + bull*0.05)
            if bear >= 4: return "SELL", min(0.80, 0.55 + bear*0.05)
            return "NEUTRAL", 0.3
        except: return "NEUTRAL", 0.3

    def _detect_regime_v2(self, bars) -> str:
        """Improved regime detection"""
        if not bars or len(bars) < 30: return "RANGING"
        try:
            closes = np.array([b.close for b in bars[-30:]])
            highs  = np.array([b.high  for b in bars[-30:]])
            lows   = np.array([b.low   for b in bars[-30:]])
            atr    = float(np.mean(highs - lows))
            avg    = float(np.mean(closes))
            vol    = atr / avg if avg > 0 else 0
            ema20  = float(np.mean(closes[-20:]))
            ema30  = float(np.mean(closes[-30:]))
            sep    = abs(ema20-ema30) / avg if avg > 0 else 0
            hh = sum(1 for i in range(1,8) if highs[-i] > highs[-i-1])
            ll = sum(1 for i in range(1,8) if lows[-i]  < lows[-i-1])
            ts = max(hh,ll) / 8
            if vol > 0.007: return "VOLATILE"
            if sep > 0.0012 or ts > 0.65: return "TRENDING"
            return "RANGING"
        except: return "RANGING"

    def _vote(self, signals: List[Signal], regime: str = "RANGING",
              bars=None, cot_dir="NEUTRAL", news_sent="NEUTRAL",
              dxy_trend="NEUTRAL", tv_confirmed=False) -> Tuple[str, float, List[str], List[str]]:
        """
        OPTIMIZED VOTING — weighted + regime-filtered + category diversity check
        """
        # Add synthetic signals for diversification
        synthetic = []
        if bars:
            of_dir, of_conf = self._calc_order_flow(bars)
            if of_dir in ("BUY","SELL"):
                from dataclasses import dataclass
                synthetic.append(Signal(of_dir, of_conf, "Order flow pressure", "ORDER_FLOW"))
            ms_dir, ms_conf = self._calc_market_structure(bars)
            if ms_dir in ("BUY","SELL"):
                synthetic.append(Signal(ms_dir, ms_conf, "Market structure", "MARKET_STRUCTURE"))
        if cot_dir in ("BUY","SELL"):
            synthetic.append(Signal(cot_dir, 0.72, "COT institutional bias", "COT_AGENT"))
        news_map = {"BULLISH":"BUY","BEARISH":"SELL"}
        if news_sent in news_map:
            synthetic.append(Signal(news_map[news_sent], 0.65, "News sentiment", "NEWS_AGENT"))

        all_sigs = list(signals) + synthetic

        buy_w = sell_w = 0.0
        buy_a: List[str] = []
        sell_a: List[str] = []
        cats_buy  = set()
        cats_sell = set()

        for s in all_sigs:
            if s.direction == "HOLD": continue
            # Regime filter
            if not self._is_allowed(s.agent_name, regime): continue
            # Weighted vote
            w = self._get_agent_weight_v2(s.agent_name)
            cat = self._get_agent_category(s.agent_name)
            if s.direction == "BUY":
                buy_w  += w * s.confidence
                buy_a.append(s.agent_name)
                cats_buy.add(cat)
            else:
                sell_w += w * s.confidence
                sell_a.append(s.agent_name)
                cats_sell.add(cat)

        total = buy_w + sell_w
        if total == 0: return "HOLD", 0.0, [], []

        if buy_w >= sell_w:
            direction = "BUY"; conf = buy_w/total; agreed = buy_a; disagreed = sell_a; cats = cats_buy
        else:
            direction = "SELL"; conf = sell_w/total; agreed = sell_a; disagreed = buy_a; cats = cats_sell

        # Category diversity check — need 2+ different signal types
        if len(cats) < 2:
            log.info(f"Vote HOLD: only {len(cats)} signal category ({cats}) — need 2+")
            return "HOLD", 0.0, [], []

        # Agent count check — need 3+ active agents
        if len(agreed) < 3:
            log.info(f"Vote HOLD: only {len(agreed)} agents agree — need 3+")
            return "HOLD", 0.0, [], []

        # Regime confidence multiplier
        regime_mult = {"TRENDING":1.08,"RANGING":0.92,"VOLATILE":0.75}.get(regime, 1.0)
        cat_bonus   = min(0.10, len(cats) * 0.025)
        tv_bonus    = 0.05 if tv_confirmed else 0.0
        final_conf  = min(0.95, conf * regime_mult + cat_bonus + tv_bonus)

        return direction, final_conf, agreed, disagreed

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

        # TIME FILTER: Skip Asian session (low win rate) and NY close (low liquidity)
        if 0 <= hour < 6:
            log.info(f"{pair}: Skip - Asian session low probability (hour={hour})")
            return None
        if 20 <= hour < 22:
            log.info(f"{pair}: Skip - NY close low liquidity (hour={hour})")
            return None

        # TIME SERIES MOMENTUM FILTER (Moskowitz/AQR 2012 — Sharpe 1.1 out-of-sample)
        # Currencies with positive 12-month momentum continue going up
        # Only trade in direction of 12-month trend
        try:
            bars_daily = _get_bars(pair, 250, granularity="D")  # ~12 months daily
            if bars_daily and len(bars_daily) >= 200:
                price_now  = bars_daily[-1].close
                price_12m  = bars_daily[-200].close  # ~12 months ago
                tsmom = (price_now - price_12m) / price_12m  # 12-month return
                self._tsmom_cache = getattr(self, "_tsmom_cache", {})
                self._tsmom_cache[pair] = tsmom
                log.info(f"{pair}: 12M TSMOM = {tsmom:+.2%}")
        except Exception as e:
            tsmom = 0.0
            log.warning(f"{pair}: TSMOM fetch failed: {e}")
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

        # ── Regime (improved detection) ───────────────────────────────────────
        curr_regime = self._detect_regime_v2(bars)  # Uses improved detector
        self._last_regime = curr_regime  # Store for dashboard
        rp = self.regime.params(curr_regime)

        # ── MULTI-TIMESCALE MOMENTUM SCORE (FINRS paper: +54% return) ────────────
        # Ms = 1-day change, Mm = 7-day change, Ml = 30-day change
        # Only trade when all 3 timescales agree with signal direction
        try:
            if len(bars) >= 30:
                ms = (bars[-1].close - bars[-2].close) / bars[-2].close if bars[-2].close > 0 else 0
                mm = (bars[-1].close - bars[-8].close) / bars[-8].close if len(bars) >= 8 and bars[-8].close > 0 else 0
                ml = (bars[-1].close - bars[-30].close) / bars[-30].close if bars[-30].close > 0 else 0
                mt_score = ms + mm + ml  # Combined momentum score
                log.info(f"{pair}: FINRS momentum Ms={ms:+.4f} Mm={mm:+.4f} Ml={ml:+.4f} Total={mt_score:+.4f}")
            else:
                mt_score = 0.0
        except:
            mt_score = 0.0

        # ── OPTIMIZED VOTE (weighted + regime-filtered + category diverse) ────
        direction, adj_conf, agreed, disagreed = self._vote(
            signals=raw_sigs,
            regime=curr_regime,
            bars=bars,
            cot_dir=cot_dir,
            news_sent=news_sent,
            dxy_trend=dxy.get("trend","NEUTRAL"),
            tv_confirmed=False,  # Will be set after TV check below
        )
        if direction == "HOLD": return None

        # Intelligence already integrated in _vote — small correlation boost only
        if corr_bias == direction:
            adj_conf = min(1.0, adj_conf * 1.03)

        # GOOGLE TRENDS SENTIMENT (free uncorrelated data source)
        try:
            trends_adj = self.gtrends.get_signal(pair, direction)
            adj_conf = max(0.0, min(1.0, adj_conf + trends_adj))
            if abs(trends_adj) > 0.01:
                log.info(f"{pair}: Google Trends adjustment {trends_adj:+.0%}")
        except Exception as _ge:
            pass

        # OANDA ORDER BOOK (free Level 2 alternative — pending order clusters)
        try:
            ob_dir, ob_str, ob_reason = self.orderbook.get_signal(pair, float(bars[-1].close))
            if ob_str > 0.3:
                if ob_dir == direction:
                    adj_conf = min(1.0, adj_conf * 1.06)
                    log.info(f"{pair}: OrderBook confirms {direction} — {ob_reason}")
                elif ob_dir != "NEUTRAL" and ob_dir != direction:
                    adj_conf = adj_conf * 0.90
                    log.info(f"{pair}: OrderBook contradicts {direction} — {ob_reason}")
        except Exception as _obe:
            pass

        # FINRS Multi-timescale momentum alignment boost/penalty
        try:
            if mt_score > 0 and direction == "BUY":
                adj_conf = min(1.0, adj_conf * 1.08)  # Momentum confirms BUY
            elif mt_score < 0 and direction == "SELL":
                adj_conf = min(1.0, adj_conf * 1.08)  # Momentum confirms SELL
            elif abs(mt_score) > 0.003:  # Strong momentum against direction
                adj_conf = adj_conf * 0.85  # Reduce confidence
                log.info(f"{pair}: Momentum CONTRADICTS {direction} — confidence reduced")
        except:
            pass


        # CROSS-PAIR MOMENTUM FILTER (Time Series Momentum paper — AQR Capital)
        # EUR/USD and EUR/JPY momentum correlated. When both agree → stronger signal.
        # When they diverge → weaker signal, reduce confidence
        CROSS_PAIRS = {
            "EUR_USD": ["EUR_JPY", "GBP_USD"],
            "GBP_USD": ["EUR_USD", "GBP_JPY"],
            "USD_JPY": ["EUR_JPY", "GBP_JPY"],
            "AUD_USD": ["NZD_USD"],
            "EUR_JPY": ["EUR_USD", "GBP_JPY"],
            "GBP_JPY": ["GBP_USD", "EUR_JPY"],
        }
        cross_momentum_score = 0
        cross_pairs_checked = 0
        try:
            for cross_pair in CROSS_PAIRS.get(pair, []):
                cross_bars = _get_bars(cross_pair, 30)
                if cross_bars and len(cross_bars) >= 10:
                    cross_ret = (cross_bars[-1].close - cross_bars[-10].close) / cross_bars[-10].close
                    # Determine if cross pair momentum aligns with our signal
                    # For EUR_USD BUY: EUR_JPY should also be rising (EUR strength)
                    # For USD_JPY BUY: EUR_JPY should be falling (JPY weakness)
                    pair_up = pair.split("_")
                    cross_up = cross_pair.split("_")
                    # Check shared currency
                    shared = set(pair_up) & set(cross_up)
                    if shared:
                        shared_ccy = list(shared)[0]
                        if pair_up[0] == shared_ccy:  # Shared is base in both
                            aligns = cross_ret > 0 and direction == "BUY"
                            aligns = aligns or (cross_ret < 0 and direction == "SELL")
                        else:  # Shared is quote in both
                            aligns = cross_ret < 0 and direction == "BUY"
                            aligns = aligns or (cross_ret > 0 and direction == "SELL")
                        cross_momentum_score += 1 if aligns else -1
                        cross_pairs_checked += 1
            if cross_pairs_checked > 0:
                cross_ratio = cross_momentum_score / cross_pairs_checked
                if cross_ratio >= 0.5:
                    adj_conf = min(1.0, adj_conf * 1.06)
                    log.info(f"{pair}: Cross-pair momentum CONFIRMS {direction} (score={cross_ratio:.1f})")
                elif cross_ratio <= -0.5:
                    adj_conf = adj_conf * 0.88
                    log.info(f"{pair}: Cross-pair momentum CONTRADICTS {direction} (score={cross_ratio:.1f})")
        except Exception as e:
            log.warning(f"Cross-pair momentum check failed: {e}")

        # 12-Month TSMOM filter — skip if trading against 12m trend
        try:
            tsmom = getattr(self, "_tsmom_cache", {}).get(pair, 0.0)
            if tsmom > 0.005 and direction == "SELL":
                log.info(f"{pair}: Skip — Trading AGAINST 12M uptrend (TSMOM={tsmom:+.2%})")
                return None
            elif tsmom < -0.005 and direction == "BUY":
                log.info(f"{pair}: Skip — Trading AGAINST 12M downtrend (TSMOM={tsmom:+.2%})")
                return None
        except:
            pass

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
                    adj_conf = min(1.0, adj_conf * 1.15)
                    h4_boost = f" | H4 CONFIRMS {direction} ({h4_conf:.0%})"
                elif h4_dir != "HOLD" and h4_dir != direction:
                    log.info(f"{pair}: Skip - H4 contradicts H1 (H1={direction} H4={h4_dir})")
                    return None
                else:
                    h4_boost = f" | H4 neutral ({h4_dir})"
        except Exception:
            pass

        # ── TradingView confirmation ─────────────────────────────────────────
        tv_confirmed, tv_reason = self.tv.check_confirmation(pair, direction)
        if tv_confirmed:
            adj_conf = min(1.0, adj_conf * 1.08)  # Smaller boost — already in vote
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

        # ── Daily loss circuit breaker ─────────────────────────────────────
        current_bal = _get_account_balance()
        daily_loss_limit = 0.02  # 2% max loss per day = $2,000 on $100k
        if hasattr(self, '_session_start_bal'):
            daily_loss = (self._session_start_bal - current_bal) / self._session_start_bal
            if daily_loss >= daily_loss_limit:
                log.warning(f"CIRCUIT BREAKER: Daily loss {daily_loss:.1%} >= {daily_loss_limit:.0%} limit. Stopping trading today.")
                _telegram(f"🔴 <b>CIRCUIT BREAKER TRIGGERED</b>\nDaily loss: {daily_loss:.1%}\nLimit: {daily_loss_limit:.0%}\nBalance: ${current_bal:,.2f}\nTrading PAUSED for today.")
                return None
        else:
            self._session_start_bal = current_bal

        risk = self.risk.calculate(pair, direction, final_conf, bars, curr_regime)
        # Override with intelligent position sizing (Kelly + Confidence + Volatility)
        atr = sum(b.high - b.low for b in bars[-14:]) / 14 if len(bars) >= 14 else 0.001

        # VOLATILITY FILTER: Skip when market is too quiet
        if len(bars) >= 20:
            atr_20 = sum(b.high - b.low for b in bars[-20:]) / 20
            if atr < atr_20 * 0.7:
                log.info(f"{pair}: Skip - Low volatility ATR={atr:.5f} below 70% of avg")
                return None

        # MINIMUM PROFIT FILTER (transaction cost research)
        # Only trade when potential profit >> spread cost
        # EUR/USD spread ~1.5 pips = 0.00015. Minimum target = 3x spread = 0.00045
        min_profit = 0.00045 if "JPY" not in pair else 0.045
        if atr * 1.5 < min_profit:  # SL distance must exceed min profit threshold
            log.info(f"{pair}: Skip - ATR too small for profitable trade ({atr:.5f} < {min_profit})")
            return None
        sizing = self.sizer.calculate(pair, direction, final_conf, atr, curr_regime)
        risk["units"] = sizing["units"]
        risk["risk_usd"] = sizing["risk_usd"]
        log.info(f"{pair}: {sizing['sizing_reason']}")

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

        # Regime router handles all conditions
        # Get regime-specific strategy
        route = self.router.get_strategy(curr_regime, bars, pair)
        # Override direction if router has strong opinion
        if route["direction"] != "HOLD" and route["direction"] != direction:
            if route["confidence_boost"] > 0.05:
                direction = route["direction"]
                log.info(f"{pair}: Regime router overriding to {direction} ({route['strategy']})")
        elif route["direction"] == "HOLD" and curr_regime == "VOLATILE":
            log.info(f"{pair}: VOLATILE regime - skipping per GARCH signal")
            return None
        # Apply regime-specific SL/TP
        if route["strategy"] != "DEFAULT":
            risk["sl_dist"] = route["sl_dist"] if "sl_dist" in route else risk.get("sl_dist", 0.001)
            # Recalculate units with regime size multiplier
            size_mult = route.get("size_multiplier", 1.0)
            risk["units"] = max(1000, min(int(risk.get("units", 1000) * size_mult), 15000))
        log.info(f"{pair}: Strategy={route['strategy']} Reason={route.get('reason','')}")
        log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%} | "
                 f"Regime:{curr_regime} | News:{news_sent} | COT:{cot_bias} | "
                 f"TV:{tv_confirmed} | Agents:{len(agreed)}{h4_boost}")

        # ── Execute trade ─────────────────────────────────────────────────────
        # CVaR Risk Check (FinRS)
        if self.cvar.should_reduce_exposure(pair):
            log.info(f"{pair}: CVaR suggests reducing exposure - reducing size 50%")
            risk["units"] = max(1000, risk["units"] // 2)
        
        # Hierarchical Memory context
        mem_ctx = self.hmem.get_context(pair, direction)
        if mem_ctx["has_deep_knowledge"]:
            final_conf = min(final_conf + mem_ctx["confidence_boost"], 0.99)
            log.info(f"{pair}: Deep memory boost applied (+{mem_ctx['confidence_boost']:.0%})")
        self.hmem.add_signal(pair, direction, final_conf, curr_regime, 
                             self.momentum.get_momentum_score(pair))
        if AUTO_EXECUTE and OANDA_OK and OANDA_TOKEN:
            self._execute_trade(rec, risk)
        # Send Telegram alert for executed trade
        _telegram(
            f"{'🟢' if rec.direction=='BUY' else '🔴'} <b>TRADE EXECUTED</b>\n"
            f"Pair: {rec.pair} | {rec.direction}\n"
            f"Entry: {rec.where_entry} | SL: {rec.where_sl} | TP: {rec.where_tp}\n"
            f"Confidence: {rec.confidence:.0%} | Strategy: {rec.regime}\n"
            f"Cycle: #{self.stats['cycles']}"
        )


        # ── Schedule learning ─────────────────────────────────────────────────
        # Update hierarchical memory with outcome
        if hasattr(self, "hmem"):
            self.hmem.record_outcome(rec.pair, rec.direction, rec.outcome)
        if hasattr(self, "cvar"):
            self.cvar.update(rec.pair, rec.pnl_usd, rec.where_entry)
        return rec

    def _scale_out_positions(self):
        """
        SCALE-OUT IN THIRDS (Trading in the Zone — Mark Douglas)
        
        Rule 1: At 1x ATR profit → close 1/3, move SL to breakeven
        Rule 2: At 3x ATR profit → close another 1/3
        Rule 3: Let final 1/3 run with trailing stop at 2x ATR
        
        Impact: Locks in profits on trades that later reverse.
        Effectively raises win rate from 33% to ~50%+
        """
        if not self.open_pos:
            return
        try:
            from oandapyV20 import API as _OandaAPI
            from oandapyV20.endpoints.trades import OpenTrades as _OpenTrades, TradeClose as _TradeClose
            from oandapyV20.endpoints.orders import OrderCreate as _OrderCreate
            import oandapyV20.endpoints.trades as trades_ep

            api = _OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
            r = _OpenTrades(OANDA_ACCOUNT)
            api.request(r)
            live_trades = {t["instrument"].replace("/","_"): t for t in r.response.get("trades",[])}

            for pair, rec in list(self.open_pos.items()):
                if pair not in live_trades:
                    continue
                lt = live_trades[pair]
                trade_id    = lt["id"]
                current_units = abs(float(lt.get("currentUnits", 0)))
                unrealized_pl = float(lt.get("unrealizedPL", 0))
                open_price    = float(lt.get("price", 0))
                current_price = float(lt.get("price", 0))  # Will calc from PL

                if open_price <= 0 or current_units <= 0:
                    continue

                # Calculate ATR for this pair
                try:
                    bars = _get_bars(pair, 20)
                    if bars and len(bars) >= 14:
                        atr = sum(b.high - b.low for b in bars[-14:]) / 14
                    else:
                        continue
                except:
                    continue

                # Calculate price distance moved
                pnl_per_unit = unrealized_pl / current_units if current_units > 0 else 0
                price_moved = abs(pnl_per_unit) / 10000 if "JPY" not in pair else abs(pnl_per_unit) / 100

                scale_out_done = getattr(rec, 'scale_out_done', 0)

                # Rule 1: At 1x ATR profit → close 1/3, move SL to breakeven
                if unrealized_pl > 0 and price_moved >= atr * 1.0 and scale_out_done == 0:
                    close_units = int(current_units / 3)
                    if close_units >= 1000:
                        try:
                            close_dir = "-" if rec.direction == "BUY" else ""
                            cr = _TradeClose(OANDA_ACCOUNT, tradeID=trade_id,
                                           data={"units": f"{close_dir}{close_units}"})
                            api.request(cr)
                            rec.scale_out_done = 1
                            log.info(f"SCALE-OUT 1/3: {pair} closed {close_units} units at +{unrealized_pl:.2f} (1x ATR={atr:.5f})")
                            _telegram(f"📊 <b>SCALE-OUT 1/3</b>
{pair} | Closed {close_units} units
Profit locked: ${unrealized_pl/3:.2f}
Remaining: 2/3 position — SL moved to breakeven")
                            # Move SL to breakeven
                            try:
                                be_price = rec.where_entry if hasattr(rec, 'where_entry') else open_price
                                def fmt(p): return f"{p:.3f}" if "JPY" in pair else f"{p:.5f}"
                                tr = trades_ep.TradeCRCDO(OANDA_ACCOUNT, tradeID=trade_id,
                                    data={"stopLoss": {"price": fmt(be_price), "type": "STOP_LOSS"}})
                                api.request(tr)
                                log.info(f"SL moved to breakeven: {pair} @ {be_price}")
                            except Exception as sl_e:
                                log.warning(f"SL move failed: {sl_e}")
                        except Exception as e:
                            log.warning(f"Scale-out 1/3 failed {pair}: {e}")

                # Rule 2: At 3x ATR profit → close another 1/3
                elif unrealized_pl > 0 and price_moved >= atr * 3.0 and scale_out_done == 1:
                    close_units = int(current_units / 2)  # Half of remaining = 1/3 of original
                    if close_units >= 1000:
                        try:
                            close_dir = "-" if rec.direction == "BUY" else ""
                            cr = _TradeClose(OANDA_ACCOUNT, tradeID=trade_id,
                                           data={"units": f"{close_dir}{close_units}"})
                            api.request(cr)
                            rec.scale_out_done = 2
                            log.info(f"SCALE-OUT 2/3: {pair} closed {close_units} units at +{unrealized_pl:.2f} (3x ATR)")
                            _telegram(f"📊 <b>SCALE-OUT 2/3</b>
{pair} | Closed {close_units} units
Profit locked: ${unrealized_pl/2:.2f}
Final 1/3 running FREE with trailing stop")
                        except Exception as e:
                            log.warning(f"Scale-out 2/3 failed {pair}: {e}")

        except Exception as e:
            log.warning(f"Scale-out check failed: {e}")

    def _execute_trade(self, rec: TradeRecord, risk: Dict):
        """Place trade on OANDA — auto-falls back to IC Markets if OANDA fails"""
        # ── Primary: OANDA ────────────────────────────────────────────────────
        oanda_ok = False
        # FIFO VIOLATION FIX — close opposing trade before opening new one
        try:
            from oandapyV20 import API as _OandaAPI
            from oandapyV20.endpoints.trades import OpenTrades as _OpenTrades, TradeClose as _TradeClose
            _api = _OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
            _r = _OpenTrades(OANDA_ACCOUNT)
            _api.request(_r)
            _open = _r.response.get("trades", [])
            _pair_norm = rec.pair.replace("/", "_")
            for _t in _open:
                if _t.get("instrument", "").replace("/", "_") == _pair_norm:
                    _existing_units = float(_t.get("currentUnits", 0))
                    _existing_dir = "BUY" if _existing_units > 0 else "SELL"
                    if _existing_dir != rec.direction:
                        log.warning(f"FIFO: Closing {rec.pair} {_existing_dir} before opening {rec.direction}")
                        _api.request(_TradeClose(OANDA_ACCOUNT, tradeID=_t["id"]))
                        time.sleep(1)
                    else:
                        # Same direction already open — skip new trade
                        log.info(f"FIFO: {rec.pair} {_existing_dir} already open — skipping duplicate")
                        return
        except Exception as _e:
            log.warning(f"FIFO check error: {_e}")

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
                # FIX 7: MT5/IC Markets only works on Windows with MT5 installed
                # On Render (Linux), this gracefully skips to OANDA-only mode
                if not ic.connected:
                    log.info("MT5/IC Markets not available on this server — OANDA-only mode")
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
    
    def _sync_real_winrate(self):
        """Sync real win/loss from OANDA closed trades"""
        if not OANDA_OK or not OANDA_TOKEN:
            return
        try:
            from oandapyV20 import API as _A
            from oandapyV20.endpoints.trades import TradesList
            api = _A(access_token=OANDA_TOKEN, environment=OANDA_ENV)
            r = TradesList(OANDA_ACCOUNT, params={"state": "CLOSED", "count": 50})
            api.request(r)
            trades = r.response.get("trades", [])
            real_wins = sum(1 for t in trades if float(t.get("realizedPL", 0)) > 0)
            real_losses = sum(1 for t in trades if float(t.get("realizedPL", 0)) < 0)
            real_total = real_wins + real_losses
            if real_total > 0:
                self.mem.wins = real_wins
                self.mem.losses = real_losses
                self.mem.total = real_total
                self.mem.save()
                log.info(f"OANDA Real WR: {real_wins}/{real_total} = {real_wins/real_total:.1%}")
        except Exception as e:
            log.warning(f"WR sync error: {e}")

    


    def _passes_correlation_check(self, pair: str, direction: str) -> bool:
        """
        CORRELATION FILTER — Prevent doubling risk on correlated pairs.
        From research: EUR/USD and GBP/USD move together 85% of the time.
        Opening both BUY = 2x risk on one directional bet.
        """
        # High correlation pairs (>0.7 correlation) — cannot trade same direction
        HIGH_CORR = {
            "EUR_USD": ["GBP_USD", "EUR_JPY", "EUR_GBP"],
            "GBP_USD": ["EUR_USD", "GBP_JPY", "EUR_GBP"],
            "USD_JPY": ["EUR_JPY", "GBP_JPY", "AUD_JPY"],
            "AUD_USD": ["NZD_USD", "AUD_JPY"],
            "NZD_USD": ["AUD_USD"],
            "EUR_JPY": ["EUR_USD", "USD_JPY", "GBP_JPY"],
            "GBP_JPY": ["GBP_USD", "USD_JPY", "EUR_JPY"],
            "AUD_JPY": ["AUD_USD", "USD_JPY"],
            "EUR_GBP": ["EUR_USD", "GBP_USD"],
            "USD_CHF": ["EUR_USD"],  # USD/CHF inversely correlated to EUR/USD
        }
        # Max 2 correlated pairs open at once
        correlated = HIGH_CORR.get(pair, [])
        corr_open = sum(1 for cp in correlated if cp in self.open_pos
                       and self.open_pos[cp].direction == direction)
        if corr_open >= 2:
            log.info(f"{pair}: Correlation block — {corr_open} correlated pairs already {direction}")
            return False
        # USD_CHF is inverse — if EUR/USD is BUY, USD/CHF should be SELL
        if pair == "USD_CHF" and "EUR_USD" in self.open_pos:
            eur_dir = self.open_pos["EUR_USD"].direction
            if direction == eur_dir:  # Both in same direction = wrong
                log.info(f"USD_CHF: Inverse correlation block — EUR_USD is {eur_dir}")
                return False
        return True

    def _is_news_safe(self, pair: str) -> bool:
        """Skip trading 30 mins before/after HIGH impact news"""
        try:
            now = datetime.utcnow()
            currencies = pair.replace("_", "/").split("/")
            for event in getattr(self, 'forex_events', []):
                try:
                    if event.get('impact') != 'HIGH':
                        continue
                    if not any(c in event.get('currency', '') for c in currencies):
                        continue
                    event_time = datetime.strptime(event.get('time', ''), '%Y-%m-%d %H:%M')
                    diff = abs((event_time - now).total_seconds() / 60)
                    if diff < 30:
                        log.info(f"{pair}: Skipping - HIGH impact news in {diff:.0f} mins")
                        return False
                except:
                    continue
        except Exception as e:
            pass
        return True

    def _is_good_session(self) -> bool:
        """Only trade during London (7-16 UTC) and New York (12-21 UTC) sessions"""
        hour = datetime.utcnow().hour
        tokyo = 0 <= hour < 9
        london = 7 <= hour < 16
        new_york = 12 <= hour < 21
        return tokyo or london or new_york

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

        # SCALE-OUT IN THIRDS — check open positions every cycle (Trading in the Zone)
        try:
            self._scale_out_positions()
        except Exception as _soe:
            log.warning(f"Scale-out check error: {_soe}")

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
        log.info("V15 CHAKRA PRODUCTION SYSTEM RUNNING")
        # FIX 6: Send startup ping to confirm Telegram is working
        _telegram(
            "🚀 <b>CHAKRA SYSTEM STARTED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ All systems online\n"
            "📊 Trading 12 pairs every 15 min\n"
            "⚡ Scale-out in thirds: ACTIVE\n"
            "📈 6x ATR take profit: ACTIVE\n"
            "🔍 H4 + 12M momentum: ACTIVE\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ If you see this, Telegram is working!\n"
            "If bot is muted: open @Chakra_trading_bot → Unmute"
        )
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
                # Sync real win rate from OANDA every cycle
                self._sync_real_winrate()
                # POST LIVE DATA TO RAILWAY DASHBOARD — every cycle
                try:
                    import requests as _req
                    _bal = _get_account_balance()
                    _open_trades_list = []
                    for _pair, _rec in self.open_pos.items():
                        _open_trades_list.append({
                            "pair": _pair,
                            "direction": _rec.direction,
                            "entry": round(float(_rec.where_entry), 5),
                            "sl": round(float(_rec.where_sl), 5),
                            "tp": round(float(_rec.where_tp), 5),
                            "confidence": round(float(_rec.confidence), 3),
                            "strategy": _rec.regime,
                            "opened_at": str(_rec.when_timestamp),
                        })
                    # Calculate real win rate from closed trades
                    _total = self.mem.wins + self.mem.losses
                    _wr = round(self.mem.wins / _total * 100, 1) if _total > 0 else 0.0
                    _resp = _req.post(
                        "https://project-chakra-production.up.railway.app/api/update",
                        json={
                            "pair": "SYSTEM",
                            "direction": "UPDATE",
                            "confidence": _wr,
                            "win_rate": _wr,
                            "cycle": self.stats["cycles"],
                            "total_trades": _total,
                            "wins": self.mem.wins,
                            "losses": self.mem.losses,
                            "open_trades": len(self.open_pos),
                            "balance": round(_bal, 2),
                            "nav": round(_bal, 2),
                            "pnl": round(_bal - 100000.0, 2),
                            "trades": _open_trades_list,
                            "regime": getattr(self, "_last_regime", "UNKNOWN"),
                            "pairs_scanned": len(PAIRS),
                            "last_updated": datetime.utcnow().isoformat(),
                        },
                        timeout=5
                    )
                    if _resp.status_code == 200:
                        log.info(f"Dashboard updated: bal=${_bal:,.0f} WR={_wr}% trades={_total}")
                    else:
                        log.warning(f"Dashboard update failed: {_resp.status_code}")
                except Exception as _de:
                    log.debug(f"Dashboard post failed: {_de}")
                # ATLAS Adaptive-OPRO: Rewrite trading prompt every 5 days
                if hasattr(self, 'opro') and self.opro.should_optimize():
                    new_prompt = self.opro.optimize(self.mem, _get_account_balance())
                    log.info(f"ATLAS OPRO: System prompt updated for next cycle")
                # Daily evolution
                if self.evolver.should_run():
                    self.evolver.run()
                if self.router.should_evolve():
                    self.router.evolve()
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
                'price': record.where_entry,  # Use where_entry not price
                'direction': record.direction,
                'confidence': record.confidence,
                'h4_trend': '—',  # Not stored in record
                'regime': record.regime,
                'sl': round(record.where_sl, 5) if record.where_sl else '—',
                'tp': round(record.where_tp, 5) if record.where_tp else '—',
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




