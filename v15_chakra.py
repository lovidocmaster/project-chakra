"""
PROJECT CHAKRA V15 — INSTITUTIONAL GRADE
Features: TSMOMAgent, Auto-Execute, Smart Telegram, Explained Dashboard
Run: python v15_chakra.py
"""
import os, json, logging, time, math, threading, requests
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from collections import deque
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, render_template_string
from v13_production import (
    OandaAPI, InstrumentsCandles, OrderCreate, OpenTrades,
    PAIRS, BarData, Signal, Agent,
    EMAAgent, MACDAgent, RSIAgent, BollingerAgent, ATRAgent,
    StochasticAgent, BreakoutAgent, BOSAgent, CHOCHAgent,
    WyckoffAgent, SessionAgent, KillzoneAgent, OrderBlockAgent,
    FVGAgent, LiquidityAgent,
    FinMem, AgentWeights, RLAgent, RegimeDetector, HiveMind,
    NewsIntelligence, FREDMacro,
    OANDA_TOKEN, OANDA_ENV, OANDA_ACCOUNT,
    TELEGRAM_TOKEN, TELEGRAM_CHAT,
    MEM_FILE, WTS_FILE, RL_FILE,
    V13Orchestrator, log
)
import numpy as np

# ── CONFIG ──────────────────────────────────────────────────────────
CONFIDENCE_BASE = 0.60
AUTO_EXECUTE    = True          # LIVE EXECUTION ON OANDA
RISK_PCT        = 0.005
MAX_DD          = 0.02
CYCLE_SECS      = 60
PORT            = 5001
RAILWAY_URL     = os.getenv("RAILWAY_URL", "https://project-chakra-production.up.railway.app")
NEWS_KEY        = os.getenv("NEWS_KEY", "")
ALPHA_KEY       = os.getenv("ALPHA_VANTAGE", "")

# ── TSMOM AGENT — Time Series Momentum (Moskowitz et al. 2012) ──────
class TSMOMAgent(Agent):
    """
    Institutional momentum agent based on AQR/Chicago Booth research.
    Checks 1-month, 3-month and 12-month return direction.
    If majority positive → BUY. If majority negative → SELL.
    """
    def __init__(self): super().__init__("TSMOM")

    def analyze(self, bars):
        if len(bars) < 260: return Signal("HOLD", 0.0, "Need 260 bars for TSMOM", self.name)

        closes = np.array([b.close for b in bars])
        now    = closes[-1]

        # Returns over 1m (21 bars), 3m (63 bars), 12m (252 bars)
        r1m  = (now - closes[-21])  / closes[-21]
        r3m  = (now - closes[-63])  / closes[-63]
        r12m = (now - closes[-252]) / closes[-252]

        # Volatility scaling (annualised, 60-day EWMA)
        daily_rets = np.diff(closes[-61:]) / closes[-61:-1]
        vol = np.std(daily_rets) * math.sqrt(252) if len(daily_rets) > 5 else 0.1
        if vol == 0: vol = 0.1

        # Score: +1 if positive, -1 if negative, weighted by recency
        score = (np.sign(r1m) * 0.5 + np.sign(r3m) * 0.3 + np.sign(r12m) * 0.2)
        conf  = min(0.95, abs(score) * 0.75 + 0.20)

        reason = (f"1m:{r1m*100:+.2f}% 3m:{r3m*100:+.2f}% "
                  f"12m:{r12m*100:+.2f}% vol:{vol*100:.1f}%")

        if score > 0:   return Signal("BUY",  conf, f"TSMOM BULL | {reason}", self.name)
        elif score < 0: return Signal("SELL", conf, f"TSMOM BEAR | {reason}", self.name)
        return Signal("HOLD", 0.0, f"TSMOM NEUTRAL | {reason}", self.name)


# ── ALL AGENTS ───────────────────────────────────────────────────────
ALL_AGENTS = [
    EMAAgent, MACDAgent, RSIAgent, BollingerAgent, ATRAgent,
    StochasticAgent, BreakoutAgent, BOSAgent, CHOCHAgent,
    WyckoffAgent, SessionAgent, KillzoneAgent, OrderBlockAgent,
    FVGAgent, LiquidityAgent, TSMOMAgent,
]

