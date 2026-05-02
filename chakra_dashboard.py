<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Project Chakra — Command Center</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@300;400;600&family=Rajdhani:wght@300;400;600;700&display=swap');

:root {
  --bg:       #020408;
  --bg2:      #040c14;
  --bg3:      #061220;
  --panel:    #071828;
  --border:   #0d3a5c;
  --border2:  #0f4a74;
  --cyan:     #00d4ff;
  --cyan2:    #00a8cc;
  --green:    #00ff88;
  --green2:   #00cc6a;
  --red:      #ff3366;
  --red2:     #cc1144;
  --gold:     #ffd700;
  --purple:   #9d4edd;
  --text:     #c8e6f0;
  --text2:    #7ab8d4;
  --text3:    #3a6b85;
  --glow:     0 0 20px rgba(0,212,255,0.3);
  --glow-g:   0 0 20px rgba(0,255,136,0.3);
  --glow-r:   0 0 20px rgba(255,51,102,0.3);
}

* { margin:0; padding:0; box-sizing:border-box; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'JetBrains Mono', monospace;
  min-height: 100vh;
  overflow-x: hidden;
}

/* ANIMATED BACKGROUND GRID */
body::before {
  content:'';
  position:fixed; inset:0;
  background-image:
    linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events:none; z-index:0;
  animation: gridPulse 8s ease-in-out infinite;
}
body::after {
  content:'';
  position:fixed; inset:0;
  background: radial-gradient(ellipse at 20% 20%, rgba(0,212,255,0.05) 0%, transparent 50%),
              radial-gradient(ellipse at 80% 80%, rgba(157,78,221,0.05) 0%, transparent 50%);
  pointer-events:none; z-index:0;
}
@keyframes gridPulse {
  0%,100%{opacity:0.5} 50%{opacity:1}
}

/* SCANLINE EFFECT */
.scanline {
  position:fixed; top:0; left:0; right:0;
  height:2px; background:rgba(0,212,255,0.1);
  z-index:1000; pointer-events:none;
  animation: scan 6s linear infinite;
}
@keyframes scan { 0%{top:-2px} 100%{top:100vh} }

/* LAYOUT */
.container { position:relative; z-index:1; padding:16px; max-width:1800px; margin:0 auto; }

/* TOP HEADER */
.header {
  display:flex; align-items:center; justify-content:space-between;
  padding:16px 24px; margin-bottom:16px;
  background: linear-gradient(135deg, rgba(7,24,40,0.95), rgba(4,12,20,0.95));
  border:1px solid var(--border2);
  border-radius:4px;
  box-shadow: var(--glow), inset 0 1px 0 rgba(0,212,255,0.1);
  position:relative; overflow:hidden;
}
.header::before {
  content:''; position:absolute; left:0; top:0; bottom:0; width:3px;
  background: linear-gradient(180deg, var(--cyan), var(--purple));
}
.logo {
  display:flex; align-items:center; gap:16px;
}
.logo-icon {
  width:48px; height:48px;
  background: conic-gradient(from 0deg, var(--cyan), var(--purple), var(--green), var(--cyan));
  border-radius:50%; display:flex; align-items:center; justify-content:center;
  animation: spinGlow 8s linear infinite;
  box-shadow: 0 0 30px rgba(0,212,255,0.5);
}
.logo-icon::after {
  content:'⚡'; font-size:20px;
  animation: spinGlow 8s linear infinite reverse;
}
@keyframes spinGlow {
  0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)}
}
.logo-text h1 {
  font-family:'Orbitron',monospace; font-size:22px; font-weight:900;
  background: linear-gradient(135deg, var(--cyan), var(--purple));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  letter-spacing:4px;
}
.logo-text p {
  font-size:10px; color:var(--text3); letter-spacing:3px; margin-top:2px;
  font-family:'Rajdhani',sans-serif; font-weight:600; text-transform:uppercase;
}
.header-center {
  display:flex; gap:24px; align-items:center;
}
.live-badge {
  display:flex; align-items:center; gap:8px;
  padding:6px 16px; border-radius:2px;
  background:rgba(0,255,136,0.1); border:1px solid var(--green);
  font-size:11px; font-family:'Orbitron',monospace; color:var(--green);
  letter-spacing:2px; box-shadow:var(--glow-g);
}
.live-dot {
  width:8px; height:8px; border-radius:50%; background:var(--green);
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }

.header-time {
  font-family:'Orbitron',monospace; font-size:18px; color:var(--cyan);
  text-shadow:var(--glow); letter-spacing:2px;
}
.session-badge {
  padding:4px 12px; border-radius:2px; font-size:10px;
  font-family:'Orbitron',monospace; letter-spacing:2px;
}
.session-open { background:rgba(0,255,136,0.1); border:1px solid var(--green); color:var(--green); }
.session-closed { background:rgba(255,51,102,0.1); border:1px solid var(--red); color:var(--red); }

/* STAT BAR */
.stat-bar {
  display:grid; grid-template-columns:repeat(6,1fr); gap:12px;
  margin-bottom:16px;
}
.stat-card {
  background: linear-gradient(135deg, var(--panel), var(--bg2));
  border:1px solid var(--border);
  border-radius:4px; padding:16px;
  position:relative; overflow:hidden;
  transition: all 0.3s ease;
  cursor:default;
}
.stat-card:hover {
  border-color:var(--border2);
  box-shadow:var(--glow);
  transform:translateY(-2px);
}
.stat-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg, transparent, var(--cyan), transparent);
  opacity:0; transition:opacity 0.3s;
}
.stat-card:hover::before { opacity:1; }
.stat-label { font-size:9px; color:var(--text3); letter-spacing:2px; text-transform:uppercase; margin-bottom:8px; }
.stat-value { font-family:'Orbitron',monospace; font-size:20px; font-weight:700; color:var(--cyan); }
.stat-value.green { color:var(--green); text-shadow:var(--glow-g); }
.stat-value.red   { color:var(--red);   text-shadow:var(--glow-r); }
.stat-value.gold  { color:var(--gold); }
.stat-sub { font-size:10px; color:var(--text3); margin-top:4px; }
.stat-change { font-size:11px; margin-top:4px; }
.stat-change.up   { color:var(--green); }
.stat-change.down { color:var(--red); }

