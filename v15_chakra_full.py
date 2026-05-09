"""
PROJECT CHAKRA V15 — MAIN SYSTEM
Run: py -3.11 v15_chakra.py
Run once: py -3.11 v15_chakra.py --once
Dashboard: http://localhost:5001
"""
import os,json,time,logging,requests,threading,math
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import deque
from flask import Flask,jsonify,render_template_string
from dotenv import load_dotenv
from v15_ict_engine import ICTChainEngine

# ── Import all V13 agents and infrastructure ──────────────────────
from v13_production import (
    EMAAgent,MACDAgent,RSIAgent,BollingerAgent,WyckoffAgent,
    ATRAgent,StochasticAgent,SessionAgent,BreakoutAgent,
    BOSAgent,CHOCHAgent,OrderBlockAgent,FVGAgent,KillzoneAgent,
    OTEAgent,SilverBulletAgent,LiquidityAgent,
    MomentumAgent,VWAPAgent,FibonacciAgent,DivergenceAgent,
    PivotPointAgent,MarketStructureAgent,HeikinAshiAgent,
    IchimokuAgent,SupertrendAgent,DXYAgent,GoldCorrelAgent,
    VIXAgent,PriceActionAgent,AdaptiveEMAAgent,SessionVolumeAgent,
    NewsFlowAgent,MultiTimeframeConfluenceAgent,
    ConsensusMetaAgent,DXYInverseCorrelAgent,
    get_oanda_candles,place_oanda_order,get_open_positions,
    MarketRegimeDetector,AgentWeightSystem,RLAgent,
    send_telegram,log_to_supabase,
    OANDA_TOKEN,OANDA_ACCOUNT,OANDA_BASE_URL,
    PAIRS
)

load_dotenv()
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [V15] %(message)s')
log=logging.getLogger("V15")

ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY","")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT","")
CONFIDENCE_BASE= 0.68
MIN_AGREE      = 0.35
RISK_PCT       = 0.005
MAX_DD         = 0.02
CYCLE_SECS     = 30
MAX_SPREAD_MULT= 2.0

CORR_PAIRS={
    "EUR_USD":["GBP_USD"],"GBP_USD":["EUR_USD"],
    "XAU_USD":["USD_JPY"],"AUD_USD":[]
}
REGIME_WEIGHTS={
    "TRENDING":{"EMAAgent":1.6,"MACDAgent":1.5,"SupertrendAgent":1.5,
                "AdaptiveEMAAgent":1.4,"IchimokuAgent":1.3,
                "BOSAgent":1.3,"CHOCHAgent":1.3,
                "RSIAgent":0.7,"BollingerAgent":0.7,"StochasticAgent":0.7},
    "RANGING":{"RSIAgent":1.5,"BollingerAgent":1.5,"StochasticAgent":1.4,
               "PivotPointAgent":1.3,"FibonacciAgent":1.3,
               "EMAAgent":0.8,"SupertrendAgent":0.7,"MACDAgent":0.8},
    "VOLATILE":{"ATRAgent":1.5,"VIXAgent":1.5,"KillzoneAgent":1.3,
                "SilverBulletAgent":1.3,"LiquidityAgent":1.3,
                "MomentumAgent":0.7,"VWAPAgent":0.8},
}

