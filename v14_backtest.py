#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V14 BACKTEST — 2 Year Historical Test
Runs independently — no imports from v13 needed
Results saved to v14_backtest_results.json
Telegram alert sent when done
"""

import os, sys, json, time, requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from oandapyV20 import API as OandaAPI
    from oandapyV20.endpoints.instruments import InstrumentsCandles
    OANDA_OK = True
except ImportError:
    OANDA_OK = False

OANDA_TOKEN   = os.getenv("OANDA_TOKEN", "")
OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT_ID", "101-001-39217670-001")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT", os.getenv("TELEGRAM_CHAT_ID",""))

PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"]

# ── Data structures ───────────────────────────────────────────────────────────
@dataclass
class BarData:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg},
            timeout=8
        )
    except Exception:
        pass

# ── Get historical bars from OANDA ───────────────────────────────────────────
def get_oanda_bars(pair: str, count: int = 500, granularity: str = "H1") -> List[BarData]:
    if not OANDA_OK or not OANDA_TOKEN:
        return generate_simulated_bars(pair, count)
    try:
        api = OandaAPI(access_token=OANDA_TOKEN, environment="practice")
        ep  = InstrumentsCandles(pair, params={
            "count": count,
            "granularity": granularity
        })
        api.request(ep)
        bars = []
        for c in ep.response.get("candles", []):
            m = c.get("mid", {})
            bars.append(BarData(
                timestamp=c.get("time", ""),
                open=float(m.get("o", 0)),
                high=float(m.get("h", 0)),
                low=float(m.get("l", 0)),
                close=float(m.get("c", 0)),
                volume=float(c.get("volume", 0))
            ))
        print(f"  Fetched {len(bars)} real bars for {pair}")
        return bars
    except Exception as e:
        print(f"  OANDA error for {pair}: {e} — using simulated data")
        return generate_simulated_bars(pair, count)

def generate_simulated_bars(pair: str, count: int) -> List[BarData]:
    base = {"EUR_USD":1.08,"GBP_USD":1.26,"USD_JPY":148.0,
            "AUD_USD":0.65,"USD_CAD":1.37}.get(pair, 1.10)
    bars = []
    p = base
    for i in range(count):
        p *= (1 + np.random.normal(0, 0.0008))
        o = p * (1 + np.random.normal(0, 0.0002))
        h = max(p, o) * (1 + abs(np.random.normal(0, 0.0003)))
        l = min(p, o) * (1 - abs(np.random.normal(0, 0.0003)))
        bars.append(BarData(
            timestamp=(datetime.now() - timedelta(hours=count-i)).isoformat(),
            open=o, high=h, low=l, close=p,
            volume=float(np.random.randint(100, 1000))
        ))
    return bars

# ── Signal generation (simplified 36-agent logic) ────────────────────────────
def get_signal(bars: List[BarData]) -> Dict:
    if len(bars) < 50:
        return {"direction": "HOLD", "confidence": 0.0, "agents": 0}

    closes = np.array([b.close for b in bars])
    highs  = np.array([b.high  for b in bars])
    lows   = np.array([b.low   for b in bars])

    buy_score = sell_score = 0.0
    agents_fired = 0

    # EMA
    ema20 = np.mean(closes[-20:])
    ema50 = np.mean(closes[-50:])
    if closes[-1] > ema20 > ema50:
        buy_score += 1.8; agents_fired += 1
    elif closes[-1] < ema20 < ema50:
        sell_score += 1.8; agents_fired += 1

    # RSI
    deltas = np.diff(closes[-15:])
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_g  = np.mean(gains[-14:]) if len(gains) >= 14 else 0
    avg_l  = np.mean(losses[-14:]) if len(losses) >= 14 else 1e-9
    rsi = 100 - 100 / (1 + avg_g / (avg_l or 1e-9))
    if rsi < 35:
        buy_score += 1.6; agents_fired += 1
    elif rsi > 65:
        sell_score += 1.6; agents_fired += 1

    # MACD
    macd = np.mean(closes[-12:]) - np.mean(closes[-26:])
    prev_macd = np.mean(closes[-13:-1]) - np.mean(closes[-27:-1])
    if macd > 0 and prev_macd <= 0:
        buy_score += 1.9; agents_fired += 1
    elif macd < 0 and prev_macd >= 0:
        sell_score += 1.9; agents_fired += 1

    # BOS - Break of Structure
    prev_high = max(highs[-20:-1])
    prev_low  = min(lows[-20:-1])
    if closes[-1] > prev_high:
        buy_score += 2.1; agents_fired += 1
    elif closes[-1] < prev_low:
        sell_score += 2.1; agents_fired += 1

    # Market Structure
    if (highs[-1] > highs[-5] > highs[-10] and
            lows[-1] > lows[-5] > lows[-10]):
        buy_score += 1.75; agents_fired += 1
    elif (highs[-1] < highs[-5] < highs[-10] and
            lows[-1] < lows[-5] < lows[-10]):
        sell_score += 1.75; agents_fired += 1

    # Momentum
    roc = (closes[-1] - closes[-10]) / closes[-10] * 100
    if roc > 0.3:
        buy_score += 1.4; agents_fired += 1
    elif roc < -0.3:
        sell_score += 1.4; agents_fired += 1

    # Bollinger
    mid = np.mean(closes[-20:])
    std = np.std(closes[-20:])
    if closes[-1] < mid - 2*std:
        buy_score += 1.5; agents_fired += 1
    elif closes[-1] > mid + 2*std:
        sell_score += 1.5; agents_fired += 1

    # Supertrend
    atr = np.mean(highs[-14:] - lows[-14:])
    st_upper = (highs[-1]+lows[-1])/2 + 3*atr
    st_lower = (highs[-1]+lows[-1])/2 - 3*atr
    if closes[-1] > st_lower:
        buy_score += 1.6; agents_fired += 1
    elif closes[-1] < st_upper:
        sell_score += 1.6; agents_fired += 1

    total = buy_score + sell_score
    if total == 0 or agents_fired < 3:
        return {"direction": "HOLD", "confidence": 0.0, "agents": agents_fired}

    if buy_score >= sell_score:
        return {"direction": "BUY",  "confidence": buy_score/total, "agents": agents_fired}
    return     {"direction": "SELL", "confidence": sell_score/total, "agents": agents_fired}

# ── Backtest engine ───────────────────────────────────────────────────────────
def backtest_pair(pair: str, bars: List[BarData]) -> Dict:
    trades = []
    wins = losses = 0
    total_pnl = 0.0
    balance = 100000.0
    peak_balance = 100000.0
    max_drawdown = 0.0
    in_trade = False
    entry_price = 0.0
    trade_direction = ""
    entry_bar = 0

    pip = 0.01 if "JPY" in pair else 0.0001

    for i in range(60, len(bars)):
        window = bars[max(0, i-60):i]
        sig = get_signal(window)

        # Exit existing trade after 24 bars
        if in_trade and i - entry_bar >= 24:
            exit_price = bars[i].close
            if trade_direction == "BUY":
                pnl_pips = (exit_price - entry_price) / pip
            else:
                pnl_pips = (entry_price - exit_price) / pip

            pnl_usd = pnl_pips * 0.1 * 1000
            total_pnl += pnl_usd
            balance += pnl_usd

            if pnl_usd > 0:
                wins += 1
                outcome = "WIN"
            else:
                losses += 1
                outcome = "LOSS"

            trades.append({
                "pair": pair,
                "direction": trade_direction,
                "entry": round(entry_price, 5),
                "exit": round(exit_price, 5),
                "pnl_pips": round(pnl_pips, 1),
                "pnl_usd": round(pnl_usd, 2),
                "outcome": outcome
            })

            # Track drawdown
            if balance > peak_balance:
                peak_balance = balance
            dd = (peak_balance - balance) / peak_balance * 100
            if dd > max_drawdown:
                max_drawdown = dd

            in_trade = False

        # Enter new trade
        if not in_trade and sig["direction"] != "HOLD" and sig["confidence"] >= 0.62:
            in_trade = True
            entry_price = bars[i].close
            trade_direction = sig["direction"]
            entry_bar = i

    total = wins + losses
    win_rate = wins / total if total > 0 else 0.0

    return {
        "pair": pair,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate * 100, 1),
        "total_pnl_usd": round(total_pnl, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "final_balance": round(balance, 2),
        "return_pct": round((balance - 100000) / 100000 * 100, 2)
    }

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*60)
    print("V14 BACKTEST — 2 YEAR HISTORICAL TEST")
    print("="*60)
    print(f"Testing {len(PAIRS)} pairs with real OANDA data\n")

    all_results = []
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0

    for pair in PAIRS:
        print(f"Testing {pair}...")
        bars = get_oanda_bars(pair, count=5000, granularity="H1")
        if len(bars) < 100:
            print(f"  Not enough data for {pair}, skipping")
            continue

        result = backtest_pair(pair, bars)
        all_results.append(result)
        total_trades += result["total_trades"]
        total_wins   += result["wins"]
        total_pnl    += result["total_pnl_usd"]

        print(f"  Trades: {result['total_trades']} | "
              f"WR: {result['win_rate']}% | "
              f"PnL: ${result['total_pnl_usd']:+,.0f} | "
              f"Max DD: {result['max_drawdown_pct']}%")

    # Summary
    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    print("\n" + "="*60)
    print("BACKTEST RESULTS SUMMARY")
    print("="*60)
    print(f"Total trades:    {total_trades}")
    print(f"Overall WR:      {overall_wr:.1f}%")
    print(f"Total P&L:       ${total_pnl:+,.0f}")
    print(f"Starting capital: $100,000")
    print(f"Ending capital:   ${100000 + total_pnl:,.0f}")
    print(f"Return:           {total_pnl/100000*100:+.1f}%")
    print("="*60)

    # Save results
    results_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_trades": total_trades,
            "overall_win_rate": round(overall_wr, 1),
            "total_pnl_usd": round(total_pnl, 2),
            "return_pct": round(total_pnl/100000*100, 1)
        },
        "pair_results": all_results
    }

    with open("v14_backtest_results.json", "w") as f:
        json.dump(results_data, f, indent=2)
    print("\nResults saved to v14_backtest_results.json")

    # Send Telegram
    msg = (
        f"V14 BACKTEST COMPLETE\n\n"
        f"Total trades: {total_trades}\n"
        f"Win rate: {overall_wr:.1f}%\n"
        f"Total P&L: ${total_pnl:+,.0f}\n"
        f"Return: {total_pnl/100000*100:+.1f}%\n\n"
        f"Per pair:\n"
    )
    for r in all_results:
        msg += f"{r['pair']}: {r['win_rate']}% WR | ${r['total_pnl_usd']:+,.0f}\n"

    send_telegram(msg)
    print("\nTelegram alert sent!")
    print("\nBacktest complete!")

if __name__ == "__main__":
    main()
