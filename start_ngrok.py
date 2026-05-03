#!/usr/bin/env python3
"""
Start ngrok tunnel for TradingView webhooks
"""

from pyngrok import ngrok
import time

# Set your authtoken
ngrok.set_auth_token("3DER999LFimJKA1ZwyF5fJq1vlB_31nQ3GrgG4r13VwzvopsR")

# Start tunnel
print("\n" + "="*70)
print("STARTING NGROK TUNNEL")
print("="*70 + "\n")

try:
    public_url = ngrok.connect(5000)
    print(f"✅ Tunnel created!")
    print(f"\n🌐 Public URL: {public_url}")
    print(f"\n📊 Webhook URL for TradingView:")
    print(f"   {public_url}/tradingview-alert")
    print(f"\n💡 Keep this terminal open while using TradingView alerts")
    print("\n" + "="*70 + "\n")
    
    # Keep running
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\n❌ Shutting down tunnel...")
    ngrok.kill()
    print("✅ Tunnel closed")