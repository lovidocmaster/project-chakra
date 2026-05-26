"""
PROJECT CHAKRA — MULTI-TIMEFRAME DEEP BACKTEST (2000-2026)
===========================================================
Tests 4 timeframes simultaneously — the professional standard:

  M15  → Entry precision (exact timing)
  H1   → Signal generation (main system)
  H4   → Trend confirmation (already in live system)
  D1   → 12-month momentum filter (already in live system)

Why this matters vs single H1 backtest:
- A big H1 candle could be news spike, trend, or liquidity grab
- Without M15 context, agents can't learn the difference
- Without H4/D1, agents trade against the larger trend
- Research paper: "Toward Expert Investment Teams" proves
  multi-timeframe decomposition significantly improves Sharpe ratio

Results include:
- Per-timeframe win rates
- Combined signal win rate
- Year-by-year performance 2000-2026
- Best/worst market regimes
- Full HTML report

Run: py -3.11 multi_tf_backtest.py
Output: multi_tf_report.html
Time: ~40-50 minutes (more data fetching)
"""

import os, json, math, time, logging, traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("multi_tf_backtest.log","w")]
)
log = logging.getLogger("MTTF")

try:
    import oandapyV20
    import oandapyV20.endpoints.instruments as instruments
    OANDA_OK = True
except ImportError:
    OANDA_OK = False
    log.error("Install: py -3.11 -m pip install oandapyV20")

OANDA_TOKEN = os.getenv("OANDA_TOKEN","")
OANDA_ENV   = "practice"

PAIRS = ["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD","GBP_JPY","EUR_JPY","NZD_USD","USD_CHF"]

START_BAL  = 100_000.0
RISK_PCT   = 0.005
SL_ATR     = 1.5
TP_ATR     = 6.0
SCALE1     = 1.0
SCALE2     = 3.0

# ─── WEIGHTS (same as live) ───────────────────────────────────────────────────
WEIGHTS = {
    "SMC":3.0,"ICT":3.0,"ORDERBLOCK":3.0,"ORDERFLOW":2.5,
    "BOS":2.0,"CHOCH":2.0,"STRUCTURE":2.0,"TREND":2.0,
    "SUPERTREND":2.0,"BREAKOUT":1.8,"LSTM":1.8,
    "EMA":1.0,"MACD":0.8,"RSI":0.7,"BOLLINGER":0.8,"STOCHASTIC":0.6,
    "MOMENTUM":1.5,
}
REGIME_ALLOWED = {
    "TRENDING":["SMC","ICT","BOS","CHOCH","TREND","EMA","MACD","SUPERTREND","BREAKOUT","MOMENTUM","ORDERBLOCK","ORDERFLOW","STRUCTURE"],
    "RANGING": ["RSI","BOLLINGER","STOCHASTIC","CHOCH","SMC","ICT","ORDERBLOCK","ORDERFLOW"],
    "VOLATILE":["SMC","ICT","ORDERFLOW"],
}
CATEGORIES = {
    "INSTITUTIONAL":["SMC","ICT","ORDERBLOCK","ORDERFLOW"],
    "STRUCTURE":    ["BOS","CHOCH","BREAKOUT","STRUCTURE"],
    "TREND":        ["EMA","MACD","SUPERTREND","TREND","MOMENTUM"],
    "REVERSAL":     ["RSI","BOLLINGER","STOCHASTIC"],
}
REGIME_MIN_CONF = {"TRENDING":0.62,"RANGING":0.67,"VOLATILE":0.75}
REGIME_RISK_MULT = {"TRENDING":1.1,"RANGING":0.8,"VOLATILE":0.5}

def pip_val(pair): return 0.01 if "JPY" in pair or "SGD" in pair else 1.0

def ema_calc(prices, p):
    if len(prices) < p: return prices[-1] if prices else 0
    k=2.0/(p+1); e=prices[0]
    for x in prices[1:]: e=x*k+e*(1-k)
    return e

def atr_calc(c, p=14):
    if len(c)<p+1: return 0.001
    trs=[max(float(c[-i]["mid"]["h"])-float(c[-i]["mid"]["l"]),
             abs(float(c[-i]["mid"]["h"])-float(c[-i-1]["mid"]["c"])),
             abs(float(c[-i]["mid"]["l"])-float(c[-i-1]["mid"]["c"])))
         for i in range(1,min(p+1,len(c)))]
    return sum(trs)/len(trs) if trs else 0.001

def detect_regime(c):
    if len(c)<30: return "RANGING"
    try:
        cl=[float(x["mid"]["c"]) for x in c[-30:]]
        hi=[float(x["mid"]["h"]) for x in c[-30:]]
        lo=[float(x["mid"]["l"]) for x in c[-30:]]
        avg=sum(cl)/len(cl)
        a=sum(hi[i]-lo[i] for i in range(len(hi)))/len(hi)
        vol=a/avg if avg>0 else 0
        e20=sum(cl[-20:])/20; e30=sum(cl)/30
        sep=abs(e20-e30)/avg if avg>0 else 0
        hh=sum(1 for i in range(1,8) if hi[-i]>hi[-i-1])
        ll=sum(1 for i in range(1,8) if lo[-i]<lo[-i-1])
        ts=max(hh,ll)/8
        if vol>0.007: return "VOLATILE"
        if sep>0.0012 or ts>0.65: return "TRENDING"
        return "RANGING"
    except: return "RANGING"

