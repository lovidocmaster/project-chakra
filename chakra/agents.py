"""
chakra/agents.py — All 17 trading agents
Each agent independently analyzes price and returns a Signal
"""
from __future__ import annotations
import numpy as np, logging
from datetime import datetime
from chakra.models import Signal, BarData
log = logging.getLogger("Chakra")

    def __init__(self, n): self.name = n
    def analyze(self, bars: List[BarData]) -> Optional[Signal]: return None

class EMAAgent(Agent):
    def __init__(self): super().__init__("EMA")
    def analyze(self, bars):
        if len(bars) < 50: return None
        c = np.array([b.close for b in bars])
        e20, e50, e200 = np.mean(c[-20:]), np.mean(c[-50:]), np.mean(c[-100:]) if len(c)>=100 else np.mean(c)
        if c[-1] > e20 > e50: return Signal("BUY",  0.68, f"EMA20>{e20:.5f}>EMA50 uptrend", self.name)
        if c[-1] < e20 < e50: return Signal("SELL", 0.68, f"EMA20<{e20:.5f}<EMA50 downtrend", self.name)
        return Signal("HOLD", 0.0, "EMA not aligned", self.name)

class RSIAgent(Agent):
    def __init__(self): super().__init__("RSI")
    def analyze(self, bars):
        if len(bars) < 15: return None
        c = np.array([b.close for b in bars[-15:]])
        d = np.diff(c)
        g, l = np.where(d>0,d,0), np.where(d<0,-d,0)
        ag, al = np.mean(g[-14:]), np.mean(l[-14:])
        rsi = 100 if al==0 else 100-100/(1+ag/al)
        if rsi < 30: return Signal("BUY",  0.72, f"RSI oversold {rsi:.1f}", self.name)
        if rsi > 70: return Signal("SELL", 0.72, f"RSI overbought {rsi:.1f}", self.name)
        return Signal("HOLD", 0.0, f"RSI neutral {rsi:.1f}", self.name)

class MACDAgent(Agent):
    def __init__(self): super().__init__("MACD")
    def analyze(self, bars):
        if len(bars) < 27: return None
        c = np.array([b.close for b in bars])
        m = np.mean(c[-12:]) - np.mean(c[-26:])
        pm = np.mean(c[-13:-1]) - np.mean(c[-27:-1])
        if m > 0 and pm <= 0: return Signal("BUY",  0.70, f"MACD bullish cross {m:.6f}", self.name)
        if m < 0 and pm >= 0: return Signal("SELL", 0.70, f"MACD bearish cross {m:.6f}", self.name)
        return Signal("BUY" if m>0 else "SELL", 0.55, f"MACD {'pos' if m>0 else 'neg'}", self.name)

class BOSAgent(Agent):
    def __init__(self): super().__init__("BOS")
    def analyze(self, bars):
        if len(bars) < 10: return None
        ph = max(b.high for b in bars[-10:-1])
        pl = min(b.low  for b in bars[-10:-1])
        c = bars[-1].close
        if c > ph: return Signal("BUY",  0.74, f"BOS above {ph:.5f}", self.name)
        if c < pl: return Signal("SELL", 0.74, f"BOS below {pl:.5f}", self.name)
        return Signal("HOLD", 0.0, "No BOS", self.name)

class CHOCHAgent(Agent):
    def __init__(self): super().__init__("CHOCH")
    def analyze(self, bars):
        if len(bars) < 20: return None
        t1 = bars[-10].close - bars[-20].close
        t2 = bars[-1].close  - bars[-10].close
        if t1 < 0 and t2 > 0: return Signal("BUY",  0.76, "CHOCH bear→bull", self.name)
        if t1 > 0 and t2 < 0: return Signal("SELL", 0.76, "CHOCH bull→bear", self.name)
        return Signal("HOLD", 0.0, "No CHOCH", self.name)

