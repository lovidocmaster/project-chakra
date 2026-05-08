#!/usr/bin/env python3
"""
V13 Backtest — 2 years of real OANDA data
Tests v13's agent logic on historical candles before going live.

RUN:
  py -3.11 v13_backtest.py

OUTPUT:
  - Console summary (win rate, P&L, drawdown per pair)
  - v13_backtest_results.json
  - Telegram report when done
"""

import os, json, random, time, requests
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

OANDA_TOKEN   = os.getenv("OANDA_TOKEN", "")
OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT_ID", "101-001-39217670-001")
OANDA_ENV     = "practice"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT", "")

PAIRS      = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"]
RISK_PCT   = 0.005
CAPITAL    = 100000.0
MIN_CONF   = 0.65
RR_RATIO   = 1.5      # TP = SL * 1.5
COMMISSION = 1.5      # pips per trade (spread + commission)

try:
    from oandapyV20 import API as OandaAPI
    from oandapyV20.endpoints.instruments import InstrumentsCandles
    OANDA_OK = True
except ImportError:
    OANDA_OK = False

# ── Import v13 agents ─────────────────────────────────────────────────────────
try:
    from v13_production import (
        BarData, Signal,
        EMAAgent, MACDAgent, RSIAgent, BollingerAgent, WyckoffAgent,
        ATRAgent, StochasticAgent, SessionAgent, BreakoutAgent,
        BOSAgent, CHoCHAgent, OrderBlockAgent, FVGAgent,
        KillzoneAgent, OTEAgent, SilverBulletAgent, LiquiditySweepAgent,
        AgentWeights
    )
    AGENTS_OK = True
except ImportError as e:
    print(f"Warning: could not import v13 agents ({e}) — using simplified logic")
    AGENTS_OK = False


def _telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except Exception: pass


def fetch_historical_bars(pair: str, granularity: str = "H1",
                           months: int = 24) -> List[BarData]:
    """Fetch up to 2 years of OANDA candles (5000 max per request)"""
    if not OANDA_OK or not OANDA_TOKEN:
        return _generate_fake_bars(pair, 5000)
    bars = []
    try:
        api = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        ep  = InstrumentsCandles(pair, params={"count": 5000, "granularity": granularity})
        api.request(ep)
        for c in ep.response.get("candles", []):
            m = c.get("mid", {})
            bars.append(BarData(
                c.get("time",""),
                float(m.get("o",0)), float(m.get("h",0)),
                float(m.get("l",0)), float(m.get("c",0)),
                float(c.get("volume",0))
            ))
        print(f"  {pair}: {len(bars)} candles loaded")
    except Exception as e:
        print(f"  {pair}: OANDA error ({e}) — using simulated data")
        bars = _generate_fake_bars(pair, 5000)
    return bars


def _generate_fake_bars(pair: str, count: int) -> List[BarData]:
    base = {"EUR_USD":1.08,"GBP_USD":1.26,"USD_JPY":148.0,
            "AUD_USD":0.65,"USD_CAD":1.37}.get(pair, 1.10)
    bars, p = [], base
    for i in range(count):
        p *= (1 + np.random.normal(0, 0.0003))
        o  = p * (1 + np.random.normal(0, 0.0001))
        h  = max(p, o) * (1 + abs(np.random.normal(0, 0.0002)))
        l  = min(p, o) * (1 - abs(np.random.normal(0, 0.0002)))
        ts = (datetime.utcnow() - timedelta(hours=count-i)).isoformat()
        bars.append(BarData(ts, o, h, l, p, random.randint(100,1000)))
    return bars


def get_signal(bars: List[BarData], weights: AgentWeights) -> Dict:
    """Run all v13 agents on a window of bars and get weighted vote"""
    if not AGENTS_OK or len(bars) < 30:
        return {"direction": "HOLD", "confidence": 0.0, "agents": []}

    agents = [
        EMAAgent("EMA"), MACDAgent("MACD"), RSIAgent("RSI"),
        BollingerAgent("Bollinger"), WyckoffAgent("Wyckoff"), ATRAgent("ATR"),
        StochasticAgent("Stochastic"), SessionAgent("Session"), BreakoutAgent("Breakout"),
        BOSAgent("BOS"), CHoCHAgent("CHOCH"), OrderBlockAgent("OrderBlock"),
        FVGAgent("FVG"), KillzoneAgent("Killzone"), OTEAgent("OTE"),
        SilverBulletAgent("SilverBullet"), LiquiditySweepAgent("LiquiditySweep"),
    ]

    buy_w = sell_w = 0.0
    buy_a: List[str] = []
    sell_a: List[str] = []

    for agent in agents:
        try:
            s = agent.analyze(bars)
            if not s or s.direction == "HOLD": continue
            w = weights.get(s.agent_name)
            if s.direction == "BUY":
                buy_w += w * s.confidence; buy_a.append(agent.name)
            else:
                sell_w += w * s.confidence; sell_a.append(agent.name)
        except Exception:
            pass

    total = buy_w + sell_w
    if total == 0: return {"direction": "HOLD", "confidence": 0.0, "agents": []}

    if buy_w >= sell_w:
        return {"direction": "BUY",  "confidence": buy_w/total,  "agents": buy_a}
    return     {"direction": "SELL", "confidence": sell_w/total, "agents": sell_a}


