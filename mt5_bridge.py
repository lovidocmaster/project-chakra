"""
PROJECT CHAKRA — MT5 BRIDGE
============================
Connects your Chakra trading system to MetaTrader 5 (Exness account).

HOW IT WORKS:
1. v15_chakra.py generates a trade signal (BUY/SELL EUR/USD at 0.78 confidence)
2. This bridge receives that signal via HTTP
3. Bridge forwards it to MT5 via MetaTrader5 Python library
4. MT5 places the real trade on your Exness account

SETUP (5 steps):
Step 1: Install MT5 Python library
        py -3.11 -m pip install MetaTrader5

Step 2: Install MT5 terminal
        Download from Exness website and log into your account

Step 3: Set your Exness credentials below

Step 4: Run this bridge on your PC:
        py -3.11 mt5_bridge.py

Step 5: Your Chakra system will automatically send signals here

PAIRS SUPPORTED:
- All 12 Chakra pairs → mapped to MT5 symbols
- BONUS: Gold (XAUUSD), US30, NAS100 via MT5

Run: py -3.11 mt5_bridge.py
"""

import os
import json
import logging
import time
import math
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mt5_bridge.log", mode="a")
    ]
)
log = logging.getLogger("MT5Bridge")

# ─── YOUR EXNESS CREDENTIALS ─────────────────────────────────────────────────
MT5_LOGIN    = int(os.getenv("MT5_LOGIN", "0"))         # Your MT5 account number
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")            # Your MT5 password
MT5_SERVER   = os.getenv("MT5_SERVER", "Exness-MT5Real")# Exness server name

# ─── PAIR MAPPING (Chakra → MT5 symbols) ─────────────────────────────────────
SYMBOL_MAP = {
    "EUR_USD": "EURUSD",
    "GBP_USD": "GBPUSD",
    "USD_JPY": "USDJPY",
    "AUD_USD": "AUDUSD",
    "USD_CAD": "USDCAD",
    "GBP_JPY": "GBPJPY",
    "EUR_JPY": "EURJPY",
    "NZD_USD": "NZDUSD",
    "USD_CHF": "USDCHF",
    "EUR_GBP": "EURGBP",
    "AUD_JPY": "AUDJPY",
    "USD_SGD": "USDSGD",
    # BONUS pairs available in MT5
    "XAU_USD": "XAUUSD",   # Gold
    "US30":    "US30",      # Dow Jones
    "NAS100":  "NAS100",    # Nasdaq
    "US500":   "SP500",     # S&P 500
}

# ─── RISK SETTINGS ───────────────────────────────────────────────────────────
LOT_SIZE        = 0.01   # Start very small — 0.01 lot = micro lot
MAX_LOT         = 0.10   # Maximum lot size
RISK_PCT        = 0.01   # 1% risk per trade
MAGIC_NUMBER    = 20260526  # Unique ID for Chakra trades in MT5
SLIPPAGE        = 20     # Max slippage in points

# ─── BRIDGE STATE ─────────────────────────────────────────────────────────────
bridge_state = {
    "connected": False,
    "trades_sent": 0,
    "trades_failed": 0,
    "last_signal": None,
    "last_error": None,
    "mt5_balance": 0.0,
    "open_positions": 0,
}

# ─── MT5 CONNECTION ───────────────────────────────────────────────────────────

def connect_mt5():
    """Connect to MetaTrader 5 terminal"""
    try:
        import MetaTrader5 as mt5

        if not mt5.initialize():
            log.error(f"MT5 initialize failed: {mt5.last_error()}")
            bridge_state["last_error"] = str(mt5.last_error())
            return False

        # Login to account
        if MT5_LOGIN > 0 and MT5_PASSWORD:
            authorized = mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
            if not authorized:
                log.error(f"MT5 login failed: {mt5.last_error()}")
                bridge_state["last_error"] = f"Login failed: {mt5.last_error()}"
                return False

        info = mt5.account_info()
        if info:
            bridge_state["connected"] = True
            bridge_state["mt5_balance"] = info.balance
            log.info(f"✅ MT5 Connected: {info.name} | Balance: ${info.balance:,.2f} | Server: {info.server}")
            return True

    except ImportError:
        log.error("MetaTrader5 not installed. Run: py -3.11 -m pip install MetaTrader5")
        bridge_state["last_error"] = "MetaTrader5 not installed"
    except Exception as e:
        log.error(f"MT5 connection error: {e}")
        bridge_state["last_error"] = str(e)

    return False


def get_symbol_info(symbol: str):
    """Get symbol info from MT5"""
    try:
        import MetaTrader5 as mt5
        info = mt5.symbol_info(symbol)
        if info is None:
            # Try enabling the symbol
            mt5.symbol_select(symbol, True)
            time.sleep(0.5)
            info = mt5.symbol_info(symbol)
        return info
    except Exception as e:
        log.warning(f"Symbol info error {symbol}: {e}")
        return None


