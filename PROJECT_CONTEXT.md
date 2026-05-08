# FOREX TRADING SYSTEM — Full Project Context
**Owner:** Lovinder (cmalovinder@gmail.com)  
**Goal:** Autonomous self-learning forex + crypto + gold trading system. 6 months paper trading proof → go live.

---

## Current Status
- Active version: **V14 Army of Agents**
- Win Rate: ~80%
- Mode: Paper trading (OANDA demo)
- RL episodes: growing every cycle
- Account: `101-001-39217670-001` (OANDA practice)

---

## Rules — NEVER Break These
- ALWAYS use `py -3.11` — never `python` or `python3`
- NEVER use `pandas-ta` (broken on Python 3.11)
- Practice endpoint: `api-fxpractice.oanda.com`
- `.env` file holds all API keys — never touch it directly
- OANDA instrument format uses underscore: `EUR_USD` not `EURUSD`

---

## How To Run
```
py -3.11 v14_army.py              # continuous 60-second cycles
py -3.11 v14_army.py --once       # single cycle (GitHub Actions)
py -3.11 v12_complete_intelligence.py  # V12 fallback
```
Dashboard: http://localhost:5001 (V14) | http://localhost:5000 (V12)

---

## Trading Pairs (7 total)
| Pair | Type | Notes |
|------|------|-------|
| EUR_USD | Forex | Inversely correlated with DXY |
| GBP_USD | Forex | Inversely correlated with DXY |
| USD_JPY | Forex | Safe haven, moves with VIX |
| AUD_USD | Forex | Risk-on pair |
| USD_CAD | Forex | Risk-off pair |
| XAU_USD | Gold CFD | Safe haven, VIX correlated |
| BTC_USD | Crypto CFD | Risk-on, low-VIX correlated |

---

## Version History
| Version | File | Key Feature |
|---------|------|-------------|
| V1–V8 | various | Early experiments |
| V9 | v9_precision.py | Precision signals |
| V10 | v10_complete.py | Professional dashboard |
| V12 | v12_complete_intelligence.py | 42 agents, full intelligence stack |
| V13 | v13_production.py | Production-ready, 17 agents |
| **V14** | **v14_army.py** | **36 parallel agents, ~200ms decisions** |

---

## V14 Architecture — 36 Agents

### V13 Agents (17, imported from v13_production.py)
EMAAgent, MACDAgent, RSIAgent, BollingerAgent, WyckoffAgent, ATRAgent, StochasticAgent, SessionAgent, BreakoutAgent, BOSAgent, CHOCHAgent, OrderBlockAgent, FVGAgent, KillzoneAgent, OTEAgent, SilverBulletAgent, LiquidityAgent

### V14 Agents (19, built into v14_army.py)
| Agent | What It Does |
|-------|-------------|
| MomentumAgent | Rate of Change — detects acceleration |
| VWAPAgent | Volume Weighted Average Price — institutional fair value |
| FibonacciAgent | Fib retracement 23.6/38.2/50/61.8/78.6 levels |
| DivergenceAgent | RSI/Price divergence — early reversal |
| PivotPointAgent | Daily pivot points S1/R1/S2/R2 |
| MarketStructureAgent | Higher highs/lower lows pure structure |
| HeikinAshiAgent | Smoothed candle trend detection |
| IchimokuAgent | Ichimoku cloud — Japanese trend system |
| SupertrendAgent | ATR-based dynamic trend direction |
| DXYAgent | Dollar index momentum → all USD pairs (skips XAU/BTC) |
| DXYInverseCorrelAgent | DXY inverse → specifically EUR/USD and GBP/USD |
| GoldCorrelAgent | Gold % change → risk-on/risk-off signal |
| VIXAgent | VIX fear gauge → XAU safe haven + BTC risk-on |
| PriceActionAgent | Pin bars, engulfing candles |
| AdaptiveEMAAgent | Self-tuning EMA period based on volatility |
| SessionVolumeAgent | London/NY power hour volume spikes |
| NewsFlowAgent | NewsAPI sentiment (BTC/XAU use targeted search terms) |
| MultiTimeframeConfluenceAgent | M15 + H1 + H4 alignment check |
| ConsensusMetaAgent | Final quality filter — momentum + volatility |

