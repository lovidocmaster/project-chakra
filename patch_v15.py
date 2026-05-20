"""
PATCH SCRIPT - Adds Regime Router + Daily Evolution to v15_chakra.py
Run: py -3.11 patch_v15.py
"""

REGIME_ROUTER_CODE = '''
# ============================================================================
# REGIME ROUTER - All-Weather Trading System
# ============================================================================

class RegimeRouter:
    """Routes strategy based on market regime - works in ALL conditions"""

    def __init__(self, mem):
        self.mem = mem
        self.regime_stats = {
            "RANGING":  {"trades": 0, "wins": 0},
            "TRENDING": {"trades": 0, "wins": 0},
            "VOLATILE": {"trades": 0, "wins": 0},
        }
        self.last_evolution = datetime.now() - timedelta(days=2)

    def get_strategy(self, regime, bars, pair):
        if len(bars) < 20:
            return self._default_strategy(bars)
        closes = [b.close for b in bars]
        highs  = [b.high  for b in bars]
        lows   = [b.low   for b in bars]
        price  = closes[-1]
        if regime == "RANGING":
            return self._mean_reversion(closes, highs, lows, price)
        elif regime == "TRENDING":
            return self._trend_following(closes, highs, lows, price)
        elif regime == "VOLATILE":
            return self._volatile_mode(closes, highs, lows, price)
        else:
            return self._default_strategy(bars)

    def _mean_reversion(self, closes, highs, lows, price):
        # Bollinger Bands
        period = 20
        sma = sum(closes[-period:]) / period
        std = (sum((c - sma)**2 for c in closes[-period:]) / period) ** 0.5
        upper = sma + 2 * std
        lower = sma - 2 * std
        # RSI
        gains  = [max(closes[i]-closes[i-1], 0) for i in range(-14,0)]
        losses = [max(closes[i-1]-closes[i], 0) for i in range(-14,0)]
        ag = sum(gains)/14; al = sum(losses)/14
        rsi = 100 - (100/(1+ag/max(al,0.0001)))
        # Support/Resistance
        support    = min(lows[-20:])
        resistance = max(highs[-20:])
        atr = sum(highs[i]-lows[i] for i in range(-14,0))/14
        # Decision
        if price <= lower and rsi < 35:
            direction = "BUY"
            sl_dist = atr * 1.0
            tp_dist = (sma - price) * 1.5
        elif price >= upper and rsi > 65:
            direction = "SELL"
            sl_dist = atr * 1.0
            tp_dist = (price - sma) * 1.5
        else:
            direction = "HOLD"
            sl_dist = atr * 1.0
            tp_dist = atr * 2.0
        return {
            "strategy": "MEAN_REVERSION",
            "direction": direction,
            "sl_dist": max(sl_dist, 0.0001),
            "tp_dist": max(tp_dist, sl_dist * 1.5),
            "confidence_boost": 0.08 if direction != "HOLD" else 0,
            "size_multiplier": 1.0,
            "reason": f"RSI:{rsi:.0f} BB:{'LOWER' if price<=lower else 'UPPER' if price>=upper else 'MID'}",
        }

    def _trend_following(self, closes, highs, lows, price):
        def ema(data, n):
            k = 2/(n+1); e = data[0]
            for d in data[1:]: e = d*k + e*(1-k)
            return e
        atr = sum(highs[i]-lows[i] for i in range(-14,0))/14
        ema12 = ema(closes[-26:] if len(closes)>=26 else closes, min(12,len(closes)))
        ema26 = ema(closes[-26:] if len(closes)>=26 else closes, min(26,len(closes)))
        macd  = ema12 - ema26
        ema50 = ema(closes[-50:] if len(closes)>=50 else closes, min(50,len(closes)))
        trend_up = price > ema50 and macd > 0
        trend_dn = price < ema50 and macd < 0
        if trend_up:
            direction = "BUY"
            sl_dist = atr * 1.2
            tp_dist = atr * 3.0
        elif trend_dn:
            direction = "SELL"
            sl_dist = atr * 1.2
            tp_dist = atr * 3.0
        else:
            direction = "HOLD"
            sl_dist = atr * 1.2
            tp_dist = atr * 2.4
        return {
            "strategy": "TREND_FOLLOWING",
            "direction": direction,
            "sl_dist": max(sl_dist, 0.0001),
            "tp_dist": max(tp_dist, 0.0001),
            "confidence_boost": 0.12 if direction != "HOLD" else 0,
            "size_multiplier": 1.2,
            "reason": f"MACD:{macd:.5f} Trend:{'UP' if trend_up else 'DOWN' if trend_dn else 'NEUTRAL'}",
        }

    def _volatile_mode(self, closes, highs, lows, price):
        atr = sum(highs[i]-lows[i] for i in range(-14,0))/14
        returns = [(closes[i]-closes[i-1])/closes[i-1] for i in range(-20,0)]
        vol = (sum(r**2 for r in returns)/20)**0.5
        # Only trade if very strong signal in volatile market
        return {
            "strategy": "VOLATILE_SURVIVAL",
            "direction": "HOLD",
            "sl_dist": max(atr * 2.0, 0.0001),
            "tp_dist": max(atr * 2.0, 0.0001),
            "confidence_boost": -0.15,
            "size_multiplier": 0.5,
            "reason": f"VOL:{vol*100:.2f}% ATR:{atr:.5f}",
        }

    def _default_strategy(self, bars):
        atr = sum(b.high-b.low for b in bars[-14:]) / min(14,len(bars)) if bars else 0.001
        return {"strategy":"DEFAULT","direction":"HOLD","sl_dist":max(atr,0.0001),
                "tp_dist":max(atr*2,0.0001),"confidence_boost":0,"size_multiplier":1.0,"reason":"DEFAULT"}

    def record_outcome(self, regime, outcome):
        if regime in self.regime_stats:
            self.regime_stats[regime]["trades"] += 1
            if outcome == "WIN":
                self.regime_stats[regime]["wins"] += 1

    def should_evolve(self):
        return (datetime.now() - self.last_evolution).days >= 1

    def evolve(self):
        if not self.should_evolve(): return
        msgs = []
        for regime, stats in self.regime_stats.items():
            if stats["trades"] > 0:
                wr = stats["wins"]/stats["trades"]*100
                msgs.append(f"{regime}:{wr:.0f}%({stats['trades']}t)")
        msg = "Regime Evolution: " + " | ".join(msgs) if msgs else "No trades yet"
        log.info(f"EVOLUTION: {msg}")
        _telegram(f"\\U0001f9ec <b>Daily Evolution</b>\\n{msg}")
        self.last_evolution = datetime.now()


class DailyEvolution:
    """Evolves system daily based on real performance"""

    def __init__(self, mem, weights):
        self.mem = mem
        self.weights = weights
        self.last_run = datetime.now() - timedelta(days=2)

    def should_run(self):
        return (datetime.now() - self.last_run).days >= 1

    def run(self):
        if not self.should_run(): return
        insights = []
        for pair, perf in self.mem.pair_perf.items():
            total = perf["wins"] + perf["losses"]
            if total >= 3:
                wr = perf["wins"]/total
                if wr < 0.4: insights.append(f"REDUCE {pair}({wr:.0%})")
                elif wr > 0.6: insights.append(f"FAVOR {pair}({wr:.0%})")
        for session, perf in self.mem.session_perf.items():
            total = perf["wins"] + perf["losses"]
            if total >= 3:
                wr = perf["wins"]/total
                if wr > 0.65: insights.append(f"BEST:{session}({wr:.0%})")
        self.weights.boost_top(3)
        self.weights.reduce_bottom(3)
        msg = f"Daily Evolution: {len(insights)} insights | " + " ".join(insights[:5])
        log.info(f"DAILY EVOLUTION: {msg}")
        _telegram(f"\\U0001f9ec <b>Daily System Evolution</b>\\n{msg[:300]}")
        self.last_run = datetime.now()

'''


