"""
chakra/risk.py — Risk management: CVaR, position sizing, drawdown protection
"""
from __future__ import annotations
import os, json, math, logging, numpy as np
from datetime import datetime
from chakra.models import TradeRecord
log = logging.getLogger("Chakra")

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