def calculate_lot_size(symbol: str, sl_pips: float, account_balance: float) -> float:
    """
    Calculate lot size based on risk percentage.
    1% of balance / (SL in pips × pip value)
    """
    try:
        import MetaTrader5 as mt5
        info = get_symbol_info(symbol)
        if not info:
            return LOT_SIZE

        risk_amount = account_balance * RISK_PCT
        pip_value   = info.trade_tick_value

        if pip_value > 0 and sl_pips > 0:
            lot = risk_amount / (sl_pips * pip_value)
            # Round to 2 decimal places and clamp
            lot = round(max(LOT_SIZE, min(lot, MAX_LOT)), 2)
        else:
            lot = LOT_SIZE

        log.info(f"{symbol}: Risk ${risk_amount:.2f} / (SL {sl_pips:.1f} pips × ${pip_value:.4f}) = {lot:.2f} lots")
        return lot

    except Exception as e:
        log.warning(f"Lot calc error: {e}")
        return LOT_SIZE


def place_trade(symbol: str, direction: str, sl_price: float = 0,
                tp_price: float = 0, lot: float = 0, comment: str = "Chakra") -> dict:
    """
    Place a trade on MT5.
    Returns dict with success status and trade details.
    """
    try:
        import MetaTrader5 as mt5

        # Reconnect if needed
        if not bridge_state["connected"]:
            connect_mt5()

        # Map direction to MT5 order type
        if direction.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid

        if price is None or price == 0:
            return {"success": False, "error": f"No price for {symbol}"}

        # Get account balance for lot calculation
        acct = mt5.account_info()
        balance = acct.balance if acct else 10000.0

        # Calculate lot if not provided
        if lot <= 0:
            sl_pips = abs(price - sl_price) * 10000 if sl_price > 0 else 20
            if "JPY" in symbol: sl_pips = abs(price - sl_price) * 100 if sl_price > 0 else 20
            lot = calculate_lot_size(symbol, sl_pips, balance)

        # Build request
        request_data = {
            "action":    mt5.TRADE_ACTION_DEAL,
            "symbol":    symbol,
            "volume":    lot,
            "type":      order_type,
            "price":     price,
            "slippage":  SLIPPAGE,
            "magic":     MAGIC_NUMBER,
            "comment":   f"Chakra|{comment[:15]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Add SL/TP if provided
        if sl_price > 0:
            request_data["sl"] = round(sl_price, 5)
        if tp_price > 0:
            request_data["tp"] = round(tp_price, 5)

        # Send order
        result = mt5.order_send(request_data)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            bridge_state["trades_sent"] += 1
            bridge_state["open_positions"] = len(mt5.positions_get())
            log.info(f"✅ MT5 TRADE: {direction} {lot:.2f} {symbol} @ {price:.5f} | Ticket: {result.order}")
            return {
                "success":  True,
                "ticket":   result.order,
                "symbol":   symbol,
                "direction": direction,
                "lot":      lot,
                "price":    price,
                "sl":       sl_price,
                "tp":       tp_price,
            }
        else:
            err = result.comment if result else "No result"
            code = result.retcode if result else 0
            bridge_state["trades_failed"] += 1
            bridge_state["last_error"] = f"retcode={code}: {err}"
            log.error(f"❌ MT5 FAILED: {direction} {symbol} retcode={code} {err}")
            return {"success": False, "error": f"retcode={code}: {err}"}

    except ImportError:
        return {"success": False, "error": "MetaTrader5 library not installed"}
    except Exception as e:
        log.error(f"Trade error {symbol}: {e}")
        return {"success": False, "error": str(e)}


def close_trade(ticket: int) -> dict:
    """Close a specific trade by ticket number"""
    try:
        import MetaTrader5 as mt5
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return {"success": False, "error": "Position not found"}

        p = pos[0]
        price = mt5.symbol_info_tick(p.symbol).bid if p.type == 0 else mt5.symbol_info_tick(p.symbol).ask

        req = {
            "action":   mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol":   p.symbol,
            "volume":   p.volume,
            "type":     mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY,
            "price":    price,
            "slippage": SLIPPAGE,
            "magic":    MAGIC_NUMBER,
            "comment":  "Chakra|close",
        }
        result = mt5.order_send(req)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            log.info(f"✅ Closed ticket {ticket}")
            return {"success": True, "ticket": ticket}
        return {"success": False, "error": str(result.retcode if result else "failed")}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── FLASK API ────────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "service":    "Project Chakra MT5 Bridge",
        "status":     "connected" if bridge_state["connected"] else "disconnected",
        "balance":    bridge_state["mt5_balance"],
        "sent":       bridge_state["trades_sent"],
        "failed":     bridge_state["trades_failed"],
        "positions":  bridge_state["open_positions"],
        "last_signal": bridge_state["last_signal"],
        "last_error": bridge_state["last_error"],
        "time":       datetime.utcnow().isoformat(),
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "mt5": bridge_state["connected"]})