def patch_v15():
    print("Reading v15_chakra.py...")
    with open('v15_chakra.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Step 1: Add RegimeRouter class before class V13Orchestrator
    target = 'class V13Orchestrator:'
    if target not in content:
        print("ERROR: Cannot find V13Orchestrator class")
        return False

    if 'class RegimeRouter:' in content:
        print("RegimeRouter already exists - skipping insertion")
    else:
        content = content.replace(target, REGIME_ROUTER_CODE + '\n' + target)
        print("✅ RegimeRouter added")

    # Step 2: Initialize RegimeRouter and DailyEvolution in __init__
    init_target = 'self.hive    = HiveMind(self.mem, self.weights)'
    init_new = '''self.hive    = HiveMind(self.mem, self.weights)
        self.router  = RegimeRouter(self.mem)
        self.evolver = DailyEvolution(self.mem, self.weights)'''

    if 'self.router' not in content:
        content = content.replace(init_target, init_new)
        print("✅ RegimeRouter initialized in __init__")
    else:
        print("Router already initialized")

    # Step 3: Remove the RANGING skip we added earlier
    old_skip = '''        # Skip RANGING/VOLATILE - only trade TRENDING markets
        if curr_regime in ["RANGING", "VOLATILE"]:
            log.info(f"{pair}: SKIP - regime={curr_regime} not TRENDING")
            return None'''
    if old_skip in content:
        content = content.replace(old_skip, '        # Regime router handles all conditions')
        print("✅ Removed RANGING-only skip")

    # Step 4: Add regime router strategy before signal execution
    signal_target = '        log.info(f"SIGNAL: {pair} {direction} {final_conf:.1%} | "'

    router_injection = '''        # Get regime-specific strategy
        route = self.router.get_strategy(curr_regime, bars, pair)
        # Override direction if router has strong opinion
        if route["direction"] != "HOLD" and route["direction"] != direction:
            if route["confidence_boost"] > 0.05:
                direction = route["direction"]
                log.info(f"{pair}: Regime router overriding to {direction} ({route['strategy']})")
        elif route["direction"] == "HOLD" and curr_regime == "VOLATILE":
            log.info(f"{pair}: VOLATILE regime - skipping per GARCH signal")
            return None
        # Apply regime-specific SL/TP
        if route["strategy"] != "DEFAULT":
            risk["sl_dist"] = route["sl_dist"] if "sl_dist" in route else risk.get("sl_dist", 0.001)
            # Recalculate units with regime size multiplier
            size_mult = route.get("size_multiplier", 1.0)
            risk["units"] = max(1000, min(int(risk.get("units", 1000) * size_mult), 15000))
        log.info(f"{pair}: Strategy={route['strategy']} Reason={route.get('reason','')}")
        '''

    if 'Regime router overriding' not in content and signal_target in content:
        content = content.replace(signal_target, router_injection + signal_target)
        print("✅ Regime router injection added before signal")
    else:
        print("Router injection already exists or signal target not found")

    # Step 5: Add daily evolution to run loop
    cycle_target = '                # Daily report at 22:00 UTC'
    evolution_inject = '''                # Daily evolution
                if self.evolver.should_run():
                    self.evolver.run()
                if self.router.should_evolve():
                    self.router.evolve()
                # Daily report at 22:00 UTC'''

    if 'self.evolver.should_run()' not in content and cycle_target in content:
        content = content.replace(cycle_target, evolution_inject)
        print("✅ Daily evolution added to run loop")
    else:
        print("Daily evolution already exists or target not found")

    # Write back
    with open('v15_chakra.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n=== PATCH COMPLETE ===")
    print("RegimeRouter: Handles RANGING/TRENDING/VOLATILE differently")
    print("DailyEvolution: Learns and evolves every day")
    print("System now works in ALL market conditions")
    return True


if __name__ == '__main__':
    patch_v15()
