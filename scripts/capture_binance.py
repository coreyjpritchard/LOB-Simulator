"""Record a short Binance partial-book stream to data/raw/.

The file is gitignored. Binance's live websocket is not the Vision dataset,
and this repository does not commit it. `python -m lobsim.build_inputs` turns
a local diff capture into the aggregates under data/.

Partial depth (`<symbol>@depth20@100ms`) is a real top-of-book snapshot each
message. The June 2025 files this repository was measured on were the diff
stream `<symbol>@depth@100ms` (absolute quantities at changed levels only).

From this environment `api.binance.com` returned HTTP 451, so the published
numbers were not recaptured live.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path


async def _collect(symbol: str, seconds: float, out: Path) -> None:
    try:
        import websockets
    except ImportError as exc:
        raise SystemExit("install the capture extra: uv sync --extra capture") from exc

    url = f"wss://stream.binance.com:9443/ws/{symbol}@depth20@100ms"
    rows: list[dict] = []
    async with websockets.connect(url) as ws:
        print(f"connected {url}")
        start = time.time()
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=10)
            except TimeoutError:
                print("no message for 10s, still waiting")
                continue
            msg = json.loads(raw)
            now = time.time()
            rows.append(
                {
                    "timestamp": now,
                    "bids": msg.get("bids") or msg.get("b") or [],
                    "asks": msg.get("asks") or msg.get("a") or [],
                }
            )
            if now - start >= seconds:
                break
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows))
    print(f"wrote {len(rows)} snapshots to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="btcusdt")
    parser.add_argument("--seconds", type=float, default=300)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="default data/raw/<symbol>_depth20.json",
    )
    args = parser.parse_args()
    symbol = args.symbol.lower()
    out = args.out or Path("data/raw") / f"{symbol}_depth20.json"
    asyncio.run(_collect(symbol, args.seconds, out))


if __name__ == "__main__":
    main()
