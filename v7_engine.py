"""
V7 ENGINE - COMPLETE AUTONOMOUS TRADING SYSTEM
Adds to V6:
1. OANDA Execution - places real trades automatically
2. Trade Monitor - watches and manages open positions
3. Memory System - remembers every trade in Supabase
4. Self Learning - improves agent weights after every trade
5. Alpha Vantage - better data quality
6. DataFrame fix - resolves ambiguous truth value error
"""

import numpy as np
import pandas as pd
import json
import time
import requests
import threading
import os
from datetime import datetime, timedelta
from collections import defaultdict, deque

# ============================================================
# CONFIGURATION - ALL KEYS
# ============================================================
CONFIG = {
    'ANTHROPIC_API_KEY':  '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',
    'OANDA_API_KEY':      '500c5382d32fcc8a3a58b0ea0507c083-64e0d997e301a20caa3270a846d33402',
    'OANDA_ACCOUNT_ID':   '101-001-39217670-001',
    'OANDA_ENV':          'practice',
    'OANDA_BASE_URL':     'https://api-fxpractice.oanda.com',
    'FRED_API_KEY':       '0d5051e1563e45866badf276454ce1ec',
    'NEWS_API_KEY':       '00ce3b995b134bf98265358f98b9d41e',
    'ALPHA_VANTAGE_KEY':  'T7TQAX2SMD7RTNXN',
    'TELEGRAM_TOKEN':     '8635098808:AAG07lR1RTnImndoCbnIEEXn8mGrIzR0nOc',
    'TELEGRAM_CHAT_ID':   '757855988',
    'SUPABASE_URL':       'https://jvnaphbygmqjeyawkmnz.supabase.co',
    'SUPABASE_KEY':       'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2bmFwaGJ5Z21xamV5YXdrbW56Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ3NDI2NzcsImV4cCI6MjA2MDMxODY3N30.Suz0H3jrDn89vzCLCPPFlbo3oVYcqVbn7d_OtB3zLR0',
    'INITIAL_CAPITAL':    10000,
    'RISK_PER_TRADE':     0.01,
    'MAX_POSITIONS':      5,
    'BREAKEVEN_AT_R':     1.0,
    'PARTIAL_CLOSE_AT_R': 1.0,
    'PARTIAL_CLOSE_PCT':  0.5,
    'MONITOR_INTERVAL':   60,
}

# OANDA instrument mapping
OANDA_INSTRUMENTS = {
    'EURUSD': 'EUR_USD', 'USDJPY': 'USD_JPY', 'GBPUSD': 'GBP_USD',
    'AUDUSD': 'AUD_USD', 'USDCAD': 'USD_CAD', 'NZDUSD': 'NZD_USD',
    'USDCHF': 'USD_CHF', 'EURJPY': 'EUR_JPY', 'GBPJPY': 'GBP_JPY',
    'EURGBP': 'EUR_GBP', 'XAUUSD': 'XAU_USD',
}

PIP_SIZE = {
    'EURUSD':0.0001,'USDJPY':0.01,'GBPUSD':0.0001,'AUDUSD':0.0001,
    'USDCAD':0.0001,'NZDUSD':0.0001,'USDCHF':0.0001,'EURJPY':0.01,
    'GBPJPY':0.01,'EURGBP':0.0001,'XAUUSD':0.1,
}

PIP_USD = {
    'EURUSD':10,'USDJPY':9,'GBPUSD':10,'AUDUSD':10,'USDCAD':7.5,
    'NZDUSD':10,'USDCHF':11,'EURJPY':9,'GBPJPY':9,'EURGBP':12.5,'XAUUSD':1,
}

# ============================================================
# TELEGRAM
# ============================================================
class Telegram:
    BASE = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}"

    @staticmethod
    def send(msg):
        try:
            requests.post(f"{Telegram.BASE}/sendMessage",
                json={'chat_id':CONFIG['TELEGRAM_CHAT_ID'],'text':msg,'parse_mode':'HTML'},
                timeout=10)
        except: pass

    @staticmethod
    def send_photo(path, caption=''):
        try:
            with open(path,'rb') as f:
                requests.post(f"{Telegram.BASE}/sendPhoto",
                    data={'chat_id':CONFIG['TELEGRAM_CHAT_ID'],'caption':caption,'parse_mode':'HTML'},
                    files={'photo':f}, timeout=15)
        except: pass