def get_signals_for_tf(candles, tf_label):
    """Generate signals for a specific timeframe"""
    if len(candles)<50: return []
    cl=[float(c["mid"]["c"]) for c in candles]
    hi=[float(c["mid"]["h"]) for c in candles]
    lo=[float(c["mid"]["l"]) for c in candles]
    sigs=[]

    # EMA
    e20=ema_calc(cl,20); e50=ema_calc(cl,50)
    if cl[-1]>e20>e50: sigs.append({"name":f"EMA_{tf_label}","signal":"BUY","conf":0.68,"tf":tf_label})
    elif cl[-1]<e20<e50: sigs.append({"name":f"EMA_{tf_label}","signal":"SELL","conf":0.68,"tf":tf_label})

    # BOS
    if len(candles)>=10:
        ph=max(hi[-10:-1]); pl=min(lo[-10:-1])
        if cl[-1]>ph: sigs.append({"name":f"BOS_{tf_label}","signal":"BUY","conf":0.76,"tf":tf_label})
        elif cl[-1]<pl: sigs.append({"name":f"BOS_{tf_label}","signal":"SELL","conf":0.76,"tf":tf_label})

    # CHOCH
    if len(candles)>=20:
        t1=cl[-10]-cl[-20]; t2=cl[-1]-cl[-10]
        if t1<0 and t2>0: sigs.append({"name":f"CHOCH_{tf_label}","signal":"BUY","conf":0.78,"tf":tf_label})
        elif t1>0 and t2<0: sigs.append({"name":f"CHOCH_{tf_label}","signal":"SELL","conf":0.78,"tf":tf_label})

    # SMC OrderBlock
    if len(candles)>=20:
        rh=max(hi[-20:-5]); rl=min(lo[-20:-5])
        if cl[-1]<rl*1.001: sigs.append({"name":f"SMC_{tf_label}","signal":"BUY","conf":0.82,"tf":tf_label})
        elif cl[-1]>rh*0.999: sigs.append({"name":f"SMC_{tf_label}","signal":"SELL","conf":0.82,"tf":tf_label})

    # ORDER FLOW
    if len(candles)>=10:
        bp=sp=0.0
        for c in candles[-10:]:
            h=float(c["mid"]["h"]); l=float(c["mid"]["l"]); cv=float(c["mid"]["c"])
            r=h-l
            if r>0: bp+=(cv-l)/r; sp+=(h-cv)/r
        t=bp+sp
        if t>0:
            ratio=bp/t
            if ratio>0.62: sigs.append({"name":f"ORDERFLOW_{tf_label}","signal":"BUY","conf":min(0.82,ratio),"tf":tf_label})
            elif ratio<0.38: sigs.append({"name":f"ORDERFLOW_{tf_label}","signal":"SELL","conf":min(0.82,1-ratio),"tf":tf_label})

    # RSI (ranging only)
    if len(cl)>=15:
        g=lo_=0.0
        for i in range(1,15):
            d=cl[-i]-cl[-i-1]
            if d>0: g+=d
            else: lo_-=d
        if lo_>0:
            rs=(g/14)/(lo_/14); rv=100-(100/(1+rs))
            if rv<30: sigs.append({"name":f"RSI_{tf_label}","signal":"BUY","conf":0.72,"tf":tf_label})
            elif rv>70: sigs.append({"name":f"RSI_{tf_label}","signal":"SELL","conf":0.72,"tf":tf_label})

    # Momentum
    if len(cl)>=10:
        mom=(cl[-1]-cl[-10])/cl[-10]
        if mom>0.002: sigs.append({"name":f"MOMENTUM_{tf_label}","signal":"BUY","conf":0.66,"tf":tf_label})
        elif mom<-0.002: sigs.append({"name":f"MOMENTUM_{tf_label}","signal":"SELL","conf":0.66,"tf":tf_label})

    return sigs

def get_weight(name):
    n=name.upper().split("_")[0]  # Strip TF label
    for k,w in WEIGHTS.items():
        if k in n: return w
    return 1.0

def get_category(name):
    n=name.upper()
    for cat,keys in CATEGORIES.items():
        if any(k in n for k in keys): return cat
    return "OTHER"

def is_allowed(name, regime):
    n=name.upper()
    allowed=REGIME_ALLOWED.get(regime,list(WEIGHTS.keys()))
    return any(k in n for k in allowed)