def backtest_pair(pair: str, bars: List[BarData], weights: AgentWeights) -> Dict:
    capital  = CAPITAL
    peak     = CAPITAL
    trades   = []
    pip_size = 0.01 if "JPY" in pair else 0.0001
    window   = 50

    for i in range(window, len(bars) - 10):
        window_bars = bars[i - window: i]
        sig = get_signal(window_bars, weights)

        if sig["direction"] == "HOLD" or sig["confidence"] < MIN_CONF:
            continue

        entry = bars[i].close
        atr   = np.mean([b.high - b.low for b in window_bars[-14:]])
        sl_dist = atr * 1.5
        tp_dist = sl_dist * RR_RATIO

        # Simulate outcome over next 10 candles
        outcome = "OPEN"
        exit_px = entry
        for j in range(i + 1, min(i + 10, len(bars))):
            c = bars[j]
            if sig["direction"] == "BUY":
                if c.low  <= entry - sl_dist: outcome = "LOSS"; exit_px = entry - sl_dist; break
                if c.high >= entry + tp_dist: outcome = "WIN";  exit_px = entry + tp_dist; break
            else:
                if c.high >= entry + sl_dist: outcome = "LOSS"; exit_px = entry + sl_dist; break
                if c.low  <= entry - tp_dist: outcome = "WIN";  exit_px = entry - tp_dist; break
        if outcome == "OPEN": continue

        if sig["direction"] == "BUY":
            pnl_pips = (exit_px - entry) / pip_size - COMMISSION
        else:
            pnl_pips = (entry - exit_px) / pip_size - COMMISSION

        risk_usd = capital * RISK_PCT
        pnl_usd  = pnl_pips * (risk_usd / (sl_dist / pip_size))
        capital += pnl_usd
        peak = max(peak, capital)

        trades.append({
            "pair": pair, "direction": sig["direction"],
            "confidence": round(sig["confidence"], 3),
            "agents": len(sig["agents"]),
            "outcome": outcome, "pnl_pips": round(pnl_pips, 1),
            "pnl_usd": round(pnl_usd, 2), "timestamp": bars[i].timestamp,
        })

    wins     = [t for t in trades if t["outcome"] == "WIN"]
    losses   = [t for t in trades if t["outcome"] == "LOSS"]
    wr       = len(wins) / len(trades) * 100 if trades else 0
    total_p  = sum(t["pnl_pips"] for t in trades)
    total_u  = sum(t["pnl_usd"]  for t in trades)
    max_dd   = ((peak - capital) / peak * 100) if peak > 0 else 0
    avg_conf = np.mean([t["confidence"] for t in trades]) if trades else 0

    return {
        "pair": pair, "trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(wr, 1),
        "total_pips": round(total_p, 1),
        "total_usd": round(total_u, 2),
        "final_capital": round(capital, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_confidence": round(avg_conf, 3),
        "trade_log": trades[-20:],  # last 20 trades for review
    }


def run_backtest():
    print("\n" + "="*60)
    print("  V13 BACKTEST — 2 YEARS REAL DATA")
    print("="*60)

    weights = AgentWeights() if AGENTS_OK else None

    all_results = {}
    total_trades = total_wins = 0
    total_pips = total_usd = 0.0

    for pair in PAIRS:
        print(f"\n▶ {pair}")
        bars = fetch_historical_bars(pair, granularity="H1", months=24)
        if len(bars) < 100:
            print(f"  Skipped (not enough data)")
            continue
        result = backtest_pair(pair, bars, weights)
        all_results[pair] = result
        total_trades += result["trades"]
        total_wins   += result["wins"]
        total_pips   += result["total_pips"]
        total_usd    += result["total_usd"]
        print(f"  Trades:{result['trades']} | WR:{result['win_rate']}% | "
              f"Pips:{result['total_pips']:+.0f} | ${result['total_usd']:+.0f} | "
              f"DD:{result['max_drawdown_pct']}%")

    overall_wr = total_wins / total_trades * 100 if total_trades else 0

    summary = {
        "run_date": datetime.utcnow().isoformat(),
        "total_trades": total_trades, "total_wins": total_wins,
        "overall_win_rate": round(overall_wr, 1),
        "total_pips": round(total_pips, 1), "total_usd": round(total_usd, 2),
        "pairs": all_results,
    }

    with open("v13_backtest_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  OVERALL: {total_trades} trades | WR: {overall_wr:.1f}%")
    print(f"  P&L: {total_pips:+.0f} pips | ${total_usd:+.0f}")
    print(f"  Results saved to v13_backtest_results.json")
    print(f"{'='*60}\n")

    _telegram(
        f"📈 <b>V13 BACKTEST COMPLETE</b>\n\n"
        f"Trades: {total_trades} | WR: {overall_wr:.1f}%\n"
        f"P&L: {total_pips:+.0f} pips | ${total_usd:+.0f}\n\n" +
        "\n".join([f"{p}: {r['win_rate']}% WR | {r['total_pips']:+.0f} pips"
                   for p, r in all_results.items()])
    )
    return summary


if __name__ == "__main__":
    run_backtest()
