import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# ==================== AGENT CLASSES ====================

class ChartAnalysisAgent:
    """Analyzes price action, trends, support/resistance"""
    def analyze(self, prices, closes):
        if len(closes) < 50:
            return {'signal': 'WAIT', 'confidence': 0}
        
        sma20 = np.mean(closes[-20:])
        sma50 = np.mean(closes[-50:])
        rsi = self.calculate_rsi(closes[-14:])
        
        signal = 'WAIT'
        confidence = 0
        
        if closes[-1] > sma20 > sma50 and rsi < 70:
            signal = 'BUY'
            confidence = 0.8
        elif closes[-1] < sma20 < sma50 and rsi > 30:
            signal = 'SELL'
            confidence = 0.8
        
        return {'signal': signal, 'confidence': confidence, 'rsi': rsi}
    
    def calculate_rsi(self, prices):
        if len(prices) < 2:
            return 50
        deltas = np.diff(prices)
        seed = deltas[:1]
        up = seed[seed >= 0].sum() / 1 or 0
        down = -seed[seed < 0].sum() / 1 or 0
        rs = up / down if down else 0
        rsi = 100 - 100 / (1 + rs) if rs else 50
        return rsi

class NewsMonitorAgent:
    """Monitors news sentiment"""
    def analyze(self, current_bar):
        # Simulate news impact
        np.random.seed(current_bar)
        return {
            'signal': np.random.choice(['BUY', 'SELL', 'NEUTRAL']),
            'confidence': np.random.uniform(0.3, 0.9),
            'impact': 'high' if np.random.random() > 0.7 else 'normal'
        }

class SentimentAgent:
    """Analyzes market sentiment"""
    def analyze(self, prices):
        recent_uptrend = prices[-1] > np.mean(prices[-10:])
        return {
            'bullish': recent_uptrend,
            'confidence': 0.6 if recent_uptrend else 0.4,
            'signal': 'BUY' if recent_uptrend else 'SELL'
        }

class RiskManagementAgent:
    """Manages position sizing and stops"""
    def calculate_position_size(self, capital, price, risk_percent=2.0):
        risk_amount = capital * (risk_percent / 100)
        stop_loss_pips = 50  # 50 pips stop loss
        position_size = risk_amount / (stop_loss_pips * price)
        return max(0.01, min(position_size, 1.0))
    
    def get_stop_loss(self, entry_price, direction):
        stop_distance = entry_price * 0.005  # 0.5% stop loss
        if direction == 'BUY':
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

class LearningAgent:
    """Tracks what strategies worked"""
    def __init__(self):
        self.trade_history = []
        self.success_rate = 0.5
    
    def record_trade(self, entry, exit, pnl):
        self.trade_history.append({'entry': entry, 'exit': exit, 'pnl': pnl})
    
    def adjust_confidence(self):
        if len(self.trade_history) > 10:
            winners = [t for t in self.trade_history[-10:] if t['pnl'] > 0]
            self.success_rate = len(winners) / 10
        return self.success_rate

class MasterOrchestratorAgent:
    """Makes final trading decisions"""
    def decide(self, signals):
        # Aggregate signals from all agents
        buy_votes = sum(1 for s in signals if s.get('signal') == 'BUY')
        sell_votes = sum(1 for s in signals if s.get('signal') == 'SELL')
        
        avg_confidence = np.mean([s.get('confidence', 0.5) for s in signals])
        
        if buy_votes > sell_votes and avg_confidence > 0.65:
            return 'BUY'
        elif sell_votes > buy_votes and avg_confidence > 0.65:
            return 'SELL'
        else:
            return 'HOLD'

# ==================== BACKTEST ENGINE ====================

