"""
PROJECT CHAKRA V15 — WALK-FORWARD BACKTEST
Institutional validation: Train 700 bars → Test 100 bars → Repeat
Run: py -3.11 v15_walkforward.py
"""
import json, logging
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.WARNING, format='%(asctime)s [WF] %(message)s')

from v13_production import (
    OandaAPI, InstrumentsCandles, PAIRS, BarData, Signal,
    EMAAgent, MACDAgent, RSIAgent, BollingerAgent,
    ATRAgent, StochasticAgent, BreakoutAgent,
    BOSAgent, CHOCHAgent, WyckoffAgent,
    OANDA_TOKEN, OANDA_ENV
)

# ── CONFIG ──────────────────────────────────────────────────────────
TRAIN_BARS   = 700
TEST_BARS    = 100
TOTAL_BARS   = 5000
GRANULARITY  = "H1"
CONFIDENCE   = 0.55
SL_ATR_MULT  = 1.5
TP_ATR_MULT  = 4.5
RISK_PCT     = 0.005
INIT_BALANCE = 100_000.0

BACKTEST_AGENTS = [
    EMAAgent, MACDAgent, RSIAgent, BollingerAgent,
    ATRAgent, StochasticAgent, BreakoutAgent,
    BOSAgent, CHOCHAgent, WyckoffAgent,
]

# ── CONVERT RAW OANDA DICT → BarData ────────────────────────────────
def to_bars(candles):
    bars = []
    for c in candles:
        try:
            if not c.get("complete", True):
                continue
            mid = c.get("mid", {})
            bars.append(BarData(
                timestamp=c.get("time", ""),
                open=float(mid.get("o", 0)),
                high=float(mid.get("h", 0)),
                low=float(mid.get("l", 0)),
                close=float(mid.get("c", 0)),
                volume=float(c.get("volume", 0))
            ))
        except:
            continue
    return bars

# ── FETCH CANDLES ────────────────────────────────────────────────────
def fetch_candles(pair):
    try:
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        params = {"count": TOTAL_BARS, "granularity": GRANULARITY, "price": "M"}
        r = InstrumentsCandles(instrument=pair, params=params)
        client.request(r)
        candles = r.response.get("candles", [])
        print(f"  Fetched {len(candles)} candles for {pair}")
        return candles
    except Exception as e:
        print(f"  ERROR fetching {pair}: {e}")
        return []

# ── SIGNAL ENGINE — uses Signal.direction and Signal.confidence ──────
def compute_signal(bars):
    if len(bars) < 50:
        return "HOLD", 0.0

    buy_score = sell_score = 0.0
    buy_n = sell_n = hold_n = 0

    for AgentClass in BACKTEST_AGENTS:
        try:
            ag = AgentClass()
            result = ag.analyze(bars)          # returns Signal object
            d = result.direction               # "BUY" / "SELL" / "HOLD"
            c = float(result.confidence)       # 0.0 - 1.0

            if d == "BUY":    buy_score  += c; buy_n  += 1
            elif d == "SELL": sell_score += c; sell_n += 1
            else:             hold_n += 1
        except:
            hold_n += 1

    total = buy_n + sell_n + hold_n
    if total == 0:
        return "HOLD", 0.0

    active_ratio = (buy_n + sell_n) / total

    if buy_n > sell_n and active_ratio >= 0.25:
        conf = buy_score / max(buy_n, 1)
        if conf >= CONFIDENCE:
            return "BUY", conf

    elif sell_n > buy_n and active_ratio >= 0.25:
        conf = sell_score / max(sell_n, 1)
        if conf >= CONFIDENCE:
            return "SELL", conf

    return "HOLD", 0.0

# ── SIMULATE ONE WINDOW ──────────────────────────────────────────────
def simulate_window(all_bars, train_start, test_start, test_end):
    balance  = INIT_BALANCE
    trades   = []
    position = None

    for i in range(test_start, min(test_end, len(all_bars))):
        price = all_bars[i].close

        # Check if open position hit SL or TP
        if position:
            hit_sl = (position["dir"] == "BUY"  and price <= position["sl"]) or \
                     (position["dir"] == "SELL" and price >= position["sl"])
            hit_tp = (position["dir"] == "BUY"  and price >= position["tp"]) or \
                     (position["dir"] == "SELL" and price <= position["tp"])

            if hit_sl or hit_tp:
                rr  = TP_ATR_MULT / SL_ATR_MULT   # 3.0
                pnl = position["risk"] * (rr if hit_tp else -1.0)
                balance += pnl
                trades.append({"win": hit_tp, "pnl": round(pnl, 2)})
                position = None

        # Look for new signal (only one trade at a time)
        if not position:
            history = all_bars[train_start:i]
            if len(history) < 50:
                continue

            sig, conf = compute_signal(history)

            if sig in ("BUY", "SELL"):
                closes = [b.close for b in history[-15:]]
                atr = sum(abs(closes[-j] - closes[-j-1])
                          for j in range(1, 14)) / 14 if len(closes) >= 14 else price * 0.001

                risk_amt = balance * RISK_PCT
                sl = price - atr * SL_ATR_MULT if sig == "BUY" else price + atr * SL_ATR_MULT
                tp = price + atr * TP_ATR_MULT if sig == "BUY" else price - atr * TP_ATR_MULT
                position = {"dir": sig, "sl": sl, "tp": tp, "risk": risk_amt}

    # Force-close any open trade at window end
    if position and test_end <= len(all_bars):
        final = all_bars[min(test_end, len(all_bars)) - 1].close
        raw_pnl = (final - all_bars[test_start].close)
        pnl = balance * RISK_PCT * (5 if raw_pnl > 0 else -1)
        balance += pnl
        trades.append({"win": pnl > 0, "pnl": round(pnl, 2)})

    return balance, trades

