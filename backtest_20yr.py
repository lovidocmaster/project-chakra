"""
PROJECT CHAKRA - 20 YEAR BACKTEST ENGINE
Tests your RegimeRouter strategies against 20 years of real data (2000-2025)
Uses Yahoo Finance for free historical data
Run: py -3.11 backtest_20yr.py
"""

import os
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Tuple
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s [BT] %(message)s')
log = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

PAIRS_YF = {
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "USD_JPY": "USDJPY=X",
    "AUD_USD": "AUDUSD=X",
    "USD_CAD": "USDCAD=X",
    "XAU_USD": "GC=F",
    "GBP_JPY": "GBPJPY=X",
}

START_DATE   = "2000-01-01"
END_DATE     = datetime.now().strftime("%Y-%m-%d")
INITIAL_BAL  = 100_000.0
RISK_PCT     = 0.005   # 0.5% risk per trade
MAX_TRADES   = 3
CONFIDENCE   = 0.65
SL_ATR_MULT  = 0.8
TP_ATR_MULT  = 2.4


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class BacktestTrade:
    pair: str
    direction: str
    entry: float
    sl: float
    tp: float
    units: int
    date: str
    strategy: str
    outcome: str = "OPEN"
    exit_price: float = 0.0
    pnl: float = 0.0
    pnl_pips: float = 0.0


# ============================================================================
# DATA FETCHER
# ============================================================================

def fetch_historical_data(pair: str, yf_symbol: str) -> List[Bar]:
    """Fetch 20+ years of daily data from Yahoo Finance"""
    try:
        import yfinance as yf
        log.info(f"Fetching {pair} ({yf_symbol}) from {START_DATE} to {END_DATE}...")
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(start=START_DATE, end=END_DATE, interval="1d")

        if df.empty:
            log.warning(f"No data for {pair}")
            return []

        # Fix MultiIndex if present
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.droplevel(1)

        bars = []
        for idx, row in df.iterrows():
            try:
                bars.append(Bar(
                    date=str(idx)[:10],
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row.get('Volume', 0))
                ))
            except:
                continue

        log.info(f"  {pair}: {len(bars)} bars from {bars[0].date} to {bars[-1].date}")
        return bars

    except ImportError:
        log.error("yfinance not installed. Run: py -3.11 -m pip install yfinance pandas")
        return []
    except Exception as e:
        log.error(f"Error fetching {pair}: {e}")
        return []


# ============================================================================
# REGIME DETECTOR
# ============================================================================

def detect_regime(bars: List[Bar], lookback: int = 20) -> str:
    """Detect market regime from price data"""
    if len(bars) < lookback + 5:
        return "RANGING"

    closes = [b.close for b in bars[-lookback:]]
    highs  = [b.high  for b in bars[-lookback:]]
    lows   = [b.low   for b in bars[-lookback:]]

    # ATR
    atr = sum(b.high - b.low for b in bars[-14:]) / 14

    # Price range
    price_range = max(highs) - min(lows)
    avg_price   = sum(closes) / len(closes)
    range_pct   = price_range / avg_price

    # Trend strength (simple linear regression slope)
    n = len(closes)
    x_mean = (n - 1) / 2
    y_mean = sum(closes) / n
    numerator   = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0
    slope_pct = abs(slope) / avg_price

    # Volatility
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5

    if volatility > 0.02:
        return "VOLATILE"
    elif slope_pct > 0.001:
        return "TRENDING"
    else:
        return "RANGING"


# ============================================================================
# STRATEGY ENGINE
# ============================================================================

def get_signal(bars: List[Bar], regime: str) -> Tuple[str, float, float, float]:
    """
    Returns (direction, confidence, sl_dist, tp_dist)
    Based on regime - uses appropriate strategy
    """
    if len(bars) < 30:
        return "HOLD", 0.0, 0.001, 0.002

    closes = [b.close for b in bars]
    highs  = [b.high  for b in bars]
    lows   = [b.low   for b in bars]
    price  = closes[-1]
    atr    = sum(b.high - b.low for b in bars[-14:]) / 14

    if regime == "RANGING":
        return _mean_reversion_signal(closes, highs, lows, price, atr)
    elif regime == "TRENDING":
        return _trend_following_signal(closes, highs, lows, price, atr)
    elif regime == "VOLATILE":
        return _volatile_signal(closes, highs, lows, price, atr)
    else:
        return "HOLD", 0.0, atr, atr * 2


