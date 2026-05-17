#!/usr/bin/env python3
from flask import Flask, jsonify
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/')
def home():
    try:
        with open('dashboard_live.html', 'r') as f:
            return f.read()
    except:
        return "Dashboard file not found", 404

@app.route('/dashboard')
def dashboard():
    try:
        with open('dashboard_live.html', 'r') as f:
            return f.read()
    except:
        return "Dashboard file not found", 404

@app.route('/api/metrics')
def metrics():
    return jsonify({"balance": 120000, "open_trades": 2, "total_signals": 247, "win_rate": 65, "agents_active": 36, "mode": "LIVE"})

if __name__ == '__main__':
    print("\n" + "="*70)
    print("DASHBOARD SERVER RUNNING ON http://localhost:5001")
    print("="*70 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