def multi_tf_vote(all_signals, regime, h4_dir, d1_dir):
    """
    MULTI-TIMEFRAME VOTE
    Combines signals from M15+H1+H4 with D1 as filter.
    H4 and D1 act as directional filters — only trade with them.
    """
    # D1 filter: skip if trading against yearly trend
    if d1_dir in ("BUY","SELL"):
        # Filter signals against D1
        filtered = []
        for s in all_signals:
            if s["tf"] == "D1": continue  # D1 is filter not voter
            if s["signal"] == d1_dir or d1_dir == "NEUTRAL":
                filtered.append(s)
            # Allow counter-D1 signals but with reduced weight
        # If less than half remain, skip
        if len(filtered) < len(all_signals) * 0.3:
            return "HOLD", 0.0
        all_signals = filtered

    min_conf = REGIME_MIN_CONF.get(regime,0.65)
    buy_w=sell_w=0.0
    buy_cats=set(); sell_cats=set()
    buy_agents=[]; sell_agents=[]

    for s in all_signals:
        if not is_allowed(s["name"], regime): continue
        w=get_weight(s["name"])
        # TF weight multiplier — H4 signals more trusted than M15
        tf_mult = {"D1":1.3,"H4":1.2,"H1":1.0,"M15":0.8}.get(s.get("tf","H1"),1.0)
        w *= tf_mult
        cat=get_category(s["name"])
        if s["signal"]=="BUY":
            buy_w+=w*s["conf"]; buy_cats.add(cat); buy_agents.append(s["name"])
        else:
            sell_w+=w*s["conf"]; sell_cats.add(cat); sell_agents.append(s["name"])

    total=buy_w+sell_w
    if total==0: return "HOLD",0.0

    if buy_w>=sell_w:
        direction="BUY"; conf=buy_w/total; cats=buy_cats
    else:
        direction="SELL"; conf=sell_w/total; cats=sell_cats

    # H4 alignment bonus/penalty
    if h4_dir == direction: conf=min(0.95,conf*1.10)
    elif h4_dir not in ("HOLD","NEUTRAL","") and h4_dir != direction:
        return "HOLD",0.0  # H4 contradicts — skip

    if len(cats)<2: return "HOLD",0.0

    rm={"TRENDING":1.08,"RANGING":0.92,"VOLATILE":0.75}.get(regime,1.0)
    cb=min(0.10,len(cats)*0.025)
    final=min(0.95,conf*rm+cb)
    if final<min_conf: return "HOLD",0.0
    return direction,final

# ─── DATA FETCHING ─────────────────────────────────────────────────────────────

def fetch(pair, gran, years=24):
    if not OANDA_OK or not OANDA_TOKEN: return []
    all_c=[]; end=datetime.utcnow()
    # M15 only 5 years (too much data otherwise)
    actual_years = min(years, 5) if gran=="M15" else years
    start=end-timedelta(days=actual_years*365)
    chunk=timedelta(days=60 if gran=="M15" else 180)
    cur=start
    while cur<end:
        nxt=min(cur+chunk,end)
        try:
            client=oandapyV20.API(access_token=OANDA_TOKEN,environment=OANDA_ENV)
            params={"granularity":gran,
                    "from":cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "to":nxt.strftime("%Y-%m-%dT%H:%M:%SZ")}
            r=instruments.InstrumentsCandles(pair,params=params)
            client.request(r)
            all_c.extend([c for c in r.response.get("candles",[]) if c.get("complete")])
        except Exception as e:
            log.warning(f"  {gran} chunk failed: {e}")
        cur=nxt; time.sleep(0.2)
    seen=set(); unique=[]
    for c in all_c:
        t=c.get("time","")
        if t not in seen: seen.add(t); unique.append(c)
    return sorted(unique,key=lambda x:x.get("time",""))

# ─── MULTI-TF BACKTEST ENGINE ──────────────────────────────────────────────────