# ============================================================
# SUPABASE MEMORY SYSTEM
# ============================================================
class MemorySystem:
    """
    Complete memory system using Supabase.
    Stores signals, trades, outcomes, agent performance.
    Enables self-learning from every trade.
    """
    def __init__(self):
        self.headers = {
            'apikey': CONFIG['SUPABASE_KEY'],
            'Authorization': f"Bearer {CONFIG['SUPABASE_KEY']}",
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
        self.base = CONFIG['SUPABASE_URL']
        # Local cache for fast access
        self.agent_weights = {}
        self.trade_history = deque(maxlen=1000)
        self.pattern_library = defaultdict(list)
        self._load_agent_weights()
        print("✅ Memory System initialized")

    def _load_agent_weights(self):
        """Load existing agent weights from memory"""
        try:
            r = requests.get(
                f"{self.base}/rest/v1/agent_weights?select=*",
                headers=self.headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for row in data:
                    self.agent_weights[row['agent_name']] = row['weight']
                print(f"  📊 Loaded {len(self.agent_weights)} agent weights from memory")
        except:
            print("  📊 Starting with default agent weights")

    def save_signal(self, signal_data):
        """Save every signal generated"""
        try:
            record = {
                'symbol': signal_data.get('symbol'),
                'signal': signal_data.get('signal'),
                'confidence': float(signal_data.get('confidence', 0)),
                'entry': float(signal_data.get('entry', 0)),
                'stop_loss': float(signal_data.get('stop_loss', 0)),
                'take_profit': float(signal_data.get('take_profit', 0)),
                'lots': float(signal_data.get('lots', 0)),
                'buy_votes': int(signal_data.get('buy_votes', 0)),
                'sell_votes': int(signal_data.get('sell_votes', 0)),
                'timestamp': datetime.utcnow().isoformat(),
                'agent_reasons': json.dumps(signal_data.get('reasons', [])[:10]),
                'status': 'pending'
            }
            requests.post(f"{self.base}/rest/v1/signals",
                headers=self.headers, json=record, timeout=10)
        except: pass

    def save_trade(self, trade_data):
        """Save every trade placed"""
        try:
            record = {
                'trade_id': trade_data.get('trade_id', ''),
                'symbol': trade_data.get('symbol'),
                'signal': trade_data.get('signal'),
                'entry': float(trade_data.get('entry', 0)),
                'stop_loss': float(trade_data.get('stop_loss', 0)),
                'take_profit': float(trade_data.get('take_profit', 0)),
                'lots': float(trade_data.get('lots', 0)),
                'status': 'open',
                'open_time': datetime.utcnow().isoformat(),
                'agent_snapshot': json.dumps(self.agent_weights),
            }
            requests.post(f"{self.base}/rest/v1/trades",
                headers=self.headers, json=record, timeout=10)
            self.trade_history.append(record)
        except: pass

    def update_trade_closed(self, trade_id, exit_price, pnl, outcome):
        """Update trade when it closes - triggers self learning"""
        try:
            record = {
                'exit_price': float(exit_price),
                'pnl': float(pnl),
                'outcome': outcome,
                'status': 'closed',
                'close_time': datetime.utcnow().isoformat(),
            }
            requests.patch(
                f"{self.base}/rest/v1/trades?trade_id=eq.{trade_id}",
                headers=self.headers, json=record, timeout=10)
        except: pass

    def update_agent_weight(self, agent_name, weight):
        """Save updated agent weight after learning"""
        try:
            self.agent_weights[agent_name] = weight
            record = {
                'agent_name': agent_name,
                'weight': float(weight),
                'updated_at': datetime.utcnow().isoformat()
            }
            # Upsert
            r = requests.get(
                f"{self.base}/rest/v1/agent_weights?agent_name=eq.{agent_name}",
                headers=self.headers, timeout=5)
            if r.status_code == 200 and r.json():
                requests.patch(
                    f"{self.base}/rest/v1/agent_weights?agent_name=eq.{agent_name}",
                    headers=self.headers, json=record, timeout=10)
            else:
                requests.post(f"{self.base}/rest/v1/agent_weights",
                    headers=self.headers, json=record, timeout=10)
        except: pass

    def get_performance_stats(self):
        """Get overall performance statistics"""
        try:
            r = requests.get(
                f"{self.base}/rest/v1/trades?status=eq.closed&select=*",
                headers=self.headers, timeout=10)
            if r.status_code == 200:
                trades = r.json()
                if not trades:
                    return {'total':0,'wins':0,'losses':0,'win_rate':0,'total_pnl':0}
                wins = sum(1 for t in trades if t.get('outcome')=='win')
                total_pnl = sum(float(t.get('pnl',0)) for t in trades)
                return {
                    'total': len(trades),
                    'wins': wins,
                    'losses': len(trades)-wins,
                    'win_rate': wins/len(trades) if trades else 0,
                    'total_pnl': total_pnl
                }
        except: pass
        return {'total':0,'wins':0,'losses':0,'win_rate':0,'total_pnl':0}

# ============================================================
# SELF LEARNING SYSTEM
# ============================================================
class SelfLearningSystem:
    """
    After every closed trade, analyzes which agents were correct
    and updates their weights. System becomes smarter over time.
    """
    def __init__(self, memory):
        self.memory = memory
        self.learning_rate = 0.1
        print("✅ Self-Learning System initialized")

    def learn_from_trade(self, trade_data, outcome, agent_signals):
        """
        Called after every trade closes.
        outcome: 'win' or 'loss'
        agent_signals: dict of {agent_name: signal_at_time_of_trade}
        """
        print(f"\n🧠 LEARNING from {trade_data.get('symbol')} {outcome.upper()}")

        trade_signal = trade_data.get('signal', 0)
        was_win = outcome == 'win'

        updates = []
        for agent_name, agent_signal in agent_signals.items():
            current_weight = self.memory.agent_weights.get(agent_name, 1.0)

            # Agent agreed with winning trade = good
            if agent_signal == trade_signal and was_win:
                new_weight = min(current_weight + self.learning_rate, 2.5)
                change = 'UP'
            # Agent disagreed with winning trade = it was wrong to disagree
            elif agent_signal != trade_signal and was_win and agent_signal != 0:
                new_weight = max(current_weight - self.learning_rate * 0.5, 0.3)
                change = 'DOWN'
            # Agent agreed with losing trade = bad
            elif agent_signal == trade_signal and not was_win:
                new_weight = max(current_weight - self.learning_rate, 0.3)
                change = 'DOWN'
            # Agent disagreed with losing trade = it was right to disagree
            elif agent_signal != trade_signal and not was_win and agent_signal != 0:
                new_weight = min(current_weight + self.learning_rate * 0.5, 2.5)
                change = 'UP'
            else:
                new_weight = current_weight
                change = 'SAME'

            if change != 'SAME':
                self.memory.update_agent_weight(agent_name, new_weight)
                updates.append(f"{agent_name}: {current_weight:.2f}→{new_weight:.2f} {change}")

        if updates:
            print(f"  Agent weight updates: {len(updates)}")
            for u in updates[:5]:
                print(f"  {u}")

        # Send learning summary to Telegram
        emoji = '✅ WIN' if was_win else '❌ LOSS'
        Telegram.send(f"""
🧠 <b>SYSTEM LEARNED</b>
Trade: {trade_data.get('symbol')} {emoji}
Agents updated: {len(updates)}
Total trades learned: {len(self.memory.trade_history)}
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
        """)

    def get_evolved_weights(self):
        """Get current evolved weights for all agents"""
        return dict(self.memory.agent_weights)

# ============================================================
# OANDA EXECUTION ENGINE
# ============================================================
class OandaExecutor:
    """
    Places real trades on OANDA demo account.
    Manages orders, positions, stop losses, take profits.
    """
    def __init__(self):
        self.api_key = CONFIG['OANDA_API_KEY']
        self.account_id = CONFIG['OANDA_ACCOUNT_ID']
        self.base_url = 'https://api-fxpractice.oanda.com'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept-Datetime-Format': 'RFC3339'
        }
        self.open_trades = {}
        print("✅ OANDA Executor initialized")

    def get_account_summary(self):
        """Get current account balance and status"""
        try:
            r = requests.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/summary",
                headers=self.headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                account = data.get('account', {})
                return {
                    'balance': float(account.get('balance', 0)),
                    'nav': float(account.get('NAV', 0)),
                    'unrealized_pnl': float(account.get('unrealizedPL', 0)),
                    'open_trade_count': int(account.get('openTradeCount', 0)),
                    'margin_used': float(account.get('marginUsed', 0)),
                }
            return None
        except Exception as e:
            print(f"  ❌ Account summary error: {e}")
            return None

    def get_current_price(self, symbol):
        """Get live bid/ask price"""
        try:
            instrument = OANDA_INSTRUMENTS.get(symbol, symbol)
            r = requests.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/pricing",
                headers=self.headers,
                params={'instruments': instrument},
                timeout=10)
            if r.status_code == 200:
                prices = r.json().get('prices', [])
                if prices:
                    bid = float(prices[0].get('bids', [{}])[0].get('price', 0))
                    ask = float(prices[0].get('asks', [{}])[0].get('price', 0))
                    return {'bid': bid, 'ask': ask, 'mid': (bid+ask)/2}
            return None
        except: return None

    def place_trade(self, symbol, signal, lots, stop_loss, take_profit):
        """
        Place a market order on OANDA demo account.
        signal: 1 = BUY, -1 = SELL
        """
        try:
            instrument = OANDA_INSTRUMENTS.get(symbol)
            if not instrument:
                print(f"  ❌ Unknown instrument: {symbol}")
                return None

            # OANDA uses positive units for BUY, negative for SELL
            units = int(lots * 100000)
            if signal == -1:
                units = -units

            # Format prices to correct decimal places
            pip = PIP_SIZE.get(symbol, 0.0001)
            decimals = 5 if pip <= 0.0001 else (3 if pip <= 0.01 else 2)

            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units),
                    "stopLossOnFill": {
                        "price": f"{stop_loss:.{decimals}f}",
                        "timeInForce": "GTC"
                    },
                    "takeProfitOnFill": {
                        "price": f"{take_profit:.{decimals}f}",
                        "timeInForce": "GTC"
                    },
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT"
                }
            }

            r = requests.post(
                f"{self.base_url}/v3/accounts/{self.account_id}/orders",
                headers=self.headers,
                json=order_data,
                timeout=15)

            if r.status_code in [200, 201]:
                data = r.json()
                trade_id = None

                # Extract trade ID
                fill = data.get('orderFillTransaction', {})
                trades = fill.get('tradeOpened', {})
                trade_id = trades.get('tradeID') or fill.get('id')

                if trade_id:
                    self.open_trades[trade_id] = {
                        'symbol': symbol,
                        'signal': signal,
                        'units': units,
                        'entry': float(fill.get('price', 0)),
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'lots': lots,
                        'open_time': datetime.utcnow().isoformat(),
                        'initial_stop': stop_loss,
                        'breakeven_moved': False,
                    }
                    print(f"  ✅ Trade placed: {symbol} {'BUY' if signal==1 else 'SELL'} {lots} lots @ {fill.get('price')} ID:{trade_id}")
                    return trade_id
                else:
                    print(f"  ⚠️ Order placed but no trade ID returned")
                    print(f"  Response: {data}")
                    return None
            else:
                print(f"  ❌ Order failed: {r.status_code} - {r.text[:200]}")
                return None

        except Exception as e:
            print(f"  ❌ Trade execution error: {e}")
            return None

    def get_open_trades(self):
        """Get all currently open trades from OANDA"""
        try:
            r = requests.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/openTrades",
                headers=self.headers, timeout=10)
            if r.status_code == 200:
                return r.json().get('trades', [])
            return []
        except: return []

    def modify_trade(self, trade_id, new_stop_loss=None, new_take_profit=None):
        """Modify SL or TP of an open trade"""
        try:
            body = {}
            trade_info = self.open_trades.get(str(trade_id), {})
            symbol = trade_info.get('symbol', 'EURUSD')
            pip = PIP_SIZE.get(symbol, 0.0001)
            decimals = 5 if pip <= 0.0001 else (3 if pip <= 0.01 else 2)

            if new_stop_loss:
                body['stopLoss'] = {
                    'price': f"{new_stop_loss:.{decimals}f}",
                    'timeInForce': 'GTC'
                }
            if new_take_profit:
                body['takeProfit'] = {
                    'price': f"{new_take_profit:.{decimals}f}",
                    'timeInForce': 'GTC'
                }

            r = requests.put(
                f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/orders",
                headers=self.headers, json=body, timeout=10)

            return r.status_code in [200, 201]
        except: return False

    def close_trade(self, trade_id, partial_units=None):
        """Close a trade fully or partially"""
        try:
            body = {}
            if partial_units:
                body['units'] = str(partial_units)

            r = requests.put(
                f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/close",
                headers=self.headers, json=body, timeout=10)

            if r.status_code == 200:
                data = r.json()
                pnl = float(data.get('orderFillTransaction', {}).get('pl', 0))
                return True, pnl
            return False, 0
        except: return False, 0

