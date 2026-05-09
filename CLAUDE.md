════════════════════════════════════════════════════════
PROJECT CHAKRA — CLAUDE.md (Updated May 2026)
════════════════════════════════════════════════════════

OWNER: Lovinder (cmalovinder@gmail.com)
PROJECT: Autonomous AI Forex Trading System
GITHUB: github.com/lovidocmaster/project-chakra
RAILWAY: project-chakra-production.up.railway.app

════════════════════════════════════════════════════════
ENVIRONMENT
════════════════════════════════════════════════════════
OS: Windows, VS Code
Python: 3.11 — ALWAYS use py -3.11
NEVER use pandas-ta (broken on 3.11)
NEVER use python or python3 — always py -3.11

════════════════════════════════════════════════════════
CURRENT SYSTEM — V15 MAX PROFIT
════════════════════════════════════════════════════════
Main file: v15_chakra.py
Run:       py -3.11 v15_chakra.py
Dashboard: project-chakra-production.up.railway.app
Deployed:  Railway (auto-deploys on git push to main)

7 TRADING PAIRS:
EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD, XAU_USD, GBP_JPY

17 AGENTS:
EMA, MACD, RSI, Bollinger, ATR, Stochastic, Breakout,
BOS, CHOCH, Wyckoff, Session, Killzone, OrderBlock,
FVG, Liquidity, VolumeAgent, TSMOMAgent

V15 FEATURES:
- Confidence threshold: 0.60
- Auto-execute: TRUE (OANDA demo)
- Risk per trade: 0.5% of balance
- SL: ATR x 1.5 | TP: ATR x 4.5 | RR: 3:1
- Trailing stop: breakeven at 1:1, lock profit at 2:1
- Session filter: London (7-12 UTC) + NY (13-18 UTC)
- Volatility circuit breaker: pauses if ATR spikes 3x
- H4 trend filter: skips counter-trend trades
- VolumeAgent: filters fake breakouts
- TSMOMAgent: 1m/3m/12m momentum (AQR paper)

AGENT STRUCTURE (v13_production.py):
- analyze(self, bars) — takes list of BarData objects
- returns Signal(direction, confidence, reason, agent_name)
- BarData: timestamp, open, high, low, close, volume
- Signal direction: "BUY" / "SELL" / "HOLD"

════════════════════════════════════════════════════════
ARCHITECTURE
════════════════════════════════════════════════════════
v15_chakra.py      — MAIN (run this)
v13_production.py  — all agents + infrastructure
v15_ict_engine.py  — ICT 4-pillar analysis
v15_walkforward.py — institutional backtest

V15 imports agents from v13_production.py
All agent changes must be in v13_production.py

════════════════════════════════════════════════════════
SELF-LEARNING (all active)
════════════════════════════════════════════════════════
FinMem:       330+ trades remembered
AgentWeights: winners get more voting power
RLAgent:      330+ episodes
RegimeDetect: TRENDING/RANGING/VOLATILE
HiveMind:     recalibrates worst agents every 5 days

════════════════════════════════════════════════════════
INFRASTRUCTURE
════════════════════════════════════════════════════════
Broker:    OANDA demo (api-fxpractice.oanda.com)
Database:  Supabase
Alerts:    Telegram @Chakra_trading_bot
Hosting:   Railway (24/7, auto-deploy from GitHub)
Branch:    main (Railway watches this)

════════════════════════════════════════════════════════
CREDENTIALS (in .env — never commit)
════════════════════════════════════════════════════════
OANDA_TOKEN, OANDA_ACCOUNT, OANDA_BASE_URL
TELEGRAM_TOKEN, TELEGRAM_CHAT
SUPABASE_URL, SUPABASE_KEY
ANTHROPIC_API_KEY
FRED_KEY, NEWS_KEY, ALPHA_VANTAGE

════════════════════════════════════════════════════════
BACKTEST RESULTS (Walk-Forward May 2026)
════════════════════════════════════════════════════════
Method: Train 700 bars → Test 100 bars → Repeat
EUR_USD: WR 31.1% | Return +100.21%
GBP_USD: WR 32.2% | Return +113.19%
USD_JPY: WR 34.2% | Return +143.08%
Overall: WR 32.5% | Avg Return +118.83%
Note: Profitable because RR ratio is 3:1
At 3:1 RR, break-even win rate is only 25%

════════════════════════════════════════════════════════
PENDING TASKS
════════════════════════════════════════════════════════
1. Forex Factory news blackout (HIGH)
2. Pyramid into winners (MEDIUM)
3. Weekly bias agent (MEDIUM)
4. Supabase logging verification (MEDIUM)
5. Live trading switch — Month 4-6 (FUTURE)

════════════════════════════════════════════════════════
KEY RULES — NEVER BREAK
════════════════════════════════════════════════════════
- ALWAYS py -3.11 (never python)
- NEVER pandas-ta
- Practice endpoint: api-fxpractice.oanda.com
- PAIRS defined in v15_chakra.py (not v13)
- Railway watches main branch (not master)
- .env never goes to GitHub
- Before writing ANY code, inspect actual function
  signatures using inspect.getsource()
════════════════════════════════════════════════════════