"""
PROJECT CHAKRA — Railway Dashboard Backend
Minimal bulletproof version — no complex imports at startup
"""

import os
import json
import logging
import threading
import time
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

# ── LIVE DATA STORE ──────────────────────────────────────────────────────────
system_data = {
    "metrics": {
        "win_rate":      0.0,
        "total_trades":  0,
        "wins":          0,
        "losses":        0,
        "cycle":         0,
        "balance":       100000.0,
        "nav":           100000.0,
        "pnl":           0.0,
        "open_trades":   0,
        "regime":        "UNKNOWN",
        "last_updated":  "",
        "pairs_scanned": 12,
    },
    "open_trades":   [],
    "closed_trades": [],
    "signals":       [],
    "alt_data":      {},
    "pair_signals":  {},
    "last_update":   None,
}

# ── BACKTEST STATE ───────────────────────────────────────────────────────────
bt_running  = False
bt_progress = "Not started"
bt_started  = None
bt_results  = {}

# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    """Serve the dashboard HTML"""
    for path in ["chakra_dashboard.html", "index.html"]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/html"}
        except:
            continue
    # Inline fallback dashboard
    m = system_data["metrics"]
    bal   = m.get("balance", 100000)
    pnl   = m.get("pnl", 0)
    wr    = m.get("win_rate", 0) * 100
    trade = m.get("total_trades", 0)
    reg   = m.get("regime", "UNKNOWN")
    upd   = m.get("last_updated", "Never")[:16]
    html  = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta http-equiv="refresh" content="15">
