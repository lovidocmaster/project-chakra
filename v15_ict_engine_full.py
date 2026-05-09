"""
PROJECT CHAKRA V15 — ICT CHAIN ENGINE
True ICT: Fractal + Bias + Structure + Liquidity = Signal
All 4 pillars must align. No partial signals.
"""
import os, json, time, logging, requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("ICT")

OANDA_TOKEN    = os.getenv("OANDA_TOKEN","")
OANDA_ACCOUNT  = os.getenv("OANDA_ACCOUNT","")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL","https://api-fxpractice.oanda.com")

# ─── OANDA DATA ───────────────────────────────────────────────────
def fetch_candles(pair, gran, count):
    url = (f"{OANDA_BASE_URL}/v3/instruments/{pair}/candles"
           f"?granularity={gran}&count={count}&price=M")
    try:
        r = requests.get(url,
            headers={"Authorization":f"Bearer {OANDA_TOKEN}"},
            timeout=10)
        return r.json().get("candles",[])
    except Exception as e:
        log.warning(f"[ICT] {pair} {gran}: {e}")
        return []

def _c(candles): return [float(x["mid"]["c"]) for x in candles if x.get("complete")]
def _h(candles): return [float(x["mid"]["h"]) for x in candles if x.get("complete")]
def _l(candles): return [float(x["mid"]["l"]) for x in candles if x.get("complete")]
def _b(candles): return [(float(x["mid"]["o"]),float(x["mid"]["c"]),
                          float(x["mid"]["h"]),float(x["mid"]["l"]))
                         for x in candles if x.get("complete")]

# ─── PILLAR 1: FRACTAL ALIGNMENT ─────────────────────────────────
class FractalAlignmentEngine:
    def _ema(self, p, n):
        if len(p)<n: return p[-1] if p else 0
        k=2/(n+1); e=sum(p[:n])/n
        for x in p[n:]: e=x*k+e*(1-k)
        return e

    def _bias(self, candles):
        c=_c(candles); h=_h(candles); l=_l(candles)
        if len(c)<50: return "NEUTRAL",0.4
        e20=self._ema(c,20); e50=self._ema(c,50)
        price=c[-1]; mid=(max(h[-20:])+min(l[-20:]))/2
        s=0.0
        if price>e20>e50: s+=0.4
        elif price<e20<e50: s-=0.4
        if price>mid: s+=0.3
        else: s-=0.3
        if e20>e50: s+=0.3
        else: s-=0.3
        if s>0.3: return "BULLISH",abs(s)
        elif s<-0.3: return "BEARISH",abs(s)
        return "NEUTRAL",abs(s)

    def analyze(self, d1, h4, h1, m15):
        b_d1,s_d1=self._bias(d1)
        b_h4,s_h4=self._bias(h4)
        b_h1,s_h1=self._bias(h1)
        b_m15,_  =self._bias(m15)
        if b_d1==b_h4 and b_d1!="NEUTRAL":
            master=b_d1; ms=(s_d1+s_h4)/2
        elif b_d1!="NEUTRAL": master=b_d1; ms=s_d1*0.7
        elif b_h4!="NEUTRAL": master=b_h4; ms=s_h4*0.6
        else: master="NEUTRAL"; ms=0.3
        biases=[b_d1,b_h4,b_h1,b_m15]
        nn=[b for b in biases if b!="NEUTRAL"]
        aligned=len(set(nn))==1 and len(nn)>=3
        score=min(1.0, ms+0.2 if aligned else ms)
        return {"master_bias":master,"h1_bias":b_h1,"m15_bias":b_m15,
                "d1_bias":b_d1,"h4_bias":b_h4,"aligned":aligned,
                "fractal_score":round(score,3)}