def _mean_reversion_signal(closes, highs, lows, price, atr):
    """RSI + Bollinger Bands mean reversion"""
    period = 20
    sma  = sum(closes[-period:]) / period
    std  = (sum((c - sma)**2 for c in closes[-period:]) / period) ** 0.5
    upper = sma + 2 * std
    lower = sma - 2 * std

    # RSI
    gains  = [max(closes[i]-closes[i-1], 0) for i in range(-14,0)]
    losses = [max(closes[i-1]-closes[i], 0) for i in range(-14,0)]
    ag = sum(gains)/14; al = sum(losses)/14
    rsi = 100 - (100/(1+ag/max(al,0.0001)))

    sl_dist = atr * SL_ATR_MULT
    tp_dist = atr * TP_ATR_MULT

    if price <= lower and rsi < 30:
        conf = 0.70 + (30 - rsi) / 100
        tp_dist = (sma - price) * 1.2
        return "BUY", min(conf, 0.95), sl_dist, max(tp_dist, sl_dist * 1.5)
    elif price >= upper and rsi > 70:
        conf = 0.70 + (rsi - 70) / 100
        tp_dist = (price - sma) * 1.2
        return "SELL", min(conf, 0.95), sl_dist, max(tp_dist, sl_dist * 1.5)
    else:
        return "HOLD", 0.0, sl_dist, tp_dist


def _trend_following_signal(closes, highs, lows, price, atr):
    """EMA crossover + MACD trend following"""
    def ema(data, n):
        k = 2/(n+1); e = data[0]
        for d in data[1:]: e = d*k + e*(1-k)
        return e

    n = len(closes)
    ema12 = ema(closes[-min(26,n):], min(12,n))
    ema26 = ema(closes[-min(26,n):], min(26,n))
    macd  = ema12 - ema26
    ema50 = ema(closes[-min(50,n):], min(50,n))

    sl_dist = atr * SL_ATR_MULT * 1.2
    tp_dist = atr * TP_ATR_MULT

    trend_up = price > ema50 and macd > 0
    trend_dn = price < ema50 and macd < 0

    if trend_up:
        conf = 0.68 + abs(macd) / price * 100
        return "BUY", min(conf, 0.92), sl_dist, tp_dist
    elif trend_dn:
        conf = 0.68 + abs(macd) / price * 100
        return "SELL", min(conf, 0.92), sl_dist, tp_dist
    else:
        return "HOLD", 0.0, sl_dist, tp_dist


