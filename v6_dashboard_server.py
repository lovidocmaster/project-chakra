"""
V6 DASHBOARD SERVER
Beautiful web dashboard + Flask API
Run: py -3.11 v6_dashboard_server.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, request
import threading
import time
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v8_ultimate import run_system, signals_store, system_status, CONFIG, TRADING_PAIRS

app = Flask(__name__)

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V6 ULTIMATE TRADING SYSTEM</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #050510;
  --surface: #0a0a1f;
  --card: #0f0f2a;
  --border: #1a1a4a;
  --accent: #00d4ff;
  --green: #00ff88;
  --red: #ff3366;
  --gold: #ffd700;
  --purple: #8b5cf6;
  --text: #e0e0ff;
  --muted: #6060a0;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:'Inter',sans-serif; min-height:100vh; overflow-x:hidden; }

/* Background grid */
body::before {
  content:''; position:fixed; top:0; left:0; width:100%; height:100%;
  background-image: linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 50px 50px; pointer-events:none; z-index:0;
}

.container { max-width:1600px; margin:0 auto; padding:20px; position:relative; z-index:1; }

/* Header */
.header {
  display:flex; align-items:center; justify-content:space-between;
  padding:20px 30px; background:var(--surface);
  border:1px solid var(--border); border-radius:16px; margin-bottom:20px;
  box-shadow:0 0 40px rgba(0,212,255,0.1);
}
.logo { font-family:'Orbitron',monospace; font-size:22px; font-weight:900;
  background:linear-gradient(135deg,var(--accent),var(--purple));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.status-badge { display:flex; align-items:center; gap:8px; font-size:13px; }
.dot { width:10px; height:10px; border-radius:50%; animation:pulse 2s infinite; }
.dot.live { background:var(--green); box-shadow:0 0 10px var(--green); }
.dot.idle { background:var(--muted); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* Capital control */
.capital-panel {
  background:var(--card); border:1px solid var(--border); border-radius:16px;
  padding:24px; margin-bottom:20px;
  background:linear-gradient(135deg,rgba(0,212,255,0.05),rgba(139,92,246,0.05));
}
.capital-panel h2 { font-family:'Orbitron',monospace; font-size:15px; color:var(--accent); margin-bottom:16px; }
.capital-controls { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
.capital-input {
  background:var(--surface); border:1px solid var(--accent); border-radius:10px;
  padding:12px 18px; color:var(--accent); font-family:'Orbitron',monospace;
  font-size:20px; width:220px; outline:none;
}
.btn {
  padding:12px 24px; border-radius:10px; border:none; cursor:pointer;
  font-family:'Orbitron',monospace; font-size:12px; font-weight:700;
  transition:all 0.2s; letter-spacing:1px;
}
.btn-primary { background:linear-gradient(135deg,var(--accent),var(--purple)); color:#000; }
.btn-primary:hover { transform:translateY(-2px); box-shadow:0 8px 20px rgba(0,212,255,0.3); }
.btn-danger { background:linear-gradient(135deg,var(--red),#880022); color:#fff; }
.btn-success { background:linear-gradient(135deg,var(--green),#008844); color:#000; }
.btn-warning { background:linear-gradient(135deg,var(--gold),#aa8800); color:#000; }

/* Stats row */
.stats-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:20px; }
.stat-card {
  background:var(--card); border:1px solid var(--border); border-radius:14px;
  padding:20px; text-align:center; position:relative; overflow:hidden;
}
.stat-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(90deg,transparent,var(--accent),transparent);
}
.stat-value { font-family:'Orbitron',monospace; font-size:26px; font-weight:700; margin-bottom:4px; }
.stat-label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }
.stat-positive { color:var(--green); }
.stat-negative { color:var(--red); }
.stat-neutral { color:var(--accent); }
.stat-gold { color:var(--gold); }

/* Main grid */
.main-grid { display:grid; grid-template-columns:1fr 380px; gap:20px; margin-bottom:20px; }
@media(max-width:1100px) { .main-grid { grid-template-columns:1fr; } }

/* Signals panel */
.panel { background:var(--card); border:1px solid var(--border); border-radius:16px; overflow:hidden; }
.panel-header {
  padding:16px 20px; background:var(--surface);
  border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;
}
.panel-title { font-family:'Orbitron',monospace; font-size:13px; color:var(--accent); font-weight:700; }
.panel-body { padding:16px; max-height:600px; overflow-y:auto; }
.panel-body::-webkit-scrollbar { width:4px; }
.panel-body::-webkit-scrollbar-track { background:var(--surface); }
.panel-body::-webkit-scrollbar-thumb { background:var(--accent); border-radius:2px; }

/* Signal card */
.signal-card {
  background:var(--surface); border-radius:12px; padding:16px; margin-bottom:12px;
  border-left:4px solid var(--muted); transition:all 0.3s; cursor:pointer;
  animation:slideIn 0.4s ease;
}
.signal-card:hover { transform:translateX(4px); border-color:var(--accent); }
.signal-card.buy { border-left-color:var(--green); }
.signal-card.sell { border-left-color:var(--red); }
@keyframes slideIn { from{opacity:0;transform:translateX(-20px)} to{opacity:1;transform:translateX(0)} }

.signal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.signal-symbol { font-family:'Orbitron',monospace; font-size:16px; font-weight:700; }
.signal-action { padding:4px 12px; border-radius:20px; font-size:11px; font-weight:700; font-family:'Orbitron',monospace; }
.signal-action.buy { background:rgba(0,255,136,0.15); color:var(--green); border:1px solid var(--green); }
.signal-action.sell { background:rgba(255,51,102,0.15); color:var(--red); border:1px solid var(--red); }

.signal-levels { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:10px; }
.level-item { background:var(--bg); border-radius:8px; padding:8px; text-align:center; }
.level-label { font-size:9px; color:var(--muted); text-transform:uppercase; margin-bottom:2px; }
.level-value { font-family:'Share Tech Mono',monospace; font-size:12px; font-weight:600; }
.level-entry { color:var(--accent); }
.level-sl { color:var(--red); }
.level-tp { color:var(--green); }

.signal-meta { display:flex; gap:8px; flex-wrap:wrap; }
.meta-badge {
  padding:3px 10px; border-radius:20px; font-size:10px;
  background:rgba(0,212,255,0.08); border:1px solid rgba(0,212,255,0.2); color:var(--accent);
}

/* Context panel */
.context-panel { display:flex; flex-direction:column; gap:16px; }
.context-card {
  background:var(--card); border:1px solid var(--border); border-radius:14px; padding:16px;
}
.context-title { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; }
.context-value { font-family:'Orbitron',monospace; font-size:22px; font-weight:700; color:var(--accent); }
.context-sub { font-size:11px; color:var(--muted); margin-top:4px; }

/* Indicator bar */
.indicator-row { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.indicator-label { font-size:11px; color:var(--muted); width:80px; flex-shrink:0; }
.indicator-bar { flex:1; height:6px; background:var(--surface); border-radius:3px; overflow:hidden; }
.indicator-fill { height:100%; border-radius:3px; transition:width 0.5s; }
.indicator-val { font-size:11px; font-family:'Share Tech Mono',monospace; width:50px; text-align:right; }

/* Agent votes */
.votes-container { display:flex; gap:8px; margin-top:8px; }
.vote-bar { flex:1; }
.vote-label { font-size:10px; margin-bottom:4px; display:flex; justify-content:space-between; }
.vote-fill { height:8px; border-radius:4px; transition:width 0.5s; }
.vote-buy .vote-fill { background:linear-gradient(90deg,var(--green),rgba(0,255,136,0.4)); }
.vote-sell .vote-fill { background:linear-gradient(90deg,var(--red),rgba(255,51,102,0.4)); }

/* Activity log */
.activity-log { background:var(--surface); border-radius:10px; padding:12px; font-family:'Share Tech Mono',monospace; font-size:11px; max-height:200px; overflow-y:auto; }
.log-entry { padding:3px 0; border-bottom:1px solid var(--border); color:var(--muted); }
.log-entry:last-child { border-bottom:none; }
.log-time { color:var(--accent); }
.log-buy { color:var(--green); }
.log-sell { color:var(--red); }

/* Live prices */
.prices-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; }
.price-card {
  background:var(--surface); border-radius:10px; padding:10px;
  border:1px solid var(--border); text-align:center;
}
.price-symbol { font-family:'Orbitron',monospace; font-size:11px; color:var(--muted); margin-bottom:4px; }
.price-value { font-family:'Share Tech Mono',monospace; font-size:14px; color:var(--text); }
.price-change { font-size:10px; margin-top:2px; }

/* Chart area */
.chart-container { background:var(--surface); border-radius:12px; padding:12px; margin-top:8px; text-align:center; }
.chart-img { max-width:100%; border-radius:8px; }

/* Controls */
.controls-row { display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }

/* Notification */
.notification {
  position:fixed; top:20px; right:20px; padding:14px 20px;
  border-radius:12px; font-size:13px; z-index:9999;
  animation:notifIn 0.4s ease; max-width:300px;
  box-shadow:0 8px 24px rgba(0,0,0,0.5);
}
.notification.success { background:rgba(0,255,136,0.15); border:1px solid var(--green); color:var(--green); }
.notification.error { background:rgba(255,51,102,0.15); border:1px solid var(--red); color:var(--red); }
@keyframes notifIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }

/* Modal */
.modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:1000; }
.modal.open { display:flex; align-items:center; justify-content:center; }
.modal-content {
  background:var(--card); border:1px solid var(--accent); border-radius:20px;
  padding:30px; max-width:700px; width:90%; max-height:80vh; overflow-y:auto;
}
.modal-title { font-family:'Orbitron',monospace; font-size:18px; color:var(--accent); margin-bottom:20px; }
.reason-list { list-style:none; }
.reason-item { padding:8px 12px; border-radius:8px; margin-bottom:6px; font-size:12px; background:var(--surface); }

/* Timer */
.timer-display { font-family:'Orbitron',monospace; font-size:13px; color:var(--gold); }
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div>
      <div class="logo">V6 ULTIMATE TRADING</div>
      <div style="font-size:11px;color:var(--muted);margin-top:4px;">SMC + ICT + Wyckoff + ML + LLM | 57 Agents</div>
    </div>
    <div style="display:flex;align-items:center;gap:20px">
      <div class="timer-display">Next scan: <span id="timer">--:--</span></div>
      <div class="status-badge">
        <div class="dot live" id="status-dot"></div>
        <span id="status-text">LIVE</span>
      </div>
    </div>
  </div>

  <!-- Capital Control Panel -->
  <div class="capital-panel">
    <h2>⚡ TRADING CONTROL CENTER</h2>
    <div class="capital-controls">
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:6px;">CAPITAL ($)</div>
        <input type="number" id="capital-input" class="capital-input" value="10000" min="100" step="100">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:6px;">RISK PER TRADE</div>
        <select id="risk-select" style="background:var(--surface);border:1px solid var(--accent);border-radius:10px;padding:12px;color:var(--accent);font-size:14px;">
          <option value="0.005">0.5% Conservative</option>
          <option value="0.01" selected>1% Standard</option>
          <option value="0.02">2% Aggressive</option>
          <option value="0.03">3% High Risk</option>
        </select>
      </div>
      <div style="display:flex;gap:10px;align-items:flex-end;">
        <button class="btn btn-primary" onclick="runAnalysis()">🔍 SCAN MARKETS</button>
        <button class="btn btn-success" onclick="startAuto()">▶ AUTO (5min)</button>
        <button class="btn btn-danger" onclick="stopAuto()">⏹ STOP</button>
        <button class="btn btn-warning" onclick="showPerformance()">📊 STATS</button>
      </div>
    </div>
  </div>

  <!-- Stats Row -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-value stat-neutral" id="stat-capital">$10,000</div>
      <div class="stat-label">Portfolio Value</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="stat-pnl" style="color:var(--gold)">$0.00</div>
      <div class="stat-label">Total P&L</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-neutral" id="stat-signals">0</div>
      <div class="stat-label">Signals Today</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-positive" id="stat-winrate">--%</div>
      <div class="stat-label">Win Rate</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-neutral" id="stat-agents">57</div>
      <div class="stat-label">Active Agents</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-negative" id="stat-dd">0.0%</div>
      <div class="stat-label">Drawdown</div>
    </div>
  </div>

  <!-- Main Grid -->
  <div class="main-grid">

    <!-- Signals -->
    <div>
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">📡 LIVE SIGNALS</div>
          <div style="font-size:11px;color:var(--muted)" id="last-update">Never updated</div>
        </div>
        <div class="panel-body" id="signals-container">
          <div style="text-align:center;color:var(--muted);padding:40px;font-size:13px">
            <div style="font-size:40px;margin-bottom:12px">🔍</div>
            Click "SCAN MARKETS" to analyze all pairs
          </div>
        </div>
      </div>

      <!-- Activity Log -->
      <div class="panel" style="margin-top:16px">
        <div class="panel-header">
          <div class="panel-title">📋 ACTIVITY LOG</div>
        </div>
        <div class="panel-body" style="padding:12px">
          <div class="activity-log" id="activity-log">
            <div class="log-entry"><span class="log-time">[SYSTEM]</span> V6 Ultimate initialized — 57 agents ready</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Panel -->
    <div class="context-panel">

      <!-- Market Context -->
      <div class="context-card">
        <div class="context-title">🌍 Market Context</div>
        <div class="indicator-row">
          <div class="indicator-label">VIX Fear</div>
          <div class="indicator-bar"><div class="indicator-fill" id="vix-bar" style="width:40%;background:linear-gradient(90deg,var(--green),var(--gold))"></div></div>
          <div class="indicator-val" id="vix-val">20.0</div>
        </div>
        <div class="indicator-row">
          <div class="indicator-label">DXY Dollar</div>
          <div class="indicator-bar"><div class="indicator-fill" id="dxy-bar" style="width:52%;background:linear-gradient(90deg,var(--accent),var(--purple))"></div></div>
          <div class="indicator-val" id="dxy-val">104.0</div>
        </div>
        <div class="indicator-row">
          <div class="indicator-label">Gold</div>
          <div class="indicator-bar"><div class="indicator-fill" id="gold-bar" style="width:70%;background:linear-gradient(90deg,var(--gold),var(--red))"></div></div>
          <div class="indicator-val" id="gold-val">2000</div>
        </div>
        <div class="indicator-row">
          <div class="indicator-label">Fed Rate</div>
          <div class="indicator-bar"><div class="indicator-fill" id="rate-bar" style="width:88%;background:linear-gradient(90deg,var(--red),var(--gold))"></div></div>
          <div class="indicator-val" id="rate-val">5.25%</div>
        </div>
      </div>

      <!-- Session Info -->
      <div class="context-card">
        <div class="context-title">⏰ Current Session</div>
        <div id="session-info" style="font-family:'Orbitron',monospace;font-size:16px;color:var(--accent)">Calculating...</div>
        <div id="session-sub" style="font-size:11px;color:var(--muted);margin-top:6px"></div>
        <div id="killzone-status" style="margin-top:10px;padding:8px;border-radius:8px;font-size:12px;text-align:center"></div>
      </div>

      <!-- Lot Calculator -->
      <div class="context-card">
        <div class="context-title">📐 LOT CALCULATOR</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
          <div>
            <div style="font-size:10px;color:var(--muted);margin-bottom:4px">Entry Price</div>
            <input id="calc-entry" type="number" step="0.00001" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text);font-size:13px" placeholder="1.08500">
          </div>
          <div>
            <div style="font-size:10px;color:var(--muted);margin-bottom:4px">Stop Loss</div>
            <input id="calc-sl" type="number" step="0.00001" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text);font-size:13px" placeholder="1.08000">
          </div>
        </div>
        <div style="margin-bottom:10px">
          <div style="font-size:10px;color:var(--muted);margin-bottom:4px">Pair</div>
          <select id="calc-pair" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px;color:var(--text);font-size:13px">
            <option>EURUSD</option><option>USDJPY</option><option>GBPUSD</option>
            <option>AUDUSD</option><option>XAUUSD</option><option>EURJPY</option>
          </select>
        </div>
        <button class="btn btn-primary" style="width:100%;margin-bottom:10px" onclick="calculateLots()">CALCULATE</button>
        <div id="calc-result" style="background:var(--surface);border-radius:8px;padding:10px;font-size:12px;display:none">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
            <div><div style="color:var(--muted);font-size:10px">Lots</div><div id="calc-lots" style="font-family:'Orbitron',monospace;color:var(--green);font-size:16px">--</div></div>
            <div><div style="color:var(--muted);font-size:10px">$ Risk</div><div id="calc-risk" style="font-family:'Orbitron',monospace;color:var(--red);font-size:16px">--</div></div>
            <div><div style="color:var(--muted);font-size:10px">Pips Risk</div><div id="calc-pips" style="font-family:'Orbitron',monospace;color:var(--accent);font-size:16px">--</div></div>
            <div><div style="color:var(--muted);font-size:10px">TP (2.5R)</div><div id="calc-tp" style="font-family:'Orbitron',monospace;color:var(--gold);font-size:16px">--</div></div>
          </div>
        </div>
      </div>

      <!-- Market Pairs Quick View -->
      <div class="context-card">
        <div class="context-title">💹 Markets</div>
        <div class="prices-grid" id="prices-grid">
          <div class="price-card"><div class="price-symbol">EURUSD</div><div class="price-value">--</div></div>
          <div class="price-card"><div class="price-symbol">USDJPY</div><div class="price-value">--</div></div>
          <div class="price-card"><div class="price-symbol">GBPUSD</div><div class="price-value">--</div></div>
          <div class="price-card"><div class="price-symbol">XAUUSD</div><div class="price-value">--</div></div>
        </div>
      </div>

    </div>
  </div>

</div>

<!-- Signal Detail Modal -->
<div class="modal" id="signal-modal">
  <div class="modal-content">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <div class="modal-title" id="modal-title">Signal Details</div>
      <button class="btn btn-danger" onclick="closeModal()" style="padding:8px 16px">✕ CLOSE</button>
    </div>
    <div id="modal-chart"></div>
    <div style="margin-top:16px">
      <div style="font-size:12px;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">Agent Reasoning</div>
      <ul class="reason-list" id="modal-reasons"></ul>
    </div>
  </div>
</div>

<script>
let autoInterval = null;
let countdown = 0;
let systemData = { signals:[], capital:10000, context:{} };

// Fetch signals from backend
async function fetchSignals() {
  try {
    const r = await fetch('/api/signals');
    const data = await r.json();
    systemData = data;
    renderSignals(data.signals);
    updateStats(data);
    updateContext(data.context);
  } catch(e) { addLog('ERROR fetching signals: '+e.message, 'error'); }
}

async function runAnalysis() {
  const capital = document.getElementById('capital-input').value;
  addLog('Starting market analysis...', 'info');
  document.getElementById('status-text').textContent = 'SCANNING';

  try {
    const r = await fetch('/api/run', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({capital: parseFloat(capital)})
    });
    const data = await r.json();
    systemData = data;
    renderSignals(data.signals);
    updateStats(data);
    updateContext(data.context || {});
    document.getElementById('last-update').textContent = 'Updated: '+new Date().toLocaleTimeString();
    addLog(`Analysis complete: ${data.signals.length} signals found`, 'success');
    showNotification(`Found ${data.signals.length} trading signals!`, 'success');
  } catch(e) {
    addLog('Analysis error: '+e.message, 'error');
    showNotification('Analysis failed - check terminal', 'error');
  }
  document.getElementById('status-text').textContent = 'LIVE';
}

function renderSignals(signals) {
  const container = document.getElementById('signals-container');
  if (!signals || signals.length===0) {
    container.innerHTML = '<div style="text-align:center;color:var(--muted);padding:40px"><div style="font-size:32px;margin-bottom:8px">⚪</div>No signals — all pairs on HOLD</div>';
    return;
  }
  container.innerHTML = signals.map((s,i) => {
    const isBuy = s.signal===1;
    const action = isBuy ? 'BUY' : 'SELL';
    const rr = s.rr ? s.rr.toFixed(1) : '?';
    return `<div class="signal-card ${isBuy?'buy':'sell'}" onclick="showSignalDetail(${i})">
      <div class="signal-header">
        <div class="signal-symbol">${s.symbol}</div>
        <div class="signal-action ${isBuy?'buy':'sell'}">${isBuy?'▲':'▼'} ${action}</div>
      </div>
      <div class="signal-levels">
        <div class="level-item"><div class="level-label">Entry</div><div class="level-value level-entry">${s.entry.toFixed(5)}</div></div>
        <div class="level-item"><div class="level-label">Stop Loss</div><div class="level-value level-sl">${s.stop_loss.toFixed(5)}</div></div>
        <div class="level-item"><div class="level-label">Take Profit</div><div class="level-value level-tp">${s.take_profit.toFixed(5)}</div></div>
      </div>
      <div class="votes-container">
        <div class="vote-bar vote-buy">
          <div class="vote-label"><span style="color:var(--green)">🟢 ${s.buy_votes}</span></div>
          <div class="indicator-bar"><div class="vote-fill" style="width:${s.buy_votes/(s.total_votes||1)*100}%"></div></div>
        </div>
        <div class="vote-bar vote-sell">
          <div class="vote-label"><span style="color:var(--red)">🔴 ${s.sell_votes}</span></div>
          <div class="indicator-bar"><div class="vote-fill" style="width:${s.sell_votes/(s.total_votes||1)*100}%"></div></div>
        </div>
      </div>
      <div class="signal-meta" style="margin-top:8px">
        <span class="meta-badge">🎯 ${(s.confidence*100).toFixed(0)}% conf</span>
        <span class="meta-badge">📦 ${s.lots} lots</span>
        <span class="meta-badge">1:${rr} R:R</span>
        <span class="meta-badge">💵 $${(s.dollar_risk||0).toFixed(0)} risk</span>
      </div>
    </div>`;
  }).join('');
}

function showSignalDetail(idx) {
  const s = systemData.signals[idx];
  if (!s) return;
  document.getElementById('modal-title').textContent = `${s.symbol} ${s.signal===1?'▲ BUY':'▼ SELL'} — ${(s.confidence*100).toFixed(0)}% Confidence`;
  if (s.chart_b64) {
    document.getElementById('modal-chart').innerHTML = `<img src="data:image/png;base64,${s.chart_b64}" style="width:100%;border-radius:8px">`;
  } else {
    document.getElementById('modal-chart').innerHTML = '<div style="text-align:center;color:var(--muted);padding:20px">Chart generating...</div>';
  }
  document.getElementById('modal-reasons').innerHTML = (s.reasons||[]).map(r => {
    const isGood = r.includes('✅');
    return `<li class="reason-item" style="color:${isGood?'var(--green)':'var(--red)'}">${r}</li>`;
  }).join('');
  document.getElementById('signal-modal').classList.add('open');
}

function closeModal() { document.getElementById('signal-modal').classList.remove('open'); }

function updateStats(data) {
  const capital = data.capital || 10000;
  const initial = 10000;
  const pnl = capital - initial;
  const dd = data.drawdown || 0;
  document.getElementById('stat-capital').textContent = '$'+capital.toLocaleString('en',{minimumFractionDigits:2,maximumFractionDigits:2});
  document.getElementById('stat-pnl').textContent = (pnl>=0?'+':'')+'$'+Math.abs(pnl).toFixed(2);
  document.getElementById('stat-pnl').className = 'stat-value '+(pnl>=0?'stat-positive':'stat-negative');
  document.getElementById('stat-signals').textContent = (data.signals||[]).length;
  document.getElementById('stat-dd').textContent = (dd*100).toFixed(1)+'%';
  document.getElementById('stat-dd').className = 'stat-value '+(dd>0.05?'stat-negative':'stat-neutral');
}

function updateContext(ctx) {
  if (!ctx) return;
  const vix = ctx.vix||20;
  const dxy = ctx.dxy||104;
  const gold = ctx.gold||2000;
  const fred = ctx.fred_data||{};
  const rate = fred.fed_rate||5.25;
  document.getElementById('vix-val').textContent = vix.toFixed(1);
  document.getElementById('dxy-val').textContent = dxy.toFixed(1);
  document.getElementById('gold-val').textContent = gold.toFixed(0);
  document.getElementById('rate-val').textContent = rate.toFixed(2)+'%';
  document.getElementById('vix-bar').style.width = Math.min(vix/50*100,100)+'%';
  document.getElementById('dxy-bar').style.width = Math.min((dxy-90)/30*100,100)+'%';
  document.getElementById('gold-bar').style.width = Math.min((gold-1500)/1500*100,100)+'%';
  document.getElementById('rate-bar').style.width = Math.min(rate/8*100,100)+'%';
}

function updateSession() {
  const hour = new Date().getUTCHours();
  const sessions = [
    {start:0,end:8,name:'Asian Session',color:'#6060a0',strategy:'Low volatility — mean reversion'},
    {start:8,end:13,name:'London Session',color:'#00d4ff',strategy:'High probability — trend following'},
    {start:13,end:16,name:'NY-London Overlap',color:'#00ff88',strategy:'PEAK VOLUME — highest probability'},
    {start:16,end:21,name:'New York Session',color:'#8b5cf6',strategy:'Continuation and reversals'},
    {start:21,end:24,name:'Dead Zone',color:'#ff3366',strategy:'Avoid trading — low liquidity'},
  ];
  for (const s of sessions) {
    if (hour>=s.start && hour<s.end) {
      document.getElementById('session-info').textContent = s.name;
      document.getElementById('session-info').style.color = s.color;
      document.getElementById('session-sub').textContent = s.strategy;
      const isKillzone = (hour>=8&&hour<=10)||(hour>=13&&hour<=16);
      const kz = document.getElementById('killzone-status');
      if (isKillzone) {
        kz.style.background = 'rgba(0,255,136,0.1)';
        kz.style.border = '1px solid var(--green)';
        kz.style.color = 'var(--green)';
        kz.textContent = '🎯 KILLZONE ACTIVE — HIGH PROBABILITY';
      } else {
        kz.style.background = 'rgba(96,96,160,0.1)';
        kz.style.border = '1px solid var(--muted)';
        kz.style.color = 'var(--muted)';
        kz.textContent = 'Off-killzone period';
      }
      break;
    }
  }
}

function calculateLots() {
  const entry = parseFloat(document.getElementById('calc-entry').value);
  const sl = parseFloat(document.getElementById('calc-sl').value);
  const pair = document.getElementById('calc-pair').value;
  const capital = parseFloat(document.getElementById('capital-input').value)||10000;
  const riskPct = parseFloat(document.getElementById('risk-select').value)||0.01;
  if (!entry||!sl) return;
  const pips_usd = {EURUSD:10,USDJPY:9,GBPUSD:10,AUDUSD:10,USDCAD:7.5,NZDUSD:10,USDCHF:11,EURJPY:9,GBPJPY:9,EURGBP:12.5,XAUUSD:1};
  const pip_size = {EURUSD:0.0001,USDJPY:0.01,GBPUSD:0.0001,AUDUSD:0.0001,USDCAD:0.0001,NZDUSD:0.0001,USDCHF:0.0001,EURJPY:0.01,GBPJPY:0.01,EURGBP:0.0001,XAUUSD:0.1};
  const pu = pips_usd[pair]||10;
  const ps = pip_size[pair]||0.0001;
  const riskAmt = capital*riskPct;
  const slPips = Math.abs(entry-sl)/ps;
  const lots = (riskAmt/(slPips*pu)).toFixed(2);
  const dollarRisk = (slPips*pu*lots).toFixed(2);
  const signal = entry>sl ? 1 : -1;
  const tp = (entry+signal*Math.abs(entry-sl)*2.5).toFixed(5);
  document.getElementById('calc-lots').textContent = lots;
  document.getElementById('calc-risk').textContent = '$'+dollarRisk;
  document.getElementById('calc-pips').textContent = slPips.toFixed(0);
  document.getElementById('calc-tp').textContent = tp;
  document.getElementById('calc-result').style.display = 'block';
}

function startAuto() {
  if (autoInterval) return;
  countdown = 300;
  runAnalysis();
  autoInterval = setInterval(() => {
    countdown--;
    const m = Math.floor(countdown/60).toString().padStart(2,'0');
    const s = (countdown%60).toString().padStart(2,'0');
    document.getElementById('timer').textContent = `${m}:${s}`;
    if (countdown<=0) { countdown=300; runAnalysis(); }
  }, 1000);
  addLog('Auto-scan started every 5 minutes', 'success');
  showNotification('Auto-scan started!', 'success');
}

function stopAuto() {
  if (autoInterval) { clearInterval(autoInterval); autoInterval=null; }
  document.getElementById('timer').textContent = '--:--';
  addLog('Auto-scan stopped', 'info');
}

function showPerformance() {
  showNotification('Performance stats coming soon!', 'success');
}

function addLog(msg, type='info') {
  const log = document.getElementById('activity-log');
  const colors = {info:'var(--muted)',success:'var(--green)',error:'var(--red)'};
  const time = new Date().toLocaleTimeString();
  log.innerHTML = `<div class="log-entry"><span class="log-time">[${time}]</span> <span style="color:${colors[type]}">${msg}</span></div>` + log.innerHTML;
  if (log.children.length>50) log.removeChild(log.lastChild);
}

function showNotification(msg, type='success') {
  const n = document.createElement('div');
  n.className = `notification ${type}`;
  n.textContent = msg;
  document.body.appendChild(n);
  setTimeout(() => n.remove(), 3000);
}

// Update session every minute
updateSession();
setInterval(updateSession, 60000);

// Initial fetch
fetchSignals();
setInterval(fetchSignals, 30000);

// Close modal on background click
document.getElementById('signal-modal').addEventListener('click', function(e) {
  if (e.target===this) closeModal();
});
</script>
</body>
</html>'''

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/signals')
def get_signals():
    from v6_brain import signals_store, system_status, orchestrator
    capital = system_status.get('capital', CONFIG['INITIAL_CAPITAL'])
    initial = CONFIG['INITIAL_CAPITAL']
    dd = max(0, (initial - capital) / initial) if capital < initial else 0
    return jsonify({
        'signals': signals_store[:20],
        'capital': capital,
        'drawdown': dd,
        'last_run': system_status.get('last_run'),
        'context': {}
    })

@app.route('/api/run', methods=['POST'])
def api_run():
    data = request.get_json() or {}
    capital = data.get('capital', CONFIG['INITIAL_CAPITAL'])
    def run_bg():
        signals = run_system(capital_override=capital)
    thread = threading.Thread(target=run_bg, daemon=True)
    thread.start()
    thread.join(timeout=120)
    from v6_brain import signals_store, system_status
    cap = system_status.get('capital', capital)
    return jsonify({
        'signals': signals_store[:20],
        'capital': cap,
        'drawdown': max(0, (capital - cap) / capital) if cap < capital else 0,
        'context': {}
    })

@app.route('/api/status')
def get_status():
    return jsonify(system_status)

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════╗
║         V6 DASHBOARD SERVER STARTING               ║
║  Open browser: http://localhost:5000               ║
╚══════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
