import pandas as pd
import numpy as np
import sys
sys.path.append('./apps/api')
from strategies.engine import mean_reversion

# Create sample data that will trigger BB conditions
np.random.seed(42)
dates = pd.date_range('2025-10-17', periods=100, freq='5min')

# Create a price series that dips below BB lower
close_prices = np.ones(100) * 100

# Make the last few prices dip below BB lower
close_prices[-5:] = [93.0, 92.5, 91.8, 91.2, 90.8]  # Last price below BB lower

# Create Bollinger Bands (20 period, 2 std)
bb_mid = pd.Series(close_prices).rolling(20).mean()
bb_std = pd.Series(close_prices).rolling(20).std()
bb_upper = bb_mid + 2 * bb_std
bb_lower = bb_mid - 2 * bb_std

# Create RSI (14 period) - make it > 42 for last few points
rsi_values = np.ones(100) * 50  # Default RSI
rsi_values[-10:] = [35, 38, 41, 44, 46, 48, 50, 52, 54, 42]  # Last RSI = 42
rsi = pd.Series(rsi_values)

# Create ATR
high = pd.Series(close_prices * (1 + np.random.randn(100) * 0.01))
low = pd.Series(close_prices * (1 - np.random.randn(100) * 0.01))
atr = (high - low).rolling(14).mean()

# Create DataFrame
df = pd.DataFrame({
    'close': close_prices,
    'bb_lower': bb_lower,
    'bb_upper': bb_upper,
    'rsi14': rsi,
    'atr14': atr
})

print("Sample data shape:", df.shape)
print("Last row:", df.iloc[-1])

# Test strategy
signal = mean_reversion(df)
print("Signal generated:", signal is not None)
if signal:
    print("Signal:", signal.action, "Entry:", signal.entry, "Stop:", signal.stop, "Target:", signal.target, "Confidence:", signal.confidence)