# ════════════════════════════════════════════════════════════════
#  UPGRADE 1 — CLAUDE NLP SENTIMENT
# ════════════════════════════════════════════════════════════════
class ClaudeNLPAgent:
    name="ClaudeNLPAgent"
    QUERIES={"EUR_USD":"Euro Dollar EUR/USD","GBP_USD":"Pound Sterling GBP",
             "USD_JPY":"Dollar Yen JPY","AUD_USD":"Australian Dollar AUD",
             "USD_CAD":"Canadian Dollar CAD oil","XAU_USD":"Gold XAUUSD",
             "BTC_USD":"Bitcoin BTC crypto"}
    def __init__(self):
        self._cache={}; self._ts={}
        self.news_key=os.getenv("NEWS_KEY","")
    def _headlines(self,pair):
        q=self.QUERIES.get(pair,pair)
        url=(f"https://newsapi.org/v2/everything?q={q}"
             f"&language=en&sortBy=publishedAt&pageSize=8"
             f"&apiKey={self.news_key}")
        try:
            r=requests.get(url,timeout=8)
            return [a["title"] for a in r.json().get("articles",[])[:8] if a.get("title")]
        except: return []
    def analyze(self,pair,candles):
        now=time.time()
        if pair in self._ts and (now-self._ts[pair])<900:
            return self._cache.get(pair,{"signal":"HOLD","confidence":0.0,"reason":""})
        if not ANTHROPIC_KEY:
            return {"signal":"HOLD","confidence":0.0,"reason":"No API key"}
        hl=self._headlines(pair)
        if not hl: return {"signal":"HOLD","confidence":0.0,"reason":"No headlines"}
        prompt=(f"Analyze these forex headlines for {pair}:\n"
                +"\n".join(f"- {h}" for h in hl[:8])
                +'\n\nReturn ONLY valid JSON (no markdown):\n'
                '{"signal":"BUY or SELL or HOLD","confidence":0.0to1.0,"reason":"one sentence"}')
        try:
            r=requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01",
                         "content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":100,
                      "messages":[{"role":"user","content":prompt}]},timeout=12)
            txt=r.json()["content"][0]["text"].strip().replace("```json","").replace("```","")
            result=json.loads(txt)
            out={"signal":result.get("signal","HOLD"),
                 "confidence":float(result.get("confidence",0.5)),
                 "reason":result.get("reason",""),"agent":self.name}
            self._cache[pair]=out; self._ts[pair]=now
            return out
        except Exception as e:
            log.warning(f"[NLP] {pair}: {e}")
            return {"signal":"HOLD","confidence":0.0,"reason":"Error"}

# ════════════════════════════════════════════════════════════════
#  UPGRADE 2 — CORRELATION GUARD
# ════════════════════════════════════════════════════════════════
class CorrelationGuard:
    def blocked(self,pair,direction):
        related=CORR_PAIRS.get(pair,[])
        if not related: return False,""
        try:
            positions=get_open_positions()
            for pos in positions:
                pp=pos.get("instrument","").replace("-","_")
                if pp in related:
                    u=float(pos.get("long",{}).get("units",0) or
                            pos.get("short",{}).get("units",0) or 0)
                    pd="BUY" if u>0 else "SELL"
                    if pd==direction:
                        return True,f"Blocked: {pp} already {pd}"
        except Exception as e: log.warning(f"[CorrGuard] {e}")
        return False,""

# ════════════════════════════════════════════════════════════════
#  UPGRADE 3 — LOXM EXECUTION OPTIMIZER
# ════════════════════════════════════════════════════════════════
class ExecutionOptimizer:
    def __init__(self): self._hist={}
    def _spread(self,pair):
        try:
            r=requests.get(f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT}/pricing?instruments={pair}",
                headers={"Authorization":f"Bearer {OANDA_TOKEN}"},timeout=6)
            pr=r.json().get("prices",[])
            if pr:
                ask=float(pr[0].get("asks",[{}])[0].get("price",0))
                bid=float(pr[0].get("bids",[{}])[0].get("price",0))
                return ask-bid
        except: pass
        return None
    def _good_session(self):
        h=datetime.utcnow().hour
        return (7<=h<=16) or (12<=h<=21)
    def check(self,pair):
        sp=self._spread(pair)
        if sp and sp>0:
            hist=self._hist.setdefault(pair,deque(maxlen=20))
            hist.append(sp)
            if len(hist)>=5:
                avg=sum(hist)/len(hist)
                if sp>avg*MAX_SPREAD_MULT:
                    return False,f"Spread {sp:.5f} is {sp/avg:.1f}x normal"
        if not self._good_session():
            return False,"Outside active session"
        return True,"OK"