<title>Project Chakra</title>
<style>
  body{{background:#050A0F;color:#E8F4F8;font-family:monospace;padding:40px;margin:0}}
  h1{{color:#06D6A0;font-size:2rem;margin-bottom:8px}}
  .sub{{color:#5A7A8A;font-size:.8rem;margin-bottom:32px}}
  .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}}
  .card{{background:#0D1821;border:1px solid #1E3448;border-radius:12px;padding:20px}}
  .lbl{{color:#5A7A8A;font-size:.65rem;text-transform:uppercase;letter-spacing:.1em}}
  .val{{font-size:1.8rem;font-weight:700;margin-top:6px}}
  .green{{color:#06D6A0}}.red{{color:#EF476F}}.gold{{color:#F0A500}}.blue{{color:#118AB2}}
  .status{{background:#0D1821;border:1px solid #1E3448;border-radius:12px;padding:20px}}
  .row{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1E3448}}
</style></head><body>
<h1>⚡ PROJECT CHAKRA</h1>
<div class="sub">AUTONOMOUS FOREX TRADING SYSTEM V15 — Live Dashboard</div>
<div class="grid">
  <div class="card"><div class="lbl">Balance</div>
    <div class="val green">${bal:,.0f}</div></div>
  <div class="card"><div class="lbl">P&L</div>
    <div class="val {'green' if pnl>=0 else 'red'}">{'+' if pnl>=0 else ''}${pnl:,.0f}</div></div>
  <div class="card"><div class="lbl">Win Rate</div>
    <div class="val {'green' if wr>=45 else 'gold'}">{wr:.1f}%</div></div>
  <div class="card"><div class="lbl">Total Trades</div>
    <div class="val gold">{trade}</div></div>
</div>
<div class="status">
  <div class="row"><span class="lbl">Regime</span><span class="gold">{reg}</span></div>
  <div class="row"><span class="lbl">Wins</span><span class="green">{m.get('wins',0)}</span></div>
  <div class="row"><span class="lbl">Losses</span><span class="red">{m.get('losses',0)}</span></div>
  <div class="row"><span class="lbl">Open Trades</span><span class="blue">{m.get('open_trades',0)}</span></div>
  <div class="row"><span class="lbl">Last Update</span><span>{upd} UTC</span></div>
  <div class="row"><span class="lbl">System</span><span class="green">● LIVE</span></div>
</div>
<div style="color:#5A7A8A;font-size:.7rem;margin-top:20px">
  Auto-refresh every 15s &nbsp;|&nbsp; Full dashboard loading...
</div>
</body></html>"""
    return html, 200, {"Content-Type": "text/html"}


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Project Chakra Dashboard",
        "timestamp": datetime.utcnow().isoformat(),
        "balance": system_data["metrics"].get("balance", 100000),
        "trades": system_data["metrics"].get("total_trades", 0),
    })


@app.route("/api/status")
def api_status():
    return jsonify({
        "status": "live",
        "metrics":      system_data["metrics"],
        "open_trades":  system_data["open_trades"],
        "closed_trades": system_data["closed_trades"][-20:],
        "alt_data":     system_data["alt_data"],
        "pair_signals": system_data["pair_signals"],
        "last_update":  system_data["last_update"],
        "timestamp":    datetime.utcnow().isoformat(),
    })


@app.route("/api/update", methods=["POST"])
def api_update():
    """Receive live data from v15_chakra.py every 5 minutes"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        m    = system_data["metrics"]

        # Update all fields
        m["win_rate"]      = float(data.get("win_rate", data.get("confidence", 0)))
        m["total_trades"]  = int(data.get("total_trades", m["total_trades"]))
        m["wins"]          = int(data.get("wins", m["wins"]))
        m["losses"]        = int(data.get("losses", m["losses"]))
        m["cycle"]         = int(data.get("cycle", m["cycle"]))
        m["balance"]       = float(data.get("balance", m["balance"]))
        m["nav"]           = float(data.get("nav", m["balance"]))
        m["pnl"]           = float(data.get("pnl", m["balance"] - 100000))
        m["open_trades"]   = int(data.get("open_trades", 0))
        m["regime"]        = str(data.get("regime", m["regime"]))
        m["last_updated"]  = str(data.get("last_updated", datetime.utcnow().isoformat()))
        m["pairs_scanned"] = int(data.get("pairs_scanned", 12))

        # Update collections
        if "trades" in data:
            system_data["open_trades"] = data["trades"]
        if "closed_trades" in data:
            system_data["closed_trades"] = data["closed_trades"][-100:]
        if "alt_data" in data:
            system_data["alt_data"] = data["alt_data"]
        if "pair_signals" in data:
            system_data["pair_signals"] = data["pair_signals"]

        system_data["last_update"] = datetime.utcnow().isoformat()
        logger.info(f"Updated: bal=${m['balance']:,.0f} wr={m['win_rate']:.1%} "
                   f"trades={m['total_trades']} regime={m['regime']}")
        return jsonify({"status": "ok", "cycle": m["cycle"]})
    except Exception as e:
        logger.error(f"Update error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/backtest/status")
def backtest_status():
    return jsonify({
        "running": bt_running,
        "progress": bt_progress,
        "started_at": bt_started,
        "results_available": len(bt_results) > 0,
    })


@app.route("/api/backtest/results")
def backtest_results_ep():
    return jsonify(bt_results)


@app.route("/api/backtest/run", methods=["POST"])
def run_backtest():
    global bt_running, bt_progress, bt_started, bt_results
    if bt_running:
        return jsonify({"error": "Already running"}), 400

    def _run():
        global bt_running, bt_progress, bt_started, bt_results
        import subprocess, sys
        bt_running  = True
        bt_started  = datetime.utcnow().isoformat()
        bt_progress = "Running..."
        try:
            subprocess.run([sys.executable, "deep_backtest.py"],
                          capture_output=True, text=True, timeout=3600)
            bt_progress = "Complete"
            try:
                with open("deep_backtest_results.json") as f:
                    bt_results = json.load(f)
            except:
                pass
        except Exception as e:
            bt_progress = f"Error: {e}"
        finally:
            bt_running = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True})


# ── AUTO SCHEDULER ───────────────────────────────────────────────────────────

def _scheduler():
    """Run deep backtest every Sunday 2am UTC"""
    global bt_running, bt_progress, bt_started, bt_results
    while True:
        try:
            now = datetime.utcnow()
            if now.weekday() == 6 and now.hour == 2 and now.minute < 5 and not bt_running:
                bt_running  = True
                bt_started  = now.isoformat()
                bt_progress = "Auto weekly backtest..."
                try:
                    import subprocess, sys
                    subprocess.run([sys.executable, "deep_backtest.py"],
                                  capture_output=True, text=True, timeout=7200)
                    bt_progress = "Complete"
                    try:
                        with open("deep_backtest_results.json") as f:
                            bt_results = json.load(f)
                    except:
                        pass
                except Exception as e:
                    bt_progress = f"Error: {e}"
                finally:
                    bt_running = False
            time.sleep(60)
        except Exception as e:
            logger.error(f"Scheduler: {e}")
            time.sleep(300)

# Start scheduler safely
try:
    _t = threading.Thread(target=_scheduler, daemon=True)
    _t.start()
    logger.info("Scheduler started")
except Exception as e:
    logger.warning(f"Scheduler failed to start: {e}")

# ── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