/* MAIN GRID */
.main-grid {
  display:grid;
  grid-template-columns: 340px 1fr 340px;
  gap:16px; margin-bottom:16px;
}

/* PANEL BASE */
.panel {
  background: linear-gradient(135deg, var(--panel), var(--bg2));
  border:1px solid var(--border);
  border-radius:4px; overflow:hidden;
}
.panel-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 16px;
  border-bottom:1px solid var(--border);
  background:rgba(0,212,255,0.03);
}
.panel-title {
  font-family:'Orbitron',monospace; font-size:11px;
  color:var(--cyan); letter-spacing:3px; text-transform:uppercase;
  display:flex; align-items:center; gap:8px;
}
.panel-title::before {
  content:''; width:3px; height:14px;
  background:linear-gradient(180deg, var(--cyan), var(--purple));
  border-radius:2px;
}
.panel-body { padding:16px; }

/* AGENT GRID */
.agents-panel { grid-column:1; }
.agent-item {
  display:flex; align-items:center; gap:12px;
  padding:10px 16px; border-bottom:1px solid rgba(13,58,92,0.4);
  transition:all 0.2s;
}
.agent-item:hover { background:rgba(0,212,255,0.03); }
.agent-status {
  width:8px; height:8px; border-radius:50%; flex-shrink:0;
}
.agent-status.active { background:var(--green); box-shadow:0 0 8px var(--green); animation:pulse 2s infinite; }
.agent-status.thinking { background:var(--gold); box-shadow:0 0 8px var(--gold); animation:pulse 0.5s infinite; }
.agent-status.idle { background:var(--text3); }
.agent-info { flex:1; }
.agent-name { font-size:11px; color:var(--text); font-weight:600; }
.agent-desc { font-size:9px; color:var(--text3); margin-top:2px; letter-spacing:1px; }
.agent-score {
  font-family:'Orbitron',monospace; font-size:13px;
  font-weight:700;
}
.agent-bar {
  height:2px; background:rgba(13,58,92,0.6); border-radius:1px;
  margin-top:4px; overflow:hidden;
}
.agent-bar-fill {
  height:100%; border-radius:1px;
  transition:width 1s ease;
}

/* CENTER: CHART + SIGNALS */
.center-panel { grid-column:2; display:flex; flex-direction:column; gap:16px; }

/* PAIR SELECTOR */
.pair-selector {
  display:flex; gap:8px; padding:16px;
  border-bottom:1px solid var(--border);
  flex-wrap:wrap;
}
.pair-btn {
  padding:6px 14px; border-radius:2px; font-size:10px;
  font-family:'Orbitron',monospace; letter-spacing:2px;
  border:1px solid var(--border); background:transparent;
  color:var(--text3); cursor:pointer; transition:all 0.2s;
}
.pair-btn:hover { border-color:var(--cyan); color:var(--cyan); }
.pair-btn.active {
  border-color:var(--cyan); color:var(--cyan);
  background:rgba(0,212,255,0.1); box-shadow:var(--glow);
}
.pair-btn.primary { border-color:var(--green); color:var(--green); }
.pair-btn.primary.active { background:rgba(0,255,136,0.1); box-shadow:var(--glow-g); }

/* TIMEFRAME SELECTOR */
.tf-selector {
  display:flex; gap:6px; padding:12px 16px;
  border-bottom:1px solid var(--border);
  align-items:center;
}
.tf-label { font-size:9px; color:var(--text3); letter-spacing:2px; margin-right:8px; }
.tf-btn {
  padding:4px 12px; border-radius:2px; font-size:10px;
  font-family:'Orbitron',monospace;
  border:1px solid var(--border); background:transparent;
  color:var(--text3); cursor:pointer; transition:all 0.2s;
}
.tf-btn:hover { border-color:var(--purple); color:var(--purple); }
.tf-btn.active {
  border-color:var(--purple); color:var(--purple);
  background:rgba(157,78,221,0.1);
}

/* FAKE CHART */
.chart-container {
  padding:16px; position:relative; height:300px;
}
.chart-canvas {
  width:100%; height:100%;
  background: linear-gradient(180deg, rgba(0,212,255,0.02) 0%, transparent 100%);
  border-radius:4px; position:relative; overflow:hidden;
}
canvas { width:100%; height:100%; }

/* MTF ALIGNMENT */
.mtf-grid {
  display:grid; grid-template-columns:repeat(5,1fr); gap:8px;
  padding:16px; border-top:1px solid var(--border);
}
.mtf-item {
  text-align:center; padding:12px 8px; border-radius:4px;
  border:1px solid var(--border); position:relative;
  transition:all 0.3s;
}
.mtf-item.buy  { border-color:var(--green); background:rgba(0,255,136,0.05); }
.mtf-item.sell { border-color:var(--red);   background:rgba(255,51,102,0.05); }
.mtf-item.neutral { border-color:var(--border); }
.mtf-tf { font-family:'Orbitron',monospace; font-size:10px; color:var(--text3); margin-bottom:6px; }
.mtf-signal { font-family:'Orbitron',monospace; font-size:12px; font-weight:700; }
.mtf-signal.buy  { color:var(--green); }
.mtf-signal.sell { color:var(--red); }
.mtf-signal.neutral { color:var(--text3); }
.mtf-weight { font-size:9px; color:var(--text3); margin-top:4px; }

