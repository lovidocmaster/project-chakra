"""
PROJECT CHAKRA V15 — WALK-FORWARD BACKTEST
Institutional validation: Train 700 bars → Test 100 bars → Repeat
Run: py -3.11 v15_walkforward.py
"""
import os,json,math,logging
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
log=logging.getLogger("WF")

from v13_production import (get_oanda_candles,PAIRS,
    EMAAgent,MACDAgent,RSIAgent,BollingerAgent,ATRAgent,
    StochasticAgent,BreakoutAgent,BOSAgent,CHOCHAgent,SupertrendAgent,
    MomentumAgent,DXYAgent)

TRAIN=700; TEST=100; TOTAL=5000; GRAN="H1"
CONF=0.68; SL=1.5; TP=4.5; RISK=0.005; BAL=100000.0
AGENTS=[EMAAgent,MACDAgent,RSIAgent,BollingerAgent,ATRAgent,
        StochasticAgent,BreakoutAgent,BOSAgent,CHOCHAgent,
        SupertrendAgent,MomentumAgent,DXYAgent]

def signal(candles,pair):
    agents=[cls() for cls in AGENTS]
    bc=sc=0.0; bn=sn=hn=0
    for ag in agents:
        try:
            s=ag.analyze(pair,candles,candles,candles)
            d=s.get("signal","HOLD"); c=float(s.get("confidence",0.5))
            if d=="BUY": bc+=c; bn+=1
            elif d=="SELL": sc+=c; sn+=1
            else: hn+=1
        except: hn+=1
    closes=[float(x["mid"]["c"]) for x in candles if x.get("complete")]
    atr=sum(abs(closes[-i]-closes[-i-1]) for i in range(1,14))/14 if len(closes)>=14 else 0.001
    tot=bn+sn+hn
    if tot==0: return "HOLD",0.0,atr
    if bn>sn:
        c=bc/max(bn,1)/1.5; ap=(bn+sn)/tot
        if c>=CONF and ap>=0.35: return "BUY",c,atr
    elif sn>bn:
        c=sc/max(sn,1)/1.5; ap=(bn+sn)/tot
        if c>=CONF and ap>=0.35: return "SELL",c,atr
    return "HOLD",0.0,atr

def backtest_window(candles,start,end,pair):
    bal=BAL; trades=[]; pos=None
    for i in range(start+20,end):
        sl=candles[max(0,i-100):i]
        if len(sl)<20: continue
        cur=candles[i]
        try:
            hi=float(cur["mid"]["h"]); lo=float(cur["mid"]["l"]); cl=float(cur["mid"]["c"])
        except: continue
        if pos:
            hit=None
            if pos["d"]=="BUY":
                if lo<=pos["sl"]: hit="SL"
                elif hi>=pos["tp"]: hit="TP"
            else:
                if hi>=pos["sl"]: hit="SL"
                elif lo<=pos["tp"]: hit="TP"
            if hit:
                ex=pos["sl"] if hit=="SL" else pos["tp"]
                pnl=(ex-pos["e"] if pos["d"]=="BUY" else pos["e"]-ex)*abs(pos["u"])*10
                bal+=pnl
                trades.append({"pnl":pnl,"type":hit,"bal":bal})
                pos=None
        if pos is None:
            sig,conf,atr=signal(sl,pair)
            if sig in ("BUY","SELL"):
                sd=atr*SL; td=atr*TP
                u=int((bal*RISK)/(sd*10000)); u=max(100,min(u,50000))
                if sig=="SELL": u=-u
                sl_p=cl-sd if sig=="BUY" else cl+sd
                tp_p=cl+td if sig=="BUY" else cl-td
                pos={"d":sig,"e":cl,"sl":sl_p,"tp":tp_p,"u":u}
    if pos and candles:
        cl=float(candles[end-1]["mid"]["c"])
        pnl=(cl-pos["e"] if pos["d"]=="BUY" else pos["e"]-cl)*abs(pos["u"])*10
        bal+=pnl; trades.append({"pnl":pnl,"type":"EOW","bal":bal})
    if not trades:
        return {"trades":0,"win_rate":0,"pnl":0,"return_pct":0,"max_dd":0,"sharpe":0,"wins":0,"losses":0}
    wins=[t for t in trades if t["pnl"]>0]
    wr=len(wins)/len(trades)
    total_pnl=bal-BAL; ret=total_pnl/BAL*100
    peak=BAL; mdd=0; b=BAL
    for t in trades:
        b+=t["pnl"]; peak=max(peak,b)
        mdd=max(mdd,(peak-b)/peak)
    pnls=[t["pnl"] for t in trades]
    avg=sum(pnls)/len(pnls); std=math.sqrt(sum((p-avg)**2 for p in pnls)/len(pnls)) if len(pnls)>1 else 1
    sharpe=(avg/std)*math.sqrt(252/len(pnls)*24) if std>0 else 0
    return {"trades":len(trades),"wins":len(wins),"losses":len(trades)-len(wins),
            "win_rate":round(wr*100,1),"pnl":round(total_pnl,2),
            "return_pct":round(ret,2),"max_dd":round(mdd*100,1),"sharpe":round(sharpe,2)}

