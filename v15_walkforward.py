"""
PROJECT CHAKRA — WALK-FORWARD VALIDATION
=========================================
Tests the optimized v2 system on rolling out-of-sample windows.
Validates system has real edge and is not curve-fitted.

Run: py -3.11 v15_walkforward.py
"""
import os, json, math, time, logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("WF")

try:
    import oandapyV20
    import oandapyV20.endpoints.instruments as instruments
    OANDA_OK = True
except ImportError:
    OANDA_OK = False

OANDA_TOKEN = os.getenv("OANDA_TOKEN", "")
PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"]

# Walk-forward settings
TRAIN_MONTHS  = 12   # 12 months training window
TEST_MONTHS   = 3    # 3 months out-of-sample test
N_WINDOWS     = 8    # 8 rolling windows = 2 years coverage
START_BAL     = 100_000.0
RISK_PCT      = 0.005
SL_ATR        = 1.5
TP_ATR        = 6.0  # Research-optimized TP

def fetch_candles(pair, start_dt, end_dt):
    if not OANDA_OK or not OANDA_TOKEN: return []
    all_c = []
    cur = start_dt
    while cur < end_dt:
        nxt = min(cur + timedelta(days=180), end_dt)
        try:
            client = oandapyV20.API(access_token=OANDA_TOKEN, environment="practice")
            params = {"granularity":"H1",
                      "from": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "to":   nxt.strftime("%Y-%m-%dT%H:%M:%SZ")}
            r = instruments.InstrumentsCandles(pair, params=params)
            client.request(r)
            all_c.extend(r.response.get("candles", []))
        except Exception as e:
            log.warning(f"{pair} chunk failed: {e}")
        cur = nxt
        time.sleep(0.3)
    seen = set(); unique = []
    for c in all_c:
        t = c.get("time","")
        if t not in seen: seen.add(t); unique.append(c)
    return sorted(unique, key=lambda x: x.get("time",""))

def ema(prices, p):
    if len(prices) < p: return prices[-1] if prices else 0
    k = 2.0/(p+1); e = prices[0]
    for x in prices[1:]: e = x*k + e*(1-k)
    return e

def calc_atr(candles, p=14):
    if len(candles) < p: return 0.001
    trs = [max(float(candles[-i]["mid"]["h"])-float(candles[-i]["mid"]["l"]),
               abs(float(candles[-i]["mid"]["h"])-float(candles[-i-1]["mid"]["c"])),
               abs(float(candles[-i]["mid"]["l"])-float(candles[-i-1]["mid"]["c"])))
           for i in range(1, min(p+1, len(candles)))]
    return sum(trs)/len(trs) if trs else 0.001

def detect_regime(candles):
    if len(candles) < 30: return "RANGING"
    closes = [float(c["mid"]["c"]) for c in candles[-30:]]
    highs  = [float(c["mid"]["h"]) for c in candles[-30:]]
    lows   = [float(c["mid"]["l"]) for c in candles[-30:]]
    atr    = sum(highs[-i]-lows[-i] for i in range(1,15))/14
    avg    = sum(closes)/len(closes)
    vol    = atr/avg if avg>0 else 0
    e20    = sum(closes[-20:])/20
    e30    = sum(closes)/30
    sep    = abs(e20-e30)/avg if avg>0 else 0
    if vol > 0.007: return "VOLATILE"
    if sep > 0.0012: return "TRENDING"
    return "RANGING"

