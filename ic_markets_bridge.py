#!/usr/bin/env python3
"""
IC Markets MT5 Bridge
Connects to MetaTrader 5 terminal running locally on Windows.
Used as backup broker when OANDA is unavailable.

SETUP (one time):
  1. Download & install MT5 from IC Markets website
  2. Log in: account=52865933, server=ICMarketsSC-Demo
  3. pip install MetaTrader5
  4. Keep MT5 terminal open and running
  5. Run: py -3.11 ic_markets_bridge.py  (to test)
"""

import os
import logging
from typing import Dict, Tuple
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("IC_MT5")

IC_ACCOUNT  = int(os.getenv("IC_MARKETS_ACCOUNT", "52865933"))
IC_PASSWORD = os.getenv("IC_MARKETS_PASSWORD", "")
IC_SERVER   = os.getenv("IC_MARKETS_SERVER", "ICMarketsSC-Demo")

SYMBOL_MAP = {
    "EUR_USD": "EURUSD", "GBP_USD": "GBPUSD", "USD_JPY": "USDJPY",
    "AUD_USD": "AUDUSD", "USD_CAD": "USDCAD",
}

try:
    import MetaTrader5 as mt5
    MT5_OK = True
except ImportError:
    MT5_OK = False
    log.warning("MetaTrader5 not installed. Run: pip install MetaTrader5")


class ICMarketsBridge:
    """
    MT5 bridge for IC Markets demo account.
    Drop-in backup for OANDA — same place_trade / close_trade interface.
    """

    def __init__(self):
        self.connected = False
        self.account_info = {}
        if MT5_OK:
            self._connect()

    def _connect(self) -> bool:
        if not MT5_OK:
            return False
        try:
            if not mt5.initialize(login=IC_ACCOUNT, password=IC_PASSWORD, server=IC_SERVER):
                log.error(f"MT5 init failed: {mt5.last_error()}")
                return False
            info = mt5.account_info()
            if info is None:
                log.error("MT5: cannot get account info")
                return False
            self.connected = True
            self.account_info = {
                "balance": info.balance, "equity": info.equity,
                "currency": info.currency, "server": info.server,
            }
            log.info(f"IC Markets MT5 connected | Balance: {info.currency}{info.balance:,.2f}")
            return True
        except Exception as e:
            log.error(f"MT5 connect error: {e}")
            return False

    def get_balance(self) -> float:
        if not self.connected or not MT5_OK:
            return 0.0
        try:
            info = mt5.account_info()
            return float(info.balance) if info else 0.0
        except Exception:
            return 0.0

    def get_price(self, pair: str) -> Tuple[float, float]:
        """Returns (bid, ask)"""
        if not self.connected or not MT5_OK:
            return 0.0, 0.0
        symbol = SYMBOL_MAP.get(pair, pair.replace("_", ""))
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return tick.bid, tick.ask
        except Exception:
            pass
        return 0.0, 0.0

    def place_trade(self, pair: str, direction: str, units: int,
                    sl: float, tp: float) -> Dict:
        """Place a market order. Returns dict with trade_id and status."""
        if not self.connected or not MT5_OK:
            return {"status": "error", "reason": "MT5 not connected"}

        symbol = SYMBOL_MAP.get(pair, pair.replace("_", ""))
        bid, ask = self.get_price(pair)
        if direction == "BUY":
            price, order_type = ask, mt5.ORDER_TYPE_BUY
        else:
            price, order_type = bid, mt5.ORDER_TYPE_SELL

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       round(units / 100000, 2),
            "type":         order_type,
            "price":        price,
            "sl":           round(sl, 5),
            "tp":           round(tp, 5),
            "deviation":    20,
            "magic":        202600,
            "comment":      "V13-ProjectChakra",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            return {"status": "error", "reason": str(mt5.last_error())}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"status": "error", "reason": f"Retcode {result.retcode}: {result.comment}"}

        log.info(f"IC Markets: {direction} {symbol} {units} units @ {price:.5f} | ID:{result.order}")
        return {"status": "ok", "trade_id": str(result.order), "entry_price": price, "broker": "IC_Markets"}

    def close_trade(self, trade_id: int, pair: str) -> Dict:
        """Close an open position by ticket ID."""
        if not self.connected or not MT5_OK:
            return {"status": "error"}
        symbol   = SYMBOL_MAP.get(pair, pair.replace("_", ""))
        position = mt5.positions_get(ticket=trade_id)
        if not position:
            return {"status": "error", "reason": "Position not found"}

        pos = position[0]
        bid, ask = self.get_price(pair)
        close_type  = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        close_price = bid if pos.type == 0 else ask

        request = {
            "action":   mt5.TRADE_ACTION_DEAL, "symbol": symbol,
            "volume":   pos.volume, "type": close_type,
            "position": trade_id,  "price": close_price,
            "deviation": 20, "magic": 202600, "comment": "V13-Close",
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"IC Markets: closed {trade_id} @ {close_price:.5f}")
            return {"status": "ok", "close_price": close_price}
        return {"status": "error", "reason": str(mt5.last_error())}

    def get_open_positions(self) -> list:
        if not self.connected or not MT5_OK:
            return []
        positions = mt5.positions_get()
        if not positions:
            return []
        return [{
            "ticket": p.ticket, "symbol": p.symbol,
            "direction": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume, "entry": p.price_open,
            "current": p.price_current, "pnl": p.profit,
            "sl": p.sl, "tp": p.tp,
        } for p in positions]

    def disconnect(self):
        if MT5_OK and self.connected:
            mt5.shutdown()
            self.connected = False


# ── Quick connection test ─────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    bridge = ICMarketsBridge()
    if bridge.connected:
        print(f"\n✅ IC Markets Connected!")
        print(f"   Account : {IC_ACCOUNT}")
        print(f"   Server  : {IC_SERVER}")
        print(f"   Balance : {bridge.account_info}")
        bid, ask = bridge.get_price("EUR_USD")
        print(f"   EURUSD  : Bid={bid:.5f}  Ask={ask:.5f}")
        print(f"   Positions: {len(bridge.get_open_positions())} open")
        bridge.disconnect()
    else:
        print("\n❌ MT5 not connected. Make sure:")
        print("   1. MetaTrader 5 is installed and running")
        print("   2. Logged in with account 52865933 on ICMarketsSC-Demo")
        print("   3. Run: pip install MetaTrader5")