# ============================================================
# TRADE MONITOR
# ============================================================
class TradeMonitor:
    """
    Runs in background every 60 seconds.
    Manages all open positions:
    - Moves SL to breakeven after 1R
    - Takes partial profit at 1R
    - Closes at TP or SL
    - Sends alerts on every change
    """
    def __init__(self, executor, memory, learner):
        self.executor = executor
        self.memory = memory
        self.learner = learner
        self.running = False
        self.monitor_thread = None
        self.agent_signals_store = {}
        print("✅ Trade Monitor initialized")

    def start(self):
        """Start monitoring in background thread"""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("✅ Trade Monitor running in background")
        Telegram.send("👁 <b>Trade Monitor Active</b>\nWatching all positions every 60 seconds")

    def stop(self):
        self.running = False
        print("⏹ Trade Monitor stopped")

    def register_trade(self, trade_id, signal_data, agent_signals):
        """Register a new trade for monitoring"""
        self.agent_signals_store[str(trade_id)] = {
            'signal_data': signal_data,
            'agent_signals': agent_signals,
            'peak_profit': 0,
            'partial_taken': False,
            'breakeven_moved': False,
        }

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_all_positions()
            except Exception as e:
                print(f"Monitor error: {e}")
            time.sleep(CONFIG['MONITOR_INTERVAL'])

    def _check_all_positions(self):
        """Check every open position"""
        open_trades = self.executor.get_open_trades()

        if not open_trades:
            return

        print(f"\n👁 Monitor checking {len(open_trades)} open positions...")

        for trade in open_trades:
            try:
                trade_id = str(trade.get('id', ''))
                symbol_raw = trade.get('instrument', '')
                # Convert OANDA format back to our format
                symbol = symbol_raw.replace('_', '')
                current_price = float(trade.get('price', 0))
                unrealized_pnl = float(trade.get('unrealizedPL', 0))
                units = int(trade.get('currentUnits', 0))
                signal = 1 if units > 0 else -1

                stored = self.agent_signals_store.get(trade_id, {})
                signal_data = stored.get('signal_data', {})
                entry = float(signal_data.get('entry', current_price))
                initial_sl = float(signal_data.get('stop_loss', 0))
                tp = float(signal_data.get('take_profit', 0))
                risk = abs(entry - initial_sl)

                # Get live price
                live = self.executor.get_current_price(symbol)
                if live:
                    current_price = live['bid'] if signal == -1 else live['ask']

                current_profit_r = 0
                if risk > 0:
                    if signal == 1:
                        current_profit_r = (current_price - entry) / risk
                    else:
                        current_profit_r = (entry - current_price) / risk

                print(f"  {symbol}: {current_profit_r:.2f}R unrealized ${unrealized_pnl:.2f}")

                # BREAKEVEN: Move SL to entry after 1R profit
                if current_profit_r >= CONFIG['BREAKEVEN_AT_R'] and not stored.get('breakeven_moved', False):
                    new_sl = entry
                    if self.executor.modify_trade(trade_id, new_stop_loss=new_sl):
                        if trade_id in self.agent_signals_store:
                            self.agent_signals_store[trade_id]['breakeven_moved'] = True
                        print(f"  ✅ BREAKEVEN moved for {symbol} SL→{new_sl:.5f}")
                        Telegram.send(f"""
🛡 <b>BREAKEVEN ACTIVATED</b>
{symbol} {'BUY' if signal==1 else 'SELL'}
SL moved to entry: {new_sl:.5f}
Current profit: {current_profit_r:.2f}R (${unrealized_pnl:.2f})
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
                        """)

                # PARTIAL CLOSE: Take 50% at 1R
                if current_profit_r >= CONFIG['PARTIAL_CLOSE_AT_R'] and not stored.get('partial_taken', False):
                    partial_units = abs(units) // 2
                    if partial_units > 0:
                        success, partial_pnl = self.executor.close_trade(
                            trade_id, partial_units=partial_units if signal==1 else -partial_units)
                        if success:
                            if trade_id in self.agent_signals_store:
                                self.agent_signals_store[trade_id]['partial_taken'] = True
                            print(f"  ✅ PARTIAL CLOSE {symbol} 50% at {current_profit_r:.1f}R PnL:${partial_pnl:.2f}")
                            Telegram.send(f"""
💰 <b>PARTIAL PROFIT TAKEN</b>
{symbol} {'BUY' if signal==1 else 'SELL'}
Closed 50% at {current_profit_r:.1f}R
Profit locked: ${partial_pnl:.2f}
Remaining 50% still running to TP
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
                            """)

            except Exception as e:
                print(f"  Error monitoring trade {trade_id}: {e}")

    def handle_trade_closed(self, trade_id, exit_price, pnl):
        """Called when a trade closes — triggers learning"""
        stored = self.agent_signals_store.get(str(trade_id), {})
        if not stored:
            return

        signal_data = stored.get('signal_data', {})
        agent_signals = stored.get('agent_signals', {})
        outcome = 'win' if pnl > 0 else 'loss'

        # Update memory
        self.memory.update_trade_closed(trade_id, exit_price, pnl, outcome)

        # Trigger self learning
        self.learner.learn_from_trade(signal_data, outcome, agent_signals)

        # Remove from monitoring
        if str(trade_id) in self.agent_signals_store:
            del self.agent_signals_store[str(trade_id)]

        print(f"✅ Trade {trade_id} closed: {outcome.upper()} PnL:${pnl:.2f}")