# ─── PILLAR 2: BIAS ENGINE ────────────────────────────────────────
class BiasEngine:
    def _sweep(self, candles, direction):
        h=_h(candles); l=_l(candles); c=_c(candles)
        if len(c)<30: return False,0.0
        rh=h[-25:-5]; rl=l[-25:-5]
        lh=h[-5:]; ll=l[-5:]; lc=c[-5:]
        if not rh or not rl: return False,0.5
        if direction=="BULLISH":
            sl=min(rl); swept=min(ll)<sl; rec=lc[-1]>sl
            if swept and rec:
                r=(lc[-1]-min(ll))/max(lc[-1]-sl,0.0001)
                return True,min(r,1.0)
        else:
            sh=max(rh); swept=max(lh)>sh; rej=lc[-1]<sh
            if swept and rej:
                r=(max(lh)-lc[-1])/max(max(lh)-sh,0.0001)
                return True,min(r,1.0)
        return False,0.3

    def _pd_zone(self, candles, bias):
        h=_h(candles); l=_l(candles); c=_c(candles)
        if len(c)<20: return "NEUTRAL",0.5
        h50=max(h[-50:]) if len(h)>=50 else max(h)
        l50=min(l[-50:]) if len(l)>=50 else min(l)
        fib50=l50+(h50-l50)*0.5
        f618=l50+(h50-l50)*0.618; f79=l50+(h50-l50)*0.79
        price=c[-1]; rng=h50-l50 if h50!=l50 else 1
        if bias=="BULLISH":
            if price<fib50:
                if f618<=price<=f79 or l50+rng*0.382<=price<=fib50:
                    return "DISCOUNT",0.85
                return "DISCOUNT",0.65
            return "PREMIUM",0.2
        else:
            if price>fib50:
                sf618=h50-rng*0.618; sf79=h50-rng*0.79
                if sf79<=price<=sf618: return "PREMIUM",0.85
                return "PREMIUM",0.65
            return "DISCOUNT",0.2

    def analyze(self, bias, h4, h1):
        sw_ok,sw_s=self._sweep(h4,bias)
        pd,pd_s=self._pd_zone(h1,bias)
        pd_ok=(bias=="BULLISH" and pd=="DISCOUNT") or \
              (bias=="BEARISH" and pd=="PREMIUM")
        score=0.0
        if sw_ok: score+=0.5
        if pd_ok: score+=0.5
        return {"bias_confirmed":score>=0.5,"liquidity_sweep":sw_ok,
                "sweep_score":round(sw_s,3),"pd_zone":pd,
                "pd_score":round(pd_s,3),"pd_correct":pd_ok,
                "bias_score":round(score,3)}

# ─── PILLAR 3: MARKET STRUCTURE ───────────────────────────────────
class MarketStructureEngine:
    def _swings(self, highs, lows, lb=3):
        sh=[]; sl=[]
        n=len(highs)
        for i in range(lb,n-lb):
            if all(highs[i]>=highs[i-j] and highs[i]>=highs[i+j]
                   for j in range(1,lb+1)): sh.append((i,highs[i]))
            if all(lows[i]<=lows[i-j] and lows[i]<=lows[i+j]
                   for j in range(1,lb+1)): sl.append((i,lows[i]))
        return sh,sl

    def _choch(self, sh, sl, c, bias):
        if not sh or not sl: return False,None
        if bias=="BULLISH":
            itls=sorted(sl[-4:],key=lambda x:x[0])
            if len(itls)>=2 and itls[-1][1]<itls[-2][1]:
                return True,itls[-1][1]
        else:
            iths=sorted(sh[-4:],key=lambda x:x[0])
            if len(iths)>=2 and iths[-1][1]>iths[-2][1]:
                return True,iths[-1][1]
        return False,None

    def _bos(self, sh, sl, c, bias):
        p=c[-1] if c else 0
        if bias=="BULLISH" and sh:
            lsh=max(h for _,h in sh[-5:])
            if p>lsh: return True,lsh
        elif bias=="BEARISH" and sl:
            lsl=min(l for _,l in sl[-5:])
            if p<lsl: return True,lsl
        return False,None

    def analyze(self, bias, h1, m15):
        h1h=_h(h1); h1l=_l(h1); h1c=_c(h1)
        m15h=_h(m15); m15l=_l(m15); m15c=_c(m15)
        if len(h1c)<20 or len(m15c)<20:
            return {"structure_valid":False,"choch":False,"bos":False,
                    "ith":None,"itl":None,"sth":None,"stl":None,
                    "structure_score":0.0,"reason":"Insufficient data"}
        h1sh,h1sl=self._swings(h1h,h1l,3)
        choch,cl=self._choch(h1sh,h1sl,h1c,bias)
        bos,bl=self._bos(h1sh,h1sl,h1c,bias)
        m15sh,m15sl=self._swings(m15h,m15l,2)
        ith=h1sh[-1][1] if h1sh else None
        itl=h1sl[-1][1] if h1sl else None
        sth=m15sh[-1][1] if m15sh else None
        stl=m15sl[-1][1] if m15sl else None
        score=0.0; parts=[]
        if bos: score+=0.4; parts.append(f"BOS@{bl:.5f}" if bl else "BOS")
        if choch: score+=0.3; parts.append(f"CHoCH@{cl:.5f}" if cl else "CHoCH")
        if ith and itl: score+=0.2; parts.append(f"ITH={ith:.5f} ITL={itl:.5f}")
        if sth and stl: score+=0.1
        return {"structure_valid":bos or choch,"choch":choch,"choch_level":cl,
                "bos":bos,"bos_level":bl,"ith":ith,"itl":itl,"sth":sth,"stl":stl,
                "structure_score":round(score,3),"reason":" | ".join(parts)}

