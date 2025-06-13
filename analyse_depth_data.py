import pandas as pd
import numpy as np
import json
import math

# Load depth snapshot data
SYMBOL = "btcusdt"
df = pd.read_pickle(f"binance_l2_{SYMBOL}.pkl")


df = df[df["bids"].apply(len) > 0]
df = df[df["asks"].apply(len) > 0]

print(df.head())
print(f"Loaded {len(df)} snapshots")

# Constants and time span

time_span = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]

# 1. Tick size
tick_size_dollar = 0.01
mid_price0 = (float(df.iloc[0]["bids"][0][0]) + float(df.iloc[0]["asks"][0][0])) / 2
dp = math.log(1 + tick_size_dollar / mid_price0)
#dp = 1e-6 # dp -> 0 for continuous model

# 2. Average spread
spread_series = []
for row in df.itertuples():
    best_bid = float(row.bids[0][0])
    best_ask = float(row.asks[0][0])
    spread = best_ask - best_bid
    spread_series.append(spread)
mean_spread = float(np.mean(spread_series))

# 3. Limit order rate α
limit_events = 0
for i in range(1, len(df)):
    prev_bids = set((float(x[0]), float(x[1])) for x in df.bids.iloc[i-1][:5])
    curr_bids = set((float(x[0]), float(x[1])) for x in df.bids.iloc[i][:5])
    limit_events += len(curr_bids - prev_bids)
alpha = limit_events / (5 * time_span)  # shares / price / sec

# 4. Market order rate μ
mid_prices = [(float(row.asks[0][0]) + float(row.bids[0][0])) / 2 for row in df.itertuples()]
price_jumps = sum(1 for i in range(1, len(mid_prices)) if mid_prices[i] != mid_prices[i-1])
mu = price_jumps / time_span

# 5. Cancellation rate δ (approximate as 50% of limit flow)
delta = 0.5 * alpha

# 6. Typical order size σ (median volume at top levels)
sample_size = [float(x[1]) for x in df.bids.iloc[0][:5]]
sigma = float(np.median(sample_size))

# 7. Granularity ε
epsilon = (2 * delta * sigma) / mu

n_ticks = int(df.apply(lambda row: max(len(row["bids"]), len(row["asks"])), axis=1).max())

# Assemble parameter dictionary
params = {
    "dp": dp,
    "mean_spread": mean_spread,
    "alpha": alpha,
    "mu": mu,
    "delta": delta,
    "sigma": sigma,
    "epsilon": epsilon,
    "n_ticks": n_ticks,
}

# Print for confirmation
for k, v in params.items():
    print(f"{k:>12s} : {v:.6f}" if isinstance(v, float) else f"{k:>12s} : {v}")

# Save to JSON
with open(f"calibrated_params_{SYMBOL}.json", "w") as f:
    json.dump(params, f, indent=4)

# Optional: save to pickle too
pd.to_pickle(params, "calibrated_params.pkl")
print("Parameters saved to 'calibrated_params.json' and 'calibrated_params.pkl'")