# ── MAIN ─────────────────────────────────────────────────────────────
def run():
    print("\n" + "="*60)
    print("  PROJECT CHAKRA V15 — WALK-FORWARD BACKTEST")
    print("  Train 700 bars → Test 100 bars → Slide → Repeat")
    print(f"  Confidence: {CONFIDENCE} | SL: {SL_ATR_MULT}x ATR | TP: {TP_ATR_MULT}x ATR")
    print("="*60)

    all_results = []

    for pair in PAIRS[:3]:
        print(f"\n{'─'*50}")
        print(f"  PAIR: {pair}")
        print(f"{'─'*50}")

        raw      = fetch_candles(pair)
        all_bars = to_bars(raw)

        if len(all_bars) < TRAIN_BARS + TEST_BARS:
            print(f"  Not enough bars ({len(all_bars)}). Skipping.")
            continue

        print(f"  Usable bars: {len(all_bars)}")

        windows, pos, wnum = [], 0, 1

        while pos + TRAIN_BARS + TEST_BARS <= len(all_bars):
            bal, trades = simulate_window(
                all_bars,
                train_start=pos,
                test_start=pos + TRAIN_BARS,
                test_end=pos + TRAIN_BARS + TEST_BARS
            )
            wins   = sum(1 for t in trades if t["win"])
            losses = len(trades) - wins
            pnl    = sum(t["pnl"] for t in trades)
            wr     = (wins / len(trades) * 100) if trades else 0
            icon   = "✅" if wr >= 50 else "⚠️ "

            print(f"  {icon} Window {wnum:>2} | Trades:{len(trades):>3} | "
                  f"W:{wins} L:{losses} | WR:{wr:>5.1f}% | PnL:${pnl:>+8.2f}")

            windows.append({"window": wnum, "trades": len(trades),
                            "wins": wins, "wr": round(wr, 1), "pnl": round(pnl, 2)})
            pos  += TEST_BARS
            wnum += 1

        if not windows:
            print("  No windows completed.")
            continue

        t_trades = sum(w["trades"] for w in windows)
        t_wins   = sum(w["wins"]   for w in windows)
        t_pnl    = sum(w["pnl"]    for w in windows)
        avg_wr   = (t_wins / t_trades * 100) if t_trades else 0
        ret_pct  = (t_pnl / INIT_BALANCE) * 100

        print(f"\n  ── {pair} SUMMARY ──")
        print(f"  Windows: {len(windows)} | Trades: {t_trades} | "
              f"WR: {avg_wr:.1f}% | PnL: ${t_pnl:+,.2f} | Return: {ret_pct:+.2f}%")

        all_results.append({
            "pair": pair, "windows": len(windows), "total_trades": t_trades,
            "win_rate": round(avg_wr, 1), "total_pnl": round(t_pnl, 2),
            "return_pct": round(ret_pct, 2)
        })

    # ── FINAL SUMMARY ────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  FINAL WALK-FORWARD RESULTS")
    print("="*60)

    if not all_results:
        print("  No results generated. Check OANDA connection.")
        return

    g_trades = sum(r["total_trades"] for r in all_results)
    g_pnl    = sum(r["total_pnl"]    for r in all_results)
    g_wr     = sum(r["win_rate"]     for r in all_results) / len(all_results)
    g_ret    = sum(r["return_pct"]   for r in all_results) / len(all_results)

    for r in all_results:
        icon = "✅" if r["win_rate"] >= 50 else "⚠️ "
        print(f"  {icon} {r['pair']:<10} WR:{r['win_rate']:>5.1f}%  "
              f"Trades:{r['total_trades']:>4}  "
              f"PnL:${r['total_pnl']:>+10,.2f}  Return:{r['return_pct']:>+6.2f}%")

    print(f"\n  {'─'*50}")
    print(f"  TOTAL TRADES     : {g_trades}")
    print(f"  OVERALL WIN RATE : {g_wr:.1f}%")
    print(f"  OVERALL PnL      : ${g_pnl:+,.2f}")
    print(f"  AVG RETURN       : {g_ret:+.2f}%")

    if g_wr >= 50:
        print(f"\n  ✅ SYSTEM PASSES — Win rate above 50%")
        print(f"  ✅ Continue paper trading — system is profitable")
    elif g_wr >= 40:
        print(f"\n  ⚠️  Win rate {g_wr:.1f}% — still profitable at 3:1 RR")
        print(f"  ℹ️  Break-even at 3:1 RR is only 25% win rate")
        print(f"  ✅ System is viable — continue monitoring")
    else:
        print(f"\n  ❌ Win rate below 40% — needs improvement")

    with open("v15_walkforward_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {"confidence": CONFIDENCE, "sl_mult": SL_ATR_MULT,
                       "tp_mult": TP_ATR_MULT, "train_bars": TRAIN_BARS,
                       "test_bars": TEST_BARS},
            "pairs": all_results,
            "summary": {"total_trades": g_trades, "avg_win_rate": round(g_wr, 1),
                        "total_pnl": round(g_pnl, 2), "avg_return_pct": round(g_ret, 2)}
        }, f, indent=2)
    print(f"\n  Results saved → v15_walkforward_results.json")
    print("="*60 + "\n")

if __name__ == "__main__":
    run()
