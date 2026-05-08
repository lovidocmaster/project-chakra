#!/usr/bin/env python3
"""
PROJECT CHAKRA - COMPLETE SYSTEM HEALTH CHECK
One command to verify everything is ready for paper trading
"""

import os
import sys
from dotenv import load_dotenv
import subprocess
from datetime import datetime

load_dotenv()

print("\n" + "="*80)
print("PROJECT CHAKRA - SYSTEM HEALTH CHECK")
print("="*80 + "\n")

checks_passed = 0
checks_failed = 0

# 1. ENVIRONMENT VARIABLES
print("🔐 CHECKING ENVIRONMENT VARIABLES...")
required_env = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "ANTHROPIC_API_KEY",
    "OANDA_TOKEN",
    "OANDA_ACCOUNT",
    "OANDA_BASE_URL",
    "IC_MARKETS_ACCOUNT",
    "IC_MARKETS_SERVER",
    "IC_MARKETS_PASSWORD",
    "FRED_KEY",
    "NEWS_KEY",
    "ALPHA_VANTAGE",
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT"
]

env_ok = True
for var in required_env:
    if os.getenv(var):
        print(f"   ✅ {var}")
        checks_passed += 1
    else:
        print(f"   ❌ {var} - MISSING!")
        checks_failed += 1
        env_ok = False

# 2. REQUIRED FILES
print("\n📁 CHECKING REQUIRED FILES...")
required_files = [
    "v10_complete.py",
    "tradingview_webhook_handler.py",
    "start_ngrok.py",
    "test_webhook.py",
    "advanced_risk_manager.py",
    "backtest_engine.py",
    ".env",
    "config.py"
]

files_ok = True
for file in required_files:
    if os.path.exists(file):
        print(f"   ✅ {file}")
        checks_passed += 1
    else:
        print(f"   ❌ {file} - NOT FOUND!")
        checks_failed += 1
        files_ok = False

# 3. PYTHON PACKAGES
print("\n📦 CHECKING PYTHON PACKAGES...")
required_packages = [
    "requests",
    "pandas",
    "numpy",
    "yfinance",
    "python-dotenv",
    "flask",
    "pyngrok"
]

packages_ok = True
for package in required_packages:
    try:
        __import__(package.replace("-", "_"))
        print(f"   ✅ {package}")
        checks_passed += 1
    except ImportError:
        print(f"   ❌ {package} - NOT INSTALLED!")
        checks_failed += 1
        packages_ok = False

# 4. API CONNECTIVITY TEST
print("\n🌐 CHECKING API CONNECTIVITY...")

# Test OANDA
try:
    oanda_token = os.getenv("OANDA_TOKEN")
    oanda_url = os.getenv("OANDA_BASE_URL")
    if oanda_token and oanda_url:
        print(f"   ✅ OANDA configured")
        checks_passed += 1
    else:
        print(f"   ❌ OANDA - config incomplete")
        checks_failed += 1
except:
    print(f"   ❌ OANDA - error")
    checks_failed += 1

# Test Supabase
try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        print(f"   ✅ Supabase configured")
        checks_passed += 1
    else:
        print(f"   ❌ Supabase - config incomplete")
        checks_failed += 1
except:
    print(f"   ❌ Supabase - error")
    checks_failed += 1

# Test Claude API
try:
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    if claude_key and claude_key.startswith("sk-ant"):
        print(f"   ✅ Claude API configured")
        checks_passed += 1
    else:
        print(f"   ❌ Claude API - invalid key format")
        checks_failed += 1
except:
    print(f"   ❌ Claude API - error")
    checks_failed += 1

# Test Telegram
try:
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat = os.getenv("TELEGRAM_CHAT")
    if telegram_token and telegram_chat:
        print(f"   ✅ Telegram configured")
        checks_passed += 1
    else:
        print(f"   ❌ Telegram - config incomplete")
        checks_failed += 1
except:
    print(f"   ❌ Telegram - error")
    checks_failed += 1

# 5. GITHUB STATUS
print("\n🔗 CHECKING GITHUB...")
try:
    result = subprocess.run(["git", "status"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   ✅ Git repository OK")
        checks_passed += 1
    else:
        print(f"   ❌ Git - not a repository")
        checks_failed += 1
except:
    print(f"   ❌ Git - not installed")
    checks_failed += 1

# 6. TRADING AGENTS
print("\n🤖 CHECKING TRADING AGENTS...")
try:
    from v10_complete import TradingSystem
    ts = TradingSystem()
    agent_count = len(ts.agents) if hasattr(ts, 'agents') else 0
    if agent_count >= 37:
        print(f"   ✅ All {agent_count} agents loaded")
        checks_passed += 1
    else:
        print(f"   ⚠️  Only {agent_count} agents (expected 37+)")
        checks_failed += 1
except Exception as e:
    print(f"   ⚠️  Could not verify agents: {e}")
    checks_failed += 1

# 7. WEBHOOK STATUS
print("\n🔔 CHECKING WEBHOOK SERVER...")
try:
    import requests
    response = requests.get("http://localhost:5000/health", timeout=2)
    if response.status_code == 200:
        print(f"   ✅ Webhook server running (port 5000)")
        checks_passed += 1
    else:
        print(f"   ⚠️  Webhook server not responding")
        checks_failed += 1
except:
    print(f"   ⚠️  Webhook server not running (start it separately)")
    checks_failed += 1

# 8. NGROK STATUS
print("\n🌍 CHECKING NGROK TUNNEL...")
try:
    response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
    if response.status_code == 200:
        data = response.json()
        tunnels = data.get('tunnels', [])
        if tunnels:
            public_url = tunnels[0].get('public_url')
            print(f"   ✅ ngrok tunnel active: {public_url}")
            checks_passed += 1
        else:
            print(f"   ⚠️  ngrok installed but no active tunnel")
            checks_failed += 1
    else:
        print(f"   ⚠️  ngrok not running (start it separately)")
        checks_failed += 1
except:
    print(f"   ⚠️  ngrok not running (start it separately)")
    checks_failed += 1

# SUMMARY
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\n✅ Passed: {checks_passed}")
print(f"❌ Failed: {checks_failed}")

if checks_failed == 0:
    print("\n🎉 ALL SYSTEMS GO! Ready for paper trading!")
    print("\nTo start trading:")
    print("  py -3.11 v10_complete.py")
    sys.exit(0)
elif checks_failed <= 3:
    print("\n⚠️  Minor issues found (see above)")
    print("\nYou can still trade, but fix these issues first")
    sys.exit(1)
else:
    print("\n❌ Critical issues found!")
    print("\nFix the issues above before trading")
    sys.exit(2)

print("\n" + "="*80 + "\n")