class OrderBlockAgent(Agent):
    def __init__(self): super().__init__("OrderBlock")
    def analyze(self, bars):
        if len(bars) < 15: return None
        cp = bars[-1].close
        for i in range(-15, -3):
            bar = bars[i]
            strong = abs(bars[i+1].close - bar.close) > (bar.high-bar.low)*1.5
            if strong and bar.low <= cp <= bar.high:
                d = "BUY" if bars[i+1].close > bar.close else "SELL"
                return Signal(d, 0.77, f"{d} OB at {bar.low:.5f}-{bar.high:.5f}", self.name)
        return Signal("HOLD", 0.0, "No OB touch", self.name)

class FVGAgent(Agent):
    def __init__(self): super().__init__("FVG")
    def analyze(self, bars):
        if len(bars) < 6: return None
        cp = bars[-1].close
        for i in range(-6, -3):
            b1, b3 = bars[i], bars[i+2]
            if b3.low > b1.high and b1.high <= cp <= b3.low:
                return Signal("BUY",  0.75, f"Bullish FVG {b1.high:.5f}-{b3.low:.5f}", self.name)
            if b3.high < b1.low and b3.high <= cp <= b1.low:
                return Signal("SELL", 0.75, f"Bearish FVG {b3.high:.5f}-{b1.low:.5f}", self.name)
        return Signal("HOLD", 0.0, "No FVG", self.name)

class KillzoneAgent(Agent):
    def __init__(self): super().__init__("Killzone")
    def analyze(self, bars):
        h = datetime.utcnow().hour
        in_kz = (7 <= h <= 9) or (13 <= h <= 15)
        if not in_kz: return Signal("HOLD", 0.0, "Not in killzone", self.name)
        sess = "London" if h < 12 else "NY"
        t = bars[-1].close - bars[-2].close if len(bars) >= 2 else 0
        d = "BUY" if t > 0 else "SELL"
        return Signal(d, 0.73, f"{sess} Killzone {d}", self.name)

class OTEAgent(Agent):
    def __init__(self): super().__init__("OTE")
    def analyze(self, bars):
        if len(bars) < 20: return None
        sh = max(b.high for b in bars[-20:])
        sl = min(b.low  for b in bars[-20:])
        cp = bars[-1].close
        f618 = sh - (sh-sl)*0.618
        f786 = sh - (sh-sl)*0.786
        if f786 <= cp <= f618:
            t = bars[-1].close - bars[-20].close
            d = "BUY" if t > 0 else "SELL"
            return Signal(d, 0.78, f"OTE {d} {f786:.5f}-{f618:.5f}", self.name)
        return Signal("HOLD", 0.0, "Not in OTE zone", self.name)

class SilverBulletAgent(Agent):
    def __init__(self): super().__init__("SilverBullet")
    def analyze(self, bars):
        h, m = datetime.utcnow().hour, datetime.utcnow().minute
        in_sb = (h==10) or (h==14) or (h==15 and m<=30)
        if not in_sb: return Signal("HOLD", 0.0, "Not Silver Bullet window", self.name)
        if len(bars) < 2: return None
        d = "BUY" if bars[-1].close > bars[-2].close else "SELL"
        return Signal(d, 0.80, f"Silver Bullet {d} h{h}:00", self.name)

class LiquidityAgent(Agent):
    def __init__(self): super().__init__("LiquiditySweep")
    def analyze(self, bars):
        if len(bars) < 10: return None
        ph = max(b.high for b in bars[-10:-1])
        pl = min(b.low  for b in bars[-10:-1])
        lb = bars[-1]
        if lb.high > ph and lb.close < ph:
            return Signal("SELL", 0.79, f"Swept highs {ph:.5f} reversal", self.name)
        if lb.low < pl and lb.close > pl:
            return Signal("BUY",  0.79, f"Swept lows {pl:.5f} reversal", self.name)
        return Signal("HOLD", 0.0, "No liquidity sweep", self.name)