# ════════════════════════════════════════════════════════════════
#  UPGRADE 4 — CLAUDE TRADE EXPLAINER
# ════════════════════════════════════════════════════════════════
class TradeExplainer:
    def explain(self,pair,direction,price,sl,tp,conf,agents,regime,nlp_reason):
        threading.Thread(target=self._run,
            args=(pair,direction,price,sl,tp,conf,agents,regime,nlp_reason),
            daemon=True).start()
    def _run(self,pair,direction,price,sl,tp,conf,agents,regime,nlp_reason):
        if not ANTHROPIC_KEY: return
        prompt=(f"Write a 2-sentence trade explanation for Telegram. Plain text only.\n"
                f"Trade: {pair} {direction} @ {price} | SL:{sl} TP:{tp} "
                f"Confidence:{conf:.1%} Regime:{regime} "
                f"Top signals:{','.join(agents[:4])} News:{nlp_reason}")
        try:
            r=requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01",
                         "content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":100,
                      "messages":[{"role":"user","content":prompt}]},timeout=10)
            txt=r.json()["content"][0]["text"].strip()
            msg=(f"⚡ CHAKRA V15\n\n{txt}\n\n"
                 f"📊 {regime} | 🎯 {conf:.1%} | "
                 f"{'✅ ICT ALIGNED' if 'ICTChain' in str(agents) else '📈 Agent Vote'}")
            send_telegram(msg)
        except Exception as e: log.warning(f"[Explainer] {e}")

# ════════════════════════════════════════════════════════════════
#  UPGRADE 5 — ADAPTIVE THRESHOLD
# ════════════════════════════════════════════════════════════════
class AdaptiveThreshold:
    def __init__(self,base=0.68,mn=0.60,mx=0.80):
        self.base=base; self.mn=mn; self.mx=mx
        self._r=deque(maxlen=20)
    def record(self,won): self._r.append(1 if won else 0)
    def get(self):
        if len(self._r)<10: return self.base
        wr=sum(self._r)/len(self._r)
        t=self.base+(0.50-wr)*0.4
        return max(self.mn,min(self.mx,t))

# ════════════════════════════════════════════════════════════════
#  UPGRADE 6 — H4 TREND FILTER
# ════════════════════════════════════════════════════════════════
class H4TrendFilter:
    def __init__(self): self._cache={}; self._ts={}
    def trend(self,pair,h4_candles=None):
        now=time.time()
        if pair in self._ts and (now-self._ts[pair])<3600:
            return self._cache[pair]
        try:
            c=h4_candles or get_oanda_candles(pair,"H4",50)
            closes=[float(x["mid"]["c"]) for x in c if x.get("complete")]
            if len(closes)<20: return "NEUTRAL"
            e20=sum(closes[-20:])/20
            e50=sum(closes[-50:])/50 if len(closes)>=50 else sum(closes)/len(closes)
            cur=closes[-1]
            t="BULLISH" if cur>e20>e50 else "BEARISH" if cur<e20<e50 else "NEUTRAL"
            self._cache[pair]=t; self._ts[pair]=now; return t
        except: return "NEUTRAL"
    def allows(self,pair,direction,h4_candles=None):
        t=self.trend(pair,h4_candles)
        if t=="NEUTRAL": return True,"H4 neutral"
        if t=="BULLISH" and direction=="BUY": return True,"H4 BULLISH ✅"
        if t=="BEARISH" and direction=="SELL": return True,"H4 BEARISH ✅"
        return False,f"H4 {t} blocks {direction}"

