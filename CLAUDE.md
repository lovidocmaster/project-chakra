# My Forex Trading System

## Owner: Lovinder
## Current Version: V12 Complete Intelligence

## What This Is
Autonomous self-learning forex trading system.
42 AI agents analyze markets and place trades automatically.
System learns from every trade and gets smarter every day.

## Tech Stack
- Python 3.11 (ALWAYS use: py -3.11)
- OANDA demo account: 101-001-39217670-001
- Supabase database
- Telegram bot: @forexlovinder_bot
- Flask dashboard: localhost:5000

## Main File To Run
py -3.11 v12_complete_intelligence.py

## Trading Pairs
EUR_USD, GBP_USD, USD_JPY, AUD_USD, USD_CAD

## 5 Self-Learning Layers
1. FinMem - saves every trade to v12_memory.json
2. AgentWeights - saved to v12_weights.json  
3. RL Agent - saved to v12_rl.json
4. MarketRegime - TRENDING/RANGING/VOLATILE
5. HiveMind - improves agents every 5 days

## Intelligence Sources
- Forex Factory calendar
- CFTC COT Chicago data
- NewsAPI news sentiment
- FRED macro data
- Yahoo Finance correlations (DXY, Gold, VIX)

## Rules (NEVER break these)
- NEVER use python, ALWAYS use py -3.11
- NEVER use pandas-ta (broken on Python 3.11)
- Practice endpoint: api-fxpractice.oanda.com
- .env file has all API keys - never touch it directly

## Current Status
System running. WR: 80%. RL episodes growing.
Paper trading mode. Goal: 6 months proof then live.