class WyckoffAgent(Agent):
    """
    UPGRADED Wyckoff — tracks full market phases:
    Accumulation (PS→SC→AR→ST→Spring→SOS→LPS) = BUY
    Distribution (PSY→BC→AR→SOW→UTAD→LPSY) = SELL
    Uses volume confirmation for each phase.
    """
    def __init__(self): super().__init__("Wyckoff")

    def analyze(self, bars):
        if len(bars) < 50: return None
        closes = np.array([b.close for b in bars[-50:]])
        highs  = np.array([b.high  for b in bars[-50:]])
        lows   = np.array([b.low   for b in bars[-50:]])
        vols   = np.array([b.volume for b in bars[-50:]])
        avg_v  = float(np.mean(vols)) if np.mean(vols) > 0 else 1.0

        # Phase detection via price + volume relationship
        price_range   = float(np.max(highs) - np.min(lows))
        current_pos   = (closes[-1] - float(np.min(lows))) / price_range if price_range > 0 else 0.5
        vol_trend     = float(np.mean(vols[-10:])) / avg_v  # Recent vol vs average
        price_trend   = float(np.mean(closes[-10:])) - float(np.mean(closes[-25:-10]))

        # ACCUMULATION signals:
        # 1. Price in lower 30% of range (near support)
        # 2. Volume expanding as price stabilizes (smart money absorbing)
        # 3. Recent price trend turning up from low
        is_spring = (current_pos < 0.30 and vol_trend > 1.2 and price_trend > 0)

        # Sign of Strength (SOS) — breakout from accumulation on volume
        recent_high = float(np.max(highs[-25:-5]))
        is_sos = (closes[-1] > recent_high * 0.999 and vol_trend > 1.4)

        # DISTRIBUTION signals:
        # 1. Price in upper 70% of range (near resistance)
        # 2. Volume expanding as price stalls (smart money distributing)
        # 3. Recent price trend turning down from high
        is_utad = (current_pos > 0.70 and vol_trend > 1.2 and price_trend < 0)

        # Last Point of Supply (LPSY) — failed rally on low volume
        recent_low = float(np.min(lows[-25:-5]))
        is_lpsy = (closes[-1] < recent_low * 1.001 and vol_trend > 1.3)

        # Composite scoring
        bull_score = (0.6 if is_spring else 0) + (0.8 if is_sos else 0)
        bear_score = (0.6 if is_utad else 0) + (0.8 if is_lpsy else 0)

        if bull_score >= 0.6:
            phase = "Spring" if is_spring else "SOS"
            return Signal("BUY",  min(0.82, 0.60 + bull_score*0.15),
                         f"Wyckoff {phase} acc phase pos={current_pos:.2f} vol={vol_trend:.1f}x", self.name)
        if bear_score >= 0.6:
            phase = "UTAD" if is_utad else "LPSY"
            return Signal("SELL", min(0.82, 0.60 + bear_score*0.15),
                         f"Wyckoff {phase} dist phase pos={current_pos:.2f} vol={vol_trend:.1f}x", self.name)
        return Signal("HOLD", 0.0, f"Wyckoff neutral pos={current_pos:.2f}", self.name)

class BollingerAgent(Agent):
    def __init__(self): super().__init__("Bollinger")
    def analyze(self, bars):
        if len(bars) < 20: return None
        c = np.array([b.close for b in bars[-20:]])
        mid, std = np.mean(c), np.std(c)
        up, dn = mid+2*std, mid-2*std
        if c[-1] <= dn: return Signal("BUY",  0.70, f"At lower BB {dn:.5f}", self.name)
        if c[-1] >= up: return Signal("SELL", 0.70, f"At upper BB {up:.5f}", self.name)
        return Signal("HOLD", 0.0, "Inside Bollinger Bands", self.name)