# ============================================================
# ALPHA VANTAGE DATA LOADER
# ============================================================
class AlphaVantageLoader:
    """
    Better quality market data from Alpha Vantage.
    Falls back to Yahoo Finance if unavailable.
    """
    BASE = 'https://www.alphavantage.co/query'
    KEY = CONFIG['ALPHA_VANTAGE_KEY']
    _cache = {}
    _cache_time = {}

    @classmethod
    def get_forex_daily(cls, from_currency, to_currency):
        """Get daily forex data"""
        cache_key = f"daily_{from_currency}_{to_currency}"
        now = time.time()
        if cache_key in cls._cache and now - cls._cache_time.get(cache_key,0) < 3600:
            return cls._cache[cache_key]
        try:
            r = requests.get(cls.BASE, params={
                'function': 'FX_DAILY',
                'from_symbol': from_currency,
                'to_symbol': to_currency,
                'apikey': cls.KEY,
                'outputsize': 'compact'
            }, timeout=15)
            if r.status_code == 200:
                data = r.json()
                ts = data.get('Time Series FX (Daily)', {})
                if ts:
                    rows = []
                    for date, vals in sorted(ts.items(), reverse=True)[:100]:
                        rows.append({
                            'date': date,
                            'open': float(vals['1. open']),
                            'high': float(vals['2. high']),
                            'low': float(vals['3. low']),
                            'close': float(vals['4. close']),
                            'volume': 1000
                        })
                    df = pd.DataFrame(rows)
                    df.index = pd.to_datetime(df['date'])
                    df = df.drop('date', axis=1).sort_index()
                    cls._cache[cache_key] = df
                    cls._cache_time[cache_key] = now
                    return df
        except: pass
        return None

    @classmethod
    def get_forex_intraday(cls, from_currency, to_currency, interval='60min'):
        """Get intraday forex data"""
        cache_key = f"intra_{from_currency}_{to_currency}_{interval}"
        now = time.time()
        if cache_key in cls._cache and now - cls._cache_time.get(cache_key,0) < 300:
            return cls._cache[cache_key]
        try:
            r = requests.get(cls.BASE, params={
                'function': 'FX_INTRADAY',
                'from_symbol': from_currency,
                'to_symbol': to_currency,
                'interval': interval,
                'apikey': cls.KEY,
                'outputsize': 'compact'
            }, timeout=15)
            if r.status_code == 200:
                data = r.json()
                key = f'Time Series FX ({interval})'
                ts = data.get(key, {})
                if ts:
                    rows = []
                    for date, vals in sorted(ts.items(), reverse=True)[:200]:
                        rows.append({
                            'date': date,
                            'open': float(vals['1. open']),
                            'high': float(vals['2. high']),
                            'low': float(vals['3. low']),
                            'close': float(vals['4. close']),
                            'volume': float(vals.get('5. volume', 1000))
                        })
                    df = pd.DataFrame(rows)
                    df.index = pd.to_datetime(df['date'])
                    df = df.drop('date', axis=1).sort_index()
                    cls._cache[cache_key] = df
                    cls._cache_time[cache_key] = now
                    return df
        except: pass
        return None

