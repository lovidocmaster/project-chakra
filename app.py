"""
PROJECT CHAKRA - Flask Backend + Live Dashboard
Railway Production Deployment
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

system_data = {
    "metrics": {"win_rate": 0.0, "total_trades": 0, "wins": 0, "losses": 0, "cycle": 0},
    "open_trades": [],
    "signals": [],
    "last_update": None
}

@app.route('/')
def dashboard():
    try:
        with open('chakra/chakra_dashboard.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"<h1>PROJECT CHAKRA</h1><p>Error: {e}</p><p><a href='/api/status'>API Status</a></p>"

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "live",
        "metrics": system_data["metrics"],
        "open_trades": system_data["open_trades"],
        "signals": system_data["signals"][-20:],
        "last_update": system_data["last_update"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/update', methods=['POST'])
def update_data():
    try:
        data = request.get_json()
        if data:
            system_data["metrics"]["win_rate"] = data.get("confidence", 0)
            system_data["metrics"]["total_trades"] = data.get("total_trades", 0)
            system_data["metrics"]["wins"] = data.get("wins", 0)
            system_data["metrics"]["losses"] = data.get("losses", 0)
            system_data["metrics"]["cycle"] = data.get("cycle", 0)
            system_data["last_update"] = datetime.now().isoformat()
            logger.info(f"Updated: cycle={data.get('cycle')}, trades={data.get('total_trades')}, wr={data.get('confidence')}")
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

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
            "opened_at": datetime.now().isoformat()
        }
        system_data["open_trades"].append(trade)
        return jsonify({"success": True, "trade": trade}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/signal/add', methods=['POST'])
def add_signal():
    try:
        data = request.get_json()
        system_data["signals"].append({
            "pair": data.get("pair"),
            "direction": data.get("direction"),
            "confidence": data.get("confidence", 0),
            "time": datetime.now().strftime("%H:%M:%S")
        })
        if len(system_data["signals"]) > 100:
            system_data["signals"] = system_data["signals"][-100:]
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/system/status')
def system_status():
    return jsonify({"status": "operational", "timestamp": datetime.now().isoformat()}), 200

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


@app.route('/api/chat', methods=['POST'])
def ai_chat():
    try:
        import anthropic
        data = request.get_json()
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=f"""You are the AI assistant for Project Chakra, a 36-agent AI forex trading system built by Lovinder. Win Rate: {system_data['metrics']['win_rate']*100:.1f}%, Total Trades: {system_data['metrics']['total_trades']}, Cycle: #{system_data['metrics']['cycle']}. Be concise and specific.""",
            messages=data.get('messages', [])
        )
        return jsonify({"reply": message.content[0].text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