# ════════════════════════════════════════════════════════════════
#  UPGRADE 7 — WEEKLY AUDITOR
# ════════════════════════════════════════════════════════════════
class WeeklyAuditor:
    def __init__(self): self.last=None
    def maybe_run(self,trades):
        if datetime.utcnow().weekday()!=6: return
        today=datetime.utcnow().strftime("%Y-%m-%d")
        if self.last==today: return
        self.last=today
        threading.Thread(target=self._run,args=(trades,),daemon=True).start()
    def _run(self,trades):
        if not ANTHROPIC_KEY or not trades: return
        recent=trades[-50:]
        prompt=(f"You are a senior quant analyst. Analyze {len(recent)} trades:\n"
                +json.dumps(recent,indent=2)[:3000]
                +"\n\nProvide: 1)Top 3 losing patterns 2)Top 3 winning patterns "
                "3)Parameter recommendations 4)Pairs to review 5)Expected WR improvement")
        try:
            r=requests.post("https://api.anthropic.com/v1/messages",
                headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01",
                         "content-type":"application/json"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":800,
                      "messages":[{"role":"user","content":prompt}]},timeout=30)
            audit=r.json()["content"][0]["text"].strip()
            entry={"date":datetime.utcnow().isoformat(),"audit":audit}
            existing=[]
            if os.path.exists("weekly_audit_log.json"):
                with open("weekly_audit_log.json") as f: existing=json.load(f)
            existing.append(entry)
            with open("weekly_audit_log.json","w") as f: json.dump(existing,f,indent=2)
            send_telegram(f"📋 WEEKLY AUDIT\n\n{audit[:400]}...")
            log.info("[Audit] Completed")
        except Exception as e: log.warning(f"[Audit] {e}")

# ════════════════════════════════════════════════════════════════
#  MACRO EVENT SCANNER
# ════════════════════════════════════════════════════════════════
class MacroScanner:
    def should_trade(self,pair):
        h=datetime.utcnow().hour
        if 12<=h<=14 and pair in ["EUR_USD","GBP_USD","USD_JPY","USD_CAD","AUD_USD"]:
            return False,"US data window 12-14 UTC"
        return True,"Clear"

