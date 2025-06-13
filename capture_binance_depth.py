# This is GPT-4o code

import asyncio
import websockets
import json
import time
import pandas as pd

SYMBOL = "btcusdt"
DEPTH_URL = f"wss://stream.binance.com:9443/ws/{SYMBOL}@depth@100ms"

data = []

async def collect_depth():
    async with websockets.connect(DEPTH_URL) as ws:
        print("Connected to Binance depth stream.")
        start_time = time.time()
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                print("Timeout waiting for message, continuing...")
                continue
            msg = json.loads(msg)
            ts = time.time()
            data.append({
                "timestamp": ts,
                "bids": msg["b"],
                "asks": msg["a"]
            })

            # Stop after ~5 minutes of data
            if ts - start_time > 300:
                break

        print("Saving captured data...")
        df = pd.DataFrame(data)
        df.to_pickle(f"binance_l2_{SYMBOL}.pkl")
        print("Saved to pickle. Exiting.")

if __name__ == "__main__":
    asyncio.run(collect_depth())