def generate_signal(candles, regime):
    if len(candles) < 50: return "HOLD", 0.0
    closes = [float(c["mid"]["c"]) for c in candles]
    highs  = [float(c["mid"]["h"]) for c in candles]
    lows   = [float(c["mid"]["l"]) for c in candles]
    
    # Regime-filtered signals (matches live system)
    if regime == "VOLATILE": return "HOLD", 0.0
    
    buy_w = sell_w = 0.0
    
    # EMA (weight 1.0 — TRENDING only)
    if regime == "TRENDING":
        e20 = ema(closes, 20); e50 = ema(closes, 50)
        if closes[-1] > e20 > e50: buy_w += 1.0
        elif closes[-1] < e20 < e50: sell_w += 1.0
    
    # BOS (weight 2.0)
    if len(candles) >= 10:
        ph = max(highs[-10:-1]); pl = min(lows[-10:-1])
        if closes[-1] > ph: buy_w += 2.0
        elif closes[-1] < pl: sell_w += 2.0
    
    # Order Flow (weight 2.5)
    bp = sp = 0.0
    for c in candles[-10:]:
        h=float(c["mid"]["h"]); l=float(c["mid"]["l"]); cl=float(c["mid"]["c"])
        r=h-l
        if r>0: bp+=(cl-l)/r; sp+=(h-cl)/r
    t=bp+sp
    if t>0:
        ratio=bp/t
        if ratio>0.62: buy_w+=2.5
        elif ratio<0.38: sell_w+=2.5
    
    # CHOCH (weight 2.0)
    if len(candles) >= 20:
        t1=closes[-10]-closes[-20]; t2=closes[-1]-closes[-10]
        if t1<0 and t2>0: buy_w+=2.0
        elif t1>0 and t2<0: sell_w+=2.0
    
    total=buy_w+sell_w
    if total==0: return "HOLD",0.0
    
    # Regime-specific threshold
    min_conf = {"TRENDING":0.62,"RANGING":0.67}.get(regime,0.65)
    
    if buy_w>=sell_w:
        conf=buy_w/total
        return ("BUY",conf) if conf>=min_conf else ("HOLD",0.0)
    else:
        conf=sell_w/total
        return ("SELL",conf) if conf>=min_conf else ("HOLD",0.0)

def run_window(candles, pair, label):
    bal=START_BAL; peak=START_BAL; max_dd=0.0
    trades=[]; pos=None
    WARMUP=100
    for i in range(WARMUP, len(candles)):
        cur=candles[i]
        try:
            hi=float(cur["mid"]["h"]); lo=float(cur["mid"]["l"]); cl=float(cur["mid"]["c"])
        except: continue
        if pos:
            hit=None
            if pos["dir"]=="BUY":
                if lo<=pos["sl"]: hit="SL"
                elif hi>=pos["tp"]: hit="TP"
            else:
                if hi>=pos["sl"]: hit="SL"
                elif lo<=pos["tp"]: hit="TP"
            if hit:
                ex=pos["sl"] if hit=="SL" else pos["tp"]
                pv=10 if "JPY" not in pair else 0.1
                pnl=(ex-pos["entry"] if pos["dir"]=="BUY" else pos["entry"]-ex)*abs(pos["units"])*pv
                bal+=pnl; peak=max(peak,bal)
                dd=(peak-bal)/peak; max_dd=max(max_dd,dd)
                trades.append({"pnl":round(pnl,2),"type":hit})
                pos=None
        if pos is None:
            window=candles[max(0,i-150):i]
            if len(window)<50: continue
            regime=detect_regime(window)
            sig,conf=generate_signal(window, regime)
            if sig in ("BUY","SELL"):
                a=calc_atr(window)
                if a<=0: continue
                units=max(1000,min(int((bal*RISK_PCT)/(a*10000)),50000)) if a>0 else 1000
                sl_p=cl-a*SL_ATR if sig=="BUY" else cl+a*SL_ATR
                tp_p=cl+a*TP_ATR if sig=="BUY" else cl-a*TP_ATR
                pos={"dir":sig,"entry":cl,"sl":sl_p,"tp":tp_p,"units":units}
    
    if not trades: return {"label":label,"trades":0,"win_rate":0,"total_pnl":0,"sharpe":0,"max_dd":0}
    wins=[t for t in trades if t["pnl"]>0]
    wr=len(wins)/len(trades)*100
    total_pnl=bal-START_BAL
    pnls=[t["pnl"] for t in trades]
    avg=sum(pnls)/len(pnls)
    std=math.sqrt(sum((p-avg)**2 for p in pnls)/len(pnls)) if len(pnls)>1 else 1
    sharpe=(avg/std)*math.sqrt(252) if std>0 else 0
    return {"label":label,"trades":len(trades),"win_rate":round(wr,1),
            "total_pnl":round(total_pnl,2),"sharpe":round(sharpe,2),
            "max_dd":round(max_dd*100,1)}