# ════════════════════════════════════════════════════════════════
#  V15 MASTER ORCHESTRATOR
# ════════════════════════════════════════════════════════════════
class V15Orchestrator:
    def __init__(self):
        self.regime_det =MarketRegimeDetector()
        self.weight_sys =AgentWeightSystem()
        self.rl_agent   =RLAgent()
        self.ict_engine =ICTChainEngine()
        self.claude_nlp =ClaudeNLPAgent()
        self.corr_guard =CorrelationGuard()
        self.exec_opt   =ExecutionOptimizer()
        self.explainer  =TradeExplainer()
        self.threshold  =AdaptiveThreshold(CONFIDENCE_BASE)
        self.h4_filter  =H4TrendFilter()
        self.macro      =MacroScanner()
        self.auditor    =WeeklyAuditor()
        self.agents=[EMAAgent(),MACDAgent(),RSIAgent(),BollingerAgent(),
                     WyckoffAgent(),ATRAgent(),StochasticAgent(),SessionAgent(),
                     BreakoutAgent(),BOSAgent(),CHOCHAgent(),OrderBlockAgent(),
                     FVGAgent(),KillzoneAgent(),OTEAgent(),SilverBulletAgent(),
                     LiquidityAgent(),MomentumAgent(),VWAPAgent(),FibonacciAgent(),
                     DivergenceAgent(),PivotPointAgent(),MarketStructureAgent(),
                     HeikinAshiAgent(),IchimokuAgent(),SupertrendAgent(),DXYAgent(),
                     GoldCorrelAgent(),VIXAgent(),PriceActionAgent(),AdaptiveEMAAgent(),
                     SessionVolumeAgent(),NewsFlowAgent(),MultiTimeframeConfluenceAgent(),
                     ConsensusMetaAgent(),DXYInverseCorrelAgent()]
        self.candle_cache={}
        self.trade_mem=self._load_mem()
        self.weights=self._load_weights()
        self.cycle=0; self.balance=100000.0
        self.signals_log=[]; self._nlp_cache={}

    def _load_mem(self):
        for f in ["v15_memory.json","v14_memory.json"]:
            if os.path.exists(f):
                with open(f) as fp: return json.load(fp)
        return []
    def _save_mem(self):
        with open("v15_memory.json","w") as f:
            json.dump(self.trade_mem[-1000:],f,indent=2)
    def _load_weights(self):
        for f in ["v15_weights.json","v14_weights.json"]:
            if os.path.exists(f):
                with open(f) as fp: return json.load(fp)
        return {a.name:1.0 for a in self.agents}
    def _save_weights(self):
        with open("v15_weights.json","w") as f: json.dump(self.weights,f,indent=2)

    # ── Pre-fetch all candles in parallel ────────────────────────
    def prefetch_candles(self):
        grans=["M15","H1","H4","D"]
        def fetch_one(pair,gran):
            try: return pair,gran,get_oanda_candles(pair,gran,count=100)
            except: return pair,gran,[]
        with ThreadPoolExecutor(max_workers=28) as ex:
            futs=[ex.submit(fetch_one,p,g) for p in PAIRS for g in grans]
            for fut in as_completed(futs):
                pair,gran,data=fut.result()
                if pair not in self.candle_cache: self.candle_cache[pair]={}
                self.candle_cache[pair][gran]=data
        log.info(f"[Cache] Fetched {len(PAIRS)} pairs × {len(grans)} TFs")

    # ── Pre-fetch NLP for all pairs in parallel ───────────────────
    def prefetch_nlp(self):
        def get_nlp(pair):
            m15=self.candle_cache.get(pair,{}).get("M15",[])
            return pair,self.claude_nlp.analyze(pair,m15)
        self._nlp_cache={}
        with ThreadPoolExecutor(max_workers=7) as ex:
            futs={ex.submit(get_nlp,p):p for p in PAIRS}
            for fut in as_completed(futs):
                pair,nlp=fut.result(); self._nlp_cache[pair]=nlp

    # ── Apply regime weights ──────────────────────────────────────
    def _weighted_conf(self,aname,conf,regime):
        rw=REGIME_WEIGHTS.get(regime,{}).get(aname,1.0)
        aw=self.weights.get(aname,1.0)
        return conf*rw*aw

    # ── Analyse one pair ──────────────────────────────────────────
    def analyze_pair(self,pair):
        try:
            cache=self.candle_cache.get(pair,{})
            m15=cache.get("M15",[]); h1=cache.get("H1",[])
            h4=cache.get("H4",[]); d1=cache.get("D",[])
            if not m15 or len([x for x in m15 if x.get("complete")])<30:
                return None
            regime=self.regime_det.detect(h1) if h1 else "RANGING"
            buy_v=sell_v=hold_v=0
            buy_c=sell_c=0.0
            top_buy=[]; top_sell=[]

            def run_agent(ag):
                try:
                    s=ag.analyze(pair,m15,h1,h4)
                    return ag.name,s
                except: return ag.name,{"signal":"HOLD","confidence":0.0}

            with ThreadPoolExecutor(max_workers=12) as ex:
                futs={ex.submit(run_agent,a):a for a in self.agents}
                for fut in as_completed(futs):
                    aname,sig=fut.result()
                    d=sig.get("signal","HOLD"); rc=float(sig.get("confidence",0.5))
                    wc=self._weighted_conf(aname,rc,regime)
                    if d=="BUY": buy_v+=1; buy_c+=wc; top_buy.append((aname,wc))
                    elif d=="SELL": sell_v+=1; sell_c+=wc; top_sell.append((aname,wc))
                    else: hold_v+=1

            # Claude NLP (37th agent, 1.5x weight)
            nlp=self._nlp_cache.get(pair,{"signal":"HOLD","confidence":0.0,"reason":""})
            nlp_s=nlp.get("signal","HOLD"); nlp_c=float(nlp.get("confidence",0.5))*1.5
            nlp_reason=nlp.get("reason","")
            if nlp_s=="BUY": buy_v+=1; buy_c+=nlp_c; top_buy.append(("ClaudeNLP",nlp_c))
            elif nlp_s=="SELL": sell_v+=1; sell_c+=nlp_c; top_sell.append(("ClaudeNLP",nlp_c))

            # ICT Engine (super-agent, 3x weight when all 4 pillars align)
            ict=self.ict_engine.analyze_with_candles(pair,d1,h4,h1,m15)
            ict_s=ict.get("direction","HOLD"); ict_c=ict.get("ict_confidence",0.0)
            ict_aligned=ict.get("all_pillars",False); ict_reason=ict.get("reason","")
            if ict_aligned and ict_c>=0.65:
                wt=3.0
                if ict_s=="BUY": buy_v+=3; buy_c+=ict_c*wt; top_buy.append(("ICT_ALL4",ict_c*wt))
                elif ict_s=="SELL": sell_v+=3; sell_c+=ict_c*wt; top_sell.append(("ICT_ALL4",ict_c*wt))
                log.info(f"[ICT] {pair} ALL 4 PILLARS: {ict_s} {ict_c:.1%}")
            elif ict_c>=0.50:
                if ict_s=="BUY": buy_v+=1; buy_c+=ict_c*1.5; top_buy.append(("ICT_partial",ict_c*1.5))
                elif ict_s=="SELL": sell_v+=1; sell_c+=ict_c*1.5; top_sell.append(("ICT_partial",ict_c*1.5))

            total=buy_v+sell_v
            if total<3: return {"pair":pair,"signal":"HOLD","confidence":0,"tradeable":False,
                                 "regime":regime,"buy_votes":buy_v,"sell_votes":sell_v,
                                 "hold_votes":hold_v,"top_agents":[],"nlp_reason":nlp_reason,
                                 "ict_aligned":ict_aligned,"h4_ok":True,"h4_reason":""}

            if buy_v>sell_v:
                direction="BUY"; conf=buy_c/max(buy_v,1)/1.5
                top=sorted(top_buy,key=lambda x:x[1],reverse=True)
            else:
                direction="SELL"; conf=sell_c/max(sell_v,1)/1.5
                top=sorted(top_sell,key=lambda x:x[1],reverse=True)

            agent_pct=max(buy_v,sell_v)/(total+hold_v)
            threshold=self.threshold.get()
            h4_ok,h4_reason=self.h4_filter.allows(pair,direction,h4)
            top_names=[t[0] for t in top[:8]]

            tradeable=(conf>=threshold and agent_pct>=MIN_AGREE and h4_ok)
            return {"pair":pair,"signal":direction,"confidence":round(conf,3),
                    "threshold":round(threshold,3),"agent_pct":round(agent_pct,3),
                    "regime":regime,"buy_votes":buy_v,"sell_votes":sell_v,
                    "hold_votes":hold_v,"top_agents":top_names,"nlp_reason":nlp_reason,
                    "ict_aligned":ict_aligned,"ict_confidence":round(ict_c,3),
                    "ict_reason":ict_reason,"h4_ok":h4_ok,"h4_reason":h4_reason,
                    "tradeable":tradeable}
        except Exception as e:
            log.error(f"[Orch] {pair}: {e}"); return None

    # ── Execute trade ─────────────────────────────────────────────
    def execute_signal(self,analysis):
        pair=analysis["pair"]; direction=analysis["signal"]
        conf=analysis["confidence"]; regime=analysis["regime"]
        top=analysis["top_agents"]; nlp_r=analysis["nlp_reason"]
        if not analysis["tradeable"]: return
        macro_ok,macro_r=self.macro.should_trade(pair)
        if not macro_ok: log.info(f"[Macro] {pair}: {macro_r}"); return
        cb,cr=self.corr_guard.blocked(pair,direction)
        if cb: log.info(f"[Corr] {pair}: {cr}"); return
        eo_ok,eo_r=self.exec_opt.check(pair)
        if not eo_ok:
            log.info(f"[LOXM] {pair}: {eo_r} — waiting 30s")
            time.sleep(30)
            eo_ok,eo_r=self.exec_opt.check(pair)
            if not eo_ok: log.info(f"[LOXM] {pair}: rejected"); return
        # Size
        candles=get_oanda_candles(pair,"H1",20)
        if not candles: return
        closes=[float(x["mid"]["c"]) for x in candles if x.get("complete")]
        if len(closes)<14: return
        atr=sum(abs(closes[i]-closes[i-1]) for i in range(1,14))/14
        price=closes[-1]
        sl_d=atr*1.5; tp_d=atr*4.5
        pip=0.01 if "JPY" in pair else (0.1 if "XAU" in pair else 0.0001)
        units=int((self.balance*RISK_PCT)/(sl_d/pip*0.0001))
        units=max(100,min(units,50000))
        if direction=="SELL": units=-units
        sl=price-sl_d if direction=="BUY" else price+sl_d
        tp=price+tp_d if direction=="BUY" else price-tp_d
        log.info(f"[EXEC] {pair} {direction} {units:+d} @ {price:.5f} "
                 f"SL={sl:.5f} TP={tp:.5f} conf={conf:.2f}")
        result=place_oanda_order(pair,units,sl,tp)
        if result:
            rec={"time":datetime.utcnow().isoformat(),"pair":pair,
                 "direction":direction,"entry":price,"sl":sl,"tp":tp,
                 "units":units,"confidence":conf,"regime":regime,
                 "agents":top,"nlp":nlp_r,"ict":analysis.get("ict_aligned",False),
                 "outcome":None}
            self.trade_mem.append(rec); self._save_mem()
            self.explainer.explain(pair,direction,price,sl,tp,conf,top,regime,nlp_r)
            try: log_to_supabase("v15_trades",rec)
            except: pass

    # ── Recalibrate weights ───────────────────────────────────────
    def recalibrate(self):
        closed=[t for t in self.trade_mem if t.get("outcome")]
        if len(closed)<20: return
        scores={}
        for tr in closed[-200:]:
            for ag in tr.get("agents",[]):
                if ag not in scores: scores[ag]={"w":0,"l":0}
                if tr["outcome"]=="WIN":
                    scores[ag]["w"]+=1; self.threshold.record(True)
                else:
                    scores[ag]["l"]+=1; self.threshold.record(False)
        for ag,sc in scores.items():
            tot=sc["w"]+sc["l"]
            if tot>5:
                wr=sc["w"]/tot
                old=self.weights.get(ag,1.0)
                self.weights[ag]=round(max(0.3,min(2.5,old*0.7+(0.3+wr*1.4)*0.3)),3)
        self._save_weights()

    # ── Main cycle ────────────────────────────────────────────────
    def run_cycle(self):
        self.cycle+=1
        log.info(f"\n{'='*55}\n CYCLE {self.cycle} — "
                 f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n{'='*55}")
        self.auditor.maybe_run(self.trade_mem)
        if self.cycle%100==0: self.recalibrate()
        self.prefetch_candles()
        self.prefetch_nlp()
        results=[]
        with ThreadPoolExecutor(max_workers=7) as ex:
            futs={ex.submit(self.analyze_pair,p):p for p in PAIRS}
            for fut in as_completed(futs):
                r=fut.result()
                if r: results.append(r)
        results.sort(key=lambda x:x["confidence"],reverse=True)
        for r in results:
            ict_tag="🏛️ ICT" if r.get("ict_aligned") else ""
            log.info(f"  {r['pair']:10s} {r['signal']:4s} "
                     f"conf={r['confidence']:.2f} reg={r['regime']:9s} "
                     f"H4:{r.get('h4_reason','')[:18]} "
                     f"{'✅' if r['tradeable'] else '❌'} {ict_tag}")
            if r["tradeable"]: self.execute_signal(r)
        self.signals_log=results
        return results

    def run(self):
        import argparse
        ap=argparse.ArgumentParser(); ap.add_argument("--once",action="store_true")
        args=ap.parse_args()
        if args.once:
            self.run_cycle(); return
        log.info("🚀 PROJECT CHAKRA V15 — LIVE")
        log.info(f"   Pairs: {PAIRS}")
        while True:
            try: self.run_cycle()
            except Exception as e: log.error(f"Cycle error: {e}")
            time.sleep(CYCLE_SECS)

# ════════════════════════════════════════════════════════════════
#  FLASK DASHBOARD
# ════════════════════════════════════════════════════════════════
DASH="""<!DOCTYPE html><html><head><title>Chakra V15</title>
<meta http-equiv="refresh" content="30">
<style>*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#e0e0e0;font-family:monospace;padding:20px}
h1{color:#a78bfa;margin-bottom:16px;font-size:1.1rem}
.stats{display:flex;gap:16px;margin-bottom:18px;flex-wrap:wrap}
.stat{background:#0f0f1a;border:1px solid #1e1e3a;padding:10px 18px;border-radius:8px}
.stat .v{font-size:1.3rem;color:#a78bfa;font-weight:800}
.stat .l{font-size:0.72rem;color:#64748b}
table{width:100%;border-collapse:collapse;font-size:0.8rem}
th{background:#1e1e3a;color:#a78bfa;padding:8px;text-align:left}
td{padding:7px 8px;border-bottom:1px solid #1e1e3a}
.buy{color:#34d399}.sell{color:#f87171}.hold{color:#64748b}
.tr{background:#0d1a0d}.badge{padding:2px 7px;border-radius:8px;font-size:0.68rem}
.bg{background:#052e16;color:#34d399}.br{background:#1c0a0a;color:#f87171}
.ict{background:#180a2e;color:#a78bfa}</style></head><body>
<h1>⚡ PROJECT CHAKRA V15 — INSTITUTIONAL</h1>
<div class="stats">
<div class="stat"><div class="v">{{cycle}}</div><div class="l">Cycles</div></div>
<div class="stat"><div class="v">{{trades}}</div><div class="l">Trade Memory</div></div>
<div class="stat"><div class="v">{{thresh}}</div><div class="l">Threshold</div></div>
<div class="stat"><div class="v">37+ICT</div><div class="l">Agents</div></div>
</div>
<table><tr><th>Pair</th><th>Signal</th><th>Conf</th><th>Regime</th>
<th>H4</th><th>ICT</th><th>NLP Reason</th><th>Status</th></tr>
{% for r in sigs %}
<tr class="{{'tr' if r.tradeable else ''}}">
<td>{{r.pair}}</td>
<td class="{{'buy' if r.signal=='BUY' else 'sell' if r.signal=='SELL' else 'hold'}}">{{r.signal}}</td>
<td>{{(r.confidence*100)|round(1)}}%</td>
<td>{{r.regime}}</td>
<td style="font-size:0.72rem">{{r.h4_reason[:20]}}</td>
<td>{{'<span class="badge ict">✅ ALL4</span>'|safe if r.ict_aligned else '—'}}</td>
<td style="font-size:0.72rem;color:#94a3b8">{{r.nlp_reason[:35]}}</td>
<td>{{'<span class="badge bg">TRADE</span>'|safe if r.tradeable else '<span class="badge br">HOLD</span>'|safe}}</td>
</tr>{% endfor %}</table>
<p style="margin-top:12px;color:#334155;font-size:0.72rem">
V15: ClaudeNLP · RegimeWeights · CorrGuard · LOXM · H4Filter · ICTChain · WeeklyAudit · AdaptiveThreshold</p>
</body></html>"""

app=Flask(__name__)
orch=None

@app.route("/")
def dash():
    return render_template_string(DASH,
        sigs=orch.signals_log if orch else [],
        cycle=orch.cycle if orch else 0,
        trades=len(orch.trade_mem) if orch else 0,
        thresh=f"{orch.threshold.get():.2f}" if orch else "—")

@app.route("/api/signals")
def api_sigs(): return jsonify(orch.signals_log if orch else [])

@app.route("/api/status")
def api_status():
    return jsonify({"version":"V15","cycle":orch.cycle if orch else 0,
                    "trades":len(orch.trade_mem) if orch else 0,
                    "threshold":orch.threshold.get() if orch else CONFIDENCE_BASE})

if __name__=="__main__":
    orch=V15Orchestrator()
    threading.Thread(target=lambda:app.run(host="0.0.0.0",port=5001,debug=False),
                     daemon=True).start()
    log.info("📊 Dashboard: http://localhost:5001")
    orch.run()
