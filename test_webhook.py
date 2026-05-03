#!/usr/bin/env python3
"""
Test TradingView webhook locally
"""

import requests
import json

print("\n" + "="*70)
print("TESTING TRADINGVIEW WEBHOOK")
print("="*70 + "\n")

# Test data
alert_data = {
    "symbol": "EURUSD",
    "price": 1.0950,
    "type": "BUY",
    "confidence": 0.85,
    "RSI": 72,
    "MACD": "BULLISH"
}

# Send to local webhook
url = "http://localhost:5000/tradingview-alert"

print(f"Sending test alert to: {url}")
print(f"Alert data: {json.dumps(alert_data, indent=2)}\n")

try:
    response = requests.post(url, json=alert_data)
    print(f"✅ Response: {response.status_code}")
    print(f"Response body: {response.json()}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70 + "\n")