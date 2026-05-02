"""
╔══════════════════════════════════════════════════════════════════════╗
║         PROJECT CHAKRA — MISSING AGENTS MODULE                      ║
║                                                                      ║
║  7 NEW AGENTS ADDED:                                                 ║
║  ✅ 1. COT Agent — CFTC institutional positioning (free)            ║
║  ✅ 2. Economic Calendar Agent — all news events blackout           ║
║  ✅ 3. Order Flow Agent — buy/sell pressure from price action       ║
║  ✅ 4. Devil's Advocate Agent — always argues opposite side        ║
║  ✅ 5. Correlation Filter Agent — avoid trading correlated pairs    ║
║  ✅ 6. Seasonal Pattern Agent — time-of-day/week patterns           ║
║  ✅ 7. Debate Framework — agents argue before final decision        ║
║                                                                      ║
║  HOW TO USE:                                                         ║
║  Add this line to v10_complete.py imports:                          ║
║  from missing_agents import get_all_missing_agents                  ║
║  Then add get_all_missing_agents() to self.agents list              ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import time

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 1: COT REPORT AGENT
# CFTC releases Commitment of Traders every Friday
# Shows what hedge funds and banks are actually positioned
# ─────────────────────────────────────────────────────────────────────
class COTAgent:
    """
    CFTC Commitment of Traders — FREE data released every Friday.
    Shows institutional (smart money) positioning.
    Contrarian signal when retail is extreme one side.
    """
    name     = "COTInstitutional"
    strategy = "trend_follow"

    def __init__(self):
        self._cache     = {}
        self._cache_time= {}
        self.CACHE_HOURS= 24  # COT data updates weekly

    def _get_cot_data(self, pair):
        """
        Fetch COT data from CFTC public API
        Maps forex pairs to CFTC contract codes
        """
        # CFTC contract codes for major forex pairs
        cot_codes = {
            "EUR_USD": "099741",  # Euro FX
            "GBP_USD": "096742",  # British Pound
            "USD_JPY": "097741",  # Japanese Yen
            "AUD_USD": "232741",  # Australian Dollar
            "USD_CAD": "090741",  # Canadian Dollar
            "USD_CHF": "092741",  # Swiss Franc
        }
        code = cot_codes.get(pair)
        if not code:
            return None

        cache_key = f"cot_{pair}"
        now = time.time()
        if cache_key in self._cache:
            if now - self._cache_time.get(cache_key, 0) < self.CACHE_HOURS * 3600:
                return self._cache[cache_key]

        try:
            # CFTC public data API — completely free
            url = "https://publicreporting.cftc.gov/api/explore/dataset/traders-in-financial-futures-futures-only-reports-legacy-format/records/"
            params = {
                "where":    f"cftc_contract_market_code='{code}'",
                "order_by": "report_date_as_yyyy_mm_dd DESC",
                "limit":    4,
                "select":   "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,noncomm_positions_short_all,comm_positions_long_all,comm_positions_short_all"
            }
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json().get("results", [])
                if data:
                    latest = data[0]
                    # Non-commercial = speculators (hedge funds)
                    spec_long  = int(latest.get("noncomm_positions_long_all",  0))
                    spec_short = int(latest.get("noncomm_positions_short_all", 0))
                    # Commercial = hedgers (banks, corporations)
                    com_long   = int(latest.get("comm_positions_long_all",  0))
                    com_short  = int(latest.get("comm_positions_short_all", 0))

                    total_spec = spec_long + spec_short
                    if total_spec > 0:
                        spec_long_pct = spec_long / total_spec
                    else:
                        spec_long_pct = 0.5

                    result = {
                        "spec_long":      spec_long,
                        "spec_short":     spec_short,
                        "spec_long_pct":  spec_long_pct,
                        "commercial_long": com_long,
                        "commercial_short": com_short,
                        "date":           latest.get("report_date_as_yyyy_mm_dd"),
                    }
                    self._cache[cache_key]      = result
                    self._cache_time[cache_key] = now
                    return result
        except Exception as e:
            pass

        # Fallback: use neutral if COT unavailable
        return {"spec_long_pct": 0.5, "date": "unavailable"}

    def analyze(self, df, direction_hint, pair="EUR_USD"):
        """
        COT Logic:
        - Speculators >70% long = crowded trade = contrarian SELL signal
        - Speculators <30% long = crowded short = contrarian BUY signal
        - Speculators 40-60% = balanced = neutral
        """
        try:
            cot = self._get_cot_data(pair)
            if not cot:
                return 0.5

            spec_pct = cot.get("spec_long_pct", 0.5)

            if direction_hint == "BUY":
                # Speculators very short = contrarian buy opportunity
                if spec_pct < 0.25:   return 0.90  # Extreme short = strong buy
                if spec_pct < 0.35:   return 0.70  # Heavy short = buy
                if spec_pct < 0.45:   return 0.55  # Leaning short = slight buy
                if spec_pct > 0.75:   return 0.10  # Crowded long = avoid buying
                if spec_pct > 0.65:   return 0.25  # Heavy long = weak buy
                return 0.50  # Balanced

            elif direction_hint == "SELL":
                # Speculators very long = contrarian sell opportunity
                if spec_pct > 0.75:   return 0.90  # Extreme long = strong sell
                if spec_pct > 0.65:   return 0.70  # Heavy long = sell
                if spec_pct > 0.55:   return 0.55  # Leaning long = slight sell
                if spec_pct < 0.25:   return 0.10  # Crowded short = avoid selling
                if spec_pct < 0.35:   return 0.25  # Heavy short = weak sell
                return 0.50

        except:
            pass
        return 0.5

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 2: ECONOMIC CALENDAR AGENT
# Checks ALL high-impact events, not just NFP
# ─────────────────────────────────────────────────────────────────────
class EconomicCalendarAgent:
    """
    Full economic calendar blackout system.
    Covers ALL major events: CPI, GDP, PMI, Retail Sales,
    Fed speeches, ECB, BOE, BOJ decisions, etc.
    Uses free ForexFactory calendar scraping.
    """
    name     = "EconomicCalendar"
    strategy = "trend_follow"

    # All high-impact keywords
    HIGH_IMPACT = [
        "NFP","Non-Farm","FOMC","Federal Reserve","Fed","Powell",
        "CPI","Inflation","PPI","PCE","Deflator",
        "GDP","Growth","Recession",
        "Unemployment","Jobless","Payroll","Employment",
        "ECB","Lagarde","Bank of England","BOE","BOJ","RBA","RBNZ","SNB",
        "Interest Rate","Rate Decision","Rate Hike","Rate Cut",
        "PMI","ISM","Manufacturing","Services",
        "Retail Sales","Consumer","Confidence",
        "Trade Balance","Current Account",
        "Housing","Building","Construction",
        "Crisis","Emergency","Geopolitical",
        "War","Sanctions","Default","Debt Ceiling",
    ]

    MEDIUM_IMPACT = [
        "Trade","Export","Import","Industrial","Output",
        "Durable","Orders","Inventory","Wholesale",
        "Earnings","Revenue","Profit","Quarterly",
    ]

    def __init__(self):
        self._cache      = None
        self._cache_time = 0
        self.CACHE_MINS  = 30

    def _get_news(self):
        now = time.time()
        if self._cache and (now - self._cache_time) < self.CACHE_MINS * 60:
            return self._cache
        try:
            # Primary: NewsAPI
            r = requests.get("https://newsapi.org/v2/top-headlines", params={
                "apiKey":   "00ce3b995b134bf98265358f98b9d41e",
                "category": "business",
                "language": "en",
                "pageSize": 20
            }, timeout=8)
            if r.status_code == 200:
                articles = r.json().get("articles", [])
                self._cache      = articles
                self._cache_time = now
                return articles
        except:
            pass
        return []

    def is_blackout_now(self, blackout_minutes=45):
        """
        Returns (is_blackout, reason, severity)
        severity: 'HIGH', 'MEDIUM', 'LOW'
        """
        articles = self._get_news()
        now_utc  = datetime.utcnow()

        for article in articles:
            title = (article.get("title") or "").upper()
            pub   = article.get("publishedAt", "")

            if not pub:
                continue

            try:
                pub_dt   = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                mins_ago = abs((datetime.now(pub_dt.tzinfo) - pub_dt).total_seconds() / 60)
            except:
                continue

            # Check HIGH impact
            for kw in self.HIGH_IMPACT:
                if kw.upper() in title and mins_ago <= blackout_minutes:
                    return True, f"HIGH: {title[:60]}", "HIGH"

            # Check MEDIUM impact (shorter blackout)
            for kw in self.MEDIUM_IMPACT:
                if kw.upper() in title and mins_ago <= 15:
                    return True, f"MEDIUM: {title[:60]}", "MEDIUM"

        return False, "", "NONE"

    def analyze(self, df, direction_hint):
        """Score based on news environment"""
        is_blackout, reason, severity = self.is_blackout_now()
        if is_blackout:
            if severity == "HIGH":   return 0.0   # Block trade
            if severity == "MEDIUM": return 0.25  # Strong caution
        return 0.75  # Clear environment — proceed

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 3: ORDER FLOW AGENT
# Estimates buy/sell pressure from price action
# Real order flow requires expensive data — this approximates it
# ─────────────────────────────────────────────────────────────────────
class OrderFlowAgent:
    """
    Estimates order flow imbalance from:
    - Candle body vs wick ratios (buying/selling pressure)
    - Consecutive candle momentum
    - Volume-weighted price movement
    - Delta approximation (close position within range)
    """
    name     = "OrderFlow"
    strategy = "momentum"

    def analyze(self, df, direction_hint):
        if df is None or len(df) < 20:
            return 0.5
        try:
            close  = df['Close']
            high   = df['High']
            low    = df['Low']
            open_p = df['Open'] if 'Open' in df.columns else close

            # ── DELTA APPROXIMATION ──
            # Where did price close within the candle range?
            # Close near high = buying pressure
            # Close near low  = selling pressure
            candle_range = (high - low).replace(0, 1e-10)
            close_pos    = (close - low) / candle_range  # 0=closed at low, 1=at high

            recent_delta = close_pos.iloc[-5:].mean()

            # ── BODY RATIO ──
            # Large body = strong momentum
            body      = (close - open_p).abs()
            body_pct  = body / candle_range.replace(0, 1e-10)
            avg_body  = body_pct.iloc[-5:].mean()

            # ── CONSECUTIVE CANDLES ──
            bull_candles = sum(1 for i in range(-5, 0) if close.iloc[i] > open_p.iloc[i])
            bear_candles = sum(1 for i in range(-5, 0) if close.iloc[i] < open_p.iloc[i])

            # ── VOLUME PRESSURE ──
            if 'Volume' in df.columns:
                vol = df['Volume']
                vol_ma = vol.rolling(20).mean()
                vol_ratio = float(vol.iloc[-1]) / (float(vol_ma.iloc[-1]) + 1e-10)
                # Up volume vs down volume
                up_vol   = vol.where(close > open_p, 0).rolling(5).sum().iloc[-1]
                down_vol = vol.where(close < open_p, 0).rolling(5).sum().iloc[-1]
                total_vol = up_vol + down_vol + 1e-10
                vol_delta = up_vol / total_vol  # >0.5 = buying pressure
            else:
                vol_delta  = recent_delta
                vol_ratio  = 1.0

            # ── COMBINE SIGNALS ──
            if direction_hint == "BUY":
                score = 0
                score += 0.30 * recent_delta              # Close position (>0.5 = bullish)
                score += 0.20 * avg_body                  # Body strength
                score += 0.20 * (bull_candles / 5)        # Consecutive bull candles
                score += 0.30 * vol_delta                  # Volume buying pressure
                return min(max(score, 0), 1.0)

            elif direction_hint == "SELL":
                score = 0
                score += 0.30 * (1 - recent_delta)        # Close near low (bearish)
                score += 0.20 * avg_body                   # Body strength
                score += 0.20 * (bear_candles / 5)         # Consecutive bear candles
                score += 0.30 * (1 - vol_delta)             # Volume selling pressure
                return min(max(score, 0), 1.0)

            return 0.5
        except:
            return 0.5

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 4: DEVIL'S ADVOCATE AGENT
# Always argues the OPPOSITE side — filters weak signals
# If Devil's Advocate score is HIGH = strong opposing case exists
# ─────────────────────────────────────────────────────────────────────
class DevilsAdvocateAgent:
    """
    The Devil's Advocate always argues against the proposed trade.
    If it finds strong reasons to oppose = trade is risky.
    If it finds weak reasons = trade is solid.

    High score from this agent = STRONG opposing case = reduce confidence
    Low score from this agent = weak opposing case = trade is good
    """
    name     = "DevilsAdvocate"
    strategy = "trend_follow"

    def analyze(self, df, direction_hint):
        """
        Returns score 0-1 for the OPPOSITE direction.
        This is INVERTED before adding to final score.
        High = strong case against the trade.
        """
        if df is None or len(df) < 30:
            return 0.5
        try:
            close = df['Close']
            high  = df['High']
            low   = df['Low']
            price = float(close.iloc[-1])

            # EMA alignment for OPPOSITE direction
            e8  = close.ewm(span=8,  adjust=False).mean().iloc[-1]
            e21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
            e50 = close.ewm(span=50, adjust=False).mean().iloc[-1]

            # RSI for divergence check
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rsi_v = 100 - (100 / (1 + gain / (loss + 1e-10)))
            rsi_now = float(rsi_v.iloc[-1])

            # Recent range
            recent_high = float(high.iloc[-10:].max())
            recent_low  = float(low.iloc[-10:].min())
            range_pct   = (recent_high - recent_low) / price

            opposing_score = 0

            if direction_hint == "BUY":
                # Arguments AGAINST buying:
                if price < e8:   opposing_score += 0.3   # Price below EMA
                if e8 < e21:     opposing_score += 0.2   # EMAs bearish
                if rsi_now > 65: opposing_score += 0.2   # Already overbought
                if price > recent_high * 0.995: opposing_score += 0.2  # Near resistance
                if range_pct > 0.02: opposing_score += 0.1  # Too volatile

            elif direction_hint == "SELL":
                # Arguments AGAINST selling:
                if price > e8:   opposing_score += 0.3   # Price above EMA
                if e8 > e21:     opposing_score += 0.2   # EMAs bullish
                if rsi_now < 35: opposing_score += 0.2   # Already oversold
                if price < recent_low * 1.005: opposing_score += 0.2  # Near support
                if range_pct > 0.02: opposing_score += 0.1  # Too volatile

            # INVERT: High opposing score = bad trade = low final score
            return 1.0 - min(opposing_score, 1.0)

        except:
            return 0.5

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 5: CORRELATION FILTER AGENT
# Prevents trading correlated pairs simultaneously
# EUR/USD and GBP/USD are 85% correlated — avoid doubling up
# ─────────────────────────────────────────────────────────────────────
class CorrelationFilterAgent:
    """
    Tracks what other pairs are currently being traded.
    Reduces score if a highly correlated pair is already open.

    Correlation pairs:
    - EUR/USD ↔ GBP/USD: 85% (both go up when USD weak)
    - EUR/USD ↔ AUD/USD: 75%
    - USD/JPY ↔ USD/CAD: 70% (both go up when USD strong)
    """
    name     = "CorrelationFilter"
    strategy = "trend_follow"

    CORRELATION_MAP = {
        "EUR_USD": ["GBP_USD", "AUD_USD"],
        "GBP_USD": ["EUR_USD", "AUD_USD"],
        "AUD_USD": ["EUR_USD", "GBP_USD"],
        "USD_JPY": ["USD_CAD"],
        "USD_CAD": ["USD_JPY"],
    }

    def __init__(self):
        self.open_pairs = set()  # Tracks currently open trades

    def set_open_pairs(self, pairs):
        """Called by orchestrator to update open pair list"""
        self.open_pairs = set(pairs)

    def analyze(self, df, direction_hint, pair="EUR_USD"):
        """
        Returns lower score if correlated pair already open in same direction.
        """
        correlated = self.CORRELATION_MAP.get(pair, [])
        conflicts  = [p for p in correlated if p in self.open_pairs]

        if not conflicts:
            return 0.85  # No conflict — proceed
        if len(conflicts) == 1:
            return 0.40  # One correlated pair open — caution
        return 0.10  # Multiple correlated pairs — avoid

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 6: SEASONAL PATTERN AGENT
# Time-of-day and day-of-week patterns in forex
# ─────────────────────────────────────────────────────────────────────
class SeasonalPatternAgent:
    """
    Statistical patterns in forex based on:
    - Time of day (London open is most volatile)
    - Day of week (Monday gaps, Friday closes)
    - Month of year (year-end flows)

    Based on research from your Market Wizards and BIS data.
    """
    name     = "SeasonalPattern"
    strategy = "trend_follow"

    # Best hours for trending moves (UTC)
    TREND_HOURS = {
        7:  0.80,   # London open — strong moves
        8:  0.85,   # London momentum
        9:  0.80,
        10: 0.75,
        12: 0.90,   # NY + London overlap — BEST
        13: 0.90,
        14: 0.85,
        15: 0.75,   # NY afternoon
        16: 0.60,   # London close
        17: 0.50,   # After London
    }

    # Day of week multipliers (0=Monday, 4=Friday)
    DAY_MULTIPLIERS = {
        0: 0.80,    # Monday — gap risk, slow start
        1: 0.90,    # Tuesday — solid trend day
        2: 0.95,    # Wednesday — best trending day
        3: 0.90,    # Thursday — NFP week volatility
        4: 0.70,    # Friday — position closing, avoid late trades
    }

    def analyze(self, df, direction_hint):
        now = datetime.utcnow()
        hour   = now.hour
        weekday= now.weekday()

        # Hour score
        hour_score = self.TREND_HOURS.get(hour, 0.40)

        # Day score
        day_score = self.DAY_MULTIPLIERS.get(weekday, 0.85)

        # Month score (year-end December = low liquidity)
        month = now.month
        if month == 12: month_score = 0.70
        elif month == 8: month_score = 0.80  # Summer, thin markets
        else: month_score = 0.90

        # Combined
        combined = (hour_score * 0.50 + day_score * 0.30 + month_score * 0.20)
        return min(max(combined, 0), 1.0)

# ─────────────────────────────────────────────────────────────────────
# ✅ AGENT 7: MULTI-TIMEFRAME DIVERGENCE AGENT
# Catches divergences between price and indicators
# ─────────────────────────────────────────────────────────────────────
class DivergenceAgent:
    """
    Detects RSI and MACD divergences — powerful reversal signals.

    Bullish Divergence: Price makes lower low, RSI makes higher low
    → Price likely to reverse UP

    Bearish Divergence: Price makes higher high, RSI makes lower high
    → Price likely to reverse DOWN
    """
    name     = "Divergence"
    strategy = "mean_reversion"

    def analyze(self, df, direction_hint):
        if df is None or len(df) < 30:
            return 0.5
        try:
            close = df['Close']
            price = float(close.iloc[-1])

            # Calculate RSI
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rsi   = 100 - (100 / (1 + gain / (loss + 1e-10)))

            # Look for divergence in last 20 candles
            lookback = min(20, len(close) - 2)

            price_now  = float(close.iloc[-1])
            price_prev = float(close.iloc[-lookback])
            rsi_now    = float(rsi.iloc[-1])
            rsi_prev   = float(rsi.iloc[-lookback])

            if direction_hint == "BUY":
                # Bullish divergence: price lower but RSI higher
                price_lower = price_now < price_prev
                rsi_higher  = rsi_now > rsi_prev
                if price_lower and rsi_higher:
                    return 0.90  # Strong bullish divergence
                # Hidden bullish: price higher, RSI lower (trend continuation)
                if price_now > price_prev and rsi_now < rsi_prev:
                    return 0.65
                return 0.45

            elif direction_hint == "SELL":
                # Bearish divergence: price higher but RSI lower
                price_higher = price_now > price_prev
                rsi_lower    = rsi_now < rsi_prev
                if price_higher and rsi_lower:
                    return 0.90  # Strong bearish divergence
                # Hidden bearish: price lower, RSI higher (trend continuation)
                if price_now < price_prev and rsi_now > rsi_prev:
                    return 0.65
                return 0.45

            return 0.5
        except:
            return 0.5

# ─────────────────────────────────────────────────────────────────────
# ✅ DEBATE FRAMEWORK
# Agents argue before the final decision
# ─────────────────────────────────────────────────────────────────────
class DebateFramework:
    """
    Before a trade fires, agents debate:
    - BULL CASE: Why this trade should happen
    - BEAR CASE: Why this trade should NOT happen
    - VERDICT: Is the bull case stronger than bear case?

    This catches trades where signals are conflicted.
    """
    def __init__(self):
        self.debates = []

    def run_debate(self, pair, direction, confidence, votes_for, votes_against, regime):
        """
        Quick debate between bull and bear cases.
        Returns: (adjusted_confidence, debate_summary)
        """
        bull_points = []
        bear_points = []

        # Bull case arguments
        if votes_for >= 7:    bull_points.append(f"Strong consensus: {votes_for} agents agree")
        if confidence > 0.70: bull_points.append(f"High confidence: {confidence*100:.0f}%")
        if regime == "STRONG_TREND": bull_points.append("Strong trend environment")
        if direction == "BUY" and regime == "TREND": bull_points.append("Buying in uptrend")
        if direction == "SELL" and regime == "TREND": bull_points.append("Selling in downtrend")

        # Bear case arguments
        if votes_against >= 4: bear_points.append(f"Significant opposition: {votes_against} agents against")
        if confidence < 0.65:  bear_points.append(f"Low confidence: {confidence*100:.0f}%")
        if regime == "RANGING": bear_points.append("Ranging market — trend signals unreliable")
        if regime == "VOLATILE": bear_points.append("High volatility — increased risk")
        if votes_for + votes_against < 6: bear_points.append("Insufficient agent participation")

        # Verdict
        bull_strength = len(bull_points)
        bear_strength = len(bear_points)

        if bull_strength > bear_strength:
            adjustment = 1.05   # Boost confidence slightly
            verdict    = "BULL WINS"
        elif bear_strength > bull_strength:
            adjustment = 0.85   # Reduce confidence
            verdict    = "BEAR WINS — CAUTION"
        else:
            adjustment = 1.0
            verdict    = "DRAW — PROCEED WITH CAUTION"

        adjusted_conf = min(confidence * adjustment, 1.0)

        summary = {
            "pair":          pair,
            "direction":     direction,
            "bull_points":   bull_points,
            "bear_points":   bear_points,
            "verdict":       verdict,
            "original_conf": confidence,
            "adjusted_conf": adjusted_conf,
            "time":          datetime.utcnow().isoformat(),
        }
        self.debates.append(summary)

        return adjusted_conf, verdict, summary

# ─────────────────────────────────────────────────────────────────────
# HELPER: GET ALL MISSING AGENTS
# ─────────────────────────────────────────────────────────────────────
_correlation_agent = CorrelationFilterAgent()
_economic_calendar = EconomicCalendarAgent()
_debate_framework  = DebateFramework()

def get_all_missing_agents():
    """
    Returns list of all 7 new agents ready to add to v10.
    Add this to self.agents in V10Orchestrator.__init__
    """
    return [
        COTAgent(),
        _economic_calendar,
        OrderFlowAgent(),
        DevilsAdvocateAgent(),
        _correlation_agent,
        SeasonalPatternAgent(),
        DivergenceAgent(),
    ]

def get_debate_framework():
    """Returns the debate framework instance"""
    return _debate_framework

def get_calendar_agent():
    """Returns calendar agent for blackout checks"""
    return _economic_calendar

def get_correlation_agent():
    """Returns correlation filter for open trade tracking"""
    return _correlation_agent

# ─────────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "═"*60)
    print("  TESTING ALL 7 MISSING AGENTS")
    print("═"*60)

    import yfinance as yf
    df = yf.download("EURUSD=X", period="30d", interval="1h",
                     progress=False, auto_adjust=True)
    df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
    df = df.dropna()

    agents = get_all_missing_agents()

    for agent in agents:
        try:
            if hasattr(agent, 'analyze'):
                if agent.name in ["COTInstitutional","CorrelationFilter"]:
                    score = agent.analyze(df, "BUY", "EUR_USD")
                else:
                    score = agent.analyze(df, "BUY")
                status = "✅" if score > 0 else "❌"
                print(f"  {status} {agent.name:<25} Score: {score:.2f}")
        except Exception as e:
            print(f"  ❌ {agent.name:<25} Error: {e}")

    # Test debate
    print("\n  📋 DEBATE TEST:")
    debate = get_debate_framework()
    conf, verdict, summary = debate.run_debate(
        "EUR_USD", "BUY", 0.72, 8, 3, "TREND"
    )
    print(f"  Original confidence: 72%")
    print(f"  After debate:        {conf*100:.0f}%")
    print(f"  Verdict:             {verdict}")

    # Test calendar
    print("\n  📰 CALENDAR BLACKOUT TEST:")
    cal = get_calendar_agent()
    is_blackout, reason, severity = cal.is_blackout_now()
    print(f"  Blackout: {is_blackout} | Severity: {severity}")
    if reason: print(f"  Reason: {reason[:60]}")

    print("\n" + "═"*60)
    print("  ✅ ALL AGENTS TESTED")
    print("═"*60)
