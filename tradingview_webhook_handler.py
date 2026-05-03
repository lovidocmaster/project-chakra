#!/usr/bin/env python3
"""
TradingView Webhook Handler
Receives real-time alerts from TradingView charts
"""

from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Store alerts
alerts_log = []

@app.route('/tradingview-alert', methods=['POST'])
def receive_alert():
    """Receive TradingView webhook alert"""
    
    try:
        alert_data = request.json or request.form.to_dict()
        
        timestamp = datetime.now().isoformat()
        
        # Parse alert
        symbol = alert_data.get("symbol", "UNKNOWN").replace(":", "/")
        signal = alert_data.get("type", "HOLD").upper()
        price = alert_data.get("price", 0)
        confidence = float(alert_data.get("confidence", 0.5))
        rsi = alert_data.get("RSI", "N/A")
        macd = alert_data.get("MACD", "N/A")
        
        # Log the alert
        alert_record = {
            "timestamp": timestamp,
            "symbol": symbol,
            "signal": signal,
            "price": price,
            "confidence": confidence,
            "RSI": rsi,
            "MACD": macd
        }
        alerts_log.append(alert_record)
        
        # Print to console
        print("\n" + "="*70)
        print("🚨 TRADINGVIEW ALERT RECEIVED")
        print("="*70)
        print(f"Timestamp:  {timestamp}")
        print(f"Symbol:     {symbol}")
        print(f"Price:      {price}")
        print(f"Signal:     {signal}")
        print(f"Confidence: {confidence:.0%}")
        if rsi != "N/A":
            print(f"RSI:        {rsi}")
        if macd != "N/A":
            print(f"MACD:       {macd}")
        
        # Determine action
        if confidence > 0.75 and signal in ["BUY", "SELL"]:
            action = "✅ EXECUTE_TRADE"
            status = "HIGH CONFIDENCE"
        elif confidence > 0.65:
            action = "⚠️  MONITOR"
            status = "MODERATE"
        else:
            action = "❌ SKIP"
            status = "LOW CONFIDENCE"
        
        print(f"Action:     {action}")
        print(f"Status:     {status}")
        print("="*70 + "\n")
        
        # Return success
        return jsonify({
            "status": "received",
            "symbol": symbol,
            "signal": signal,
            "action": action,
            "message": f"{symbol} {signal} signal at {confidence:.0%}"
        }), 200
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/tradingview-alert', methods=['GET'])
def check_status():
    """Check webhook status"""
    return jsonify({
        "status": "webhook_active",
        "alerts_received": len(alerts_log),
        "endpoint": "/tradingview-alert",
        "ready": True
    }), 200

@app.route('/alerts', methods=['GET'])
def get_recent_alerts():
    """Get recent alerts"""
    return jsonify({
        "total": len(alerts_log),
        "recent": alerts_log[-10:] if alerts_log else []
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    print("\n" + "="*70)
    print("TRADINGVIEW WEBHOOK SERVER")
    print("="*70)
    print("\n✅ Endpoints:")
    print("   POST  /tradingview-alert  - Receive TradingView alerts")
    print("   GET   /tradingview-alert  - Check status")
    print("   GET   /alerts             - View recent alerts")
    print("   GET   /health             - Health check")
    print("\n🌐 Running on port 5000")
    print("   Local: http://localhost:5000")
    print("   Status: http://localhost:5000/health")
    print("\n📊 After starting ngrok:")
    print("   Webhook URL: https://your-ngrok-url.ngrok.io/tradingview-alert")
    print("\n" + "="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)