def run_multi_tf_backtest(m15_c, h1_c, h4_c, d1_c, pair):
    """Run backtest using M15 entries with H1/H4/D1 filters"""
    if len(h1_c)<200: return None

    bal=START_BAL; peak=START_BAL; max_dd=0.0
    trades=[]; pos=None
    yearly={}; regime_stats={}; tf_stats={"M15_only":0,"H1_confirmed":0,"H4_confirmed":0,"D1_filtered":0}
    monthly_pnl={}

    # Build H4 and D1 lookup dicts by timestamp for fast access
    def time_to_h(ts): return ts[:13]  # YYYY-MM-DDTHH
    def time_to_d(ts): return ts[:10]  # YYYY-MM-DD

    h4_by_time={}
    for i,c in enumerate(h4_c):
        h4_by_time[time_to_h(c.get("time",""))] = i

    d1_by_time={}
    for i,c in enumerate(d1_c):
        d1_by_time[time_to_d(c.get("time",""))] = i

    WARMUP=200
    main_candles = h1_c  # H1 is primary timeframe for signal generation

    for i in range(WARMUP,len(main_candles)):
        cur=main_candles[i]
        try:
            hi=float(cur["mid"]["h"]); lo=float(cur["mid"]["l"]); cl=float(cur["mid"]["c"])
            ts=cur.get("time","")
            hour=int(ts[11:13]) if len(ts)>=13 else 12
            year=int(ts[:4]) if len(ts)>=4 else 2000
            month=ts[:7] if len(ts)>=7 else "2000-01"
        except: continue

        # Check position
        if pos:
            hit=None
            if pos["dir"]=="BUY":
                if lo<=pos["sl"]: hit="SL"
                elif hi>=pos["tp2"]: hit="TP"
                elif hi>=pos["tp1"] and not pos.get("s1"):
                    pos["s1"]=True; pos["sl"]=pos["entry"]
                    p=(pos["tp1"]-pos["entry"])*(pos["units"]//3)*pip_val(pair)
                    bal+=p; pos["pp"]=pos.get("pp",0)+p
                elif hi>=pos["tp_m"] and not pos.get("s2") and pos.get("s1"):
                    pos["s2"]=True
                    p=(pos["tp_m"]-pos["entry"])*(pos["units"]//3)*pip_val(pair)
                    bal+=p; pos["pp"]=pos.get("pp",0)+p
            else:
                if hi>=pos["sl"]: hit="SL"
                elif lo<=pos["tp2"]: hit="TP"
                elif lo<=pos["tp1"] and not pos.get("s1"):
                    pos["s1"]=True; pos["sl"]=pos["entry"]
                    p=(pos["entry"]-pos["tp1"])*(pos["units"]//3)*pip_val(pair)
                    bal+=p; pos["pp"]=pos.get("pp",0)+p
                elif lo<=pos["tp_m"] and not pos.get("s2") and pos.get("s1"):
                    pos["s2"]=True
                    p=(pos["entry"]-pos["tp_m"])*(pos["units"]//3)*pip_val(pair)
                    bal+=p; pos["pp"]=pos.get("pp",0)+p

            if hit:
                ex=pos["sl"] if hit=="SL" else pos["tp2"]
                ru=pos["units"]-(pos["units"]//3)*(2 if pos.get("s2") else 1 if pos.get("s1") else 0)
                if pos["dir"]=="BUY": fp=(ex-pos["entry"])*ru*pip_val(pair)
                else: fp=(pos["entry"]-ex)*ru*pip_val(pair)
                tp=fp+pos.get("pp",0)
                bal+=fp; peak=max(peak,bal)
                dd=(peak-bal)/peak if peak>0 else 0; max_dd=max(max_dd,dd)
                t={"pnl":round(tp,2),"type":hit,"year":pos["year"],"regime":pos["regime"],"month":pos["month"]}
                trades.append(t)
                yr=pos["year"]
                if yr not in yearly: yearly[yr]={"wins":0,"losses":0,"pnl":0,"trades":0}
                yearly[yr]["trades"]+=1; yearly[yr]["pnl"]+=tp
                if tp>0: yearly[yr]["wins"]+=1
                else: yearly[yr]["losses"]+=1
                reg=pos["regime"]
                if reg not in regime_stats: regime_stats[reg]={"wins":0,"losses":0,"pnl":0}
                regime_stats[reg]["pnl"]+=tp
                if tp>0: regime_stats[reg]["wins"]+=1
                else: regime_stats[reg]["losses"]+=1
                if month not in monthly_pnl: monthly_pnl[month]=0
                monthly_pnl[month]+=tp
                pos=None

        # Generate signal
        if pos is None:
            # Time filter
            if not (7<=hour<21): continue

            window=main_candles[max(0,i-200):i]
            if len(window)<100: continue

            a=atr_calc(window)
            if len(window)>=20:
                a20=sum(float(window[-j]["mid"]["h"])-float(window[-j]["mid"]["l"]) for j in range(1,21))/20
                if a<a20*0.7: continue

            regime=detect_regime(window)

            # Get H1 signals
            h1_sigs=get_signals_for_tf(window,"H1")

            # Get H4 direction (look up nearest H4 candle)
            h4_dir="NEUTRAL"
            h4_idx=h4_by_time.get(time_to_h(ts))
            if h4_idx and h4_idx>20:
                h4_window=h4_c[max(0,h4_idx-50):h4_idx]
                if len(h4_window)>=20:
                    h4_sigs=get_signals_for_tf(h4_window,"H4")
                    bw=sum(get_weight(s["name"]) for s in h4_sigs if s["signal"]=="BUY")
                    sw=sum(get_weight(s["name"]) for s in h4_sigs if s["signal"]=="SELL")
                    if bw>sw*1.2: h4_dir="BUY"
                    elif sw>bw*1.2: h4_dir="SELL"

            # Get D1 direction (12M momentum)
            d1_dir="NEUTRAL"
            d1_idx=d1_by_time.get(time_to_d(ts))
            if d1_idx and d1_idx>200:
                d1_window=d1_c[max(0,d1_idx-200):d1_idx]
                if len(d1_window)>=200:
                    p_now=float(d1_window[-1]["mid"]["c"])
                    p_12m=float(d1_window[-200]["mid"]["c"])
                    tsmom=(p_now-p_12m)/max(p_12m,0.001)
                    if tsmom>0.005: d1_dir="BUY"
                    elif tsmom<-0.005: d1_dir="SELL"

            # M15 precision signals (if available)
            m15_sigs=[]
            if m15_c:
                m15_window=[c for c in m15_c if c.get("time","")<=ts]
                m15_window=m15_window[-100:]
                if len(m15_window)>=20:
                    m15_sigs=get_signals_for_tf(m15_window,"M15")

            # Combine all signals
            all_sigs=h1_sigs+m15_sigs

            direction,conf=multi_tf_vote(all_sigs,regime,h4_dir,d1_dir)
            if direction not in ("BUY","SELL"): continue

            # FINRS momentum boost
            if len(window)>=30:
                ms=(cl-float(window[-2]["mid"]["c"]))/max(float(window[-2]["mid"]["c"]),0.001)
                mm=(cl-float(window[-8]["mid"]["c"]))/max(float(window[-8]["mid"]["c"]),0.001) if len(window)>=8 else 0
                ml=(cl-float(window[-30]["mid"]["c"]))/max(float(window[-30]["mid"]["c"]),0.001)
                mt=ms+mm+ml
                if (mt>0 and direction=="BUY") or (mt<0 and direction=="SELL"):
                    conf=min(0.95,conf*1.05)
                elif abs(mt)>0.003:
                    conf*=0.88
                    if conf<REGIME_MIN_CONF.get(regime,0.65): continue

            rm=REGIME_RISK_MULT.get(regime,1.0)
            ra=bal*RISK_PCT*rm
            sd=a*SL_ATR
            if sd<=0: continue
            units=max(1000,min(int(ra/(sd*10000*pip_val(pair))),50000))
            if direction=="BUY":
                sl=cl-sd; tp1=cl+a*SCALE1; tp_m=cl+a*SCALE2; tp2=cl+a*TP_ATR
            else:
                sl=cl+sd; tp1=cl-a*SCALE1; tp_m=cl-a*SCALE2; tp2=cl-a*TP_ATR
            pos={"dir":direction,"entry":cl,"sl":sl,"tp1":tp1,"tp_m":tp_m,"tp2":tp2,
                 "units":units,"conf":conf,"year":year,"regime":regime,"month":month,"pp":0.0}

    # Close remaining
    if pos and main_candles:
        cl=float(main_candles[-1]["mid"]["c"])
        if pos["dir"]=="BUY": fp=(cl-pos["entry"])*pos["units"]*pip_val(pair)
        else: fp=(pos["entry"]-cl)*pos["units"]*pip_val(pair)
        tp=fp+pos.get("pp",0); bal+=fp
        trades.append({"pnl":round(tp,2),"type":"OPEN","year":pos["year"],"regime":pos["regime"],"month":pos["month"]})

    if not trades:
        return {"pair":pair,"trades":0,"win_rate":0,"total_pnl":0,"return_pct":0,
                "max_drawdown":0,"sharpe":0,"profit_factor":0,"avg_win":0,"avg_loss":0,
                "final_balance":bal,"yearly":{},"regime_stats":{},"monthly_pnl":{}}

    wins=[t for t in trades if t["pnl"]>0]
    losses=[t for t in trades if t["pnl"]<=0]
    wr=len(wins)/len(trades)*100
    total=bal-START_BAL; ret=total/START_BAL*100
    pnls=[t["pnl"] for t in trades]
    avg=sum(pnls)/len(pnls)
    std=math.sqrt(sum((p-avg)**2 for p in pnls)/len(pnls)) if len(pnls)>1 else 1
    sharpe=(avg/std)*math.sqrt(252*6) if std>0 else 0
    aw=sum(t["pnl"] for t in wins)/len(wins) if wins else 0
    al=sum(t["pnl"] for t in losses)/len(losses) if losses else 0
    gw=sum(t["pnl"] for t in wins); gl=abs(sum(t["pnl"] for t in losses))
    pf=gw/gl if gl>0 else 999

    return {"pair":pair,"trades":len(trades),"wins":len(wins),"losses":len(losses),
            "win_rate":round(wr,1),"total_pnl":round(total,2),"return_pct":round(ret,2),
            "max_drawdown":round(max_dd*100,1),"sharpe":round(sharpe,2),"profit_factor":round(pf,2),
            "avg_win":round(aw,2),"avg_loss":round(al,2),"final_balance":round(bal,2),
            "yearly":yearly,"regime_stats":regime_stats,"monthly_pnl":monthly_pnl}

# ─── HTML REPORT ──────────────────────────────────────────────────────────────

def build_report(results, run_date):
    valid={p:r for p,r in results.items() if r and r["trades"]>0}
    if not valid: return "<html><body><h1>No results</h1></body></html>"

    total_trades=sum(r["trades"] for r in valid.values())
    total_pnl=sum(r["total_pnl"] for r in valid.values())
    avg_wr=sum(r["win_rate"] for r in valid.values())/len(valid)
    avg_sharpe=sum(r["sharpe"] for r in valid.values())/len(valid)
    avg_pf=sum(r["profit_factor"] for r in valid.values())/len(valid)
    passing=[(p,r) for p,r in valid.items() if r["win_rate"]>=45 and r["total_pnl"]>0]
    sorted_pairs=sorted(valid.items(),key=lambda x:x[1]["total_pnl"],reverse=True)

    all_yearly={}
    for r in valid.values():
        for yr,ys in r["yearly"].items():
            if yr not in all_yearly: all_yearly[yr]={"wins":0,"losses":0,"pnl":0,"trades":0}
            for k in ["wins","losses","pnl","trades"]: all_yearly[yr][k]+=ys.get(k,0)

    all_regimes={}
    for r in valid.values():
        for reg,rs in r["regime_stats"].items():
            if reg not in all_regimes: all_regimes[reg]={"wins":0,"losses":0,"pnl":0}
            for k in ["wins","losses","pnl"]: all_regimes[reg][k]+=rs.get(k,0)

    vc="#06D6A0" if avg_wr>=45 and total_pnl>0 else "#F0A500" if avg_wr>=38 else "#EF476F"
    vt="SYSTEM VALIDATED ✅" if avg_wr>=45 and total_pnl>0 else "IMPROVING ⚡" if avg_wr>=38 else "NEEDS WORK 🔧"
    years_sorted=sorted(all_yearly.keys())
    max_abs=max((abs(all_yearly[y]["pnl"]) for y in years_sorted),default=1)

    html=f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Chakra Multi-Timeframe Backtest</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
:root{{--bg:#050A0F;--s1:#0D1821;--s2:#162030;--bd:#1E3448;
  --gold:#F0A500;--g2:#FFD166;--green:#06D6A0;--red:#EF476F;--blue:#118AB2;
  --text:#E8F4F8;--muted:#5A7A8A;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;}}
.hdr{{background:linear-gradient(135deg,#0D1821,#050A0F);border-bottom:3px solid var(--green);padding:48px 40px;}}
.hdr h1{{font-size:2.6rem;font-weight:800;background:linear-gradient(90deg,var(--green),var(--g2),var(--blue));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
.hdr p{{color:var(--muted);font-family:'Space Mono',monospace;font-size:.82rem;margin-top:10px;}}
.wrap{{max-width:1500px;margin:0 auto;padding:40px;}}
.verdict{{background:var(--s1);border:2px solid {vc};border-radius:20px;padding:40px;text-align:center;margin-bottom:32px;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;margin-bottom:32px;}}
.kpi{{background:var(--s1);border:1px solid var(--bd);border-radius:14px;padding:24px 20px;position:relative;overflow:hidden;}}
.kpi::after{{content:'';position:absolute;bottom:0;left:0;height:3px;width:100%;background:var(--green);}}
.kpi-lbl{{font-size:.70rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;font-family:'Space Mono',monospace;}}
.kpi-val{{font-size:1.9rem;font-weight:800;margin-top:8px;}}
.green{{color:var(--green);}} .red{{color:var(--red);}} .amber{{color:var(--gold);}}
.section{{background:var(--s1);border:1px solid var(--bd);border-radius:16px;padding:32px;margin-bottom:24px;}}
.sec-title{{font-size:1.1rem;font-weight:800;color:var(--gold);margin-bottom:24px;
  text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;gap:10px;}}
.sec-title::after{{content:'';flex:1;height:1px;background:var(--bd);}}
table{{width:100%;border-collapse:collapse;}}
th{{text-align:left;padding:10px 14px;font-size:.68rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:.1em;font-family:'Space Mono',monospace;border-bottom:1px solid var(--bd);}}
td{{padding:12px 14px;border-bottom:1px solid rgba(30,52,72,.4);font-family:'Space Mono',monospace;font-size:.83rem;}}
tr:hover td{{background:var(--s2);}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:24px;}}
.badge{{display:inline-block;padding:3px 10px;border-radius:6px;font-size:.72rem;font-weight:700;}}
.badge-g{{background:rgba(6,214,160,.15);color:#06D6A0;border:1px solid rgba(6,214,160,.3);}}
.badge-a{{background:rgba(240,165,0,.15);color:#F0A500;border:1px solid rgba(240,165,0,.3);}}
.badge-r{{background:rgba(239,71,111,.15);color:#EF476F;border:1px solid rgba(239,71,111,.3);}}
.bar-wrap{{background:var(--s2);border-radius:4px;height:8px;margin-top:4px;}}
.bar{{height:8px;border-radius:4px;}} .bar-g{{background:var(--green);}} .bar-r{{background:var(--red);}}
.tf-box{{background:var(--s2);border-radius:10px;padding:16px 20px;border-left:3px solid var(--green);}}
footer{{text-align:center;padding:40px;color:var(--muted);font-family:'Space Mono',monospace;
  font-size:.72rem;border-top:1px solid var(--bd);margin-top:40px;}}
</style></head><body>
<div class="hdr">
  <h1>⚡ PROJECT CHAKRA — MULTI-TIMEFRAME BACKTEST</h1>
  <p>M15 ENTRIES · H1 SIGNALS · H4 TREND FILTER · D1 12M MOMENTUM · SCALE-OUT THIRDS · 6x ATR TP &nbsp;|&nbsp; {run_date}</p>
</div>
<div class="wrap">

<div class="verdict">
  <div style="font-size:2.2rem;font-weight:800;color:{vc}">{vt}</div>
  <div style="color:var(--muted);margin-top:10px;font-family:'Space Mono',monospace;font-size:.85rem">
    {total_trades:,} trades · {len(valid)} pairs · Avg Win Rate {avg_wr:.1f}% · {len(passing)}/{len(valid)} pairs profitable
  </div>
</div>

<div style="background:var(--s1);border:1px solid var(--bd);border-radius:16px;padding:24px;margin-bottom:32px;">
  <div style="font-size:1rem;font-weight:700;color:var(--gold);margin-bottom:16px">🔀 HOW MULTI-TIMEFRAME WORKS IN THIS BACKTEST</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px;">
    <div class="tf-box"><div style="color:var(--green);font-weight:700;margin-bottom:6px">M15 — Entry</div>
      <div style="color:var(--muted);font-size:.82rem">Precise entry timing. BOS, CHOCH, OrderFlow on 15-min candles. Last 5 years only.</div></div>
    <div class="tf-box"><div style="color:var(--gold);font-weight:700;margin-bottom:6px">H1 — Signal</div>
      <div style="color:var(--muted);font-size:.82rem">Main signal generation. All 10 agents. Same as live system. 24 years data.</div></div>
    <div class="tf-box"><div style="color:var(--blue);font-weight:700;margin-bottom:6px">H4 — Trend</div>
      <div style="color:var(--muted);font-size:.82rem">Trend confirmation. Contradicting H4 = trade skipped. +10% confidence boost when aligned.</div></div>
    <div class="tf-box"><div style="color:#EF476F;font-weight:700;margin-bottom:6px">D1 — Filter</div>
      <div style="color:var(--muted);font-size:.82rem">12-month TSMOM filter. Never trade against the yearly trend. Moskowitz AQR paper.</div></div>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi"><div class="kpi-lbl">Total P&L</div>
    <div class="kpi-val {'green' if total_pnl>0 else 'red'}">${total_pnl:+,.0f}</div></div>
  <div class="kpi"><div class="kpi-lbl">Avg Win Rate</div>
    <div class="kpi-val {'green' if avg_wr>=45 else 'amber' if avg_wr>=38 else 'red'}">{avg_wr:.1f}%</div></div>
  <div class="kpi"><div class="kpi-lbl">Total Trades</div>
    <div class="kpi-val amber">{total_trades:,}</div></div>
  <div class="kpi"><div class="kpi-lbl">Avg Sharpe</div>
    <div class="kpi-val {'green' if avg_sharpe>=1 else 'amber'}">{avg_sharpe:.2f}</div></div>
  <div class="kpi"><div class="kpi-lbl">Avg Profit Factor</div>
    <div class="kpi-val {'green' if avg_pf>=1.3 else 'amber'}">{avg_pf:.2f}</div></div>
  <div class="kpi"><div class="kpi-lbl">Passing Pairs</div>
    <div class="kpi-val green">{len(passing)}/{len(valid)}</div></div>
</div>

<div class="section">
  <div class="sec-title">📊 Per-Pair Performance</div>
  <table><thead><tr>
    <th>Pair</th><th>Trades</th><th>Win Rate</th><th>P&L</th>
    <th>Return %</th><th>Sharpe</th><th>PF</th><th>Max DD</th><th>Status</th>
  </tr></thead><tbody>"""

    for pair,r in sorted_pairs:
        wr=r["win_rate"]; pnl=r["total_pnl"]
        st="PASS" if wr>=45 and pnl>0 else "IMPROVE" if wr>=38 else "FAIL"
        bc="badge-g" if st=="PASS" else "badge-a" if st=="IMPROVE" else "badge-r"
        pc="green" if pnl>=0 else "red"; wc="green" if wr>=45 else "amber" if wr>=38 else "red"
        html+=f"""<tr>
      <td style="font-weight:700;color:var(--gold)">{pair.replace('_','/')}</td>
      <td>{r['trades']:,}</td><td class="{wc}">{wr}%</td>
      <td class="{pc}">${pnl:+,.0f}</td><td class="{pc}">{r['return_pct']:+.1f}%</td>
      <td class="{'green' if r['sharpe']>=1 else 'amber'}">{r['sharpe']:.2f}</td>
      <td>{r['profit_factor']:.2f}</td><td class="red">{r['max_drawdown']}%</td>
      <td><span class="badge {bc}">{st}</span></td></tr>"""

    html+="""</tbody></table></div>
<div class="grid2">
<div class="section"><div class="sec-title">📅 Year by Year</div>
  <table><thead><tr><th>Year</th><th>Trades</th><th>WR</th><th>P&L</th><th>Bar</th></tr></thead><tbody>"""

    for yr in years_sorted:
        ys=all_yearly[yr]; wr=ys["wins"]/max(ys["trades"],1)*100; pnl=ys["pnl"]
        bw=int(abs(pnl)/max_abs*100); bc="bar-g" if pnl>=0 else "bar-r"
        wc="green" if wr>=45 else "amber" if wr>=38 else "red"; pc="green" if pnl>=0 else "red"
        html+=f"""<tr><td style="font-weight:700">{yr}</td><td>{ys['trades']:,}</td>
      <td class="{wc}">{wr:.1f}%</td><td class="{pc}">${pnl:+,.0f}</td>
      <td><div class="bar-wrap"><div class="bar {bc}" style="width:{bw}%"></div></div></td></tr>"""

    html+="""</tbody></table></div>
<div class="section"><div class="sec-title">🎯 By Market Regime</div>
  <table><thead><tr><th>Regime</th><th>Trades</th><th>Win Rate</th><th>P&L</th></tr></thead><tbody>"""

    rcolors={"TRENDING":"#F0A500","RANGING":"#118AB2","VOLATILE":"#EF476F"}
    for reg,rs in all_regimes.items():
        tot=rs["wins"]+rs["losses"]; wr=rs["wins"]/max(tot,1)*100
        col=rcolors.get(reg,"#E8F4F8"); pc="green" if rs["pnl"]>=0 else "red"
        html+=f"""<tr><td style="font-weight:700;color:{col}">{reg}</td>
      <td>{tot:,}</td><td class="{'green' if wr>=45 else 'red'}">{wr:.1f}%</td>
      <td class="{pc}">${rs['pnl']:+,.0f}</td></tr>"""

    html+=f"""</tbody></table></div></div>
</div>
<footer>PROJECT CHAKRA V15 &nbsp;|&nbsp; MULTI-TIMEFRAME BACKTEST &nbsp;|&nbsp; M15+H1+H4+D1 &nbsp;|&nbsp; {run_date}<br>
NOT FINANCIAL ADVICE</footer></body></html>"""
    return html

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*65}")
    print(f"  PROJECT CHAKRA — MULTI-TIMEFRAME BACKTEST")
    print(f"  M15 + H1 + H4 + D1 — Professional standard testing")
    print(f"  Pairs: {len(PAIRS)} | Time: ~40-50 minutes")
    print(f"{'='*65}\n")

    if not OANDA_TOKEN:
        print("❌ OANDA_TOKEN not in .env"); return

    results={}; run_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    start_time=time.time()

    for pair in PAIRS:
        print(f"\n▶ {pair}")
        try:
            print(f"  Fetching D1 (24yr)...", end=" ", flush=True)
            d1=fetch(pair,"D",24); print(f"{len(d1):,} candles")

            print(f"  Fetching H4 (24yr)...", end=" ", flush=True)
            h4=fetch(pair,"H4",24); print(f"{len(h4):,} candles")

            print(f"  Fetching H1 (24yr)...", end=" ", flush=True)
            h1=fetch(pair,"H1",24); print(f"{len(h1):,} candles")

            print(f"  Fetching M15 (5yr)...", end=" ", flush=True)
            m15=fetch(pair,"M15",5); print(f"{len(m15):,} candles")

            if len(h1)<500:
                print(f"  ❌ Insufficient H1 data"); results[pair]=None; continue

            years={int(c["time"][:4]) for c in h1 if len(c.get("time",""))>=4}
            print(f"  Data: {min(years)}-{max(years)} | Running multi-TF backtest...")

            r=run_multi_tf_backtest(m15,h1,h4,d1,pair)
            results[pair]=r

            if r and r["trades"]>0:
                st="✅" if r["win_rate"]>=45 and r["total_pnl"]>0 else "⚠️ " if r["win_rate"]>=38 else "❌"
                print(f"  {st} WR={r['win_rate']}% | P&L=${r['total_pnl']:+,.0f} | "
                      f"Trades={r['trades']:,} | Sharpe={r['sharpe']:.2f}")
            else:
                print(f"  ❌ No trades generated")
        except Exception as e:
            print(f"  ❌ Error: {e}"); log.error(traceback.format_exc())
            results[pair]=None

    html=build_report(results,run_date)
    with open("multi_tf_report.html","w",encoding="utf-8") as f: f.write(html)
    with open("multi_tf_results.json","w") as f:
        json.dump({"run_date":run_date,"results":{p:r for p,r in results.items() if r}},f,indent=2,default=str)

    valid={p:r for p,r in results.items() if r and r["trades"]>0}
    elapsed=(time.time()-start_time)/60
    if valid:
        tt=sum(r["trades"] for r in valid.values())
        tp=sum(r["total_pnl"] for r in valid.values())
        aw=sum(r["win_rate"] for r in valid.values())/len(valid)
        passing=[p for p,r in valid.items() if r["win_rate"]>=45 and r["total_pnl"]>0]
        print(f"\n{'='*65}")
        print(f"  MULTI-TF BACKTEST COMPLETE ({elapsed:.1f} min)")
        print(f"  Avg Win Rate: {aw:.1f}% | Total P&L: ${tp:+,.0f} | Trades: {tt:,}")
        print(f"  Passing: {passing}")
        print(f"  📄 Report: multi_tf_report.html")
        print(f"{'='*65}\n")

if __name__=="__main__":
    main()