def _volatile_signal(closes, highs, lows, price, atr):
    """In volatile markets - very selective, wider stops"""
    sl_dist = atr * 2.0
    tp_dist = atr * 2.0
    return "HOLD", 0.0, sl_dist, tp_dist


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def backtest_pair(pair: str, bars: List[Bar]) -> Dict:
    """Run backtest on single pair"""
    balance   = INITIAL_BAL
    trades    = []
    open_trade = None
    wins = losses = 0
    max_balance = INITIAL_BAL
    max_drawdown = 0.0
    equity_curve = [INITIAL_BAL]

    pip_value = 0.01 if "JPY" in pair else 0.0001 if "XAU" not in pair else 0.1

    for i in range(50, len(bars)):
        bar = bars[i]
        hist = bars[:i]

        # Check if open trade hit SL or TP
        if open_trade:
            if open_trade.direction == "BUY":
                if bar.low <= open_trade.sl:
                    # SL hit
                    pnl_pips = (open_trade.sl - open_trade.entry) / pip_value
                    pnl = pnl_pips * pip_value * open_trade.units
                    open_trade.outcome = "LOSS"
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = pnl_pips
                    open_trade.exit_price = open_trade.sl
                    balance += pnl
                    losses += 1
                    trades.append(open_trade)
                    open_trade = None
                elif bar.high >= open_trade.tp:
                    # TP hit
                    pnl_pips = (open_trade.tp - open_trade.entry) / pip_value
                    pnl = pnl_pips * pip_value * open_trade.units
                    open_trade.outcome = "WIN"
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = pnl_pips
                    open_trade.exit_price = open_trade.tp
                    balance += pnl
                    wins += 1
                    trades.append(open_trade)
                    open_trade = None
            elif open_trade.direction == "SELL":
                if bar.high >= open_trade.sl:
                    pnl_pips = (open_trade.entry - open_trade.sl) / pip_value
                    pnl = -pnl_pips * pip_value * open_trade.units
                    open_trade.outcome = "LOSS"
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = -pnl_pips
                    open_trade.exit_price = open_trade.sl
                    balance += pnl
                    losses += 1
                    trades.append(open_trade)
                    open_trade = None
                elif bar.low <= open_trade.tp:
                    pnl_pips = (open_trade.entry - open_trade.tp) / pip_value
                    pnl = pnl_pips * pip_value * open_trade.units
                    open_trade.outcome = "WIN"
                    open_trade.pnl = pnl
                    open_trade.pnl_pips = pnl_pips
                    open_trade.exit_price = open_trade.tp
                    balance += pnl
                    wins += 1
                    trades.append(open_trade)
                    open_trade = None

        # Track drawdown
        if balance > max_balance:
            max_balance = balance
        dd = (max_balance - balance) / max_balance
        if dd > max_drawdown:
            max_drawdown = dd
        equity_curve.append(balance)

        # Generate new signal if no open trade
        if open_trade is None:
            regime    = detect_regime(hist)
            direction, conf, sl_dist, tp_dist = get_signal(hist, regime)

            if direction != "HOLD" and conf >= CONFIDENCE:
                price = bar.close
                risk_usd = balance * RISK_PCT
                units    = max(100, min(int(risk_usd / max(sl_dist * 10, 0.0001)), 15000))

                if direction == "BUY":
                    sl = price - sl_dist
                    tp = price + tp_dist
                else:
                    sl = price + sl_dist
                    tp = price - tp_dist

                open_trade = BacktestTrade(
                    pair=pair, direction=direction,
                    entry=price, sl=sl, tp=tp,
                    units=units, date=bar.date,
                    strategy=regime
                )

    total = wins + losses
    wr    = wins / total if total > 0 else 0
    total_pnl = balance - INITIAL_BAL
    annual_return = (balance / INITIAL_BAL) ** (1 / 25) - 1 if balance > 0 else 0

    return {
        "pair": pair,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wr,
        "final_balance": round(balance, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / INITIAL_BAL * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "annual_return_pct": round(annual_return * 100, 2),
        "avg_win": round(sum(t.pnl for t in trades if t.outcome=="WIN") / max(wins,1), 2),
        "avg_loss": round(sum(t.pnl for t in trades if t.outcome=="LOSS") / max(losses,1), 2),
        "profit_factor": round(abs(sum(t.pnl for t in trades if t.outcome=="WIN") /
                               max(abs(sum(t.pnl for t in trades if t.outcome=="LOSS")),1)), 2),
        "equity_curve": equity_curve[::30],  # Sample every 30 days
        "data_from": bars[0].date if bars else "N/A",
        "data_to": bars[-1].date if bars else "N/A",
        "total_bars": len(bars),
    }


# ============================================================================
# MAIN RUNNER
# ============================================================================

def run_full_backtest():
    print("\n" + "="*70)
    print("PROJECT CHAKRA - 20 YEAR BACKTEST ENGINE")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Initial Capital: ${INITIAL_BAL:,.0f}")
    print(f"Risk per trade: {RISK_PCT*100}%")
    print(f"Strategy: RegimeRouter (Mean Reversion + Trend Following + Volatile)")
    print("="*70 + "\n")

    results = []
    all_data = {}

    for pair, yf_symbol in PAIRS_YF.items():
        bars = fetch_historical_data(pair, yf_symbol)
        if len(bars) < 100:
            log.warning(f"Skipping {pair} - insufficient data")
            continue
        all_data[pair] = bars
        result = backtest_pair(pair, bars)
        results.append(result)

    if not results:
        print("No results - check yfinance installation")
        return

    # Print results table
    print("\n" + "="*70)
    print("BACKTEST RESULTS - 20+ YEARS")
    print("="*70)
    print(f"{'Pair':<12} {'Trades':>7} {'WR':>7} {'P/L $':>12} {'P/L %':>8} {'MaxDD':>8} {'AnnRet':>8} {'PF':>6}")
    print("-"*70)

    total_pnl = 0
    for r in sorted(results, key=lambda x: x['total_pnl'], reverse=True):
        print(f"{r['pair']:<12} {r['total_trades']:>7} {r['win_rate']:>7.1%} "
              f"{r['total_pnl']:>12,.0f} {r['total_pnl_pct']:>8.1f}% "
              f"{r['max_drawdown']:>8.1f}% {r['annual_return_pct']:>8.1f}% "
              f"{r['profit_factor']:>6.2f}")
        total_pnl += r['total_pnl']

    print("-"*70)
    print(f"{'TOTAL':<12} {'':>7} {'':>7} {total_pnl:>12,.0f}")
    print("="*70)

    # Find best and worst
    best  = max(results, key=lambda x: x['win_rate'])
    worst = min(results, key=lambda x: x['win_rate'])
    print(f"\n✅ Best pair: {best['pair']} ({best['win_rate']:.1%} WR)")
    print(f"❌ Worst pair: {worst['pair']} ({worst['win_rate']:.1%} WR)")

    # Save results
    with open('backtest_20yr_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to backtest_20yr_results.json")

    # Period breakdown
    print("\n=== DATA COVERAGE ===")
    for r in results:
        print(f"{r['pair']}: {r['data_from']} to {r['data_to']} ({r['total_bars']} days)")

    return results


if __name__ == '__main__':
    run_full_backtest()