# ─── PILLAR 4: LIQUIDITY + POI ────────────────────────────────────
class LiquidityPOIEngine:
    KZ={"London":(6,10),"NewYork":(12,16),"LondonNY":(11,13),"Asian":(0,3)}

    def _killzone(self):
        h=datetime.now(timezone.utc).hour
        for n,(s,e) in self.KZ.items():
            if s<=h<e: return n
        return None

    def _displacement(self, candles, bias):
        b=_b(candles)
        if len(b)<10: return False,0.0
        sizes=[abs(c-o) for o,c,h,l in b[-20:]]
        avg=sum(sizes)/len(sizes) if sizes else 0
        for o,c,hh,l in b[-5:]:
            bd=abs(c-o)
            if bd<avg*1.5: continue
            if bias=="BULLISH" and c>o: return True,min(bd/(avg*2),1.0)
            elif bias=="BEARISH" and c<o: return True,min(bd/(avg*2),1.0)
        return False,0.0

    def _order_block(self, candles, bias):
        b=_b(candles); c=_c(candles)
        if len(b)<10: return False,0,0,0.0
        price=c[-1] if c else 0
        for i in range(len(b)-2,max(0,len(b)-10),-1):
            o,cl,h,l=b[i]
            if bias=="BULLISH" and o>cl:
                if l<=price<=h*1.005:
                    return True,h,l,1.0-(i/len(b))
            elif bias=="BEARISH" and cl>o:
                if l*0.995<=price<=h:
                    return True,h,l,1.0-(i/len(b))
        return False,0,0,0.0

    def _fvg(self, candles, bias):
        b=_b(candles); c=_c(candles)
        if len(b)<5: return False,0,0,0.0
        price=c[-1] if c else 0
        for i in range(len(b)-3,max(0,len(b)-15),-1):
            o1,c1,h1,l1=b[i]; _,_,_,_=b[i+1]; o3,c3,h3,l3=b[i+2]
            if bias=="BULLISH" and h1<l3:
                if h1<=price<=l3: return True,l3,h1,0.9
                if price<h1*1.001: return True,l3,h1,0.7
            elif bias=="BEARISH" and l1>h3:
                if h3<=price<=l1: return True,l1,h3,0.9
                if price>l1*0.999: return True,l1,h3,0.7
        return False,0,0,0.0

    def _ote(self, candles, bias):
        h=_h(candles); l=_l(candles); c=_c(candles)
        if len(c)<20: return False,0.0
        hi=max(h[-20:]); lo=min(l[-20:]); price=c[-1]; rng=hi-lo if hi!=lo else 1
        f618=lo+rng*0.618; f79=lo+rng*0.79
        if bias=="BULLISH": return f618<=price<=f79, f618
        sf618=hi-rng*0.618; sf79=hi-rng*0.79
        return sf79<=price<=sf618, sf618

    def analyze(self, bias, m15, h1):
        kz=self._killzone()
        d_ok,d_s=self._displacement(m15,bias)
        ob_ok,ob_h,ob_l,ob_s=self._order_block(m15,bias)
        fvg_ok,fvg_h,fvg_l,fvg_s=self._fvg(m15,bias)
        ote_ok,ote_l=self._ote(m15,bias)
        poi=ob_ok or fvg_ok
        score=0.0
        if d_ok: score+=0.25
        if poi:  score+=0.30
        if ote_ok: score+=0.20
        if kz: score+=0.15
        score+=0.10
        return {"poi_found":poi,"poi_type":"OB" if ob_ok else ("FVG" if fvg_ok else None),
                "poi_high":ob_h if ob_ok else fvg_h,"poi_low":ob_l if ob_ok else fvg_l,
                "displacement":d_ok,"disp_score":round(d_s,3),
                "order_block":ob_ok,"ob_high":ob_h,"ob_low":ob_l,
                "fvg_found":fvg_ok,"fvg_high":fvg_h,"fvg_low":fvg_l,
                "ote_zone":ote_ok,"ote_level":ote_l,
                "killzone":kz,"in_killzone":kz is not None,
                "liq_score":round(min(score,1.0),3)}

