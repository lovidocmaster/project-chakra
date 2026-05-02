import yfinance as yf
import pandas as pd
import numpy as np

print("\n" + "="*70)
print("🚀 REAL BACKTEST ENGINE - EURUSD 2015-2026")
print("="*70)

# Download data
print("\n📊 Downloading EURUSD data from 2015-2026...")
data = yf.download('EURUSD=X', start='2015-01-01', end='2026-05-01', progress=False)

print(f"✅ Downloaded {len(data)} days of data")
print(f"   From: {data.index[0].strftime('%Y-%m-%d')}")
print(f"   To: {data.index[-1].strftime('%Y-%m-%d')}")

# Calculate moving averages
data['SMA20'] = data['Close'].rolling(20).mean()
data['SMA50'] = data['Close'].rolling(50).mean()

# Generate signals
data['Signal'] = 0
data['Signal'][data['SMA20'] > data['SMA50']] = 1
data['Signal'][data['SMA20'] <= data['SMA50']] = -1
data['Position'] = data['Signal'].diff()

# Backtest
capital = 10000
position = 0
entry_price = 0
trades = []
equity = [capital]

print("\n📈 Running backtest with SMA20/SMA50 strategy...")

for i in range(len(data)):
    price = data['Close'].iloc[i]
    
    if data['Position'].iloc[i] == 1 and position == 0:
        # Buy signal
        position = 1
        entry_price = price
        trades.append({'date': data.index[i], 'type': 'BUY', 'price': price})
    
    elif data['Position'].iloc[i] == -1 and position == 1:
        # Sell signal
        pnl = (price - entry_price) * 100  # Simplified
        capital = capital + pnl
        trades.append({'date': data.index[i], 'type': 'SELL', 'price': price, 'pnl': pnl})
        position = 0
    
    # Update equity
    if position == 1:
        current_equity = capital + (price - entry_price) * 100
    else:
        current_equity = capital
    
    equity.append(current_equity)

# Calculate metrics
final_capital = equity[-1]
total_return = final_capital - 10000
return_pct = (total_return / 10000) * 100

closed_trades = [t for t in trades if 'pnl' in t]
winning = [t for t in closed_trades if t['pnl'] > 0]
losing = [t for t in closed_trades if t['pnl'] < 0]

win_rate = (len(winning) / len(closed_trades) * 100) if len(closed_trades) > 0 else 0

# Print results
print("\n" + "="*70)
print("📊 BACKTEST RESULTS")
print("="*70)
print(f"Initial Capital:          ${10000:>20,.2f}")
print(f"Final Capital:            ${final_capital:>20,.2f}")
print(f"Total Return:             ${total_return:>20,.2f}")
print(f"Return %:                 {return_pct:>20.2f}%")
print("-"*70)
print(f"Total Trades:             {len(closed_trades):>20.0f}")
print(f"Winning Trades:           {len(winning):>20.0f}")
print(f"Losing Trades:            {len(losing):>20.0f}")
print(f"Win Rate:                 {win_rate:>20.2f}%")
print("="*70)
print("\n✅ Backtest Complete!\n")