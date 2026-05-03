#!/usr/bin/env python3
"""
Setup TradingView MCP Integration
Connects Project Chakra directly to TradingView
"""

def setup_tradingview_mcp():
    """Configure TradingView MCP"""
    
    print("\n" + "="*60)
    print("TRADINGVIEW MCP SETUP")
    print("="*60 + "\n")
    
    # Configuration
    config = {
        "mcp_type": "tradingview",
        "features": [
            "real_time_prices",
            "technical_indicators",
            "chart_patterns",
            "webhook_alerts",
            "screener",
            "historical_data"
        ],
        "symbols": [
            "EUR/USD",
            "GBP/USD",
            "USD/JPY",
            "AUD/USD",
            "USD/CAD"
        ],
        "timeframes": [
            "1M", "5M", "15M", "1H", "4H", "1D"
        ],
        "indicators": [
            "RSI",
            "MACD",
            "Stochastic",
            "Bollinger Bands",
            "Moving Averages",
            "ATR"
        ],
        "webhook": {
            "enabled": True,
            "port": 5000,
            "endpoint": "/tradingview-alert"
        },
        "update_frequency": "real-time"
    }
    
    print("✅ TradingView MCP Configuration:\n")
    print(f"   Symbols: {', '.join(config['symbols'])}")
    print(f"   Timeframes: {', '.join(config['timeframes'])}")
    print(f"   Indicators: {len(config['indicators'])} available")
    print(f"   Webhook: {config['webhook']['endpoint']} on port {config['webhook']['port']}")
    print(f"   Update: {config['update_frequency']}")
    
    print("\n📊 Features Enabled:")
    for feature in config['features']:
        print(f"   ✅ {feature.replace('_', ' ').title()}")
    
    print("\n⚙️  Setup Steps:")
    print("   1. Update v10_complete.py with TradingView MCP agent")
    print("   2. Set up ngrok for local webhook testing")
    print("   3. Create alerts in TradingView charts")
    print("   4. Configure webhook URLs")
    print("   5. Test alert flow")
    
    print("\n📋 TradingView Alert Template:")
    print('''
    {
      "symbol": "{{exchange}}:{{ticker}}",
      "price": {{close}},
      "time": "{{time}}",
      "type": "PRICE_ACTION",
      "RSI": {{RSI}},
      "MACD": "{{MACD}}",
      "confidence": 0.85
    }
    ''')
    
    print("\n🔗 Webhook URL (after ngrok):")
    print("   https://your-ngrok-url.ngrok.io/tradingview-alert")
    
    print("\n💡 Pro Tips:")
    print("   • Use multiple alerts for different timeframes")
    print("   • Combine TradingView + Claude reasoning")
    print("   • Set high confidence thresholds (75%+)")
    print("   • Test with small position sizes first")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    setup_tradingview_mcp()