/* SIGNAL CARD */
.signal-card {
  margin:0 16px 16px; padding:16px;
  border-radius:4px; border:1px solid;
  position:relative; overflow:hidden;
  animation: slideIn 0.5s ease;
}
@keyframes slideIn { from{opacity:0;transform:translateY(-10px)} to{opacity:1;transform:translateY(0)} }
.signal-card.buy  { border-color:var(--green); background:linear-gradient(135deg, rgba(0,255,136,0.05), transparent); }
.signal-card.sell { border-color:var(--red);   background:linear-gradient(135deg, rgba(255,51,102,0.05), transparent); }
.signal-card::before {
  content:''; position:absolute; top:0; left:0; bottom:0; width:3px;
}
.signal-card.buy::before  { background:var(--green); }
.signal-card.sell::before { background:var(--red); }
.signal-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.signal-dir {
  font-family:'Orbitron',monospace; font-size:20px; font-weight:900;
  display:flex; align-items:center; gap:8px;
}
.signal-dir.buy  { color:var(--green); text-shadow:var(--glow-g); }
.signal-dir.sell { color:var(--red);   text-shadow:var(--glow-r); }
.signal-pair { font-family:'Orbitron',monospace; font-size:14px; color:var(--text2); }
.signal-conf {
  display:flex; flex-direction:column; align-items:flex-end; gap:4px;
}
.conf-value {
  font-family:'Orbitron',monospace; font-size:24px; font-weight:700; color:var(--gold);
}
.conf-label { font-size:9px; color:var(--text3); letter-spacing:2px; }
.signal-levels {
  display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px;
}
.level-item { text-align:center; }
.level-label { font-size:9px; color:var(--text3); letter-spacing:2px; margin-bottom:4px; }
.level-value { font-family:'Orbitron',monospace; font-size:14px; font-weight:700; }
.level-value.entry  { color:var(--cyan); }
.level-value.sl     { color:var(--red); }
.level-value.tp     { color:var(--green); }
.signal-meta {
  display:flex; gap:16px; flex-wrap:wrap;
}
.meta-item { font-size:10px; color:var(--text3); }
.meta-item span { color:var(--text2); }
.vote-bar {
  display:flex; height:4px; border-radius:2px; overflow:hidden; margin-top:12px;
}
.vote-for   { background:var(--green); transition:width 0.5s; }
.vote-against { background:var(--red); transition:width 0.5s; }
.execute-btn {
  width:100%; margin-top:12px; padding:12px;
  background:linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,212,255,0.1));
  border:1px solid var(--green); border-radius:2px;
  color:var(--green); font-family:'Orbitron',monospace;
  font-size:11px; letter-spacing:3px; cursor:pointer;
  transition:all 0.3s;
}
.execute-btn:hover {
  background:linear-gradient(135deg, rgba(0,255,136,0.3), rgba(0,212,255,0.2));
  box-shadow:var(--glow-g);
  transform:translateY(-1px);
}
.execute-btn.sell-btn {
  background:linear-gradient(135deg, rgba(255,51,102,0.2), rgba(255,51,102,0.1));
  border-color:var(--red); color:var(--red);
}
.execute-btn.sell-btn:hover {
  background:linear-gradient(135deg, rgba(255,51,102,0.3), rgba(255,51,102,0.2));
  box-shadow:var(--glow-r);
}

/* RIGHT PANEL */
.right-panel { grid-column:3; display:flex; flex-direction:column; gap:16px; }

/* TRADE LOG */
.trade-item {
  padding:12px 16px; border-bottom:1px solid rgba(13,58,92,0.4);
  display:flex; align-items:center; gap:12px;
  transition:all 0.2s;
}
.trade-item:hover { background:rgba(0,212,255,0.03); }
.trade-dir-badge {
  width:36px; height:36px; border-radius:2px;
  display:flex; align-items:center; justify-content:center;
  font-family:'Orbitron',monospace; font-size:10px; font-weight:700;
  flex-shrink:0;
}
.trade-dir-badge.buy  { background:rgba(0,255,136,0.15); color:var(--green); border:1px solid var(--green); }
.trade-dir-badge.sell { background:rgba(255,51,102,0.15); color:var(--red);   border:1px solid var(--red); }
.trade-info { flex:1; }
.trade-pair { font-size:12px; color:var(--text); font-weight:600; }
.trade-time { font-size:9px; color:var(--text3); margin-top:2px; }
.trade-pnl {
  font-family:'Orbitron',monospace; font-size:13px; font-weight:700;
  text-align:right;
}
.trade-pnl.win  { color:var(--green); }
.trade-pnl.loss { color:var(--red); }
.trade-pnl.open { color:var(--gold); }

/* PERFORMANCE CHART */
.equity-chart {
  padding:16px; height:160px; position:relative;
}
.equity-svg { width:100%; height:100%; }

/* MACRO DATA */
.macro-grid {
  display:grid; grid-template-columns:1fr 1fr; gap:8px;
  padding:16px;
}
.macro-item {
  padding:10px 12px; border:1px solid var(--border); border-radius:4px;
  transition:all 0.2s;
}
.macro-item:hover { border-color:var(--border2); }
.macro-label { font-size:9px; color:var(--text3); letter-spacing:1px; margin-bottom:4px; }
.macro-val { font-family:'Orbitron',monospace; font-size:13px; color:var(--cyan); }
.macro-trend { font-size:9px; margin-top:2px; }
.macro-trend.up   { color:var(--green); }
.macro-trend.down { color:var(--red); }

/* BOTTOM ROW */
.bottom-grid {
  display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;
  margin-bottom:16px;
}

/* RISK GAUGE */
.gauge-container {
  display:flex; justify-content:center; align-items:center;
  padding:20px; flex-direction:column; gap:12px;
}
.gauge {
  position:relative; width:160px; height:80px;
}
.gauge svg { width:100%; height:auto; }
.gauge-value {
  position:absolute; bottom:0; left:50%; transform:translateX(-50%);
  font-family:'Orbitron',monospace; font-size:22px; font-weight:700;
  color:var(--green);
}
.gauge-label { font-size:10px; color:var(--text3); letter-spacing:2px; text-align:center; }

/* SYSTEM HEALTH */
.health-grid { padding:16px; display:flex; flex-direction:column; gap:8px; }
.health-item { display:flex; align-items:center; gap:12px; }
.health-label { font-size:10px; color:var(--text3); width:100px; flex-shrink:0; }
.health-bar-wrap { flex:1; height:4px; background:rgba(13,58,92,0.6); border-radius:2px; overflow:hidden; }
.health-bar-fill {
  height:100%; border-radius:2px; transition:width 1s ease;
}
.health-val { font-family:'Orbitron',monospace; font-size:10px; color:var(--cyan); width:40px; text-align:right; }