class AgentBacktester:
    def __init__(self, symbol='EURUSD', start_date='2015-01-01', end_date='2026-01-01'):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        
        # Initialize agents
        self.chart_agent = ChartAnalysisAgent()
        self.news_agent = NewsMonitorAgent()
        self.sentiment_agent = SentimentAgent()
        self.risk_agent = RiskManagementAgent()
        self.learning_agent = LearningAgent()
        self.orchestrator = MasterOrchestratorAgent()
        
        self.trades = []
        self.equity_curve = []
    
    def generate_realistic_data(self):
        """Generate realistic EURUSD data"""
        print(f"\n📊 Generating {self.symbol} data from {self.start_date} to {self.end_date}...")
        
        dates = pd.date_range(start=self.start_date, end=self.end_date, freq='D')
        prices = [1.0500]
        
        np.random.seed(42)
        for _ in range(len(dates)-1):
            change = np.random.normal(0.0002, 0.008)
            new_price = prices[-1] * (1 + change)
            new_price = max(0.9000, min(1.2500, new_price))
            prices.append(new_price)
        
        data = pd.DataFrame({
            'Date': dates,
            'Open': [p * 0.999 for p in prices],
            'High': [p * 1.002 for p in prices],
            'Low': [p * 0.998 for p in prices],
            'Close': prices,
        })
        
        print(f"✅ Generated {len(data)} days of data")
        return data
    
    def run_backtest(self, initial_capital=10000):
        """Execute backtest with agents"""
        print(f"\n🚀 RUNNING AGENT-BASED BACKTEST")
        print(f"   Initial Capital: ${initial_capital:,.2f}")
        print(f"   Strategy: Multi-Agent Consensus")
        
        data = self.generate_realistic_data()
        
        capital = initial_capital
        position = 0
        entry_price = 0
        equity_curve = [initial_capital]
        
        for idx in range(50, len(data)):
            current_price = data['Close'].iloc[idx]
            prices = data['Close'].iloc[:idx+1].values
            
            # All agents analyze current market
            chart_signal = self.chart_agent.analyze(prices, prices[-50:])
            news_signal = self.news_agent.analyze(idx)
            sentiment_signal = self.sentiment_agent.analyze(prices[-20:])
            
            # Orchestrator makes decision
            all_signals = [chart_signal, news_signal, sentiment_signal]
            decision = self.orchestrator.decide(all_signals)
            
            # Execute if signal strong enough
            if decision == 'BUY' and position == 0:
                position_size = self.risk_agent.calculate_position_size(capital, current_price)
                position = position_size
                entry_price = current_price
                stop_loss = self.risk_agent.get_stop_loss(entry_price, 'BUY')
                
                self.trades.append({
                    'date': data['Date'].iloc[idx],
                    'type': 'BUY',
                    'price': current_price,
                    'size': position_size,
                    'stop_loss': stop_loss
                })
            
            elif decision == 'SELL' and position > 0:
                pnl = (current_price - entry_price) * position * 100000
                capital += pnl
                
                self.trades.append({
                    'date': data['Date'].iloc[idx],
                    'type': 'SELL',
                    'price': current_price,
                    'pnl': pnl,
                    'position_size': position
                })
                
                self.learning_agent.record_trade(entry_price, current_price, pnl)
                position = 0
            
            # Update equity
            if position > 0:
                unrealized = (current_price - entry_price) * position * 100000
                equity = capital + unrealized
            else:
                equity = capital
            
            equity_curve.append(equity)
        
        return capital, equity_curve
    
    def calculate_metrics(self, final_capital, initial_capital, equity_curve):
        """Calculate performance metrics"""
        total_return = final_capital - initial_capital
        return_pct = (total_return / initial_capital) * 100
        
        closed_trades = [t for t in self.trades if 'pnl' in t]
        winning = [t for t in closed_trades if t['pnl'] > 0]
        losing = [t for t in closed_trades if t['pnl'] <= 0]
        
        win_rate = (len(winning) / len(closed_trades) * 100) if closed_trades else 0
        
        total_wins = sum([t['pnl'] for t in winning])
        total_losses = abs(sum([t['pnl'] for t in losing]))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Sharpe Ratio
        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])
        sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0
        
        # Max Drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (np.array(equity_curve) - peak) / peak
        max_dd = np.min(drawdown) * 100
        
        return {
            'final_capital': final_capital,
            'total_return': total_return,
            'return_pct': return_pct,
            'num_trades': len(closed_trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
        }
    
    def print_results(self, metrics):
        """Print backtest results"""
        print("\n" + "="*80)
        print("🎯 AGENT-BASED BACKTEST RESULTS")
        print("="*80)
        print(f"Symbol: {self.symbol} | Period: {self.start_date} to {self.end_date}")
        print("-"*80)
        print(f"Initial Capital:          ${10000:>20,.2f}")
        print(f"Final Capital:            ${metrics['final_capital']:>20,.2f}")
        print(f"Total Return:             ${metrics['total_return']:>20,.2f}")
        print(f"Return %:                 {metrics['return_pct']:>20.2f}%")
        print("-"*80)
        print(f"Total Trades:             {metrics['num_trades']:>20.0f}")
        print(f"Winning Trades:           {metrics['winning_trades']:>20.0f}")
        print(f"Losing Trades:            {metrics['losing_trades']:>20.0f}")
        print(f"Win Rate:                 {metrics['win_rate']:>20.2f}%")
        print(f"Profit Factor:            {metrics['profit_factor']:>20.2f}")
        print("-"*80)
        print(f"Sharpe Ratio:             {metrics['sharpe_ratio']:>20.2f}")
        print(f"Max Drawdown:             {metrics['max_drawdown']:>20.2f}%")
        print("="*80)
        print("\n✅ Backtest Complete!\n")

# ==================== RUN BACKTEST ====================

if __name__ == '__main__':
    backtest = AgentBacktester(
        symbol='EURUSD',
        start_date='2015-01-01',
        end_date='2026-01-01'
    )
    
    final_capital, equity_curve = backtest.run_backtest(initial_capital=10000)
    metrics = backtest.calculate_metrics(final_capital, 10000, equity_curve)
    backtest.print_results(metrics)