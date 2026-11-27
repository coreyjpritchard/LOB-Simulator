"""Smith, Farmer, Gillemot and Krishnamurthy (2003) zero-intelligence book.

Prices are integer ticks. The three flows are independent Poisson processes:

- limit orders, density alpha shares per tick per unit time on each side,
  placed uniformly on the n_ticks ticks strictly inside the opposite best quote;
- market orders, total share rate mu, each of size sigma, buy or sell with
  equal probability;
- cancellation of a whole resting order at rate delta.

With those units the paper's scales are

- granularity epsilon = 2 * delta * sigma / mu (Table II);
- characteristic price pc = mu / (2 * alpha), the dimensional estimate of the
  spread (the text's argument that limit flow inside the spread balances
  market orders);
- asymptotic depth d = alpha / delta shares per tick (Table IV).

Nc = mu / (2 * delta) is a characteristic number of shares, not a depth.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from lobsim.book import Book


@dataclass(frozen=True)
class RunResult:
    mids: list[float]
    times: list[float]
    spreads: list[float]
    depth: list[list[float]]
    n_market: int
    n_limit: int
    n_cancel: int


class ZeroIntelligence:
    def __init__(
        self,
        alpha: float,
        mu: float,
        delta: float,
        sigma: float,
        n_ticks: int,
        rng: random.Random,
    ) -> None:
        if min(alpha, mu, delta, sigma) <= 0:
            raise ValueError("alpha, mu, delta and sigma must be positive")
        if n_ticks < 1:
            raise ValueError("n_ticks must be at least 1")
        self.alpha = float(alpha)
        self.mu = float(mu)
        self.delta = float(delta)
        self.sigma = float(sigma)
        self.n_ticks = int(n_ticks)
        self.rng = rng
        self.book = Book()
        self.time = 0.0

    @property
    def epsilon(self) -> float:
        return 2.0 * self.delta * self.sigma / self.mu

    @property
    def pc(self) -> float:
        """Dimensional spread mu / (2 alpha), in ticks."""
        return self.mu / (2.0 * self.alpha)

    @property
    def asymptotic_depth(self) -> float:
        """Table IV: d = alpha / delta, shares per tick."""
        return self.alpha / self.delta

    @property
    def characteristic_shares(self) -> float:
        """Table II: Nc = mu / (2 delta). Not a depth."""
        return self.mu / (2.0 * self.delta)

    def _rates(self) -> tuple[float, float, float]:
        limit = 2.0 * (self.alpha / self.sigma) * self.n_ticks
        market = self.mu / self.sigma
        cancel = self.delta * self.book.n_orders
        return limit, market, cancel

    def step(self) -> str:
        limit, market, cancel = self._rates()
        total = limit + market + cancel
        self.time += self.rng.expovariate(total)
        u = self.rng.random() * total
        if u < market:
            self._market()
            return "market"
        if u < market + limit:
            self._limit()
            return "limit"
        self._cancel()
        return "cancel"

    def _market(self) -> None:
        side = "buy" if self.rng.random() < 0.5 else "sell"
        self.book.add_market(side, self.sigma)

    def _limit(self) -> None:
        if self.rng.random() < 0.5:
            ask = self.book.best_ask()
            upper = 0 if ask is None else ask
            price = upper - self.rng.randrange(1, self.n_ticks + 1)
            self.book.add_limit("buy", price, self.sigma)
        else:
            bid = self.book.best_bid()
            lower = 0 if bid is None else bid
            price = lower + self.rng.randrange(1, self.n_ticks + 1)
            self.book.add_limit("sell", price, self.sigma)

    def _cancel(self) -> None:
        oid = self.book.random_id(self.rng)
        if oid is not None:
            self.book.cancel(oid)


def run(
    alpha: float,
    mu: float,
    delta: float,
    sigma: float,
    n_ticks: int,
    seed: int,
    n_events: int,
    burn_in: int,
    depth_every: int = 50,
) -> RunResult:
    """Burn `burn_in` events, then record `n_events` mids. Seed is `random.Random(seed)`."""
    model = ZeroIntelligence(alpha, mu, delta, sigma, n_ticks, random.Random(seed))
    for _ in range(burn_in):
        model.step()
    mids: list[float] = []
    times: list[float] = []
    spreads: list[float] = []
    depth: list[list[float]] = []
    n_market = n_limit = n_cancel = 0
    for i in range(n_events):
        kind = model.step()
        if kind == "market":
            n_market += 1
        elif kind == "limit":
            n_limit += 1
        else:
            n_cancel += 1
        mid = model.book.mid()
        spread = model.book.spread()
        mids.append(float("nan") if mid is None else mid)
        times.append(model.time)
        spreads.append(float("nan") if spread is None else spread)
        if depth_every and i % depth_every == 0:
            prof = model.book.depth_by_distance(n_ticks)
            if prof is not None:
                bids, asks = prof
                depth.append([(b + a) / 2.0 for b, a in zip(bids, asks, strict=True)])
    return RunResult(mids, times, spreads, depth, n_market, n_limit, n_cancel)