@app.route("/trade", methods=["POST"])
def receive_trade():
    """
    Receive trade signal from v15_chakra.py and execute on MT5.

    Expected JSON:
    {
        "pair":       "EUR_USD",
        "direction":  "BUY",
        "confidence": 0.78,
        "sl_price":   1.0820,
        "tp_price":   1.0950,
        "lot":        0.0,      # 0 = auto-calculate
        "source":     "Chakra"
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON"}), 400

        pair      = data.get("pair", "")
        direction = data.get("direction", "").upper()
        conf      = float(data.get("confidence", 0.5))
        sl_price  = float(data.get("sl_price", 0))
        tp_price  = float(data.get("tp_price", 0))
        lot       = float(data.get("lot", 0))

        # Map Chakra pair to MT5 symbol
        symbol = SYMBOL_MAP.get(pair, pair.replace("_",""))
        if not symbol:
            return jsonify({"error": f"Unknown pair: {pair}"}), 400

        # Minimum confidence filter
        if conf < 0.55:
            return jsonify({
                "executed": False,
                "reason": f"Confidence {conf:.0%} below 55% minimum"
            })

        log.info(f"Signal received: {direction} {pair} ({symbol}) conf={conf:.0%}")
        bridge_state["last_signal"] = {
            "pair": pair, "direction": direction,
            "confidence": conf, "time": datetime.utcnow().isoformat()
        }

        # Execute trade
        result = place_trade(symbol, direction, sl_price, tp_price, lot,
                           comment=f"{conf:.0%}")

        return jsonify({
            "executed": result["success"],
            "symbol":   symbol,
            "direction": direction,
            **result
        })

    except Exception as e:
        log.error(f"Trade endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/close", methods=["POST"])
def close_position():
    """Close a trade by ticket number"""
    data = request.get_json(force=True) or {}
    ticket = int(data.get("ticket", 0))
    if not ticket:
        return jsonify({"error": "ticket required"}), 400
    result = close_trade(ticket)
    return jsonify(result)


@app.route("/positions")
def get_positions():
    """Get all open positions"""
    try:
        import MetaTrader5 as mt5
        positions = mt5.positions_get()
        if positions:
            return jsonify([{
                "ticket":    p.ticket,
                "symbol":    p.symbol,
                "type":      "BUY" if p.type == 0 else "SELL",
                "volume":    p.volume,
                "open_price": p.price_open,
                "current":   p.price_current,
                "profit":    p.profit,
                "sl":        p.sl,
                "tp":        p.tp,
                "time":      datetime.fromtimestamp(p.time).isoformat(),
                "comment":   p.comment,
            } for p in positions])
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/account")
def get_account():
    """Get MT5 account info"""
    try:
        import MetaTrader5 as mt5
        info = mt5.account_info()
        if info:
            bridge_state["mt5_balance"] = info.balance
            return jsonify({
                "name":    info.name,
                "login":   info.login,
                "server":  info.server,
                "balance": info.balance,
                "equity":  info.equity,
                "margin":  info.margin,
                "free_margin": info.margin_free,
                "profit":  info.profit,
                "currency": info.currency,
                "leverage": info.leverage,
            })
        return jsonify({"error": "No account info"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║        PROJECT CHAKRA — MT5 BRIDGE                   ║
║        Connects Chakra signals to MetaTrader 5       ║
╚══════════════════════════════════════════════════════╝
""")

    # Attempt MT5 connection
    log.info("Connecting to MetaTrader 5...")
    if connect_mt5():
        log.info("✅ MT5 connected successfully")
    else:
        log.warning("⚠️  MT5 not connected — bridge running in test mode")
        log.warning("   Make sure MT5 terminal is open and logged in")

    # Start Flask server
    port = int(os.getenv("MT5_BRIDGE_PORT", 6001))
    print(f"""
Bridge is running at: http://localhost:{port}

Endpoints:
  GET  /           — Status and stats
  GET  /account    — MT5 account balance
  GET  /positions  — Open positions
  POST /trade      — Execute trade signal
  POST /close      — Close a position

Your v15_chakra.py will automatically send signals here.
Keep this window open while trading.

Press Ctrl+C to stop.
""")
    app.run(host="0.0.0.0", port=port, debug=False)
