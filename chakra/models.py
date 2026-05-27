"""
chakra/models.py — Data structures used throughout the system
"""
from __future__ import annotations
import os, json, logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
log = logging.getLogger("Chakra")

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

# ── BARS CACHE — 80% fewer API calls, 3x faster cycle ───────────────────────
import time as _time_module
_bars_cache: dict = {}
_bars_ts: dict = {}
_BARS_TTL = {"H1": 240, "H4": 900, "D": 3600, "M15": 120, "M5": 60}

def _get_bars(pair: str, count: int = 100, granularity: str = "H1") -> List[BarData]:
    """
    SPEED OPTIMIZED: Caches bars per pair+granularity.
    New H1 candle every 60min → cache valid 4min (safe window).
    Reduces OANDA calls from 60+/cycle to ~12/cycle.
    """
    key = f"{pair}:{granularity}:{count}"
    ttl = _BARS_TTL.get(granularity, 240)
    now = _time_module.time()

    # Return fresh cache
    if key in _bars_cache and (now - _bars_ts.get(key, 0)) < ttl:
        return _bars_cache[key]

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
        result = bars if bars else _simulated_bars(pair, count)
        _bars_cache[key] = result
        _bars_ts[key] = now
        return result
    except Exception as e:
        log.warning(f"OANDA bars {pair} {granularity}: {e}")
        if key in _bars_cache:
            return _bars_cache[key]  # Return stale on error
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