# ── HELPERS ──────────────────────────────────────────────────────────
def fetch_bars(pair, granularity="H1", count=300):
    try:
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        params = {"count": count, "granularity": granularity, "price": "M"}
        r = InstrumentsCandles(instrument=pair, params=params)
        client.request(r)
        bars = []
        for c in r.response.get("candles", []):
            if not c.get("complete"): continue
            m = c.get("mid", {})
            bars.append(BarData(
                timestamp=c.get("time",""),
                open=float(m.get("o",0)), high=float(m.get("h",0)),
                low=float(m.get("l",0)),  close=float(m.get("c",0)),
                volume=float(c.get("volume",0))
            ))
        return bars
    except Exception as e:
        log.warning(f"fetch_bars {pair} {granularity}: {e}")
        return []

def get_atr(bars, period=14):
    if len(bars) < period+1: return 0.001
    trs = []
    for i in range(1, period+1):
        h, l, pc = bars[-i].high, bars[-i].low, bars[-i-1].close
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs)

def get_balance():
    try:
        from v13_production import AccountDetails
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        r = AccountDetails(accountID=OANDA_ACCOUNT)
        client.request(r)
        return float(r.response["account"]["balance"])
    except:
        return 100000.0

def get_news_headlines(pair):
    """Fetch real news for the pair currencies"""
    try:
        currencies = pair.replace("_", " ").replace("XAU", "Gold").replace("BTC", "Bitcoin")
        url = (f"https://newsapi.org/v2/everything?q={currencies}+forex&"
               f"sortBy=publishedAt&pageSize=3&apiKey={NEWS_KEY}")
        resp = requests.get(url, timeout=5)
        articles = resp.json().get("articles", [])
        headlines = [a["title"] for a in articles[:3] if a.get("title")]
        return headlines if headlines else ["No recent headlines found"]
    except:
        return ["News API unavailable"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=5)
    except Exception as e:
        log.warning(f"Telegram: {e}")

def execute_trade(pair, direction, bars, balance):
    """Execute real trade on OANDA with proper SL/TP"""
    try:
        price = bars[-1].close
        atr   = get_atr(bars)
        risk  = balance * RISK_PCT          # e.g. $500 on $100k
        sl_distance = atr * 1.5            # in price units

        # Pip value calculation (safe for all pairs)
        # Risk / SL_distance gives units in base currency terms
        # Cap at 50,000 units max for safety
        if sl_distance > 0:
            units = int(risk / sl_distance)
        else:
            units = 1000
        units = min(units, 50000)          # safety cap
        units = max(units, 100)            # minimum trade size
        if direction == "SELL": units = -units

        sl_price = price - atr*1.5 if direction=="BUY" else price + atr*1.5
        tp_price = price + atr*4.5 if direction=="BUY" else price - atr*4.5

        data = {
            "order": {
                "type": "MARKET",
                "instrument": pair,
                "units": str(units),
                "stopLossOnFill":   {"price": f"{sl_price:.5f}"},
                "takeProfitOnFill": {"price": f"{tp_price:.5f}"},
                "timeInForce": "FOK"
            }
        }
        client = OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
        r = OrderCreate(accountID=OANDA_ACCOUNT, data=data)
        client.request(r)
        log.info(f"[EXECUTED] {pair} {direction} units={units} "
                 f"SL={sl_price:.5f} TP={tp_price:.5f}")
        return True, price, sl_price, tp_price, units
    except Exception as e:
        log.error(f"[EXECUTE ERROR] {pair}: {e}")
        return False, 0, 0, 0, 0

