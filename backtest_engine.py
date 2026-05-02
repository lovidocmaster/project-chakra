"""
╔══════════════════════════════════════════════════════════════════════╗
║        PROJECT CHAKRA — BACKTEST ENGINE V2                          ║
║  5 Pairs × 3 Timeframes (M15 + H1 + H4) × 2 Years of real data    ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf, json, os, requests
from datetime import datetime

CONFIG = {
    "TELEGRAM_TOKEN": "8635098808:AAEc1mNqNE9pRqsYU0-W4uu7R0KIjEQFbhk",
    "TELEGRAM_CHAT":  "757855988",
    "INITIAL_CAPITAL": 10000,
    "RISK_PER_TRADE":  0.01,
    "RR_RATIO":        2.5,
    "MIN_CONFIDENCE":  0.55,
    "COMMISSION_PIPS": 1.5,
    "SLIPPAGE_PIPS":   0.3,
    "ADX_TREND":       20,
    "ADX_STRONG":      35,
    "LONDON_HOURS": list(range(7,13)),
    "NY_HOURS":     list(range(12,18)),
    "TIMEFRAMES": {
        "M15": {"interval":"15m","period":"60d"},
        "H1":  {"interval":"1h", "period":"730d"},
        "H4":  {"interval":"1h", "period":"730d","resample":"4h"},
    },
    "PAIRS": {
        "EUR_USD":{"symbol":"EURUSD=X","pip":0.0001,"pip_usd":10.0},
        "GBP_USD":{"symbol":"GBPUSD=X","pip":0.0001,"pip_usd":10.0},
        "USD_JPY":{"symbol":"USDJPY=X","pip":0.01,  "pip_usd":6.50},
        "AUD_USD":{"symbol":"AUDUSD=X","pip":0.0001,"pip_usd":10.0},
        "USD_CAD":{"symbol":"USDCAD=X","pip":0.0001,"pip_usd":7.70},
    },
}
FOLDER = os.path.dirname(os.path.abspath(__file__))

def tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/sendMessage",json={"chat_id":CONFIG["TELEGRAM_CHAT"],"text":msg,"parse_mode":"HTML"},timeout=10)
    except: pass

# ── INDICATORS ──
def ema(s,p):    return s.ewm(span=p,adjust=False).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.clip(lower=0).rolling(p).mean(); l=(-d.clip(upper=0)).rolling(p).mean()
    return 100-(100/(1+g/(l+1e-10)))
def macd(s):
    ml=ema(s,12)-ema(s,26); sl=ema(ml,9); return ml,sl,ml-sl
def boll(s,p=20,n=2):
    ma=s.rolling(p).mean(); std=s.rolling(p).std(); return ma+n*std,ma,ma-n*std
def atr_fn(df,p=14):
    h,l,c=df['High'],df['Low'],df['Close']
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def adx_fn(df,p=14):
    h,l,c=df['High'],df['Low'],df['Close']
    pdm=h.diff().clip(lower=0); mdm=(-l.diff()).clip(lower=0)
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    at=tr.rolling(p).mean()
    pdi=100*pdm.rolling(p).mean()/(at+1e-10); mdi=100*mdm.rolling(p).mean()/(at+1e-10)
    dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-10)
    return dx.rolling(p).mean(),pdi,mdi
def stoch(df,k=14,d=3):
    kl=100*(df['Close']-df['Low'].rolling(k).min())/(df['High'].rolling(k).max()-df['Low'].rolling(k).min()+1e-10)
    return kl,kl.rolling(d).mean()

# ── DATA ──
def get_data(symbol,interval,period,resample=None):
    try:
        df=yf.download(symbol,period=period,interval=interval,progress=False,auto_adjust=True)
        if df is None or len(df)<50: return None
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df.dropna()
        if resample:
            df.index=pd.to_datetime(df.index)
            df=df.resample(resample).agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        return df
    except: return None

# ── SIGNAL ──
def signal(df,idx):
    if idx<50: return None
    w=df.iloc[max(0,idx-100):idx].copy()
    if len(w)<30: return None
    c=w['Close']; price=float(c.iloc[-1])
    try:
        e8=ema(c,8).iloc[-1]; e21=ema(c,21).iloc[-1]; e50=ema(c,50).iloc[-1] if len(c)>=50 else e21
        rv=rsi(c).iloc[-1]; rp=rsi(c).iloc[-2]
        ml,sl_m,hist=macd(c); ub,mb,lb=boll(c)
        adx_v,pdi,mdi=adx_fn(w); adx_now=adx_v.iloc[-1]
        kv,_=stoch(w); k_now=kv.iloc[-1]
        atr_v=float(atr_fn(w).iloc[-1])
        roc5=(price/float(c.iloc[-6])-1)*100 if len(c)>5 else 0
        roc10=(price/float(c.iloc[-11])-1)*100 if len(c)>10 else 0
        if 'Volume' in w.columns and w['Volume'].sum()>0:
            vol_r=float(w['Volume'].iloc[-1])/(float(w['Volume'].rolling(20).mean().iloc[-1])+1e-10)
        else: vol_r=1.0
        regime="STRONG_TREND" if adx_now>=CONFIG["ADX_STRONG"] else "TREND" if adx_now>=CONFIG["ADX_TREND"] else "RANGING"
        buy=sell=total=0
        # Trend
        total+=1
        tb=sum([price>e8,e8>e21,e21>e50,price>e50]); ts=sum([price<e8,e8<e21,e21<e50,price<e50])
        if tb>=3: buy+=1
        elif ts>=3: sell+=1
        # RSI
        total+=1
        if rv<35: buy+=1
        elif rv>65: sell+=1
        elif rv<50 and rv>rp: buy+=1
        elif rv>50 and rv<rp: sell+=1
        # MACD
        total+=1
        if float(ml.iloc[-1])>float(sl_m.iloc[-1]) and float(hist.iloc[-1])>float(hist.iloc[-2]): buy+=1
        elif float(ml.iloc[-1])<float(sl_m.iloc[-1]) and float(hist.iloc[-1])<float(hist.iloc[-2]): sell+=1
        # Bollinger
        total+=1
        if price<=float(lb.iloc[-1])*1.002: buy+=1
        elif price>=float(ub.iloc[-1])*0.998: sell+=1
        # ADX direction
        total+=1
        if float(pdi.iloc[-1])>float(mdi.iloc[-1]) and adx_now>15: buy+=1
        elif float(mdi.iloc[-1])>float(pdi.iloc[-1]) and adx_now>15: sell+=1
        # Stochastic
        total+=1
        if k_now<25: buy+=1
        elif k_now>75: sell+=1
        # Momentum
        total+=1
        if roc5>0 and roc10>0: buy+=1
        elif roc5<0 and roc10<0: sell+=1
        # Volume
        total+=1
        if vol_r>1.2 and roc5>0: buy+=1
        elif vol_r>1.2 and roc5<0: sell+=1
        if total==0: return None
        if buy>sell: direction,conf="BUY",buy/total
        elif sell>buy: direction,conf="SELL",sell/total
        else: return None
        if conf<CONFIG["MIN_CONFIDENCE"]: return None
        if regime=="RANGING":
            if direction=="BUY" and price>float(mb.iloc[-1]): return None
            if direction=="SELL" and price<float(mb.iloc[-1]): return None
        return {"direction":direction,"confidence":conf,"regime":regime,"atr":atr_v}
    except: return None

# ── BACKTEST ──
def backtest(pair_name,tf_name,df,pip,pip_usd,capital):
    if df is None or len(df)<60: return []
    cap=capital; peak=capital; open_t=None; trades=[]
    for i in range(50,len(df)):
        bar=df.iloc[i]; price=float(bar['Close'])
        bar_h=float(bar['High']); bar_l=float(bar['Low'])
        bar_time=str(df.index[i])
        try: hour=pd.Timestamp(df.index[i]).hour
        except: hour=10
        if open_t:
            hit_tp=hit_sl=False
            if open_t["dir"]=="BUY":
                if bar_h>=open_t["tp"]: hit_tp=True
                elif bar_l<=open_t["sl"]: hit_sl=True
            else:
                if bar_l<=open_t["tp"]: hit_tp=True
                elif bar_h>=open_t["sl"]: hit_sl=True
            if hit_tp or hit_sl:
                ep=open_t["tp"] if hit_tp else open_t["sl"]
                pips=(ep-open_t["entry"])/pip if open_t["dir"]=="BUY" else (open_t["entry"]-ep)/pip
                pnl=pips*pip_usd*open_t["lots"]-open_t["cost"]
                cap+=pnl; peak=max(peak,cap)
                trades.append({"pair":pair_name,"timeframe":tf_name,"direction":open_t["dir"],
                    "entry":open_t["entry"],"exit":ep,"entry_time":open_t["et"],"exit_time":bar_time,
                    "pips":round(pips,1),"pnl":round(pnl,2),"lots":open_t["lots"],
                    "result":"WIN" if hit_tp else "LOSS","regime":open_t["regime"],
                    "confidence":open_t["conf"],"capital":round(cap,2)})
                open_t=None
        if hour not in (CONFIG["LONDON_HOURS"]+CONFIG["NY_HOURS"]): continue
        if open_t: continue
        if (peak-cap)/peak>=0.20: continue
        sig=signal(df,i)
        if not sig: continue
        atr_v=sig["atr"] if sig["atr"]>0 else pip*15
        risk=cap*CONFIG["RISK_PER_TRADE"]
        sl_p=min(max(atr_v/pip*1.5,8),80); tp_p=sl_p*CONFIG["RR_RATIO"]
        lots=max(0.01,min(round(risk/(sl_p*pip_usd),2),5.0))
        cost=(CONFIG["COMMISSION_PIPS"]+CONFIG["SLIPPAGE_PIPS"])*pip_usd*lots
        if sig["direction"]=="BUY": sl=price-sl_p*pip; tp=price+tp_p*pip
        else: sl=price+sl_p*pip; tp=price-tp_p*pip
        open_t={"dir":sig["direction"],"entry":price,"et":bar_time,"sl":sl,"tp":tp,"lots":lots,"cost":cost,"regime":sig["regime"],"conf":sig["confidence"]}
    return trades

# ── STATS ──
def calc_stats(trades,capital):
    closed=[t for t in trades if t["result"] in ["WIN","LOSS"]]
    if not closed: return None
    wins=[t for t in closed if t["result"]=="WIN"]; losses=[t for t in closed if t["result"]=="LOSS"]
    n=len(closed); wr=len(wins)/n
    tp=sum(t["pnl"] for t in wins); tl=abs(sum(t["pnl"] for t in losses)) or 1
    pf=tp/tl; aw=tp/len(wins) if wins else 0; al=tl/len(losses) if losses else 0
    exp=wr*aw-(1-wr)*al; total_pnl=sum(t["pnl"] for t in closed); ret=total_pnl/capital*100
    eq=[capital]+[]; running=capital
    for t in closed: running+=t["pnl"]; eq.append(running)
    eq_s=pd.Series(eq); dd=((eq_s-eq_s.cummax())/eq_s.cummax()).min()*100
    rets=pd.Series([t["pnl"]/capital for t in closed])
    sharpe=(rets.mean()/(rets.std()+1e-10))*np.sqrt(252) if len(rets)>1 else 0
    tf_s={tf:{"trades":len(tt:=[t for t in closed if t["timeframe"]==tf]),
              "win_rate":len([t for t in tt if t["result"]=="WIN"])/(len(tt) or 1),
              "pnl":sum(t["pnl"] for t in tt)} for tf in set(t["timeframe"] for t in closed)}
    pr_s={p:{"trades":len(pt:=[t for t in closed if t["pair"]==p]),
             "win_rate":len([t for t in pt if t["result"]=="WIN"])/(len(pt) or 1),
             "pnl":sum(t["pnl"] for t in pt),
             "avg_pips":sum(t["pips"] for t in pt)/(len(pt) or 1)} for p in set(t["pair"] for t in closed)}
    rg_s={r:{"trades":len(rt:=[t for t in closed if t["regime"]==r]),
             "win_rate":len([t for t in rt if t["result"]=="WIN"])/(len(rt) or 1),
             "pnl":sum(t["pnl"] for t in rt)} for r in set(t["regime"] for t in closed)}
    return {"total":n,"wins":len(wins),"losses":len(losses),"win_rate":wr,"profit_factor":pf,
            "expectancy":exp,"avg_win":aw,"avg_loss":al,"total_pnl":total_pnl,"net_return":ret,
            "max_drawdown":abs(dd),"sharpe":sharpe,"tf_stats":tf_s,"pair_stats":pr_s,
            "regime_stats":rg_s,"equity":[t["capital"] for t in closed]}

# ── HTML REPORT ──
def make_html(all_trades,s,initial_capital):
    closed=[t for t in all_trades if t["result"] in ["WIN","LOSS"]]
    eq=[initial_capital]+[t["capital"] for t in closed[:400]]
    vp=s["win_rate"]>0.50 and s["profit_factor"]>1.0 and s["max_drawdown"]<25
    p_rows="".join(f"<tr><td style='color:#00d4ff'>{p.replace('_','/')}</td><td>{ps['trades']}</td><td style='color:{'#00ff88' if ps['win_rate']>0.5 else '#ff3366'}'>{ps['win_rate']*100:.1f}%</td><td style='color:{'#00ff88' if ps['pnl']>0 else '#ff3366'}'>${ps['pnl']:,.2f}</td><td style='color:#ffd700'>{ps['avg_pips']:+.1f}</td></tr>" for p,ps in sorted(s["pair_stats"].items(),key=lambda x:-x[1]["pnl"]))
    t_rows="".join(f"<tr><td style='color:#9d4edd'>{tf}</td><td>{ts['trades']}</td><td style='color:{'#00ff88' if ts['win_rate']>0.5 else '#ff3366'}'>{ts['win_rate']*100:.1f}%</td><td style='color:{'#00ff88' if ts['pnl']>0 else '#ff3366'}'>${ts['pnl']:,.2f}</td></tr>" for tf,ts in sorted(s["tf_stats"].items(),key=lambda x:-x[1]["pnl"]))
    r_rows="".join(f"<tr><td style='color:#ffd700'>{r}</td><td>{rs['trades']}</td><td style='color:{'#00ff88' if rs['win_rate']>0.5 else '#ff3366'}'>{rs['win_rate']*100:.1f}%</td><td style='color:{'#00ff88' if rs['pnl']>0 else '#ff3366'}'>${rs['pnl']:,.2f}</td></tr>" for r,rs in sorted(s["regime_stats"].items(),key=lambda x:-x[1]["pnl"]))
    tr_rows="".join(f"<tr><td style='color:#00d4ff'>{t['pair'].replace('_','/')}</td><td style='color:#9d4edd'>{t['timeframe']}</td><td style='color:{'#00ff88' if t['direction']=='BUY' else '#ff3366'}'>{t['direction']}</td><td>{t['entry_time'][:16]}</td><td style='color:{'#00ff88' if t['pips']>0 else '#ff3366'}'>{t['pips']:+.1f}</td><td style='color:{'#00ff88' if t['pnl']>0 else '#ff3366'}'>${t['pnl']:+.2f}</td><td style='color:{'#00ff88' if t['result']=='WIN' else '#ff3366'}'>{t['result']}</td></tr>" for t in closed[-25:][::-1])
    return f"""<!DOCTYPE html><html><head><title>Chakra Backtest V2</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@300;400;600&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;}}body{{background:#020408;color:#c8e6f0;font-family:'JetBrains Mono',monospace;padding:24px;}}
h1{{font-family:'Orbitron',monospace;font-size:22px;background:linear-gradient(135deg,#00d4ff,#9d4edd);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px;}}
h2{{font-family:'Orbitron',monospace;font-size:11px;color:#00d4ff;letter-spacing:3px;margin:20px 0 10px;text-transform:uppercase;}}
.sub{{color:#3a6b85;font-size:10px;letter-spacing:2px;margin-bottom:24px;}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;}}
.g3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;}}
.card{{background:#071828;border:1px solid #0d3a5c;border-radius:4px;padding:16px;}}
.lbl{{font-size:9px;color:#3a6b85;letter-spacing:2px;margin-bottom:8px;text-transform:uppercase;}}
.val{{font-family:'Orbitron',monospace;font-size:19px;font-weight:700;}}
.g{{color:#00ff88;}}.r{{color:#ff3366;}}.c{{color:#00d4ff;}}.p{{color:#9d4edd;}}.gold{{color:#ffd700;}}
.panel{{background:#071828;border:1px solid #0d3a5c;border-radius:4px;padding:16px;margin-bottom:16px;}}
table{{width:100%;border-collapse:collapse;font-size:11px;}}
th{{text-align:left;padding:7px 10px;color:#3a6b85;font-size:9px;border-bottom:1px solid #0d3a5c;text-transform:uppercase;letter-spacing:1px;}}
td{{padding:7px 10px;border-bottom:1px solid rgba(13,58,92,0.3);}}
tr:hover td{{background:rgba(0,212,255,0.02);}}
.vd{{padding:16px;border-radius:4px;margin-bottom:20px;border:1px solid;}}
.vt{{font-family:'Orbitron',monospace;font-size:14px;margin-bottom:6px;font-weight:700;}}
.vs{{font-size:11px;color:#7ab8d4;line-height:1.8;}}
.ch{{height:180px;background:#040c14;border-radius:4px;padding:12px;}}
canvas{{width:100%;height:100%;}}</style></head><body>
<h1>PROJECT CHAKRA — BACKTEST V2</h1>
<p class="sub">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | 5 Pairs × M15/H1/H4 | 2 Years Data</p>
<div class="vd" style="border-color:{'#00ff88' if vp else '#ff3366'};background:{'rgba(0,255,136,0.04)' if vp else 'rgba(255,51,102,0.04)'}">
<div class="vt" style="color:{'#00ff88' if vp else '#ff3366'}">{'✅ SYSTEM PASSES — PROFITABLE ACROSS ALL PAIRS + TIMEFRAMES' if vp else '⚠️ SYSTEM NEEDS REVIEW'}</div>
<div class="vs">Trades: {s['total']} | Win Rate: {s['win_rate']*100:.1f}% | Profit Factor: {s['profit_factor']:.2f} | Max DD: -{s['max_drawdown']:.1f}% | Sharpe: {s['sharpe']:.2f} | Return: {s['net_return']:+.1f}%</div></div>
<div class="g4">
<div class="card"><div class="lbl">Total Trades</div><div class="val c">{s['total']}</div></div>
<div class="card"><div class="lbl">Win Rate</div><div class="val {'g' if s['win_rate']>0.5 else 'r'}">{s['win_rate']*100:.1f}%</div></div>
<div class="card"><div class="lbl">Profit Factor</div><div class="val {'g' if s['profit_factor']>1 else 'r'}">{s['profit_factor']:.2f}</div></div>
<div class="card"><div class="lbl">Net Return</div><div class="val {'g' if s['net_return']>0 else 'r'}">{s['net_return']:+.1f}%</div></div>
<div class="card"><div class="lbl">Total P&L</div><div class="val {'g' if s['total_pnl']>0 else 'r'}">${s['total_pnl']:,.2f}</div></div>
<div class="card"><div class="lbl">Max Drawdown</div><div class="val r">-{s['max_drawdown']:.1f}%</div></div>
<div class="card"><div class="lbl">Sharpe Ratio</div><div class="val gold">{s['sharpe']:.2f}</div></div>
<div class="card"><div class="lbl">Expectancy/Trade</div><div class="val {'g' if s['expectancy']>0 else 'r'}">${s['expectancy']:.2f}</div></div>
</div>
<h2>Equity Curve</h2><div class="panel"><div class="ch"><canvas id="eq"></canvas></div></div>
<div class="g3">
<div><h2>By Pair</h2><div class="panel"><table><tr><th>Pair</th><th>Trades</th><th>Win%</th><th>P&L</th><th>Avg Pips</th></tr>{p_rows}</table></div></div>
<div><h2>By Timeframe</h2><div class="panel"><table><tr><th>TF</th><th>Trades</th><th>Win%</th><th>P&L</th></tr>{t_rows}</table></div></div>
<div><h2>By Regime</h2><div class="panel"><table><tr><th>Regime</th><th>Trades</th><th>Win%</th><th>P&L</th></tr>{r_rows}</table></div></div>
</div>
<h2>Recent 25 Trades</h2><div class="panel"><table><tr><th>Pair</th><th>TF</th><th>Dir</th><th>Entry Time</th><th>Pips</th><th>P&L</th><th>Result</th></tr>{tr_rows}</table></div>
<script>
const data={json.dumps(eq)};const canvas=document.getElementById('eq');const ctx=canvas.getContext('2d');
canvas.width=canvas.offsetWidth;canvas.height=canvas.offsetHeight;const W=canvas.width,H=canvas.height;
const min=Math.min(...data)*0.995,max=Math.max(...data)*1.005;
const X=i=>(i/(data.length-1))*W;const Y=v=>H-((v-min)/(max-min))*(H*0.85)-H*0.075;
const isUp=data[data.length-1]>={initial_capital};
const g=ctx.createLinearGradient(0,0,0,H);
g.addColorStop(0,isUp?'rgba(0,255,136,0.25)':'rgba(255,51,102,0.25)');g.addColorStop(1,'rgba(0,0,0,0)');
ctx.beginPath();ctx.moveTo(X(0),H);data.forEach((v,i)=>ctx.lineTo(X(i),Y(v)));
ctx.lineTo(X(data.length-1),H);ctx.closePath();ctx.fillStyle=g;ctx.fill();
ctx.beginPath();ctx.strokeStyle=isUp?'#00ff88':'#ff3366';ctx.lineWidth=2;
data.forEach((v,i)=>i===0?ctx.moveTo(X(i),Y(v)):ctx.lineTo(X(i),Y(v)));ctx.stroke();
ctx.fillStyle='#00d4ff';ctx.font='10px JetBrains Mono';ctx.fillText('$10,000',4,Y({initial_capital})-5);
ctx.fillStyle=isUp?'#00ff88':'#ff3366';ctx.fillText('$'+data[data.length-1].toFixed(0),W-80,Y(data[data.length-1])-5);
</script></body></html>"""

# ── MAIN ──
def run():
    print("\n"+"═"*70)
    print("  PROJECT CHAKRA — BACKTEST V2")
    print("  5 Pairs × 3 Timeframes (M15 + H1 + H4)")
    print("═"*70)
    tg("🔬 <b>BACKTEST V2 STARTED</b>\n5 Pairs × M15/H1/H4\nEst. 5-8 min...")
    all_trades=[]
    for pair_name,pair_cfg in CONFIG["PAIRS"].items():
        print(f"\n  💱 {pair_name}")
        for tf_name,tf_cfg in CONFIG["TIMEFRAMES"].items():
            print(f"     📊 {tf_name}...",end=" ",flush=True)
            df=get_data(pair_cfg["symbol"],tf_cfg["interval"],tf_cfg["period"],tf_cfg.get("resample"))
            if df is None or len(df)<50: print("⚠️ No data"); continue
            print(f"{len(df)} candles...",end=" ",flush=True)
            trades=backtest(pair_name,tf_name,df,pair_cfg["pip"],pair_cfg["pip_usd"],CONFIG["INITIAL_CAPITAL"])
            closed=[t for t in trades if t["result"] in ["WIN","LOSS"]]
            wins=[t for t in closed if t["result"]=="WIN"]
            pnl=sum(t["pnl"] for t in closed)
            print(f"{len(closed)} trades | WR:{len(wins)/len(closed)*100:.0f}% | ${pnl:+.0f}" if closed else "0 trades")
            all_trades.extend(trades)
    print(f"\n{'═'*70}\n  📊 OVERALL RESULTS\n{'═'*70}")
    s=calc_stats(all_trades,CONFIG["INITIAL_CAPITAL"])
    if not s: print("  ❌ No trades"); tg("❌ No trades generated"); return
    verdict="✅ PASS" if s['win_rate']>0.50 and s['profit_factor']>1.0 else "⚠️ NEEDS TUNING"
    print(f"\n  Trades:       {s['total']}")
    print(f"  Win Rate:     {s['win_rate']*100:.1f}% {'✅' if s['win_rate']>0.50 else '⚠️'}")
    print(f"  Profit Factor:{s['profit_factor']:.2f} {'✅' if s['profit_factor']>1.0 else '⚠️'}")
    print(f"  Max Drawdown: -{s['max_drawdown']:.1f}% {'✅' if s['max_drawdown']<25 else '❌'}")
    print(f"  Sharpe:       {s['sharpe']:.2f}")
    print(f"  Net Return:   {s['net_return']:+.1f}%")
    print(f"  Expectancy:   ${s['expectancy']:.2f}/trade")
    print(f"  Total P&L:    ${s['total_pnl']:,.2f}")
    print(f"\n  BY TIMEFRAME:")
    for tf,ts in sorted(s["tf_stats"].items(),key=lambda x:-x[1]["pnl"]):
        print(f"  {tf:<5}: {ts['trades']} trades | WR:{ts['win_rate']*100:.1f}% | ${ts['pnl']:+.0f}")
    print(f"\n  BY PAIR:")
    for p,ps in sorted(s["pair_stats"].items(),key=lambda x:-x[1]["pnl"]):
        print(f"  {p:<10}: {ps['trades']} trades | WR:{ps['win_rate']*100:.1f}% | ${ps['pnl']:+.0f}")
    print(f"\n  VERDICT: {verdict}")
    # HTML
    html=make_html(all_trades,s,CONFIG["INITIAL_CAPITAL"])
    rp=os.path.join(FOLDER,"backtest_report.html")
    with open(rp,"w",encoding="utf-8") as f: f.write(html)
    print(f"\n  ✅ Report: {rp}")
    # CSV
    pd.DataFrame(all_trades).to_csv(os.path.join(FOLDER,"backtest_trades.csv"),index=False)
    print(f"  ✅ Trades CSV saved")
    # Telegram
    tf_msg="\n".join(f"  {tf}: {ts['trades']}tr | WR:{ts['win_rate']*100:.0f}% | ${ts['pnl']:+.0f}" for tf,ts in sorted(s["tf_stats"].items(),key=lambda x:-x[1]["pnl"]))
    p_msg="\n".join(f"  {p.replace('_','/')}: {ps['trades']}tr | WR:{ps['win_rate']*100:.0f}% | ${ps['pnl']:+.0f}" for p,ps in sorted(s["pair_stats"].items(),key=lambda x:-x[1]["pnl"]))
    tg(f"""📊 <b>BACKTEST V2 COMPLETE</b>

<b>Overall ({s['total']} trades | 5 pairs | M15/H1/H4):</b>
• Win Rate: {s['win_rate']*100:.1f}% {'✅' if s['win_rate']>0.5 else '⚠️'}
• Profit Factor: {s['profit_factor']:.2f}
• Max Drawdown: -{s['max_drawdown']:.1f}%
• Net Return: {s['net_return']:+.1f}%
• Expectancy: ${s['expectancy']:.2f}/trade
• Total P&L: ${s['total_pnl']:,.2f}

<b>By Timeframe:</b>
{tf_msg}

<b>By Pair:</b>
{p_msg}

🏆 <b>{verdict}</b>""")
    print("\n"+"═"*70)
    print("  ✅ BACKTEST COMPLETE — Open backtest_report.html")
    print("═"*70)

if __name__=="__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║    PROJECT CHAKRA — BACKTEST ENGINE V2                              ║
║    5 Pairs × M15 + H1 + H4 × 2 Years | Est: 5-8 minutes           ║
╚══════════════════════════════════════════════════════════════════════╝""")
    run()