# ─── TRADE MEMORY ────────────────────────────────────────────────
class ICTTradeMemory:
    FILE="v15_ict_memory.json"
    def __init__(self):
        self.mem=json.load(open(self.FILE)) if os.path.exists(self.FILE) else {}
    def _save(self):
        with open(self.FILE,"w") as f: json.dump(self.mem,f,indent=2)
    def update(self, pair, result):
        if pair not in self.mem:
            self.mem[pair]={"bias_cycles":0,"bias_history":[],"last_trade_time":None,"wins":0,"losses":0}
        m=self.mem[pair]
        hist=m.get("bias_history",[]); hist.append(result.get("master_bias","NEUTRAL"))
        if len(hist)>20: hist=hist[-20:]
        m["bias_history"]=hist
        m["bias_cycles"]=m.get("bias_cycles",0)+1 if len(hist)>=3 and len(set(hist[-3:]))==1 else 0
        m["last_updated"]=datetime.utcnow().isoformat()
        self._save()
    def get(self,pair): return self.mem.get(pair,{})
    def record_trade(self,pair,direction,price):
        if pair not in self.mem: self.mem[pair]={}
        self.mem[pair].update({"last_signal":direction,"last_trade_time":datetime.utcnow().isoformat(),"last_entry":price})
        self._save()
    def recently_traded(self,pair,hours=4):
        lt=self.get(pair).get("last_trade_time")
        if not lt: return False
        try:
            diff=(datetime.utcnow()-datetime.fromisoformat(lt)).total_seconds()/3600
            return diff<hours
        except: return False

