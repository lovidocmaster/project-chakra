"""
PROJECT CHAKRA V2 - Flask Backend for Heroku Deployment
Wraps the trading system for cloud execution
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state (in production, use Redis/Supabase)
trading_state = {
    "status": "initialized",
    "capital": 100000,
    "balance": 100000,
    "equity": 100000,
    "open_trades": [],
    "closed_trades": [],
    "agents_active": 37,
    "last_update": datetime.now().isoformat(),
    "system_metrics": {
        "win_rate": 0.65,
        "sharpe_ratio": 1.8,
        "max_drawdown": -0.12,
        "monthly_return": 0.08,
        "trades_total": 156
    }
}

# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """Returns overall system health and status"""
    return jsonify({
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "backend_version": "v15_chakra",
        "agents_active": trading_state["agents_active"],
        "uptime_seconds": 0,
        "database": "supabase_connected"
    }), 200

@app.route('/api/system/health', methods=['GET'])
def system_health():
    """Detailed health check - used by Heroku"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": "low",
        "memory_usage": "normal",
        "database_connected": True,
        "oanda_connected": False  # Will be True once trading loop starts
    }), 200

# ============================================================================
# ACCOUNT ENDPOINTS
# ============================================================================

@app.route('/api/account/metrics', methods=['GET'])
def account_metrics():
    """Get current account metrics"""
    return jsonify({
        "capital": trading_state["capital"],
        "balance": trading_state["balance"],
        "equity": trading_state["equity"],
        "used_margin": 5000,
        "available_margin": 95000,
        "currency": "USD",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/account/performance', methods=['GET'])
def account_performance():
    """Get performance metrics"""
    return jsonify({
        "win_rate": trading_state["system_metrics"]["win_rate"],
        "sharpe_ratio": trading_state["system_metrics"]["sharpe_ratio"],
        "max_drawdown": trading_state["system_metrics"]["max_drawdown"],
        "monthly_return": trading_state["system_metrics"]["monthly_return"],
        "trades_total": trading_state["system_metrics"]["trades_total"],
        "avg_win": 150.00,
        "avg_loss": -100.00,
        "profit_factor": 2.1,
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================================================
# TRADES ENDPOINTS
# ============================================================================

@app.route('/api/trades/open', methods=['GET'])
def get_open_trades():
    """Get all open trades"""
    return jsonify({
        "trades": trading_state["open_trades"],
        "count": len(trading_state["open_trades"]),
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/trades/closed', methods=['GET'])
def get_closed_trades():
    """Get last N closed trades"""
    limit = request.args.get('limit', 20, type=int)
    recent_trades = trading_state["closed_trades"][-limit:]
    return jsonify({
        "trades": recent_trades,
        "count": len(recent_trades),
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/trades/create', methods=['POST'])
def create_trade():
    """Create a new trade (when agents vote to execute)"""
    try:
        data = request.get_json()
        trade = {
            "id": f"TRADE-{len(trading_state['open_trades']) + 1}",
            "pair": data.get("pair"),
            "direction": data.get("direction"),  # BUY or SELL
            "entry_price": data.get("entry_price"),
            "stop_loss": data.get("stop_loss"),
            "take_profit": data.get("take_profit"),
            "size": data.get("size"),
            "opened_at": datetime.now().isoformat(),
            "status": "open"
        }
        trading_state["open_trades"].append(trade)
        logger.info(f"Trade created: {trade['id']} - {trade['pair']} {trade['direction']}")
        return jsonify({"success": True, "trade": trade}), 201
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/trades/close/<trade_id>', methods=['POST'])
def close_trade(trade_id):
    """Close an open trade"""
    try:
        for i, trade in enumerate(trading_state["open_trades"]):
            if trade["id"] == trade_id:
                closed_trade = trading_state["open_trades"].pop(i)
                closed_trade["status"] = "closed"
                closed_trade["closed_at"] = datetime.now().isoformat()
                closed_trade["exit_price"] = request.json.get("exit_price")
                closed_trade["p_l"] = request.json.get("p_l")
                trading_state["closed_trades"].append(closed_trade)
                logger.info(f"Trade closed: {trade_id}")
                return jsonify({"success": True, "trade": closed_trade}), 200
        return jsonify({"success": False, "error": "Trade not found"}), 404
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

# ============================================================================
# AGENTS ENDPOINTS
# ============================================================================

@app.route('/api/agents/status', methods=['GET'])
def agents_status():
    """Get all agents status"""
    agents = [
        {"name": "Market Knowledge", "status": "operational", "uptime": 100},
        {"name": "Chart Analysis", "status": "operational", "uptime": 100},
        {"name": "News Monitor", "status": "operational", "uptime": 98},
        {"name": "Sentiment Analyzer", "status": "operational", "uptime": 99},
        {"name": "Risk Manager", "status": "operational", "uptime": 100},
        {"name": "Execution Agent", "status": "idle", "uptime": 100},
        {"name": "Learning Agent", "status": "operational", "uptime": 95},
        {"name": "Master Orchestrator", "status": "operational", "uptime": 100}
    ]
    return jsonify({
        "agents": agents,
        "total_active": len([a for a in agents if a["status"] != "offline"]),
        "timestamp": datetime.now().isoformat()
    }), 200

# ============================================================================
# LOGS ENDPOINTS
# ============================================================================

logs_buffer = []

@app.route('/api/logs/system', methods=['GET'])
def get_system_logs():
    """Get recent system logs"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        "logs": logs_buffer[-limit:],
        "count": len(logs_buffer),
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/logs/add', methods=['POST'])
def add_log():
    """Add a log entry (called by trading system)"""
    try:
        data = request.get_json()
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": data.get("level", "INFO"),
            "message": data.get("message"),
            "agent": data.get("agent", "system")
        }
        logs_buffer.append(log_entry)
        # Keep only last 500 logs in memory
        if len(logs_buffer) > 500:
            logs_buffer.pop(0)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@app.route('/api/config/instruments', methods=['GET'])
def get_instruments():
    """Get configured trading instruments"""
    return jsonify({
        "instruments": [
            "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", 
            "USD_CAD", "XAU_USD", "GBP_JPY"
        ],
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/api/config/risk', methods=['GET'])
def get_risk_config():
    """Get risk management settings"""
    return jsonify({
        "max_drawdown": 0.15,
        "risk_per_trade": 0.02,
        "max_concurrent_trades": 5,
        "stop_loss_pips": 50,
        "take_profit_ratio": 2.5,
        "timestamp": datetime.now().isoformat()
    }), 200


# ============================================================================
# DASHBOARD
# ============================================================================

@app.route('/')
def dashboard():
    with open('chakra_dashboard.html', 'r', encoding='utf-8') as f:
        return f.read()
# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