def main():
    print(f"\n{'='*60}")
    print("  PROJECT CHAKRA — WALK-FORWARD VALIDATION")
    print(f"  {N_WINDOWS} rolling windows | {TRAIN_MONTHS}M train | {TEST_MONTHS}M test")
    print(f"{'='*60}\n")
    
    all_results=[]
    end_dt=datetime.utcnow()
    
    for pair in PAIRS:
        print(f"\n▶ {pair}")
        # Fetch 3 years of data
        start_dt=end_dt-timedelta(days=3*365)
        candles=fetch_candles(pair, start_dt, end_dt)
        if not candles or len(candles)<1000:
            print(f"  Insufficient data — skip"); continue
        print(f"  {len(candles):,} candles fetched")
        
        pair_results=[]
        total_candles=len(candles)
        candles_per_month=int(total_candles/(36))  # ~30 candles per month H1
        
        for w in range(N_WINDOWS):
            train_start=w*candles_per_month
            train_end=train_start+(TRAIN_MONTHS*candles_per_month)
            test_end=train_end+(TEST_MONTHS*candles_per_month)
            if test_end>total_candles: break
            test_candles=candles[train_end:test_end]
            if len(test_candles)<200: break
            label=f"W{w+1}"
            result=run_window(test_candles, pair, label)
            pair_results.append(result)
            status="✅" if result["win_rate"]>=45 and result["total_pnl"]>0 else "❌"
            print(f"  {status} {label}: WR={result['win_rate']}% | P&L=${result['total_pnl']:+,.0f} | Sharpe={result['sharpe']:.2f}")
        
        if pair_results:
            avg_wr=sum(r["win_rate"] for r in pair_results)/len(pair_results)
            avg_pnl=sum(r["total_pnl"] for r in pair_results)/len(pair_results)
            passing=sum(1 for r in pair_results if r["win_rate"]>=45 and r["total_pnl"]>0)
            print(f"  SUMMARY: Avg WR={avg_wr:.1f}% | Avg P&L=${avg_pnl:+,.0f} | {passing}/{len(pair_results)} windows PASS")
            all_results.extend(pair_results)
    
    if all_results:
        overall_wr=sum(r["win_rate"] for r in all_results)/len(all_results)
        overall_pnl=sum(r["total_pnl"] for r in all_results)
        passing=sum(1 for r in all_results if r["win_rate"]>=45 and r["total_pnl"]>0)
        print(f"\n{'='*60}")
        print(f"  WALK-FORWARD COMPLETE")
        print(f"  Windows tested: {len(all_results)}")
        print(f"  Avg Win Rate:   {overall_wr:.1f}%")
        print(f"  Total P&L:      ${overall_pnl:+,.0f}")
        print(f"  Passing:        {passing}/{len(all_results)}")
        verdict="✅ SYSTEM VALIDATED" if overall_wr>=45 and passing>=len(all_results)*0.6 else "⚠️  NEEDS OPTIMIZATION"
        print(f"  {verdict}")
        print(f"{'='*60}\n")
        with open("walkforward_results.json","w") as f:
            json.dump({"run_date":datetime.utcnow().isoformat(),"results":all_results,
                       "summary":{"avg_wr":overall_wr,"total_pnl":overall_pnl}}, f, indent=2)
        print("Results saved to: walkforward_results.json")

if __name__ == "__main__":
    main()
