"""Build the committed summaries from a local diff capture and a Vision zip.

Not part of `make reproduce`. The raw diffs are not redistributed; this writes
the aggregates in data/ and a small trade extract. Needs pandas and a local
pickle (see scripts/capture_binance.py).
"""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from pathlib import Path

from lobsim.flow import Diff, flow_from_diffs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# book_time - trade_time, from large prints in this capture. See README.
CLOCK_SHIFT = {"btcusdt": -0.59, "ethusdt": -0.35}
BURN_IN_S = 45.0
N_BINS = 40
TICK = 0.01


def _load_diffs(pickle_path: Path) -> list[Diff]:
    import pandas as pd

    frame = pd.read_pickle(pickle_path)
    diffs: list[Diff] = []
    for row in frame.itertuples(index=False):
        bids = tuple((float(price), float(qty)) for price, qty in row.bids)
        asks = tuple((float(price), float(qty)) for price, qty in row.asks)
        diffs.append(Diff(float(row.timestamp), bids, asks))
    return diffs


def _load_zip_trades(
    zip_path: Path, start: float, end: float
) -> list[tuple[float, float, float, bool]]:
    rows: list[tuple[float, float, float, bool]] = []
    start_us = int((start - 2) * 1_000_000)
    end_us = int((end + 2) * 1_000_000)
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(archive.namelist()[0]) as handle:
            for line in handle:
                parts = line.decode().strip().split(",")
                stamp = int(parts[5])
                if stamp < start_us:
                    continue
                if stamp > end_us:
                    break
                rows.append(
                    (
                        stamp / 1_000_000,
                        float(parts[1]),
                        float(parts[2]),
                        parts[6] in ("true", "True"),
                    )
                )
    return rows


def build_symbol(symbol: str, pickle_path: Path, zip_path: Path) -> None:
    diffs = _load_diffs(pickle_path)
    start, end = diffs[0].time, diffs[-1].time
    trades = _load_zip_trades(zip_path, start, end)
    totals = flow_from_diffs(
        diffs,
        trades,
        tick=TICK,
        burn_in_s=BURN_IN_S,
        n_bins=N_BINS,
        clock_shift_s=CLOCK_SHIFT[symbol],
    )
    summary = {
        "symbol": symbol.upper(),
        "source": "Binance diff-depth stream @depth@100ms, reconstructed locally",
        "capture_start_unix": start,
        "capture_end_unix": end,
        "flow_start_unix": totals.flow_start,
        "flow_end_unix": totals.flow_end,
        "burn_in_s": BURN_IN_S,
        "measured_span_s": totals.measured_span_s,
        "tick_size": TICK,
        "clock_shift_s": CLOCK_SHIFT[symbol],
        "n_spreads": totals.n_spreads,
        "spread_mean": totals.spread_mean,
        "spread_median": totals.spread_median,
        "spread_p10": totals.spread_p10,
        "spread_p90": totals.spread_p90,
        "mid_median": totals.mid_median,
        "positive_dq_shares": totals.positive_dq_shares,
        "exec_shares": totals.exec_shares,
        "depth_shares_per_tick": totals.depth_shares_per_tick,
        "n_bins": N_BINS,
    }
    out = DATA / f"{symbol}_book.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    trade_path = DATA / f"{symbol}_aggtrades.csv"
    with trade_path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["time_us", "price", "qty", "buyer_is_maker"])
        for stamp, price, qty, buyer_is_maker in trades:
            writer.writerow(
                [int(round(stamp * 1_000_000)), f"{price:.8f}", f"{qty:.8f}", int(buyer_is_maker)]
            )
    print(
        f"{symbol}: span {totals.measured_span_s:.2f}s "
        f"spread mean {totals.spread_mean:.4f} median {totals.spread_median:.4f} "
        f"trades {len(trades)} -> {out.name}, {trade_path.name}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, choices=sorted(CLOCK_SHIFT))
    parser.add_argument("--pickle", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    build_symbol(args.symbol, args.pickle, args.zip)


if __name__ == "__main__":
    main()