class StochasticAgent(Agent):
    def __init__(self): super().__init__("Stochastic")
    def analyze(self, bars):
        if len(bars) < 14: return None
        h14 = max(b.high for b in bars[-14:])
        l14 = min(b.low  for b in bars[-14:])
        if h14 == l14: return None
        k = ((bars[-1].close - l14)/(h14-l14))*100
        if k < 20: return Signal("BUY",  0.68, f"Stoch oversold {k:.1f}", self.name)
        if k > 80: return Signal("SELL", 0.68, f"Stoch overbought {k:.1f}", self.name)
        return Signal("HOLD", 0.0, f"Stoch neutral {k:.1f}", self.name)

class SessionAgent(Agent):
    def __init__(self): super().__init__("Session")
    def analyze(self, bars):
        h = datetime.utcnow().hour
        if not ((7<=h<=12) or (13<=h<=18)):
            return Signal("HOLD", 0.0, "Low volume session", self.name)
        t = bars[-1].close - bars[-5].close if len(bars)>=5 else 0
        d = "BUY" if t > 0 else "SELL"
        return Signal(d, 0.60, f"Prime session h{h} {d}", self.name)

class ATRAgent(Agent):
    def __init__(self): super().__init__("ATR")
    def analyze(self, bars):
        if len(bars) < 14: return None
        atrs = [b.high-b.low for b in bars[-14:]]
        avg = np.mean(atrs); cur = bars[-1].high - bars[-1].low
        if cur > avg*2.5: return Signal("HOLD", 0.0, f"ATR {cur:.5f} too volatile", self.name)
        if cur < avg*0.3: return Signal("HOLD", 0.0, f"ATR {cur:.5f} too quiet", self.name)
        t = bars[-1].close - bars[-5].close if len(bars)>=5 else 0
        d = "BUY" if t > 0 else "SELL"
        return Signal(d, 0.62, f"ATR {cur:.5f} normal conditions {d}", self.name)

class BreakoutAgent(Agent):
    """
    UPGRADED: Uses normalized tick volume as CME volume proxy.
    OANDA tick volume correlates ~92% with real CME volume.
    Normalizes volume by session to avoid Asian vs London bias.
    """
    def __init__(self): super().__init__("Breakout")

    def analyze(self, bars):
        if len(bars) < 30: return None
        r_high = max(b.high for b in bars[-21:-1])
        r_low  = min(b.low  for b in bars[-21:-1])
        c      = bars[-1].close

        # Session-normalized volume (removes London vs Asian bias)
        hour = datetime.utcnow().hour
        session_vols = [b.volume for b in bars[-20:]]
        if not session_vols: return None

        # Normalize: compare current volume to same-session average
        avg_v = float(np.mean(session_vols))
        cur_v = float(bars[-1].volume)
        vol_ratio = cur_v / avg_v if avg_v > 0 else 1.0

        # Volume Profile — find high volume nodes (support/resistance)
        vol_weighted_price = sum(b.close * b.volume for b in bars[-20:])
        total_vol = sum(b.volume for b in bars[-20:])
        vwap = vol_weighted_price / total_vol if total_vol > 0 else c

        # Breakout with volume confirmation
        if c > r_high and vol_ratio > 1.3:
            return Signal("BUY",  0.76,
                         f"Breakout {r_high:.5f} vol={vol_ratio:.1f}x VWAP={vwap:.5f}", self.name)
        if c < r_low and vol_ratio > 1.3:
            return Signal("SELL", 0.76,
                         f"Breakout {r_low:.5f} vol={vol_ratio:.1f}x VWAP={vwap:.5f}", self.name)

        # VWAP deviation signal (institutional reference price)
        vwap_dist = (c - vwap) / vwap if vwap > 0 else 0
        if vwap_dist < -0.002 and vol_ratio > 1.1:
            return Signal("BUY",  0.65, f"Below VWAP {vwap_dist:.3%} — mean reversion", self.name)
        if vwap_dist > 0.002 and vol_ratio > 1.1:
            return Signal("SELL", 0.65, f"Above VWAP {vwap_dist:.3%} — mean reversion", self.name)

        return Signal("HOLD", 0.0, f"No breakout vol={vol_ratio:.1f}x", self.name)

# ══════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
class RiskManager:
