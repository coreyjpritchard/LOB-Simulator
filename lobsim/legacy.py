"""The notebook simulator, kept so the old ratio can be rerun.

`calibrated.ipynb` called `numpy.random.seed` and then drew from the `random`
module. Those are different generators, so that seed did not fix the path.
This module seeds `random.Random` and follows the notebook: alpha and mu are
event rates, limit prices are offsets from the mid in log-price, and each
event draws an exponential clock tick before the event type (the clock is not
used for the event-lag variance, but the draw stays so the seed matches).
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass

from sortedcontainers import SortedDict


@dataclass
class _Order:
    id: int
    side: str
    price: float
    qty: float


@dataclass(frozen=True)
class LegacyResult:
    mids: list[float]
    spreads: list[float]
    epsilon: float


class _FloatBook:
    """Float-price book matching OrderBook.mid_price / add_market for the notebook."""

    def __init__(self) -> None:
        self.bids: SortedDict[float, deque[_Order]] = SortedDict()
        self.asks: SortedDict[float, deque[_Order]] = SortedDict()
        self.orders: dict[int, _Order] = {}
        self.ids: list[int] = []
        self._next = 1

    def best_bid(self) -> float:
        return self.bids.peekitem(-1)[0] if self.bids else math.nan

    def best_ask(self) -> float:
        return self.asks.peekitem(0)[0] if self.asks else math.nan

    def mid(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return (self.best_bid() + self.best_ask()) / 2.0

    def spread(self) -> float:
        if not self.bids or not self.asks:
            return math.nan
        return self.best_ask() - self.best_bid()

    def add_limit(self, side: str, price: float, qty: float) -> None:
        oid = self._next
        self._next += 1
        order = _Order(oid, side, price, qty)
        self.orders[oid] = order
        self.ids.append(oid)
        book = self.bids if side == "buy" else self.asks
        book.setdefault(price, deque()).append(order)

    def cancel(self, oid: int) -> None:
        order = self.orders.pop(oid, None)
        if order is None:
            return
        self.ids.remove(oid)
        book = self.bids if order.side == "buy" else self.asks
        queue = book[order.price]
        for i, resting in enumerate(queue):
            if resting.id == oid:
                del queue[i]
                break
        if not queue:
            del book[order.price]

    def add_market(self, side: str, qty: float) -> None:
        book = self.asks if side == "buy" else self.bids
        left = qty
        while left > 0 and book:
            price, queue = book.peekitem(0) if side == "buy" else book.peekitem(-1)
            maker = queue[0]
            take = min(left, maker.qty)
            maker.qty -= take
            left -= take
            if maker.qty <= 0:
                queue.popleft()
                self.orders.pop(maker.id, None)
                self.ids.remove(maker.id)
                if not queue:
                    del book[price]


def run_legacy(
    alpha: float,
    mu: float,
    delta: float,
    sigma: float,
    dp: float,
    n_ticks: int,
    seed: int,
    n_events: int,
    burn_in: int = 0,
) -> LegacyResult:
    rng = random.Random(seed)
    book = _FloatBook()
    epsilon = 2.0 * delta * sigma / mu

    def alpha_total() -> float:
        return 2.0 * alpha * n_ticks

    def one() -> None:
        cancel = delta * len(book.ids)
        total = alpha_total() + mu + cancel
        rng.expovariate(total)
        u = rng.random() * total
        if u < mu:
            side = rng.choice(("buy", "sell"))
            book.add_market(side, sigma)
            return
        if u < mu + alpha_total():
            side = rng.choice(("buy", "sell"))
            best_opp = book.best_ask() if side == "buy" else book.best_bid()
            mid = 0.0 if math.isnan(best_opp) else book.mid()
            offset = rng.randint(1, n_ticks) * dp
            price = mid - offset if side == "buy" else mid + offset
            book.add_limit(side, price, sigma)
            return
        if book.ids:
            book.cancel(rng.choice(book.ids))

    for _ in range(burn_in):
        one()
    mids: list[float] = []
    spreads: list[float] = []
    for _ in range(n_events):
        one()
        mids.append(book.mid())
        spreads.append(book.spread())
    return LegacyResult(mids, spreads, epsilon)


def variance_per_event(values: list[float], lag: int) -> float:
    """Population variance of increments, divided by lag. Skips NaNs."""
    if lag < 1 or lag >= len(values):
        raise ValueError("lag out of range")
    n = 0
    mean = 0.0
    m2 = 0.0
    for i in range(lag, len(values)):
        a, b = values[i], values[i - lag]
        if math.isnan(a) or math.isnan(b):
            continue
        diff = a - b
        n += 1
        mean_next = mean + (diff - mean) / n
        m2 += (diff - mean) * (diff - mean_next)
        mean = mean_next
    if n < 2:
        return float("nan")
    return (m2 / n) / lag