/* PENDING UPGRADES */
.pending-list { padding:16px; display:flex; flex-direction:column; gap:8px; }
.pending-item {
  display:flex; align-items:center; gap:10px; padding:8px 12px;
  border:1px solid var(--border); border-radius:4px; font-size:10px;
  transition:all 0.2s;
}
.pending-item:hover { border-color:var(--border2); background:rgba(0,212,255,0.02); }
.pending-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.pending-dot.high   { background:var(--red); box-shadow:0 0 6px var(--red); }
.pending-dot.medium { background:var(--gold); box-shadow:0 0 6px var(--gold); }
.pending-dot.low    { background:var(--text3); }
.pending-name { color:var(--text2); flex:1; }
.pending-tag { font-size:9px; color:var(--text3); letter-spacing:1px; }

/* FOOTER */
.footer {
  text-align:center; padding:16px;
  font-size:9px; color:var(--text3); letter-spacing:3px;
  border-top:1px solid var(--border);
}
.footer span { color:var(--cyan); }

/* SCROLLBAR */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }

/* ANIMATIONS */
@keyframes fadeUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
.panel { animation: fadeUp 0.5s ease both; }
.panel:nth-child(2) { animation-delay:0.1s; }
.panel:nth-child(3) { animation-delay:0.2s; }