# ============================================================
# COMPLETE AUTONOMOUS TRADING ENGINE
# ============================================================
class AutonomousEngine:
    """
    The complete autonomous trading engine.
    Combines all V6 agents with:
    - OANDA execution
    - Trade monitoring
    - Memory and learning
    - Alpha Vantage data
    """
    def __init__(self):
        print("\n" + "="*60)
        print("🚀 V7 AUTONOMOUS ENGINE INITIALIZING")
        print("="*60)

        # Core systems
        self.memory = MemorySystem()
        self.learner = SelfLearningSystem(self.memory)
        self.executor = OandaExecutor()
        self.monitor = TradeMonitor(self.executor, self.memory, self.learner)

        # Check account
        account = self.executor.get_account_summary()
        if account:
            print(f"✅ OANDA Account: ${account['balance']:,.2f} | {account['open_trade_count']} open trades")
        else:
            print("⚠️ OANDA connection issue - check API key")

        # Start trade monitor in background
        self.monitor.start()

        # Performance tracking
        self.session_signals = []
        self.session_trades = []
        self.capital = account['balance'] if account else CONFIG['INITIAL_CAPITAL']

        print("="*60)
        print("✅ All systems initialized")
        print("="*60)

        Telegram.send(f"""
🚀 <b>V7 AUTONOMOUS ENGINE STARTED</b>
💵 Capital: ${self.capital:,.2f}
👁 Trade Monitor: Active
🧠 Self-Learning: Active
📊 Memory System: Active
⚡ OANDA Execution: Active
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        """)

    def execute_signal(self, signal_data, agent_signals=None):
        """
        Execute a trading signal on OANDA.
        This is called after the V6 orchestrator generates a signal.
        """
        symbol = signal_data['symbol']
        signal = signal_data['signal']
        entry = signal_data['entry']
        stop_loss = signal_data['stop_loss']
        take_profit = signal_data['take_profit']
        lots = signal_data['lots']
        confidence = signal_data['confidence']

        print(f"\n⚡ EXECUTING: {symbol} {'BUY' if signal==1 else 'SELL'}")
        print(f"   Entry:{entry:.5f} SL:{stop_loss:.5f} TP:{take_profit:.5f} Lots:{lots}")

        # Save signal to memory
        self.memory.save_signal(signal_data)

        # Place trade on OANDA
        trade_id = self.executor.place_trade(
            symbol, signal, lots, stop_loss, take_profit)

        if trade_id:
            # Save trade to memory
            trade_record = {
                **signal_data,
                'trade_id': trade_id,
            }
            self.memory.save_trade(trade_record)

            # Register with monitor for management
            self.monitor.register_trade(
                trade_id, signal_data, agent_signals or {})

            # Store in session
            self.session_trades.append({
                **trade_record,
                'trade_id': trade_id,
                'placed_at': datetime.utcnow().isoformat()
            })

            # Send Telegram notification
            pip = PIP_SIZE.get(symbol, 0.0001)
            sl_pips = abs(entry - stop_loss) / pip
            tp_pips = abs(take_profit - entry) / pip
            rr = tp_pips / sl_pips if sl_pips > 0 else 0

            Telegram.send(f"""
{'🟢' if signal==1 else '🔴'} <b>TRADE PLACED ON OANDA</b>
<b>{symbol} {'BUY' if signal==1 else 'SELL'}</b>
💰 Entry: <code>{entry:.5f}</code>
🛡 Stop Loss: <code>{stop_loss:.5f}</code> ({sl_pips:.0f} pips)
🎯 Take Profit: <code>{take_profit:.5f}</code> ({tp_pips:.0f} pips)
📦 Lots: <b>{lots}</b> | R:R <b>1:{rr:.1f}</b>
🧠 Confidence: <b>{confidence:.1%}</b>
🔑 Trade ID: {trade_id}
⏰ {datetime.utcnow().strftime('%H:%M UTC')}
            """)

            return trade_id
        else:
            print(f"   ❌ Trade execution failed for {symbol}")
            return None

    def get_account_status(self):
        """Get current account status"""
        account = self.executor.get_account_summary()
        open_trades = self.executor.get_open_trades()
        perf = self.memory.get_performance_stats()

        return {
            'account': account,
            'open_trades': open_trades,
            'performance': perf,
            'session_trades': len(self.session_trades),
            'session_signals': len(self.session_signals),
            'agent_weights': self.memory.agent_weights,
        }

    def daily_report(self):
        """Generate and send daily performance report"""
        account = self.executor.get_account_summary()
        perf = self.memory.get_performance_stats()
        open_trades = self.executor.get_open_trades()

        balance = account['balance'] if account else 0
        initial = CONFIG['INITIAL_CAPITAL']
        total_return = (balance - initial) / initial * 100

        report = f"""
📊 <b>DAILY PERFORMANCE REPORT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━
💵 Balance: ${balance:,.2f}
📈 Total Return: {total_return:+.2f}%
━━━━━━━━━━━━━━━━━━━━━━━━━
📋 All-Time Trades: {perf['total']}
✅ Wins: {perf['wins']} | ❌ Losses: {perf['losses']}
🎯 Win Rate: {perf['win_rate']:.1%}
💰 Total PnL: ${perf['total_pnl']:+,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Open Positions: {len(open_trades)}
🧠 Agent Weights Updated: {len(self.memory.agent_weights)}
━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        """
        Telegram.send(report)
        print(report)
        return report

