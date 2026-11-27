"""Price-time priority limit order book on an integer tick grid."""

from collections import deque
from dataclasses import dataclass

from sortedcontainers import SortedDict


@dataclass
class Order:
    id: int
    side: str
    price: int
    qty: float


class Book:
    def __init__(self) -> None:
        self.bids: SortedDict[int, deque[Order]] = SortedDict()
        self.asks: SortedDict[int, deque[Order]] = SortedDict()
        self.orders: dict[int, Order] = {}
        self._ids: list[int] = []
        self._pos: dict[int, int] = {}
        self._next_id = 1

    @property
    def n_orders(self) -> int:
        return len(self._ids)

    def best_bid(self) -> int | None:
        if not self.bids:
            return None
        return int(self.bids.peekitem(-1)[0])

    def best_ask(self) -> int | None:
        if not self.asks:
            return None
        return int(self.asks.peekitem(0)[0])

    def spread(self) -> float | None:
        bid, ask = self.best_bid(), self.best_ask()
        if bid is None or ask is None:
            return None
        return float(ask - bid)

    def mid(self) -> float | None:
        bid, ask = self.best_bid(), self.best_ask()
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2.0

    def add_limit(self, side: str, price: int, qty: float) -> int:
        oid = self._next_id
        self._next_id += 1
        order = Order(oid, side, int(price), float(qty))
        self.orders[oid] = order
        self._pos[oid] = len(self._ids)
        self._ids.append(oid)
        book = self.bids if side == "buy" else self.asks
        book.setdefault(order.price, deque()).append(order)
        return oid

    def _drop_id(self, oid: int) -> None:
        i = self._pos.pop(oid)
        last = self._ids.pop()
        if i < len(self._ids):
            self._ids[i] = last
            self._pos[last] = i

    def cancel(self, oid: int) -> bool:
        order = self.orders.pop(oid, None)
        if order is None:
            return False
        self._drop_id(oid)
        book = self.bids if order.side == "buy" else self.asks
        queue = book[order.price]
        for i, resting in enumerate(queue):
            if resting.id == oid:
                del queue[i]
                break
        if not queue:
            del book[order.price]
        return True

    def random_id(self, rng) -> int | None:
        if not self._ids:
            return None
        return self._ids[rng.randrange(len(self._ids))]

    def add_market(self, side: str, qty: float) -> float:
        """Walk the opposite side. Returns the unfilled remainder."""
        book = self.asks if side == "buy" else self.bids
        left = float(qty)
        while left > 1e-12 and book:
            price, queue = book.peekitem(0) if side == "buy" else book.peekitem(-1)
            maker = queue[0]
            take = min(left, maker.qty)
            maker.qty -= take
            left -= take
            if maker.qty <= 1e-12:
                queue.popleft()
                self.orders.pop(maker.id, None)
                self._drop_id(maker.id)
                if not queue:
                    del book[price]
        return left

    def depth_by_distance(self, n_ticks: int) -> tuple[list[float], list[float]] | None:
        """Shares on each side in tick bins 0, 1, ... measured from the mid."""
        mid = self.mid()
        if mid is None:
            return None
        bids = [0.0] * n_ticks
        asks = [0.0] * n_ticks
        for price, queue in self.bids.items():
            dist = int((mid - price) + 1e-9)
            if 0 <= dist < n_ticks:
                bids[dist] += sum(order.qty for order in queue)
        for price, queue in self.asks.items():
            dist = int((price - mid) + 1e-9)
            if 0 <= dist < n_ticks:
                asks[dist] += sum(order.qty for order in queue)
        return bids, asks
