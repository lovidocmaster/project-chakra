"""
PythonAnywhere WSGI entry point — Project Chakra V13

HOW TO DEPLOY (step by step):
──────────────────────────────────────────────────────────────
1. Go to https://www.pythonanywhere.com and create a FREE account
   Username: lovidocmaster  (or whatever you choose)

2. Dashboard → Files → Upload your entire project folder
   OR use the Bash console: git clone https://github.com/lovidocmaster/project-chakra.git

3. Dashboard → Consoles → Bash
   cd project-chakra
   pip3.11 install --user -r requirements_pythonanywhere.txt

4. Dashboard → Web → Add new web app
   → Manual configuration → Python 3.11

5. In the WSGI configuration file section, click the link and
   REPLACE the entire file content with this file's content

6. In "Code" section set:
   Source code: /home/lovidocmaster/project-chakra
   Working dir: /home/lovidocmaster/project-chakra

7. In "Environment variables" section add all your keys:
   OANDA_TOKEN        = (from your .env)
   OANDA_ACCOUNT_ID   = 101-001-39217670-001
   SUPABASE_URL       = (from your .env)
   SUPABASE_KEY       = (from your .env)
   TELEGRAM_TOKEN     = (from your .env)
   TELEGRAM_CHAT      = (from your .env)
   FRED_KEY           = 0d5051e1563e45866badf276454ce1ec
   NEWS_KEY           = 00ce3b995b134bf98265358f98b9d41e

8. Click Reload

YOUR LIVE WEBHOOK URL:
   https://lovidocmaster.pythonanywhere.com/webhook/tradingview

PASTE IN TRADINGVIEW → Alert → Webhook URL:
   https://lovidocmaster.pythonanywhere.com/webhook/tradingview

TRADINGVIEW ALERT MESSAGE (copy-paste exactly):
{
  "secret": "lovinder_forex_v13",
  "pair": "{{ticker}}",
  "direction": "BUY",
  "strategy": "My Strategy",
  "timeframe": "{{interval}}",
  "price": {{close}}
}
──────────────────────────────────────────────────────────────
"""

import sys
import os

project_home = '/home/lovidocmaster/project-chakra'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_home, '.env'))
except Exception:
    pass

# Import Flask app from v13
from v13_production import app as application
