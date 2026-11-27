"""Turn a reconstructed book and a trade print into Smith et al. parameters.

The capture is a 100 ms diff of absolute level quantities, not a message per
order. Gross adds and cancels inside one bin are not observed. What is observed
is the positive part of the net quantity change. That understates arrivals.

Parameters used for the run, over a stated band of ticks on each side of the mid:

- mu: share volume of aggTrades per second (Vision trades);
- sigma: mean size of prints that share a timestamp and an aggressor side,
  so mu / sigma is that print-cluster rate;
- alpha: lower-bound arrival density, (positive net shares per second) / band,
  one side, shares per tick per second;
- delta: from the stationary closure cancel_rate = add_rate - execution_rate,
  then delta = cancel_rate / shares standing in the band.

The closure makes alpha / delta equal the average depth in the band, up to the
small execution term. Depth versus alpha / delta is therefore not an independent
test. The spread versus mu / (2 alpha) is independent of that closure.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

PRIMARY_BAND = 10
SENSITIVITY_BANDS = (1, 5, 10, 20)


@dataclass(frozen=True)
class TradePrint:
    time: float
    price: float
    qty: float
    buyer_is_maker: bool


@dataclass(frozen=True)
class Calibration:
    symbol: str
    band_ticks: int
    mu: float
    sigma: float
    sigma_median_print: float
    n_prints: int
    n_clusters: int
    alpha: float
    delta: float
    add_rate: float
    exec_rate: float
    occupancy: float
    spread_mean_ticks: float
    spread_median_ticks: float
    tick_size: float
    mid_median: float
    measured_span_s: float
    closure_ok: bool

    @property
    def epsilon(self) -> float:
        return 2.0 * self.delta * self.sigma / self.mu

    @property
    def pc(self) -> float:
        return self.mu / (2.0 * self.alpha)

    @property
    def asymptotic_depth(self) -> float:
        return self.alpha / self.delta

    @property
    def characteristic_shares(self) -> float:
        return self.mu / (2.0 * self.delta)


def cluster_sizes(trades: list[TradePrint]) -> list[float]:
    """Sum qty of aggTrades that share an exchange timestamp and an aggressor side."""
    buckets: dict[tuple[int, bool], float] = defaultdict(float)
    for trade in trades:
        # Vision timestamps are microseconds. Cluster identical ones.
        key = (int(round(trade.time * 1_000_000)), trade.buyer_is_maker)
        buckets[key] += trade.qty
    return list(buckets.values())


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _median(xs: list[float]) -> float:
    ordered = sorted(xs)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def calibrate(
    summary: dict,
    trades: list[TradePrint],
    band: int = PRIMARY_BAND,
) -> Calibration:
    span = float(summary["measured_span_s"])
    tick = float(summary["tick_size"])
    adds = [float(x) for x in summary["positive_dq_shares"][:band]]
    execs = [float(x) for x in summary["exec_shares"][:band]]
    depth = [float(x) for x in summary["depth_shares_per_tick"][:band]]
    add_rate = sum(adds) / span
    exec_rate = sum(execs) / span
    occupancy = sum(depth)
    alpha = add_rate / band
    cancel_rate = add_rate - exec_rate
    closure_ok = cancel_rate > 0 and occupancy > 0 and alpha > 0
    delta = cancel_rate / occupancy if closure_ok else float("nan")

    start = float(summary["flow_start_unix"])
    end = float(summary["flow_end_unix"])
    # book_ts - trade_ts, estimated from large prints. Shift prints onto the book clock.
    shift = float(summary["clock_shift_s"])
    in_flow = [
        trade
        for trade in trades
        if start <= trade.time + shift <= end
    ]
    if not in_flow:
        raise ValueError(f"no trades in the flow window for {summary['symbol']}")
    window = end - start
    mu = sum(trade.qty for trade in in_flow) / window
    clusters = cluster_sizes(in_flow)
    sigma = _mean(clusters)
    sigma_median = _median([trade.qty for trade in in_flow])
    return Calibration(
        symbol=str(summary["symbol"]),
        band_ticks=band,
        mu=mu,
        sigma=sigma,
        sigma_median_print=sigma_median,
        n_prints=len(in_flow),
        n_clusters=len(clusters),
        alpha=alpha,
        delta=delta,
        add_rate=add_rate,
        exec_rate=exec_rate,
        occupancy=occupancy,
        spread_mean_ticks=float(summary["spread_mean"]) / tick,
        spread_median_ticks=float(summary["spread_median"]) / tick,
        tick_size=tick,
        mid_median=float(summary["mid_median"]),
        measured_span_s=span,
        closure_ok=closure_ok and math.isfinite(delta),
    )


def band_table(summary: dict, trades: list[TradePrint]) -> list[Calibration]:
    return [calibrate(summary, trades, band) for band in SENSITIVITY_BANDS]