/* NOTIFICATION */
.notif {
  position:fixed; top:20px; right:20px; z-index:9999;
  padding:12px 20px; border-radius:4px;
  font-family:'Orbitron',monospace; font-size:11px; letter-spacing:2px;
  border:1px solid var(--green); background:rgba(0,255,136,0.1);
  color:var(--green); box-shadow:var(--glow-g);
  animation: notifIn 0.3s ease, notifOut 0.3s ease 2.7s forwards;
}
@keyframes notifIn  { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
@keyframes notifOut { from{opacity:1} to{opacity:0} }

/* TAGS */
.tag {
  display:inline-flex; align-items:center; gap:4px;
  padding:2px 8px; border-radius:2px; font-size:9px;
  letter-spacing:1px; font-family:'Orbitron',monospace;
}
.tag.cyan   { background:rgba(0,212,255,0.1); border:1px solid var(--cyan2); color:var(--cyan); }
.tag.green  { background:rgba(0,255,136,0.1); border:1px solid var(--green2); color:var(--green); }
.tag.red    { background:rgba(255,51,102,0.1); border:1px solid var(--red2); color:var(--red); }
.tag.purple { background:rgba(157,78,221,0.1); border:1px solid var(--purple); color:var(--purple); }
.tag.gold   { background:rgba(255,215,0,0.1);  border:1px solid var(--gold); color:var(--gold); }
</style>
</head>
<body>
<div class="scanline"></div>

<div class="container">

  <!-- HEADER -->
  <div class="header">
    <div class="logo">
      <div class="logo-icon"></div>
      <div class="logo-text">
        <h1>PROJECT CHAKRA</h1>
        <p>Multi-Agent AI Forex Trading System — V10 Complete</p>
      </div>
    </div>
    <div class="header-center">
      <div class="live-badge"><div class="live-dot"></div>LIVE TRADING</div>
      <div id="clock" class="header-time">--:--:-- UTC</div>
      <div id="sessionBadge" class="session-badge session-open">LONDON OPEN</div>
    </div>
    <div style="display:flex;gap:12px;align-items:center;">
      <div class="tag cyan">OANDA CONNECTED</div>
      <div class="tag green">SUPABASE ACTIVE</div>
      <div class="tag purple">CLAUDE AI ACTIVE</div>
    </div>
  </div>

  <!-- STAT BAR -->
  <div class="stat-bar">
    <div class="stat-card">
      <div class="stat-label">Account Balance</div>
      <div class="stat-value green" id="balance">$100,000.00</div>
      <div class="stat-sub">OANDA Paper Account</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Today P&L</div>
      <div class="stat-value green" id="todayPnl">+$0.00</div>
      <div class="stat-change up" id="todayPct">+0.00%</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Win Rate</div>
      <div class="stat-value gold" id="winRate">0.0%</div>
      <div class="stat-sub">Min 30 trades to learn</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Expectancy</div>
      <div class="stat-value" id="expectancy">$0.00</div>
      <div class="stat-sub">Per trade average</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Open Trades</div>
      <div class="stat-value cyan" id="openTrades">0</div>
      <div class="stat-sub">Max 3 allowed</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">System Cycle</div>
      <div class="stat-value cyan" id="cycleCount">0</div>
      <div class="stat-sub">Every 60 seconds</div>
    </div>
  </div>

  <!-- MAIN GRID -->
  <div class="main-grid">

    <!-- LEFT: AGENTS -->
    <div class="panel agents-panel">
      <div class="panel-header">
        <div class="panel-title">Agent Status</div>
        <div class="tag cyan" id="agentCount">15 ACTIVE</div>
      </div>
      <div id="agentList">
        <!-- Agents rendered by JS -->
      </div>
    </div>

    <!-- CENTER -->
    <div class="center-panel">

      <!-- CHART PANEL -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">Price Action & Signals</div>
          <div style="display:flex;gap:8px;">
            <div class="tag green" id="currentPair">EUR/USD</div>
            <div class="tag cyan" id="currentPrice">1.08450</div>
          </div>
        </div>

        <!-- PAIR SELECTOR -->
        <div class="pair-selector">
          <button class="pair-btn primary active" onclick="selectPair('EUR_USD',this)">EUR/USD</button>
          <button class="pair-btn primary" onclick="selectPair('GBP_USD',this)">GBP/USD</button>
          <button class="pair-btn" onclick="selectPair('USD_JPY',this)">USD/JPY</button>
          <button class="pair-btn" onclick="selectPair('AUD_USD',this)">AUD/USD</button>
          <button class="pair-btn" onclick="selectPair('USD_CAD',this)">USD/CAD</button>
          <button class="pair-btn" onclick="selectPair('US30',this)">US30</button>
          <button class="pair-btn" onclick="selectPair('SPX500',this)">SPX500</button>
          <button class="pair-btn" onclick="selectPair('NAS100',this)">NAS100</button>
        </div>

        <!-- TIMEFRAME SELECTOR -->
        <div class="tf-selector">
          <span class="tf-label">TIMEFRAME</span>
          <button class="tf-btn" onclick="selectTF('H4',this)">H4</button>
          <button class="tf-btn" onclick="selectTF('H1',this)">H1</button>
          <button class="tf-btn active" onclick="selectTF('M15',this)">M15</button>
          <button class="tf-btn" onclick="selectTF('M5',this)">M5</button>
          <button class="tf-btn" onclick="selectTF('M1',this)">M1</button>
        </div>

        <!-- CHART -->
        <div class="chart-container">
          <canvas id="mainChart"></canvas>
        </div>

        <!-- MTF ALIGNMENT -->
        <div class="mtf-grid" id="mtfGrid">
          <!-- Rendered by JS -->
        </div>
      </div>

      <!-- SIGNAL CARD -->
      <div id="signalContainer">
        <!-- Rendered by JS -->
      </div>

    </div>

    <!-- RIGHT PANEL -->
    <div class="right-panel">

      <!-- TRADE LOG -->
      <div class="panel" style="flex:1;">
        <div class="panel-header">
          <div class="panel-title">Trade Log</div>
          <div class="tag green">SUPABASE</div>
        </div>
        <div id="tradeLog">
          <!-- Rendered by JS -->
        </div>
      </div>

      <!-- MACRO DATA -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">FRED Macro Data</div>
          <div class="tag cyan">LIVE</div>
        </div>
        <div class="macro-grid" id="macroGrid">
          <!-- Rendered by JS -->
        </div>
      </div>

    </div>
  </div>

  <!-- BOTTOM ROW -->
  <div class="bottom-grid">

    <!-- RISK GAUGE -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Risk Monitor</div>
        <div class="tag gold">1% PER TRADE</div>
      </div>
      <div class="health-grid">
        <div class="health-item">
          <span class="health-label">Daily Loss</span>
          <div class="health-bar-wrap"><div class="health-bar-fill" id="dailyLossBar" style="width:0%;background:var(--green);"></div></div>
          <span class="health-val" id="dailyLossVal">0%</span>
        </div>
        <div class="health-item">
          <span class="health-label">Drawdown</span>
          <div class="health-bar-wrap"><div class="health-bar-fill" id="drawdownBar" style="width:0%;background:var(--cyan);"></div></div>
          <span class="health-val" id="drawdownVal">0%</span>
        </div>
        <div class="health-item">
          <span class="health-label">Open Trades</span>
          <div class="health-bar-wrap"><div class="health-bar-fill" id="openTradesBar" style="width:0%;background:var(--purple);"></div></div>
          <span class="health-val" id="openTradesVal">0/3</span>
        </div>
        <div class="health-item">
          <span class="health-label">Confidence</span>
          <div class="health-bar-wrap"><div class="health-bar-fill" id="confBar" style="width:60%;background:var(--gold);"></div></div>
          <span class="health-val" id="confVal">60%</span>
        </div>
        <div class="health-item">
          <span class="health-label">System Health</span>
          <div class="health-bar-wrap"><div class="health-bar-fill" style="width:95%;background:var(--green);"></div></div>
          <span class="health-val">95%</span>
        </div>
        <div class="health-item">
          <span class="health-label">Session</span>
          <div class="health-bar-wrap"><div class="health-bar-fill" id="sessionBar" style="width:40%;background:var(--cyan);"></div></div>
          <span class="health-val" id="sessionVal">LON</span>
        </div>
      </div>
    </div>

    <!-- EQUITY CURVE -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Equity Curve</div>
        <div style="display:flex;gap:8px;">
          <div class="tag green">+0.00%</div>
          <div class="tag cyan">Paper</div>
        </div>
      </div>
      <div class="equity-chart">
        <canvas id="equityChart"></canvas>
      </div>
    </div>

    <!-- PENDING UPGRADES -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Build Roadmap</div>
        <div class="tag purple">PHASE 2</div>
      </div>
      <div class="pending-list">
        <div class="pending-item">
          <div class="pending-dot high"></div>
          <span class="pending-name">Backtesting Engine</span>
          <span class="pending-tag">5Y DATA</span>
        </div>
        <div class="pending-item">
          <div class="pending-dot high"></div>
          <span class="pending-name">Oracle VPS 24/7</span>
          <span class="pending-tag">PENDING</span>
        </div>
        <div class="pending-item">
          <div class="pending-dot medium"></div>
          <span class="pending-name">Event-Driven LSTM</span>
          <span class="pending-tag">MONTH 2</span>
        </div>
        <div class="pending-item">
          <div class="pending-dot medium"></div>
          <span class="pending-name">HiveMind Optimizer</span>
          <span class="pending-tag">MONTH 2</span>
        </div>
        <div class="pending-item">
          <div class="pending-dot medium"></div>
          <span class="pending-name">COT Institutional Data</span>
          <span class="pending-tag">MONTH 2</span>
        </div>
        <div class="pending-item">
          <div class="pending-dot low"></div>
          <span class="pending-name">TradingView MCP</span>
          <span class="pending-tag">MONTH 3</span>
        </div>
        <div class="pending-item">
          <div class="pending-dot low"></div>
          <span class="pending-name">Walk-Forward Optimization</span>
          <span class="pending-tag">MONTH 3</span>
        </div>
      </div>
    </div>

  </div>

  <div class="footer">
    PROJECT CHAKRA V10 COMPLETE — <span>15 AGENTS</span> — <span>5 TIMEFRAMES</span> —
    <span>CLAUDE AI + SUPABASE + FRED + OANDA</span> — PRIVATE & CONFIDENTIAL
  </div>

</div>

<script>
// ── CLOCK ──
function updateClock() {
  const now = new Date();
  const utc = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
  document.getElementById('clock').textContent =
    utc.toTimeString().slice(0,8) + ' UTC';
  const h = utc.getHours();
  const isLondon  = h >= 7  && h < 12;
  const isNY      = h >= 12 && h < 17;
  const badge = document.getElementById('sessionBadge');
  if (isLondon && isNY) {
    badge.textContent = 'LONDON/NY OVERLAP'; badge.className='session-badge session-open';
    document.getElementById('sessionBar').style.width='100%';
    document.getElementById('sessionVal').textContent='OVLP';
  } else if (isLondon) {
    badge.textContent = 'LONDON OPEN'; badge.className='session-badge session-open';
    document.getElementById('sessionBar').style.width='70%';
    document.getElementById('sessionVal').textContent='LON';
  } else if (isNY) {
    badge.textContent = 'NEW YORK OPEN'; badge.className='session-badge session-open';
    document.getElementById('sessionBar').style.width='80%';
    document.getElementById('sessionVal').textContent='NY';
  } else {
    badge.textContent = 'SESSION CLOSED'; badge.className='session-badge session-closed';
    document.getElementById('sessionBar').style.width='10%';
    document.getElementById('sessionVal').textContent='WAIT';
  }
}
setInterval(updateClock, 1000); updateClock();

// ── AGENTS ──
const agents = [
  {name:'Master Orchestrator', desc:'Coordinates all agents', score:0.95, status:'active', color:'var(--cyan)'},
  {name:'Claude Reasoning',    desc:'LLM trade analysis',   score:0.88, status:'thinking', color:'var(--purple)'},
  {name:'Trend Agent',         desc:'EMA alignment H4-M1',  score:0.82, status:'active', color:'var(--green)'},
  {name:'RSI Agent',           desc:'Momentum oscillator',  score:0.71, status:'active', color:'var(--green)'},
  {name:'MACD Agent',          desc:'Trend momentum',       score:0.68, status:'active', color:'var(--cyan)'},
  {name:'Bollinger Agent',     desc:'Mean reversion bands', score:0.55, status:'active', color:'var(--cyan)'},
  {name:'SMC Agent',           desc:'Smart money concepts', score:0.79, status:'active', color:'var(--gold)'},
  {name:'Wyckoff Agent',       desc:'Accumulation detect',  score:0.63, status:'active', color:'var(--gold)'},
  {name:'Volume Lead Agent',   desc:'Volume precedes price',score:0.74, status:'active', color:'var(--green)'},
  {name:'Structure Break',     desc:'Market structure',     score:0.81, status:'active', color:'var(--cyan)'},
  {name:'Momentum Lead',       desc:'Rate of change',       score:0.69, status:'active', color:'var(--cyan)'},
  {name:'Liquidity Sweep',     desc:'ICT liquidity grabs',  score:0.77, status:'active', color:'var(--purple)'},
  {name:'FRED Macro Agent',    desc:'Fed rates + bonds',    score:0.60, status:'active', color:'var(--gold)'},
  {name:'Alpha Vantage',       desc:'Backup data source',   score:0.58, status:'active', color:'var(--cyan)'},
  {name:'Sentiment Agent',     desc:'News sentiment NLP',   score:0.52, status:'active', color:'var(--text3)'},
];

function renderAgents() {
  const list = document.getElementById('agentList');
  list.innerHTML = agents.map(a => `
    <div class="agent-item">
      <div class="agent-status ${a.status}"></div>
      <div class="agent-info">
        <div class="agent-name">${a.name}</div>
        <div class="agent-desc">${a.desc}</div>
        <div class="agent-bar">
          <div class="agent-bar-fill" style="width:${a.score*100}%;background:${a.color};"></div>
        </div>
      </div>
      <div class="agent-score" style="color:${a.color}">${(a.score*100).toFixed(0)}%</div>
    </div>
  `).join('');
}
renderAgents();

// Randomly fluctuate agent scores
setInterval(() => {
  agents.forEach(a => {
    a.score = Math.min(1, Math.max(0.3, a.score + (Math.random()-0.5)*0.05));
    if (Math.random() < 0.05) a.status = a.status === 'active' ? 'thinking' : 'active';
  });
  renderAgents();
}, 3000);

// ── MTF GRID ──
function renderMTF(signals) {
  const tfs = ['H4','H1','M15','M5','M1'];
  const weights = ['30%','25%','20%','15%','10%'];
  document.getElementById('mtfGrid').innerHTML = tfs.map((tf,i) => {
    const sig = signals[i] || {dir:'NEUTRAL',strength:0};
    const cls = sig.dir === 'BUY' ? 'buy' : sig.dir === 'SELL' ? 'sell' : 'neutral';
    const sigCls = sig.dir === 'BUY' ? 'buy' : sig.dir === 'SELL' ? 'sell' : 'neutral';
    return `
      <div class="mtf-item ${cls}">
        <div class="mtf-tf">${tf}</div>
        <div class="mtf-signal ${sigCls}">${sig.dir}</div>
        <div class="mtf-weight">WT: ${weights[i]}</div>
      </div>
    `;
  }).join('');
}

const defaultMTF = [
  {dir:'BUY',strength:0.82},
  {dir:'BUY',strength:0.71},
  {dir:'BUY',strength:0.68},
  {dir:'NEUTRAL',strength:0.0},
  {dir:'SELL',strength:0.4},
];
renderMTF(defaultMTF);

// ── SIGNAL CARD ──
function renderSignal(signal) {
  const container = document.getElementById('signalContainer');
  const isBuy = signal.direction === 'BUY';
  const cls = isBuy ? 'buy' : 'sell';
  const emoji = isBuy ? '▲' : '▼';
  const votePct = (signal.votes_for / (signal.votes_for + signal.votes_against)) * 100;

  container.innerHTML = `
    <div class="signal-card ${cls}" style="margin:0 0 0 0;">
      <div class="signal-header">
        <div>
          <div class="signal-dir ${cls}">${emoji} ${signal.direction}</div>
          <div class="signal-pair">${signal.pair.replace('_','/')}</div>
          <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;">
            <div class="tag ${isBuy?'green':'red'}">${signal.regime}</div>
            <div class="tag purple">LLM: ${(signal.llm_score*100).toFixed(0)}%</div>
            <div class="tag cyan">R:R 1:2.5</div>
          </div>
        </div>
        <div class="signal-conf">
          <div class="conf-value">${(signal.confidence*100).toFixed(1)}%</div>
          <div class="conf-label">CONFIDENCE</div>
          <div style="margin-top:8px;font-size:10px;color:var(--text3);">
            🟢${signal.votes_for} AGENTS FOR<br>
            🔴${signal.votes_against} AGENTS AGAINST
          </div>
        </div>
      </div>

      <div class="signal-levels">
        <div class="level-item">
          <div class="level-label">ENTRY PRICE</div>
          <div class="level-value entry">${signal.entry.toFixed(5)}</div>
        </div>
        <div class="level-item">
          <div class="level-label">STOP LOSS</div>
          <div class="level-value sl">${signal.sl.toFixed(5)}</div>
        </div>
        <div class="level-item">
          <div class="level-label">TAKE PROFIT</div>
          <div class="level-value tp">${signal.tp.toFixed(5)}</div>
        </div>
      </div>

      <div class="vote-bar">
        <div class="vote-for" style="width:${votePct}%;"></div>
        <div class="vote-against" style="width:${100-votePct}%;"></div>
      </div>

      <div class="signal-meta" style="margin-top:12px;">
        <div class="meta-item">Lots: <span>${signal.lots}</span></div>
        <div class="meta-item">Risk: <span>$${signal.risk}</span></div>
        <div class="meta-item">Session: <span>${signal.session}</span></div>
        <div class="meta-item">ATR: <span>${signal.atr.toFixed(5)}</span></div>
      </div>

      <button class="execute-btn ${isBuy?'':'sell-btn'}" onclick="showNotif('${signal.direction} ${signal.pair} — Forwarded to OANDA via v10')">
        ⚡ EXECUTE ${signal.direction} ${signal.pair.replace('_','/')} ON OANDA
      </button>
    </div>
  `;
}

const demoSignal = {
  direction: 'BUY', pair: 'EUR_USD', confidence: 0.74,
  regime: 'TREND', llm_score: 0.82,
  entry: 1.08452, sl: 1.08200, tp: 1.09080,
  votes_for: 9, votes_against: 2,
  lots: 0.08, risk: 86.40, session: 'LONDON',
  atr: 0.00085,
};
renderSignal(demoSignal);

// ── TRADE LOG ──
const trades = [
  {dir:'BUY',  pair:'EUR/USD', time:'09:24 UTC', pnl:'+$124.50', cls:'win',  status:'CLOSED'},
  {dir:'SELL', pair:'GBP/USD', time:'08:47 UTC', pnl:'-$43.20',  cls:'loss', status:'CLOSED'},
  {dir:'BUY',  pair:'USD/JPY', time:'10:12 UTC', pnl:'+$0.00',   cls:'open', status:'OPEN'},
  {dir:'BUY',  pair:'EUR/USD', time:'Yesterday', pnl:'+$210.00', cls:'win',  status:'CLOSED'},
  {dir:'SELL', pair:'US30',    time:'Yesterday', pnl:'+$89.40',  cls:'win',  status:'CLOSED'},
];

function renderTrades() {
  document.getElementById('tradeLog').innerHTML = trades.map(t => `
    <div class="trade-item">
      <div class="trade-dir-badge ${t.dir.toLowerCase()}">${t.dir}</div>
      <div class="trade-info">
        <div class="trade-pair">${t.pair}</div>
        <div class="trade-time">${t.time} · ${t.status}</div>
      </div>
      <div class="trade-pnl ${t.cls}">${t.pnl}</div>
    </div>
  `).join('');
}
renderTrades();

// ── MACRO DATA ──
const macroData = [
  {label:'Fed Rate',    val:'5.33%', trend:'↓ FALLING', cls:'down'},
  {label:'10Y Bond',    val:'4.28%', trend:'↑ RISING',  cls:'up'},
  {label:'2Y Bond',     val:'4.71%', trend:'↑ RISING',  cls:'up'},
  {label:'Yield Curve', val:'-0.43%',trend:'INVERTED',  cls:'down'},
  {label:'DXY Index',   val:'104.2', trend:'↑ RISING',  cls:'up'},
  {label:'VIX Fear',    val:'18.4',  trend:'↓ CALM',    cls:'down'},
];

function renderMacro() {
  document.getElementById('macroGrid').innerHTML = macroData.map(m => `
    <div class="macro-item">
      <div class="macro-label">${m.label}</div>
      <div class="macro-val">${m.val}</div>
      <div class="macro-trend ${m.cls}">${m.trend}</div>
    </div>
  `).join('');
}
renderMacro();

// ── CHART ──
function drawChart() {
  const canvas = document.getElementById('mainChart');
  const ctx = canvas.getContext('2d');
  canvas.width  = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight;
  const W = canvas.width, H = canvas.height;

  // Generate fake candle data
  const candles = [];
  let price = 1.0845;
  for (let i = 0; i < 60; i++) {
    const open  = price;
    const close = price + (Math.random()-0.48)*0.0015;
    const high  = Math.max(open,close) + Math.random()*0.0008;
    const low   = Math.min(open,close) - Math.random()*0.0008;
    candles.push({open,close,high,low});
    price = close;
  }

  const allPrices = candles.flatMap(c=>[c.high,c.low]);
  const minP = Math.min(...allPrices);
  const maxP = Math.max(...allPrices);
  const priceToY = p => H - ((p-minP)/(maxP-minP))*(H*0.8) - H*0.1;

  const cw  = W / candles.length;
  const pad = cw * 0.2;

  // Background glow
  const bg = ctx.createLinearGradient(0,0,0,H);
  bg.addColorStop(0,'rgba(0,212,255,0.03)');
  bg.addColorStop(1,'transparent');
  ctx.fillStyle = bg; ctx.fillRect(0,0,W,H);

  // Grid lines
  ctx.strokeStyle = 'rgba(13,58,92,0.4)'; ctx.lineWidth = 0.5;
  for (let i=0;i<6;i++) {
    const y = H*0.1 + (H*0.8/5)*i;
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke();
    const pVal = maxP - (maxP-minP)/5*i;
    ctx.fillStyle='rgba(58,107,133,0.8)'; ctx.font='9px JetBrains Mono';
    ctx.fillText(pVal.toFixed(5), 4, y-3);
  }

  // EMA line
  ctx.beginPath(); ctx.strokeStyle='rgba(157,78,221,0.6)'; ctx.lineWidth=1.5;
  const ema = []; let emav = candles[0].close;
  candles.forEach((c,i)=>{
    emav = emav*0.95 + c.close*0.05;
    ema.push(emav);
    const x=i*cw+cw/2, y=priceToY(emav);
    i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
  });
  ctx.stroke();

  // Candles
  candles.forEach((c,i)=>{
    const x   = i*cw+pad;
    const bw  = cw-pad*2;
    const isBull = c.close >= c.open;
    const col  = isBull ? '#00ff88' : '#ff3366';
    const colD = isBull ? 'rgba(0,255,136,0.2)' : 'rgba(255,51,102,0.2)';

    // Wick
    ctx.strokeStyle=col; ctx.lineWidth=1;
    ctx.beginPath();
    ctx.moveTo(x+bw/2, priceToY(c.high));
    ctx.lineTo(x+bw/2, priceToY(c.low));
    ctx.stroke();

    // Body
    const bodyTop = priceToY(Math.max(c.open,c.close));
    const bodyH   = Math.max(1, Math.abs(priceToY(c.open)-priceToY(c.close)));
    ctx.fillStyle = colD; ctx.fillRect(x,bodyTop,bw,bodyH);
    ctx.strokeStyle=col; ctx.strokeRect(x,bodyTop,bw,bodyH);
  });

  // Entry line
  const entryY = priceToY(1.08452);
  ctx.setLineDash([4,4]);
  ctx.strokeStyle='rgba(0,212,255,0.8)'; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(0,entryY); ctx.lineTo(W,entryY); ctx.stroke();
  ctx.fillStyle='rgba(0,212,255,0.9)'; ctx.font='9px JetBrains Mono';
  ctx.fillText('ENTRY 1.08452', W-100, entryY-3);

  // SL line
  const slY = priceToY(1.08200);
  ctx.strokeStyle='rgba(255,51,102,0.8)';
  ctx.beginPath(); ctx.moveTo(0,slY); ctx.lineTo(W,slY); ctx.stroke();
  ctx.fillStyle='rgba(255,51,102,0.9)';
  ctx.fillText('SL 1.08200', W-80, slY-3);

  // TP line
  const tpY = priceToY(1.09080);
  ctx.strokeStyle='rgba(0,255,136,0.8)';
  ctx.beginPath(); ctx.moveTo(0,tpY); ctx.lineTo(W,tpY); ctx.stroke();
  ctx.fillStyle='rgba(0,255,136,0.9)';
  ctx.fillText('TP 1.09080', W-80, tpY-3);

  ctx.setLineDash([]);

  // BUY arrow
  const lastX = (candles.length-1)*cw+cw/2;
  const lastY = priceToY(candles[candles.length-1].close);
  ctx.fillStyle='rgba(0,255,136,0.9)';
  ctx.beginPath();
  ctx.moveTo(lastX,lastY-20);
  ctx.lineTo(lastX-8,lastY-8);
  ctx.lineTo(lastX+8,lastY-8);
  ctx.closePath(); ctx.fill();
}

// ── EQUITY CHART ──
function drawEquity() {
  const canvas = document.getElementById('equityChart');
  const ctx = canvas.getContext('2d');
  canvas.width  = canvas.offsetWidth;
  canvas.height = canvas.offsetHeight;
  const W = canvas.width, H = canvas.height;

  // Fake equity data starting flat
  const pts = [];
  let val = 10000;
  for (let i=0;i<50;i++) {
    val += (Math.random()-0.45)*120;
    pts.push(val);
  }
  const minV = Math.min(...pts)*0.999;
  const maxV = Math.max(...pts)*1.001;
  const toY  = v => H - ((v-minV)/(maxV-minV))*(H*0.8) - H*0.1;
  const toX  = i => (i/(pts.length-1))*W;

  // Fill
  const grad = ctx.createLinearGradient(0,0,0,H);
  grad.addColorStop(0,'rgba(0,255,136,0.2)');
  grad.addColorStop(1,'rgba(0,255,136,0)');
  ctx.beginPath();
  ctx.moveTo(toX(0),H);
  pts.forEach((v,i)=>ctx.lineTo(toX(i),toY(v)));
  ctx.lineTo(toX(pts.length-1),H);
  ctx.closePath(); ctx.fillStyle=grad; ctx.fill();

  // Line
  ctx.beginPath(); ctx.strokeStyle='#00ff88'; ctx.lineWidth=2;
  pts.forEach((v,i)=>i===0?ctx.moveTo(toX(i),toY(v)):ctx.lineTo(toX(i),toY(v)));
  ctx.stroke();

  // Current value dot
  const lx=toX(pts.length-1), ly=toY(pts[pts.length-1]);
  ctx.beginPath(); ctx.arc(lx,ly,4,0,Math.PI*2);
  ctx.fillStyle='#00ff88'; ctx.fill();
  ctx.beginPath(); ctx.arc(lx,ly,8,0,Math.PI*2);
  ctx.strokeStyle='rgba(0,255,136,0.4)'; ctx.lineWidth=2; ctx.stroke();
}

// ── PAIR / TF SELECTION ──
let currentPair = 'EUR_USD';
let currentTF   = 'M15';

function selectPair(pair, btn) {
  document.querySelectorAll('.pair-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  currentPair = pair;
  document.getElementById('currentPair').textContent = pair.replace('_','/');
  document.getElementById('currentPrice').textContent =
    pair.includes('JPY') ? '149.850' :
    pair.includes('US30') ? '49,607' :
    pair.includes('SPX') ? '5,612' :
    pair.includes('NAS') ? '19,840' : '1.08450';
  drawChart();
  showNotif(`Switched to ${pair.replace('_','/')}`);
}

function selectTF(tf, btn) {
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  currentTF = tf;
  drawChart();
  showNotif(`Timeframe: ${tf}`);
}

// ── NOTIFICATION ──
function showNotif(msg) {
  const existing = document.querySelector('.notif');
  if (existing) existing.remove();
  const n = document.createElement('div');
  n.className = 'notif';
  n.textContent = msg;
  document.body.appendChild(n);
  setTimeout(()=>n.remove(), 3000);
}

// ── CYCLE COUNTER ──
let cycleCount = 0;
function runCycle() {
  cycleCount++;
  document.getElementById('cycleCount').textContent = cycleCount;
  // Fluctuate scores slightly
  const conf = 60 + Math.random()*20;
  document.getElementById('confBar').style.width = conf+'%';
  document.getElementById('confVal').textContent = conf.toFixed(0)+'%';
  drawChart();
}
setInterval(runCycle, 60000);

// ── INIT ──
window.addEventListener('load', ()=>{
  drawChart();
  drawEquity();
  setTimeout(()=>showNotif('PROJECT CHAKRA V10 — ALL SYSTEMS ONLINE'), 500);
});
window.addEventListener('resize', ()=>{ drawChart(); drawEquity(); });
</script>
</body>
</html>