### Execution Logic
- All 36 agents run **simultaneously** via `ThreadPoolExecutor(max_workers=36)`
- Decision in ~200ms
- Signal fires only if: `confidence >= 0.60` AND `≥35% of active agents agree`
- Agent weights self-update via `AgentWeights` (V13 infrastructure)

---

## Instrument-Specific Trade Sizing
| Instrument | Pip Size | Min Units | Max Units |
|------------|----------|-----------|-----------|
| EUR/GBP/AUD/CAD pairs | 0.0001 | 1,000 | 50,000 |
| USD_JPY | 0.01 | 1,000 | 50,000 |
| XAU_USD | 0.01 | 1 oz | 50 oz |
| BTC_USD | 1.0 | 1 | 3 BTC |

Risk per trade: **0.5% of account balance**

---

## 5 Self-Learning Layers
1. **FinMem** — every trade saved to `v12_memory.json`
2. **AgentWeights** — per-agent performance weights in `v14_weights.json`
3. **RLAgent** — reinforcement learning episodes in `v14_rl.json`
4. **MarketRegime** — classifies TRENDING / RANGING / VOLATILE
5. **HiveMind** — rewrites agent logic every 5 days

---

## Intelligence Data Sources
| Source | What |
|--------|------|
| OANDA API | Live price bars (M15, H1, H4) |
| yfinance | DXY (DX-Y.NYB), Gold (GC=F), VIX (^VIX) |
| NewsAPI | News sentiment per pair |
| Forex Factory | Economic calendar — avoids high-impact events |
| CFTC COT | Chicago commitment of traders data |
| FRED | Macro economic data |
| Yahoo Finance | DXY, Gold, VIX correlations |

---

## Key Files
| File | Purpose |
|------|---------|
| `v14_army.py` | **MAIN — run this** |
| `v13_production.py` | V13 agents + infrastructure (imported by V14) |
| `v12_complete_intelligence.py` | V12 fallback system |
| `v14_weights.json` | Agent performance weights |
| `v14_rl.json` | RL learning episodes |
| `v14_trades_local.json` | Local trade log (when Supabase offline) |
| `v14_system.log` | Full system log |
| `.env` | All API keys (never edit directly) |

---

## Infrastructure
- **Broker:** OANDA (demo) — `oandapyV20` library
- **Database:** Supabase — table `v14_trades`
- **Notifications:** Telegram bot `@forexlovinder_bot`
- **Dashboard:** Flask on port 5001
- **Webhooks:** TradingView via ngrok tunnel
- **Secondary broker:** IC Markets (demo, for redundancy)

---

## DXY Knowledge Layer (added V14)
DXY (US Dollar Index) is **inversely correlated** with EUR/USD and GBP/USD:
- DXY rising → USD strengthening → EUR/USD falls, GBP/USD falls
- DXY falling → USD weakening → EUR/USD rises, GBP/USD rises

Two agents encode this:
- `DXYAgent` — general USD momentum for all forex pairs
- `DXYInverseCorrelAgent` — dedicated inverse signal for EUR/USD + GBP/USD only

Both fetch `DX-Y.NYB` via yfinance, cached 30–60 min to avoid rate limits.

---

## Environment Variables (in .env)
```
OANDA_TOKEN=
OANDA_ACCOUNT_ID=101-001-39217670-001
TELEGRAM_TOKEN=
TELEGRAM_CHAT=
NEWS_KEY=
FRED_KEY=
SUPABASE_URL=
SUPABASE_KEY=
```

---

## Next Milestones
1. 6 months consistent paper profit → apply to go live
2. Add outcome-based weight updates to AgentWeights (currently logs only)
3. BTCVolatilityAgent — scale down confidence when BTC 24h ATR is extreme
4. GoldMomentumAgent — dedicated RSI+breakout agent for XAU_USD bars
5. Verify OANDA practice account supports BTC_USD and XAU_USD instruments
