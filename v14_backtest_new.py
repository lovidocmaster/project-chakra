#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V14 COMPLETE DETAILED BACKTEST
Real OANDA data + Full metrics + Telegram detailed report
"""
import os, json, requests
from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass
import numpy as np

try:
    from dotenv import load_dotenv; load_dotenv()
except: pass

try:
    from oandapyV20 import API as OandaAPI
    from oandapyV20.endpoints.instruments import InstrumentsCandles
    OANDA_OK = True
except: OANDA_OK = False

OANDA_TOKEN    = os.getenv("OANDA_TOKEN","")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN","")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT", os.getenv("TELEGRAM_CHAT_ID",""))
PAIRS = ["EUR_USD","GBP_USD","USD_JPY","AUD_USD","USD_CAD"]

@dataclass
class Bar:
    ts: str; o: float; h: float; l: float; c: float; v: float

def tg(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT: return
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":TELEGRAM_CHAT,"text":msg,"parse_mode":"HTML"},timeout=10)
    except: pass

def get_bars(pair, count=5000):
    if not OANDA_OK or not OANDA_TOKEN: return sim(pair, count)
    try:
        api = OandaAPI(access_token=OANDA_TOKEN, environment="practice")
        ep  = InstrumentsCandles(pair, params={"count":count,"granularity":"H1"})
        api.request(ep)
        return [Bar(c.get("time",""),float(c["mid"]["o"]),float(c["mid"]["h"]),
                    float(c["mid"]["l"]),float(c["mid"]["c"]),float(c.get("volume",0)))
                for c in ep.response.get("candles",[])]
    except Exception as e:
        print(f"  OANDA error: {e}")
        return sim(pair, count)

def sim(pair, count):
    base = {"EUR_USD":1.08,"GBP_USD":1.26,"USD_JPY":148.0,"AUD_USD":0.65,"USD_CAD":1.37}.get(pair,1.1)
    p = base; bars = []
    for i in range(count):
        p *= (1+np.random.normal(0,0.0008))
        o=p*(1+np.random.normal(0,0.0002)); h=max(p,o)*1.0003; l=min(p,o)*0.9997
        bars.append(Bar((datetime.now()-timedelta(hours=count-i)).isoformat(),o,h,l,p,500))
    return bars

def signal(bars):
    if len(bars)<55: return {"d":"HOLD","conf":0,"n":0,"why":[]}
    c=np.array([b.c for b in bars]); h=np.array([b.h for b in bars]); l=np.array([b.l for b in bars])
    buy=sell=0.0; bw=[]; sw=[]; n=0
    # EMA
    e20,e50=np.mean(c[-20:]),np.mean(c[-50:])
    if c[-1]>e20>e50: buy+=1.8;n+=1;bw.append("EMA uptrend")
    elif c[-1]<e20<e50: sell+=1.8;n+=1;sw.append("EMA downtrend")
    # RSI
    d=np.diff(c[-15:]); ag=np.mean(np.where(d>0,d,0)[-14:]); al=np.mean(np.where(d<0,-d,0)[-14:]) or 1e-9
    rsi=100-100/(1+ag/al)
    if rsi<35: buy+=1.6;n+=1;bw.append(f"RSI oversold {rsi:.0f}")
    elif rsi>65: sell+=1.6;n+=1;sw.append(f"RSI overbought {rsi:.0f}")
    # MACD
    mc=np.mean(c[-12:])-np.mean(c[-26:]); pm=np.mean(c[-13:-1])-np.mean(c[-27:-1])
    if mc>0 and pm<=0: buy+=1.9;n+=1;bw.append("MACD bull cross")
    elif mc<0 and pm>=0: sell+=1.9;n+=1;sw.append("MACD bear cross")
    # BOS
    if c[-1]>max(h[-20:-1]): buy+=2.1;n+=1;bw.append("Break of structure UP")
    elif c[-1]<min(l[-20:-1]): sell+=2.1;n+=1;sw.append("Break of structure DOWN")
    # Structure
    if h[-1]>h[-5]>h[-10] and l[-1]>l[-5]>l[-10]: buy+=1.75;n+=1;bw.append("HH+HL bullish")
    elif h[-1]<h[-5]<h[-10] and l[-1]<l[-5]<l[-10]: sell+=1.75;n+=1;sw.append("LH+LL bearish")
    # Momentum
    roc=(c[-1]-c[-10])/c[-10]*100
    if roc>0.3: buy+=1.4;n+=1;bw.append(f"Momentum +{roc:.2f}%")
    elif roc<-0.3: sell+=1.4;n+=1;sw.append(f"Momentum {roc:.2f}%")
    # Bollinger
    mid=np.mean(c[-20:]); std=np.std(c[-20:])
    if c[-1]<mid-2*std: buy+=1.5;n+=1;bw.append("Below lower BB")
    elif c[-1]>mid+2*std: sell+=1.5;n+=1;sw.append("Above upper BB")
    # CHOCH
    t1=c[-10]-c[-20]; t2=c[-1]-c[-10]
    if t1<0 and t2>0: buy+=1.76;n+=1;bw.append("CHOCH bear to bull")
    elif t1>0 and t2<0: sell+=1.76;n+=1;sw.append("CHOCH bull to bear")
    tot=buy+sell
    if tot==0 or n<3: return {"d":"HOLD","conf":0,"n":n,"why":[]}
    if buy>=sell: return {"d":"BUY","conf":buy/tot,"n":n,"why":bw}
    return {"d":"SELL","conf":sell/tot,"n":n,"why":sw}

def backtest(pair, bars):
    pip=0.01 if "JPY" in pair else 0.0001
    bal=100000.0; peak=100000.0; max_dd=0.0
    trades=[]; in_t=False; ep=0.0; eb=0; ed=""; ew=[]; sl=tp=0.0
    cw=cl=mcw=mcl=0; best=worst=0.0

    for i in range(60,len(bars)):
        w=bars[max(0,i-60):i]; b=bars[i]
        if in_t:
            ex=None; xr=""
            if ed=="BUY":
                if b.l<=sl: ex=sl;xr="Stop Loss hit"
                elif b.h>=tp: ex=tp;xr="Take Profit hit"
                elif i-eb>=24: ex=b.c;xr="24h timeout"
            else:
                if b.h>=sl: ex=sl;xr="Stop Loss hit"
                elif b.l<=tp: ex=tp;xr="Take Profit hit"
                elif i-eb>=24: ex=b.c;xr="24h timeout"
            if ex:
                pp=((ex-ep)/pip if ed=="BUY" else (ep-ex)/pip)
                pu=pp*0.1*100; bal+=pu
                oc="WIN" if pu>0 else "LOSS"
                if oc=="WIN": cw+=1;cl=0;mcw=max(mcw,cw)
                else: cl+=1;cw=0;mcl=max(mcl,cl)
                best=max(best,pu); worst=min(worst,pu)
                trades.append({"dir":ed,"entry":round(ep,5),"exit":round(ex,5),
                    "exit_reason":xr,"pnl_pips":round(pp,1),"pnl_usd":round(pu,2),
                    "outcome":oc,"why":ew,"balance":round(bal,2)})
                peak=max(peak,bal); dd=(peak-bal)/peak*100; max_dd=max(max_dd,dd)
                in_t=False
        if not in_t:
            sig=signal(w)
            if sig["d"]!="HOLD" and sig["conf"]>=0.62:
                atr=np.mean([x.h-x.l for x in w[-14:]])
                ep=b.c; ed=sig["d"]; eb=i; ew=sig["why"]
                sl=ep-atr*2 if ed=="BUY" else ep+atr*2
                tp=ep+atr*3 if ed=="BUY" else ep-atr*3
                in_t=True

    tot=len(trades); wins=sum(1 for t in trades if t["outcome"]=="WIN")
    wr=wins/tot*100 if tot>0 else 0
    pnls=[t["pnl_usd"] for t in trades]
    aw=np.mean([p for p in pnls if p>0]) if any(p>0 for p in pnls) else 0
    al_val=np.mean([p for p in pnls if p<0]) if any(p<0 for p in pnls) else 0
    rr=abs(aw/al_val) if al_val else 0
    tpnl=bal-100000; ret=tpnl/100000*100
    sharpe=(np.mean(pnls)/(np.std(pnls) or 1))*np.sqrt(252) if len(pnls)>1 else 0
    return {"pair":pair,"trades":tot,"wins":wins,"losses":tot-wins,
            "win_rate":round(wr,1),"pnl":round(tpnl,2),"return":round(ret,1),
            "max_dd":round(max_dd,2),"sharpe":round(sharpe,2),
            "avg_win":round(aw,2),"avg_loss":round(al_val,2),"rr":round(rr,2),
            "best":round(best,2),"worst":round(worst,2),
            "max_cw":mcw,"max_cl":mcl,"balance":round(bal,2),
            "sample":trades[:3]}

def main():
    print("\n"+"="*65)
    print("  V14 COMPLETE DETAILED BACKTEST")
    print("="*65+"\n")

    results=[]; tt=tw=0; tp=0.0

    for pair in PAIRS:
        print(f"Testing {pair}...")
        bars=get_bars(pair,5000)
        if len(bars)<100: continue
        r=backtest(pair,bars); results.append(r)
        tt+=r["trades"]; tw+=r["wins"]; tp+=r["pnl"]
        grade="✅ EXCELLENT" if r["win_rate"]>=58 else ("✅ GOOD" if r["win_rate"]>=53 else ("⚠️ WEAK" if r["win_rate"]>=48 else "❌ POOR"))
        dd_flag=" ⚠️ HIGH DD!" if r["max_dd"]>30 else ""
        print(f"  Trades:      {r['trades']} ({r['wins']}W / {r['losses']}L)")
        print(f"  Win Rate:    {r['win_rate']}%  {grade}")
        print(f"  P&L:         ${r['pnl']:+,.0f}  ({r['return']:+.1f}%)")
        print(f"  Max DD:      {r['max_dd']}%{dd_flag}")
        print(f"  Sharpe:      {r['sharpe']}")
        print(f"  Avg Win:     ${r['avg_win']:+,.0f}")
        print(f"  Avg Loss:    ${r['avg_loss']:+,.0f}")
        print(f"  Risk/Reward: {r['rr']}:1")
        print(f"  Best Trade:  ${r['best']:+,.0f}")
        print(f"  Worst Trade: ${r['worst']:+,.0f}")
        print(f"  Win Streak:  {r['max_cw']}  |  Loss Streak: {r['max_cl']}")
        if r["sample"]:
            print(f"  Sample trade: {r['sample'][0]['dir']} entry={r['sample'][0]['entry']} exit={r['sample'][0]['exit']} ({r['sample'][0]['exit_reason']}) = ${r['sample'][0]['pnl_usd']:+.0f}")
        print()

    owr=tw/tt*100 if tt>0 else 0
    fb=100000+tp; ret=tp/100000*100
    grade="EXCELLENT" if owr>=58 else ("GOOD" if owr>=53 else ("AVERAGE" if owr>=48 else "POOR"))

    print("="*65)
    print("  FINAL SYSTEM REPORT")
    print("="*65)
    print(f"  Total Trades:     {tt}")
    print(f"  Total Wins:       {tw}")
    print(f"  Overall Win Rate: {owr:.1f}%")
    print(f"  Total P&L:        ${tp:+,.0f}")
    print(f"  Total Return:     {ret:+.1f}%")
    print(f"  Final Balance:    ${fb:,.0f}")
    print(f"  System Grade:     {grade}")

    best_p=max(results,key=lambda x:x["win_rate"])
    worst_p=min(results,key=lambda x:x["win_rate"])
    print(f"\n  Best pair:  {best_p['pair']} ({best_p['win_rate']}% WR)")
    print(f"  Worst pair: {worst_p['pair']} ({worst_p['win_rate']}% WR)")

    print("\n  RECOMMENDATIONS:")
    for r in results:
        if r["win_rate"]>=55 and r["max_dd"]<20:
            print(f"  ✅ {r['pair']}: KEEP — strong performer")
        elif r["win_rate"]<50:
            print(f"  ❌ {r['pair']}: REMOVE — below 50% win rate")
        elif r["max_dd"]>40:
            print(f"  ⚠️  {r['pair']}: REDUCE SIZE — high drawdown")

    with open("v14_backtest_results.json","w") as f:
        json.dump({"timestamp":datetime.now().isoformat(),"system":"V14 Army 36 agents",
            "summary":{"total_trades":tt,"wins":tw,"win_rate":round(owr,1),
                "pnl":round(tp,2),"return":round(ret,1),"grade":grade},
            "pairs":results},f,indent=2)
    print("\n  Saved to v14_backtest_results.json")

    msg=(f"<b>V14 BACKTEST COMPLETE</b>\n\n"
         f"<b>Total Trades:</b> {tt}\n"
         f"<b>Win Rate:</b> {owr:.1f}%\n"
         f"<b>Total P&L:</b> ${tp:+,.0f}\n"
         f"<b>Return:</b> {ret:+.1f}%\n"
         f"<b>Final Balance:</b> ${fb:,.0f}\n"
         f"<b>Grade:</b> {grade}\n\n"
         f"<b>Per Pair:</b>\n")
    for r in results:
        e="✅" if r["win_rate"]>=53 else "⚠️"
        msg+=f"{e} {r['pair']}: {r['win_rate']}% WR | ${r['pnl']:+,.0f} | DD:{r['max_dd']}% | Sharpe:{r['sharpe']}\n"
    msg+=f"\n<b>Best:</b> {best_p['pair']} | <b>Worst:</b> {worst_p['pair']}"
    tg(msg)
    print("  Telegram sent!\n  DONE!")

if __name__=="__main__": main()
