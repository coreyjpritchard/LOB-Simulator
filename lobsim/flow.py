"""Reconstruct a book from Binance diff-depth messages and tally net flow.

A diff message lists absolute quantities at the levels that changed. Quantity
zero deletes a level. Levels that never change stay invisible, so tallies start
after a burn-in and only inside a fixed number of ticks of the mid.

`positive_dq_shares[k]` sums positive net quantity changes on tick k, averaged
across the bid and the ask. It is a lower bound on share arrivals: an add and
a cancel in the same 100 ms bin at the same price are invisible.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Diff:
    time: float
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class FlowTotals:
    measured_span_s: float
    flow_start: float
    flow_end: float
    spread_mean: float
    spread_median: float
    spread_p10: float
    spread_p90: float
    mid_median: float
    n_spreads: int
    positive_dq_shares: list[float]
    exec_shares: list[float]
    depth_shares_per_tick: list[float]


def _percentile(sorted_values: list[float], q: float) -> float:
    pos = (len(sorted_values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    weight = pos - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def _tally(old, new, executed, add_side, exe_side, mid, n_bins, bid_side: bool) -> None:
    for price in set(old) | set(new) | set(executed):
        dist = int((mid - price) + 1e-9) if bid_side else int((price - mid) + 1e-9)
        if not 0 <= dist < n_bins:
            continue
        dq = new.get(price, 0.0) - old.get(price, 0.0)
        if dq > 0:
            add_side[dist] += dq
        ex = executed.get(price, 0.0)
        if ex:
            exe_side[dist] += ex


def _tick_key(price: float, tick: float) -> int:
    return int(round(price / tick))


def _apply(book: dict[int, float], updates: tuple[tuple[float, float], ...], tick: float) -> None:
    for price, qty in updates:
        key = _tick_key(price, tick)
        if qty == 0.0:
            book.pop(key, None)
        else:
            book[key] = qty


def flow_from_diffs(
    diffs: list[Diff],
    trades: list[tuple[float, float, float, bool]],
    tick: float,
    burn_in_s: float,
    n_bins: int,
    clock_shift_s: float,
) -> FlowTotals:
    """`trades` are (exchange_time, price, qty, buyer_is_maker).

    `clock_shift_s` is book_time - trade_time. A print is placed on the book
    clock at exchange_time + clock_shift_s.
    """
    if len(diffs) < 2:
        raise ValueError("need at least two diffs")
    bids: dict[int, float] = {}
    asks: dict[int, float] = {}
    burn = diffs[0].time + burn_in_s
    add = [[0.0] * n_bins for _ in range(2)]
    exe = [[0.0] * n_bins for _ in range(2)]
    depth_sum = [0.0] * n_bins
    depth_n = 0
    spreads: list[float] = []
    mids: list[float] = []
    ordered_trades = sorted(trades, key=lambda row: row[0])
    ti = 0
    flow_start: float | None = None
    flow_end: float | None = None

    for index, diff in enumerate(diffs):
        old_bids = dict(bids)
        old_asks = dict(asks)
        _apply(bids, diff.bids, tick)
        _apply(asks, diff.asks, tick)
        if index == 0 or not old_bids or not old_asks:
            continue
        prev_t = diffs[index - 1].time
        if diff.time < burn or not (0.0 < diff.time - prev_t < 2.0):
            continue
        bb = max(old_bids)
        ba = min(old_asks)
        if ba <= bb:
            continue
        mid = (bb + ba) / 2.0
        spreads.append((ba - bb) * tick)
        mids.append(mid * tick)
        for price, qty in old_bids.items():
            dist = int(mid - price + 1e-9)
            if 0 <= dist < n_bins:
                depth_sum[dist] += qty / 2.0
        for price, qty in old_asks.items():
            dist = int(price - mid + 1e-9)
            if 0 <= dist < n_bins:
                depth_sum[dist] += qty / 2.0
        depth_n += 1

        exec_bid: dict[int, float] = defaultdict(float)
        exec_ask: dict[int, float] = defaultdict(float)
        while ti < len(ordered_trades) and ordered_trades[ti][0] + clock_shift_s <= diff.time:
            trade_time, price, qty, buyer_is_maker = ordered_trades[ti]
            local = trade_time + clock_shift_s
            if local > prev_t:
                key = _tick_key(price, tick)
                if buyer_is_maker:
                    exec_bid[key] += qty
                else:
                    exec_ask[key] += qty
            ti += 1

        _tally(old_bids, bids, exec_bid, add[0], exe[0], mid, n_bins, bid_side=True)
        _tally(old_asks, asks, exec_ask, add[1], exe[1], mid, n_bins, bid_side=False)
        flow_end = diff.time
        if flow_start is None:
            flow_start = prev_t

    if not spreads or flow_start is None or flow_end is None or depth_n == 0:
        raise ValueError("flow window is empty; burn-in left no two-sided book")
    ordered_spreads = sorted(spreads)
    ordered_mids = sorted(mids)
    return FlowTotals(
        measured_span_s=flow_end - flow_start,
        flow_start=flow_start,
        flow_end=flow_end,
        spread_mean=sum(spreads) / len(spreads),
        spread_median=_percentile(ordered_spreads, 0.5),
        spread_p10=_percentile(ordered_spreads, 0.1),
        spread_p90=_percentile(ordered_spreads, 0.9),
        mid_median=_percentile(ordered_mids, 0.5),
        n_spreads=len(spreads),
        positive_dq_shares=[(add[0][i] + add[1][i]) / 2.0 for i in range(n_bins)],
        exec_shares=[(exe[0][i] + exe[1][i]) / 2.0 for i in range(n_bins)],
        depth_shares_per_tick=[depth_sum[i] / depth_n for i in range(n_bins)],
    )
