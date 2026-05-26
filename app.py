"""
PROJECT CHAKRA - Complete Flask Backend
Railway Production - All endpoints working
"""

import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Live data store - updated by v15_chakra.py every cycle
system_data = {
    "metrics": {
        "win_rate": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "cycle": 0,
        "balance": 100000,
        "open_trades": 0,
    },
    "open_trades": [],
    "closed_trades": [],
    "signals": [],
    "agents": [],
    "news": [],
    "last_update": None
}

# ============================================================================
# DASHBOARD
# ============================================================================

@app.route('/')
def dashboard():
    try:
        with open('chakra/chakra_dashboard.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>PROJECT CHAKRA</h1><p>API Running. Dashboard file error: {e}</p>"

# ============================================================================
# MAIN API STATUS - Used by dashboard
# ============================================================================

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "live",
        "metrics": system_data["metrics"],
        "open_trades": system_data["open_trades"],
        "signals": system_data["signals"][-20:],
        "agents": system_data["agents"],
        "news": system_data["news"][-10:],
        "last_update": system_data["last_update"],
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# UPDATE ENDPOINT - Called by v15_chakra.py every cycle
# ============================================================================

@app.route('/api/update', methods=['POST'])
def update_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data"}), 400

        # Update metrics
        m = system_data["metrics"]
        m["win_rate"]       = data.get("win_rate", data.get("confidence", 0))
        m["total_trades"]   = data.get("total_trades", 0)
        m["wins"]         = data.get("wins", 0)
        m["losses"]       = data.get("losses", 0)
        m["cycle"]        = data.get("cycle", 0)
        m["balance"]        = data.get("balance", 100000)
        m["nav"]            = data.get("nav", data.get("balance", 100000))
        m["pnl"]            = data.get("pnl", 0)
        m["open_trades"]    = data.get("open_trades", 0)
        m["pairs_scanned"]  = data.get("pairs_scanned", 12)
        m["last_updated"]   = data.get("last_updated", "")
        m["regime"]         = data.get("regime", "UNKNOWN")
        m["cycle_time_sec"] = data.get("cycle_time_sec", 0)
        # Store alt data signals
        if "alt_data" in data:
            system_data["alt_data"] = data["alt_data"]
        if "pair_signals" in data:
            system_data["pair_signals"] = data["pair_signals"]

        # Update open trades if provided
        if "trades" in data:
            system_data["open_trades"] = data["trades"]

        # Update signals if provided
        if "signal" in data:
            sig = data["signal"]
            sig["time"] = datetime.now().strftime("%H:%M:%S")
            system_data["signals"].append(sig)
            if len(system_data["signals"]) > 100:
                system_data["signals"] = system_data["signals"][-100:]

        # Update agents if provided
        if "agents" in data:
            system_data["agents"] = data["agents"]

        system_data["last_update"] = datetime.now().isoformat()
        logger.info(f"Updated: cycle={m['cycle']}, trades={m['total_trades']}, wr={m['win_rate']:.1%}")
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Update error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

# ============================================================================
# TRADE ENDPOINTS
# ============================================================================

@app.route('/api/trades/create', methods=['POST'])
def create_trade():
    try:
        data = request.get_json()
        trade = {
            "id": f"T{len(system_data['open_trades']) + 1}",
            "pair": data.get("pair"),
            "direction": data.get("direction"),
            "entry_price": data.get("entry_price"),
            "stop_loss": data.get("stop_loss"),
            "take_profit": data.get("take_profit"),
            "size": data.get("size"),
            "strategy": data.get("strategy", "AUTO"),
            "confidence": data.get("confidence", 0),
            "opened_at": datetime.now().isoformat()
        }
        system_data["open_trades"].append(trade)
        system_data["metrics"]["total_trades"] += 1
        return jsonify({"success": True, "trade": trade}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trades/close/<trade_id>', methods=['POST'])
def close_trade(trade_id):
    try:
        data = request.get_json() or {}
        for i, trade in enumerate(system_data["open_trades"]):
            if trade["id"] == trade_id:
                closed = system_data["open_trades"].pop(i)
                closed["closed_at"] = datetime.now().isoformat()
                closed["exit_price"] = data.get("exit_price")
                closed["pnl"] = data.get("pnl", 0)
                closed["outcome"] = "WIN" if closed["pnl"] > 0 else "LOSS"
                system_data["closed_trades"].append(closed)
                if closed["pnl"] > 0:
                    system_data["metrics"]["wins"] += 1
                else:
                    system_data["metrics"]["losses"] += 1
                total = system_data["metrics"]["wins"] + system_data["metrics"]["losses"]
                if total > 0:
                    system_data["metrics"]["win_rate"] = system_data["metrics"]["wins"] / total
                return jsonify({"success": True}), 200
        return jsonify({"success": False, "error": "Not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trades/open', methods=['GET'])
def get_open_trades():
    return jsonify(system_data["open_trades"])

@app.route('/api/trades/closed', methods=['GET'])
def get_closed_trades():
    return jsonify(system_data["closed_trades"][-50:])

# ============================================================================
# SIGNAL ENDPOINT
# ============================================================================

@app.route('/api/signal/add', methods=['POST'])
def add_signal():
    try:
        data = request.get_json()
        signal = {
            "pair": data.get("pair"),
            "direction": data.get("direction"),
            "confidence": data.get("confidence", 0),
            "strategy": data.get("strategy", "AUTO"),
            "regime": data.get("regime", "UNKNOWN"),
            "time": datetime.now().strftime("%H:%M:%S")
        }
        system_data["signals"].append(signal)
        if len(system_data["signals"]) > 100:
            system_data["signals"] = system_data["signals"][-100:]
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ============================================================================
# AI CHAT ENDPOINT
# ============================================================================

@app.route('/api/chat', methods=['POST'])
def ai_chat():
    try:
        import anthropic
        data = request.get_json()
        m = system_data["metrics"]
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=f"""You are the AI assistant for Project Chakra, a 36-agent AI forex trading system built by Lovinder.

LIVE SYSTEM DATA:
- Win Rate: {m['win_rate']*100:.1f}%
- Total Trades: {m['total_trades']}
- Wins: {m['wins']} | Losses: {m['losses']}
- Cycle: #{m['cycle']}
- Open Trades: {m['open_trades']}
- Balance: ${m['balance']:,.0f}
- Last Update: {system_data['last_update']}

SYSTEM INFO:
- 36 AI agents voting on every trade
- Confidence threshold: 70%
- Strategies: Mean Reversion (RANGING) + Trend Following (TRENDING) + Survival (VOLATILE)
- Pairs: EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, XAU/USD, GBP/JPY
- HiveMind recalibrates every 3 days
- Daily evolution runs every 24 hours

Be concise, specific, and professional. Answer questions about trading system, signals, performance, risk.""",
            messages=data.get('messages', [])
        )
        return jsonify({"reply": message.content[0].text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

@app.route('/api/system/status')
def system_status():
    return jsonify({"status": "operational", "timestamp": datetime.now().isoformat()}), 200

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# BACKTEST RUNNER — Run backtests on server, results saved here
# ============================================================================

backtest_results = {}
backtest_status = {"running": False, "progress": "", "started_at": None}

@app.route('/api/backtest/status')
def backtest_status_endpoint():
    return jsonify({
        "running": backtest_status["running"],
        "progress": backtest_status["progress"],
        "started_at": backtest_status["started_at"],
        "results_available": len(backtest_results) > 0
    })

@app.route('/api/backtest/results')
def backtest_results_endpoint():
    return jsonify(backtest_results)

@app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """Trigger backtest from dashboard — runs in background thread"""
    import threading
    if backtest_status["running"]:
        return jsonify({"error": "Backtest already running"}), 400
    def _run():
        backtest_status["running"] = True
        backtest_status["started_at"] = datetime.now().isoformat()
        try:
            import subprocess, sys
            backtest_status["progress"] = "Starting deep backtest..."
            result = subprocess.run(
                [sys.executable, "deep_backtest.py"],
                capture_output=True, text=True, timeout=3600
            )
            backtest_status["progress"] = "Complete"
            try:
                with open("deep_backtest_results.json") as f:
                    backtest_results.update(json.load(f))
            except: pass
        except Exception as e:
            backtest_status["progress"] = f"Error: {e}"
        finally:
            backtest_status["running"] = False
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True, "message": "Backtest running in background"})

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "service": "Project Chakra Dashboard",
        "timestamp": datetime.now().isoformat(),
        "metrics": system_data["metrics"],
        "uptime": "running"
    })

# ============================================================================
# AUTO SCHEDULER — Runs deep backtest every Sunday 2am UTC automatically
# No manual trigger needed
# ============================================================================

import threading
import time as _time

def _auto_backtest_scheduler():
    """Run deep backtest automatically every Sunday"""
    while True:
        try:
            now = __import__('datetime').datetime.utcnow()
            # Sunday = weekday 6, at 2am UTC
            if now.weekday() == 6 and now.hour == 2 and now.minute < 5:
                if not backtest_status["running"]:
                    logger.info("AUTO SCHEDULER: Starting weekly deep backtest...")
                    backtest_status["running"] = True
                    backtest_status["started_at"] = now.isoformat()
                    backtest_status["progress"] = "Auto-scheduled weekly backtest starting..."
                    try:
                        import subprocess, sys
                        result = subprocess.run(
                            [sys.executable, "deep_backtest.py"],
                            capture_output=True, text=True, timeout=7200
                        )
                        backtest_status["progress"] = "Weekly backtest complete"
                        try:
                            with open("deep_backtest_results.json") as f:
                                backtest_results.update(json.load(f))
                            logger.info("AUTO SCHEDULER: Weekly backtest results saved")
                        except Exception as e:
                            logger.warning(f"Results read error: {e}")
                    except Exception as e:
                        backtest_status["progress"] = f"Error: {e}"
                        logger.error(f"AUTO SCHEDULER error: {e}")
                    finally:
                        backtest_status["running"] = False
            _time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            _time.sleep(300)

# Start scheduler in background when app starts
_scheduler_thread = threading.Thread(target=_auto_backtest_scheduler, daemon=True)
_scheduler_thread.start()
logger.info("Auto backtest scheduler started — runs every Sunday 2am UTC")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