# ─── MASTER ICT CHAIN ENGINE ─────────────────────────────────────
class ICTChainEngine:
    def __init__(self):
        self.fractal=FractalAlignmentEngine()
        self.bias_e =BiasEngine()
        self.struct =MarketStructureEngine()
        self.liq_e  =LiquidityPOIEngine()
        self.memory =ICTTradeMemory()

    def analyze_with_candles(self, pair, d1, h4, h1, m15):
        if len(_c(m15))<30: return self._empty(pair,"Insufficient M15")
        frac=self.fractal.analyze(d1,h4,h1,m15)
        mb=frac["master_bias"]
        if mb=="NEUTRAL":
            r=self._empty(pair,"No fractal bias"); self.memory.update(pair,r); return r
        bias=self.bias_e.analyze(mb,h4,h1)
        struct=self.struct.analyze(mb,h1,m15)
        liq=self.liq_e.analyze(mb,m15,h1)
        ctx=self.memory.get(pair)
        bc=ctx.get("bias_cycles",0)
        rt=self.memory.recently_traded(pair,4)
        p1=frac["fractal_score"]>=0.50 and mb!="NEUTRAL"
        p2=bias["bias_score"]>=0.50
        p3=struct["structure_score"]>=0.30
        p4=liq["liq_score"]>=0.50
        all_ok=p1 and p2 and p3 and p4
        bonus=0.0
        if bc>=3: bonus+=0.08
        if struct["choch"]: bonus+=0.05
        if struct["bos"]: bonus+=0.05
        if liq["order_block"]: bonus+=0.07
        if liq["fvg_found"]: bonus+=0.05
        if liq["in_killzone"]: bonus+=0.08
        if liq["ote_zone"]: bonus+=0.07
        if frac["aligned"]: bonus+=0.05
        base=(frac["fractal_score"]*0.25 + bias["bias_score"]*0.30 +
              struct["structure_score"]*0.25 + liq["liq_score"]*0.20)
        conf=min(1.0,base+bonus)
        trade=all_ok and conf>=0.65 and not rt
        # entry
        et="NONE"; el=0.0
        if trade:
            if liq["ote_zone"] and liq["ote_level"]: et="OTE"; el=liq["ote_level"]
            elif liq["order_block"] and liq["ob_low"]:
                et="OB"; el=liq["ob_low"] if mb=="BULLISH" else liq["ob_high"]
            elif liq["fvg_found"] and liq["fvg_low"]:
                et="FVG"; el=liq["fvg_low"] if mb=="BULLISH" else liq["fvg_high"]
        sl=0.0
        if struct["itl"] and mb=="BULLISH": sl=struct["itl"]*0.9995
        elif struct["ith"] and mb=="BEARISH": sl=struct["ith"]*1.0005
        parts=[]
        if frac["aligned"]: parts.append("AllTF-aligned")
        if bias["liquidity_sweep"]: parts.append(f"Swept({bias['pd_zone']})")
        if struct["choch"]: parts.append("CHoCH")
        if struct["bos"]: parts.append("BOS")
        if liq["order_block"]: parts.append(f"OB@{liq['ob_low']:.5f}")
        if liq["fvg_found"]: parts.append(f"FVG@{liq['fvg_low']:.5f}")
        if liq["in_killzone"]: parts.append(f"KZ:{liq['killzone']}")
        result={"pair":pair,"trade_signal":trade,
                "signal":"BUY" if mb=="BULLISH" else "SELL" if trade else "HOLD",
                "direction":"BUY" if mb=="BULLISH" else "SELL",
                "ict_confidence":round(conf,3),"entry_type":et,
                "entry_level":round(el,5),"sl_level":round(sl,5),
                "master_bias":mb,"fractal":frac,"bias":bias,
                "structure":struct,"liquidity":liq,
                "p1_fractal_ok":p1,"p2_bias_ok":p2,
                "p3_structure_ok":p3,"p4_liquidity_ok":p4,
                "all_pillars":all_ok,"bias_cycles":bc,
                "killzone":liq["killzone"],"choch":struct["choch"],
                "bos":struct["bos"],"order_block":liq["order_block"],
                "fvg":liq["fvg_found"],"ote":liq["ote_zone"],
                "pd_zone":bias["pd_zone"],"displacement":liq["displacement"],
                "reason":" | ".join(parts) if parts else f"Bias:{mb}",
                "all_pillars_aligned":all_ok}
        self.memory.update(pair,result)
        if trade: self.memory.record_trade(pair,result["direction"],el)
        return result

    def analyze(self, pair):
        d1=fetch_candles(pair,"D",60); h4=fetch_candles(pair,"H4",80)
        h1=fetch_candles(pair,"H1",100); m15=fetch_candles(pair,"M15",80)
        return self.analyze_with_candles(pair,d1,h4,h1,m15)

    def _empty(self,pair,reason):
        return {"pair":pair,"trade_signal":False,"signal":"HOLD","direction":"HOLD",
                "ict_confidence":0.0,"master_bias":"NEUTRAL","reason":reason,
                "all_pillars":False,"all_pillars_aligned":False,
                "p1_fractal_ok":False,"p2_bias_ok":False,
                "p3_structure_ok":False,"p4_liquidity_ok":False,
                "killzone":None,"choch":False,"bos":False,"order_block":False,
                "fvg":False,"ote":False,"bias_cycles":0,"displacement":False,
                "entry_type":"NONE","entry_level":0.0,"sl_level":0.0,
                "fractal":{},"bias":{},"structure":{},"liquidity":{}}

# ─── STANDALONE TEST ─────────────────────────────────────────────
if __name__=="__main__":
    import sys
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
    pairs=["EUR_USD","GBP_USD","XAU_USD","USD_JPY"]
    if len(sys.argv)>1: pairs=[sys.argv[1]]
    engine=ICTChainEngine()
    for pair in pairs:
        print(f"\n{'─'*55}\n  {pair}")
        r=engine.analyze(pair)
        print(f"  Bias:      {r['master_bias']} | Fractal aligned: {r.get('fractal',{}).get('aligned',False)}")
        print(f"  P1 Fractal:   {'✅' if r['p1_fractal_ok'] else '❌'} score={r.get('fractal',{}).get('fractal_score',0):.2f}")
        print(f"  P2 Bias:      {'✅' if r['p2_bias_ok'] else '❌'} sweep={r.get('bias',{}).get('liquidity_sweep',False)} pd={r.get('pd_zone','?')}")
        print(f"  P3 Structure: {'✅' if r['p3_structure_ok'] else '❌'} CHoCH={r['choch']} BOS={r['bos']}")
        print(f"  P4 Liquidity: {'✅' if r['p4_liquidity_ok'] else '❌'} OB={r['order_block']} FVG={r['fvg']} KZ={r['killzone']}")
        print(f"  ALL PILLARS:  {'✅ TRADE SIGNAL' if r['all_pillars'] else '❌ NO TRADE'}")
        print(f"  Confidence:   {r['ict_confidence']:.1%}")
        print(f"  Reason:       {r['reason']}")