def run():
    print(f"\n{'='*60}\n  CHAKRA V15 — WALK-FORWARD BACKTEST\n{'='*60}")
    all_results={}
    for pair in PAIRS:
        print(f"\n  {pair}")
        try: candles=get_oanda_candles(pair,GRAN,count=TOTAL)
        except Exception as e: print(f"  ❌ Fetch failed: {e}"); continue
        if not candles or len(candles)<TRAIN+TEST:
            print(f"  ❌ Not enough candles ({len(candles) if candles else 0})"); continue
        n=len(candles); wins=[]; results=[]; start=0; wn=0
        while start+TRAIN+TEST<=n:
            wn+=1; te=start+TRAIN; ee=te+TEST
            r=backtest_window(candles,te,ee,pair)
            r["window"]=wn; results.append(r)
            if r["trades"]>0: wins.append(r["win_rate"])
            print(f"  W{wn}: WR={r['win_rate']}% P&L=${r['pnl']:+.0f} "
                  f"DD={r['max_dd']}% Sharpe={r['sharpe']:.2f} Trades={r['trades']}")
            start+=TEST
        if not results: continue
        tt=sum(r["trades"] for r in results)
        tw=sum(r.get("wins",0) for r in results)
        awr=tw/tt*100 if tt>0 else 0
        passed=awr>=50
        print(f"  {'✅ PASS' if passed else '❌ FAIL'}  AvgWR={awr:.1f}%  "
              f"Trades={tt}  MaxDD={max(r['max_dd'] for r in results)}%")
        all_results[pair]={"avg_win_rate":round(awr,1),"total_trades":tt,
                           "pass":passed,"windows":len(results)}
    print(f"\n{'='*60}\n  RESULTS SUMMARY")
    passing=[p for p,r in all_results.items() if r["pass"]]
    failing=[p for p,r in all_results.items() if not r["pass"]]
    for p,r in all_results.items():
        print(f"  {'✅' if r['pass'] else '❌'} {p:12s} WR={r['avg_win_rate']}% Trades={r['total_trades']}")
    print(f"\n  Passing: {passing}")
    print(f"  Failing: {failing}")
    verdict="✅ VALIDATED — proceed to live trading" if len(passing)>=len(PAIRS)*0.6 else "⚠️  NEEDS WORK"
    print(f"\n  {verdict}")
    with open("v15_walkforward_results.json","w") as f:
        json.dump({"date":datetime.utcnow().isoformat(),"config":{"conf":CONF,"sl":SL,"tp":TP},
                   "results":all_results,"passing":passing,"failing":failing},f,indent=2)
    print(f"  Saved: v15_walkforward_results.json\n{'='*60}\n")

if __name__=="__main__": run()
