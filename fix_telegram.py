"""
TELEGRAM DIAGNOSTIC + FIX
Tests your Telegram bot and finds the correct chat ID
Run: py -3.11 fix_telegram.py
"""

import os
import requests
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
CHAT  = os.getenv("TELEGRAM_CHAT",  os.getenv("TELEGRAM_CHAT_ID", ""))

print("="*50)
print("TELEGRAM DIAGNOSTIC")
print("="*50)
print(f"Token found: {'YES' if TOKEN else 'NO - check .env file'}")
print(f"Chat ID found: {'YES - ' + str(CHAT) if CHAT else 'NO - check .env file'}")

if not TOKEN:
    print("\n❌ No Telegram token found!")
    print("Add this to your .env file:")
    print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
    exit()

# Test 1: Get bot info
print("\n1. Testing bot connection...")
try:
    r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=10)
    if r.status_code == 200:
        bot = r.json()["result"]
        print(f"   ✅ Bot connected: @{bot['username']} ({bot['first_name']})")
    else:
        print(f"   ❌ Bot error: {r.text}")
        exit()
except Exception as e:
    print(f"   ❌ Connection error: {e}")
    exit()

# Test 2: Get updates to find chat ID
print("\n2. Getting chat ID from recent messages...")
try:
    r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10)
    updates = r.json().get("result", [])
    if updates:
        for upd in updates[-5:]:
            msg = upd.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            username = msg.get("chat", {}).get("username", "unknown")
            text = msg.get("text", "")
            if chat_id:
                print(f"   Found chat: ID={chat_id} User=@{username} Msg='{text}'")
        
        # Use the latest chat ID
        last_chat = updates[-1].get("message", {}).get("chat", {}).get("id")
        if last_chat:
            print(f"\n   ✅ Your Chat ID is: {last_chat}")
            CHAT = str(last_chat)
    else:
        print("   ⚠️  No recent messages found")
        print("   → Send ANY message to your bot first (@forexlovinder_bot)")
        print("   → Then run this script again")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Send test message
if CHAT:
    print(f"\n3. Sending test message to chat {CHAT}...")
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT,
                "text": "🚀 <b>Project Chakra</b>\nTelegram connection working!\n✅ Alerts are active",
                "parse_mode": "HTML"
            },
            timeout=10
        )
        if r.status_code == 200:
            print("   ✅ Message sent successfully! Check your Telegram")
        else:
            print(f"   ❌ Failed: {r.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Test 4: Update .env with correct chat ID
if CHAT and CHAT != os.getenv("TELEGRAM_CHAT", os.getenv("TELEGRAM_CHAT_ID", "")):
    print(f"\n4. Updating .env with correct chat ID: {CHAT}")
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
        
        if 'TELEGRAM_CHAT_ID' in env_content:
            import re
            env_content = re.sub(r'TELEGRAM_CHAT_ID=.*', f'TELEGRAM_CHAT_ID={CHAT}', env_content)
        else:
            env_content += f'\nTELEGRAM_CHAT_ID={CHAT}\n'
        
        with open('.env', 'w') as f:
            f.write(env_content)
        print(f"   ✅ .env updated with TELEGRAM_CHAT_ID={CHAT}")
    except Exception as e:
        print(f"   ⚠️  Could not update .env: {e}")
        print(f"   Manually add to .env: TELEGRAM_CHAT_ID={CHAT}")

print("\n" + "="*50)
print("DONE - Restart v15_chakra.py to activate alerts")
print("="*50)