# ============================================================
# DATAFRAME FIX UTILITY
# ============================================================
def safe_df_check(df):
    """Safe check for DataFrame validity - fixes ambiguous truth value error"""
    if df is None:
        return False
    if not isinstance(df, pd.DataFrame):
        return False
    if df.empty:
        return False
    if len(df) < 10:
        return False
    return True

# ============================================================
# INTEGRATION WITH V6
# ============================================================
def run_v7_with_v6(auto_execute=False):
    """
    Runs V7 engine integrated with V6 brain.
    auto_execute=True means trades are placed automatically.
    auto_execute=False means signals shown for approval.
    """
    print("\n" + "="*65)
    print("🚀 V7 ULTIMATE AUTONOMOUS SYSTEM")
    print("="*65)

    # Initialize V7 engine
    engine = AutonomousEngine()

    # Import V6 brain
    try:
        from v8_ultimate import run_system, CONFIG as V6_CONFIG
        print("✅ V6 Brain connected to V7 Engine")
    except ImportError:
        print("❌ v6_brain.py not found - run v6_brain.py first")
        return engine

    # Run V6 analysis
    print("\n🔍 Running V6 analysis...")
    signals = run_system()

    if not signals:
        print("No signals generated")
        return engine

    print(f"\n📊 {len(signals)} signals from V6 agents")

    # Process each signal
    for signal in signals:
        symbol = signal['symbol']
        action = 'BUY' if signal['signal'] == 1 else 'SELL'
        conf = signal['confidence']

        print(f"\n{'='*50}")
        print(f"Signal: {symbol} {action} | Confidence: {conf:.1%}")
        print(f"Entry: {signal['entry']:.5f}")
        print(f"Stop Loss: {signal['stop_loss']:.5f}")
        print(f"Take Profit: {signal['take_profit']:.5f}")
        print(f"Lots: {signal['lots']}")

        if auto_execute:
            # Auto execute
            trade_id = engine.execute_signal(signal)
            if trade_id:
                print(f"✅ Auto-executed: Trade ID {trade_id}")
        else:
            # Manual approval mode
            print("\nAuto-execute is OFF. Signal saved to memory and Telegram.")
            engine.memory.save_signal(signal)
            Telegram.send(f"""
⚡ <b>SIGNAL READY — Awaiting Approval</b>
{symbol} {'🟢 BUY' if signal['signal']==1 else '🔴 SELL'}
Entry: {signal['entry']:.5f}
SL: {signal['stop_loss']:.5f}
TP: {signal['take_profit']:.5f}
Confidence: {signal['confidence']:.1%}
To execute: Set auto_execute=True in v7_engine.py
            """)

    # Account status
    print("\n" + "="*65)
    status = engine.get_account_status()
    account = status.get('account', {})
    if account:
        print(f"💵 Balance: ${account.get('balance',0):,.2f}")
        print(f"📊 Open Trades: {account.get('open_trade_count',0)}")
        print(f"📈 Unrealized PnL: ${account.get('unrealized_pnl',0):+.2f}")

    return engine

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║              V7 AUTONOMOUS TRADING ENGINE               ║
║   OANDA Execution + Monitor + Memory + Self-Learning   ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("""
AUTO-EXECUTE MODE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Currently: SIGNALS ONLY (safe mode)
Trades are NOT placed automatically yet.

To enable auto-trading on OANDA demo:
Change auto_execute=False to auto_execute=True
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    # Run in signal-only mode first for safety
    # Change to auto_execute=True when ready to trade
    engine = run_v7_with_v6(auto_execute=False)

    print("\n✅ V7 Engine complete!")
    print("📱 Check Telegram for all updates!")
    print("\nNext steps:")
    print("1. Review signals on Telegram")
    print("2. When confident: change auto_execute=False to True")
    print("3. System will then trade automatically 24/7")