# ── MAIN ORCHESTRATOR ────────────────────────────────────────────────
class ChakraV15:
    def __init__(self):
        self.cycle       = 0
        self.results     = {}
        agent_names      = [ag().name for ag in ALL_AGENTS]
        self.mem         = FinMem()
        self.weights     = AgentWeights(agent_names)
        self.rl          = RLAgent()
        self.regime_det  = RegimeDetector()
        self.hivemind    = HiveMind(self.mem, self.weights)
        self.news_intel  = NewsIntelligence()
        self.lock        = threading.Lock()
        log.info(f"[Dashboard] {RAILWAY_URL}")
        log.info(f"PROJECT CHAKRA V15 - LIVE | AUTO_EXECUTE={AUTO_EXECUTE}")
        log.info(f"   Pairs: {PAIRS}")

    def analyze_pair(self, pair):
        try:
            # Fetch multiple timeframes
            bars_m15 = fetch_bars(pair, "M15", 200)
            bars_h1  = fetch_bars(pair, "H1",  300)
            bars_h4  = fetch_bars(pair, "H4",  300)

            if not bars_h1 or len(bars_h1) < 50:
                return None

            price = bars_h1[-1].close
            atr   = get_atr(bars_h1)
            regime = self.regime_det.detect(bars_h1) if bars_h1 else "UNKNOWN"

            # H4 trend direction
            h4_trend = "NEUTRAL"
            h4_reason = ""
            if bars_h4 and len(bars_h4) >= 50:
                c = np.array([b.close for b in bars_h4])
                e20 = np.mean(c[-20:])
                e50 = np.mean(c[-50:])
                if c[-1] > e20 > e50:
                    h4_trend = "BULLISH"
                    h4_reason = f"Price>{e20:.5f}>EMA50"
                elif c[-1] < e20 < e50:
                    h4_trend = "BEARISH"
                    h4_reason = f"Price<{e20:.5f}<EMA50"
                else:
                    h4_trend = "RANGING"
                    h4_reason = f"EMA20={e20:.5f} EMA50={e50:.5f}"

            # Run all agents
            buy_votes = sell_votes = hold_votes = 0
            buy_conf = sell_conf = 0.0
            agent_opinions = []

            for AgentClass in ALL_AGENTS:
                try:
                    ag = AgentClass()
                    sig = ag.analyze(bars_h1)
                    if sig is None: continue
                    w = self.weights.get(ag.name)
                    if sig.direction == "BUY":
                        buy_votes += 1; buy_conf += sig.confidence * w
                    elif sig.direction == "SELL":
                        sell_votes += 1; sell_conf += sig.confidence * w
                    else:
                        hold_votes += 1
                    agent_opinions.append({
                        "agent": ag.name,
                        "signal": sig.direction,
                        "confidence": round(sig.confidence, 2),
                        "reason": sig.reason
                    })
                except:
                    hold_votes += 1

            total = buy_votes + sell_votes + hold_votes
            active = buy_votes + sell_votes

            # Determine final signal
            direction = "HOLD"
            final_conf = 0.0
            conflict = ""

            if active >= 3:
                if buy_votes > sell_votes:
                    # Normalize: divide by weight (3.0) to keep 0-1 range
                    raw_conf = buy_conf / max(buy_votes, 1)
                    final_conf = min(0.99, raw_conf / 3.0)
                    if final_conf >= CONFIDENCE_BASE:
                        direction = "BUY"
                        if h4_trend == "BEARISH":
                            conflict = "⚠️ H4 trend is BEARISH — counter-trend trade"
                elif sell_votes > buy_votes:
                    raw_conf = sell_conf / max(sell_votes, 1)
                    final_conf = min(0.99, raw_conf / 3.0)
                    if final_conf >= CONFIDENCE_BASE:
                        direction = "SELL"
                        if h4_trend == "BULLISH":
                            conflict = "⚠️ H4 trend is BULLISH — counter-trend trade"

            # H4 alignment check
            h4_aligned = (
                (direction == "BUY"  and h4_trend == "BULLISH") or
                (direction == "SELL" and h4_trend == "BEARISH") or
                direction == "HOLD"
            )

            # SL/TP levels
            sl = tp = 0.0
            if direction == "BUY":
                sl = price - atr * 1.5
                tp = price + atr * 4.5
            elif direction == "SELL":
                sl = price + atr * 1.5
                tp = price - atr * 4.5

            # News headlines
            headlines = get_news_headlines(pair)

            # Build explanation in plain English
            explanation = self._explain(
                pair, direction, final_conf, buy_votes, sell_votes,
                h4_trend, h4_reason, conflict, agent_opinions, headlines,
                price, sl, tp, atr
            )

            return {
                "pair": pair,
                "price": round(price, 5),
                "direction": direction,
                "confidence": round(final_conf * 100, 1),
                "regime": regime,
                "h4_trend": h4_trend,
                "h4_reason": h4_reason,
                "h4_aligned": h4_aligned,
                "conflict": conflict,
                "buy_votes": buy_votes,
                "sell_votes": sell_votes,
                "hold_votes": hold_votes,
                "sl": round(sl, 5),
                "tp": round(tp, 5),
                "atr": round(atr, 5),
                "rr": "3:1",
                "agent_opinions": agent_opinions,
                "headlines": headlines,
                "explanation": explanation,
                "bars_m15": [[b.timestamp, b.open, b.high, b.low, b.close] for b in bars_m15[-50:]],
                "bars_h1":  [[b.timestamp, b.open, b.high, b.low, b.close] for b in bars_h1[-50:]],
                "bars_h4":  [[b.timestamp, b.open, b.high, b.low, b.close] for b in bars_h4[-50:]],
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            }
        except Exception as e:
            log.error(f"analyze_pair {pair}: {e}")
            return None

    def _explain(self, pair, direction, conf, buy_v, sell_v,
                 h4_trend, h4_reason, conflict, opinions, headlines,
                 price, sl, tp, atr):
        """Generate plain English explanation for every signal"""
        base = pair.replace("_", "/")
        lines = []

        if direction == "HOLD":
            lines.append(f"📊 {base} — NO TRADE SIGNAL")
            lines.append(f"Agents are split: {buy_v} bullish, {sell_v} bearish.")
            lines.append("Not enough agreement to enter a position.")
        else:
            emoji = "🟢" if direction == "BUY" else "🔴"
            lines.append(f"{emoji} {base} — {direction} SIGNAL ({conf*100:.1f}% confidence)")
            lines.append(f"Current price: {price:.5f}")
            lines.append(f"Stop Loss: {sl:.5f} | Take Profit: {tp:.5f} | RR: 3:1")
            lines.append(f"ATR: {atr:.5f} (market volatility measure)")
            lines.append("")
            lines.append(f"📈 H4 Trend: {h4_trend} — {h4_reason}")

            if conflict:
                lines.append(conflict)
            else:
                lines.append("✅ Signal aligns with H4 trend direction")

            lines.append("")
            lines.append(f"🤖 Agent votes: {buy_v} BUY | {sell_v} SELL")

            # Top 3 agent reasons
            relevant = [o for o in opinions if o["signal"] == direction][:3]
            if relevant:
                lines.append("Top agent reasons:")
                for o in relevant:
                    lines.append(f"  • {o['agent']}: {o['reason']}")

        # News context
        lines.append("")
        lines.append("📰 Latest news context:")
        for h in headlines[:2]:
            lines.append(f"  • {h[:80]}")

        return "\n".join(lines)

    def run_cycle(self):
        self.cycle += 1
        log.info(f"\n{'='*55}\n CYCLE {self.cycle} - "
                 f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n{'='*55}")

        balance = get_balance()
        new_results = {}

        for pair in PAIRS:
            result = self.analyze_pair(pair)
            if not result:
                continue

            new_results[pair] = result
            direction = result["direction"]
            conf      = result["confidence"]

            log.info(f"  {pair:<10} {direction:<5} conf={conf:.1f}% "
                     f"H4:{result['h4_trend']} "
                     f"votes:{result['buy_votes']}B/{result['sell_votes']}S")

            # AUTO EXECUTE
            if AUTO_EXECUTE and direction in ("BUY", "SELL"):
                if result["h4_aligned"] and not result["conflict"]:
                    ok, price, sl, tp, units = execute_trade(
                        pair, direction, 
                        [BarData(**dict(zip(
                            ['timestamp','open','high','low','close','volume'],
                            [b[0],b[1],b[2],b[3],b[4],0]
                        ))) for b in result["bars_h1"]],
                        balance
                    )
                    if ok:
                        msg = (
                            f"🚀 <b>CHAKRA TRADE EXECUTED</b>\n\n"
                            f"Pair: <b>{pair}</b>\n"
                            f"Direction: <b>{direction}</b>\n"
                            f"Price: {price:.5f}\n"
                            f"Stop Loss: {sl:.5f}\n"
                            f"Take Profit: {tp:.5f}\n"
                            f"Units: {units}\n"
                            f"Risk: {balance*0.005:.2f} USD\n\n"
                            f"Reason:\n{result['explanation']}\n\n"
                            f"📊 Dashboard: {RAILWAY_URL}"
                        )
                        send_telegram(msg)
                else:
                    if result["conflict"]:
                        log.info(f"  ⚠️ {pair} skipped — {result['conflict']}")

            elif direction in ("BUY", "SELL"):
                # Send alert even without execution
                msg = (
                    f"⚡ <b>CHAKRA SIGNAL</b>\n\n"
                    f"Pair: <b>{pair}</b>\n"
                    f"Signal: <b>{direction}</b> ({conf:.1f}%)\n"
                    f"H4 Trend: {result['h4_trend']}\n"
                    f"Entry: {result['price']:.5f}\n"
                    f"SL: {result['sl']:.5f} | TP: {result['tp']:.5f}\n\n"
                    f"{result['explanation']}\n\n"
                    f"📊 Dashboard: {RAILWAY_URL}"
                )
                send_telegram(msg)

        with self.lock:
            self.results = new_results

    def run(self):
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                log.error(f"Cycle error: {e}")
            time.sleep(CYCLE_SECS)


# ── FLASK DASHBOARD ──────────────────────────────────────────────────
app = Flask(__name__)
chakra = None

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Project Chakra V15</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#050510; color:#e0e0ff; font-family:'Courier New',monospace; }
.header { background:linear-gradient(135deg,#0a0a2e,#1a0a3e);
          padding:16px 24px; border-bottom:1px solid #2a2a6e;
          display:flex; align-items:center; justify-content:space-between; }
.logo { font-size:1.4em; font-weight:bold; color:#7b5cff; letter-spacing:2px; }
.stats { display:flex; gap:24px; }
.stat { text-align:center; }
.stat-val { font-size:1.4em; font-weight:bold; color:#00f5ff; }
.stat-lbl { font-size:0.7em; color:#888; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
        gap:16px; padding:16px; }
.card { background:#0a0a1e; border:1px solid #1a1a4e; border-radius:12px;
        padding:16px; transition:border-color 0.3s; }
.card:hover { border-color:#7b5cff; }
.card-header { display:flex; justify-content:space-between; align-items:center;
               margin-bottom:12px; }
.pair { font-size:1.2em; font-weight:bold; color:#fff; }
.signal-buy  { color:#00ff88; font-weight:bold; font-size:1.1em; }
.signal-sell { color:#ff4466; font-weight:bold; font-size:1.1em; }
.signal-hold { color:#888888; }
.price { font-size:1.4em; font-weight:bold; color:#00f5ff; margin:8px 0; }
.levels { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin:8px 0; }
.level { background:#0f0f2e; border-radius:6px; padding:6px; text-align:center; }
.level-lbl { font-size:0.65em; color:#888; }
.level-val { font-size:0.85em; font-weight:bold; }
.sl-val { color:#ff4466; }
.tp-val { color:#00ff88; }
.entry-val { color:#00f5ff; }
.trend { padding:4px 8px; border-radius:4px; font-size:0.8em; font-weight:bold; }
.trend-bull { background:#003322; color:#00ff88; }
.trend-bear { background:#330011; color:#ff4466; }
.trend-neutral { background:#1a1a2e; color:#888; }
.conflict { background:#2a1500; border:1px solid #ff8800;
            border-radius:6px; padding:6px; font-size:0.75em;
            color:#ff8800; margin:8px 0; }
.votes { display:flex; gap:8px; margin:8px 0; font-size:0.8em; }
.vote-b { color:#00ff88; } .vote-s { color:#ff4466; } .vote-h { color:#888; }
.conf-bar { background:#0f0f2e; border-radius:4px; height:6px; margin:4px 0; }
.conf-fill { height:100%; border-radius:4px;
             background:linear-gradient(90deg,#7b5cff,#00f5ff); }
.tabs { display:flex; gap:4px; margin:8px 0; }
.tab { padding:4px 10px; border-radius:4px; cursor:pointer; font-size:0.75em;
       border:1px solid #2a2a6e; color:#888; background:#050510; }
.tab.active { background:#1a1a4e; color:#00f5ff; border-color:#7b5cff; }
.chart-wrap { height:140px; position:relative; margin:8px 0; }
.explain { background:#05051a; border-radius:6px; padding:8px;
           font-size:0.72em; line-height:1.6; color:#aaa;
           max-height:120px; overflow-y:auto; margin:8px 0;
           border:1px solid #1a1a3e; white-space:pre-wrap; }
.news { margin-top:8px; }
.news-item { font-size:0.7em; color:#888; padding:3px 0;
             border-bottom:1px solid #1a1a2e; }
.news-item::before { content:"📰 "; }
.agents-btn { background:#1a1a4e; border:1px solid #2a2a6e; color:#7b5cff;
              padding:4px 10px; border-radius:4px; cursor:pointer;
              font-size:0.75em; font-family:inherit; margin-top:6px; }
.agents-panel { display:none; max-height:200px; overflow-y:auto; margin-top:6px; }
.agent-row { display:flex; justify-content:space-between; padding:3px 0;
             border-bottom:1px solid #0f0f2e; font-size:0.7em; }
.agent-name { color:#7b5cff; width:100px; }
.agent-sig-buy  { color:#00ff88; } .agent-sig-sell { color:#ff4466; }
.agent-sig-hold { color:#555; }
.agent-reason { color:#666; flex:1; text-align:right; font-size:0.65em; }
.footer { text-align:center; padding:12px; font-size:0.7em; color:#333;
          border-top:1px solid #0a0a2e; }
.live-dot { display:inline-block; width:8px; height:8px; border-radius:50%;
            background:#00ff88; margin-right:6px;
            animation:pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
@media(max-width:600px) { .grid{grid-template-columns:1fr;} }
</style>
</head>
<body>
<div class="header">
  <div class="logo">⚡ PROJECT CHAKRA V15</div>
  <div class="stats">
    <div class="stat"><div class="stat-val" id="cycles">—</div><div class="stat-lbl">CYCLES</div></div>
    <div class="stat"><div class="stat-val" id="signals">—</div><div class="stat-lbl">SIGNALS</div></div>
    <div class="stat"><div class="stat-val" id="agents">37+ICT</div><div class="stat-lbl">AGENTS</div></div>
    <div class="stat"><div class="stat-val"><span class="live-dot"></span>LIVE</div><div class="stat-lbl">STATUS</div></div>
  </div>
</div>

<div class="grid" id="grid"></div>

<div class="footer">
  V15: TSMOMAgent · ICTChain · H4Filter · AutoExecute · SmartTelegram · 
  Last update: <span id="lastUpdate">—</span>
</div>

<script>
const charts = {};

function tfLabel(tf) { return {M15:'15min',H1:'1 Hour',H4:'4 Hour'}[tf]||tf; }

function buildCard(r) {
  const sigClass = r.direction==='BUY'?'signal-buy':r.direction==='SELL'?'signal-sell':'signal-hold';
  const trendClass = r.h4_trend==='BULLISH'?'trend-bull':r.h4_trend==='BEARISH'?'trend-bear':'trend-neutral';
  const conflict = r.conflict ? `<div class="conflict">${r.conflict}</div>` : '';

  const agentRows = (r.agent_opinions||[]).map(a =>
    `<div class="agent-row">
      <span class="agent-name">${a.agent}</span>
      <span class="agent-sig-${a.signal.toLowerCase()}">${a.signal}</span>
      <span class="agent-reason">${(a.reason||'').substring(0,40)}</span>
    </div>`
  ).join('');

  const newsItems = (r.headlines||[]).map(h =>
    `<div class="news-item">${h.substring(0,70)}</div>`
  ).join('');

  return `
  <div class="card" id="card-${r.pair}">
    <div class="card-header">
      <span class="pair">${r.pair.replace('_','/')}</span>
      <span class="${sigClass}">${r.direction}</span>
    </div>
    <div class="price">${r.price}</div>
    <div class="levels">
      <div class="level"><div class="level-lbl">STOP LOSS</div>
        <div class="level-val sl-val">${r.sl||'—'}</div></div>
      <div class="level"><div class="level-lbl">ENTRY</div>
        <div class="level-val entry-val">${r.price}</div></div>
      <div class="level"><div class="level-lbl">TAKE PROFIT</div>
        <div class="level-val tp-val">${r.tp||'—'}</div></div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;margin:8px 0;">
      <span class="trend ${trendClass}">H4: ${r.h4_trend}</span>
      <span style="font-size:0.75em;color:#666;">${r.h4_reason||''}</span>
    </div>
    ${conflict}
    <div class="conf-bar"><div class="conf-fill" style="width:${r.confidence}%"></div></div>
    <div style="font-size:0.75em;color:#888;margin:2px 0;">Confidence: ${r.confidence}% | RR: ${r.rr}</div>
    <div class="votes">
      <span class="vote-b">▲${r.buy_votes} BUY</span>
      <span class="vote-s">▼${r.sell_votes} SELL</span>
      <span class="vote-h">◆${r.hold_votes} HOLD</span>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="switchTF('${r.pair}','M15',this)">15min</div>
      <div class="tab" onclick="switchTF('${r.pair}','H1',this)">1H</div>
      <div class="tab" onclick="switchTF('${r.pair}','H4',this)">4H</div>
    </div>
    <div class="chart-wrap"><canvas id="chart-${r.pair}"></canvas></div>
    <div class="explain" id="explain-${r.pair}">${r.explanation||''}</div>
    <div class="news">${newsItems}</div>
    <button class="agents-btn" onclick="toggleAgents('${r.pair}')">🤖 Show All Agent Opinions</button>
    <div class="agents-panel" id="agents-${r.pair}">${agentRows}</div>
    <div style="font-size:0.65em;color:#333;margin-top:6px;">${r.timestamp}</div>
  </div>`;
}

function drawChart(pair, barsKey, data) {
  const canvasId = `chart-${pair}`;
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (charts[canvasId]) { charts[canvasId].destroy(); }

  const bars = data[barsKey] || data.bars_h1 || [];
  const labels = bars.map(b => b[0].substring(11,16));
  const closes = bars.map(b => b[4]);

  const color = closes[closes.length-1] >= closes[0] ? '#00ff88' : '#ff4466';

  charts[canvasId] = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data: closes,
        borderColor: color,
        borderWidth: 1.5,
        pointRadius: 0,
        fill: true,
        backgroundColor: color+'15'
      }]
    },
    options: {
      responsive:true, maintainAspectRatio:false, animation:false,
      plugins:{ legend:{display:false} },
      scales:{
        x:{ ticks:{color:'#444',font:{size:9},maxTicksLimit:6}, grid:{color:'#0f0f2e'} },
        y:{ ticks:{color:'#444',font:{size:9},maxTicksLimit:5}, grid:{color:'#0f0f2e'} }
      }
    }
  });
}

function switchTF(pair, tf, el) {
  el.closest('.card').querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  const data = window._data && window._data[pair];
  if (!data) return;
  const key = tf==='M15'?'bars_m15':tf==='H4'?'bars_h4':'bars_h1';
  drawChart(pair, key, data);
}

function toggleAgents(pair) {
  const panel = document.getElementById('agents-'+pair);
  panel.style.display = panel.style.display==='block' ? 'none' : 'block';
}

function update() {
  fetch('/api/data').then(r=>r.json()).then(data => {
    window._data = data.pairs || {};
    const pairs = Object.values(window._data);
    document.getElementById('cycles').textContent = data.cycle || '—';
    document.getElementById('signals').textContent =
      pairs.filter(p=>p.direction!=='HOLD').length;
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

    const grid = document.getElementById('grid');
    pairs.forEach(r => {
      let card = document.getElementById('card-'+r.pair);
      if (!card) {
        const div = document.createElement('div');
        div.innerHTML = buildCard(r);
        grid.appendChild(div.firstElementChild);
      } else {
        // Update key fields only
        const sigEl = card.querySelector('.'+['signal-buy','signal-sell','signal-hold'].find(c=>card.querySelector('.'+c)));
        card.querySelector('.price').textContent = r.price;
        document.getElementById('explain-'+r.pair).textContent = r.explanation||'';
      }
      drawChart(r.pair, 'bars_m15', r);
    });
  }).catch(e => console.error('API error:', e));
}

update();
setInterval(update, 30000);
</script>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/data")
def api_data():
    with chakra.lock:
        return jsonify({
            "cycle": chakra.cycle,
            "pairs": chakra.results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

@app.route("/api/pair/<pair>")
def api_pair(pair):
    with chakra.lock:
        return jsonify(chakra.results.get(pair, {}))

@app.route("/health")
def health():
    return jsonify({"status": "ok", "cycle": chakra.cycle if chakra else 0})

# ── ENTRY POINT ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    chakra = ChakraV15()

    if "--once" in sys.argv:
        chakra.run_cycle()
    else:
        t = threading.Thread(target=chakra.run, daemon=True)
        t.start()
        app.run(host="0.0.0.0", port=PORT, debug=False)
