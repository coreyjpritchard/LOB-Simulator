from sortedcontainers import SortedDict
from collections import deque
from dataclasses import dataclass, field
import itertools, random, math
from typing import Literal, Deque

@dataclass(slots=True)
class Order:
    id:     int
    side:   Literal["buy", "sell"]
    price:  float
    qty:    int      # always σ in the ZI model
    ts:     float    # simulator clock – for FIFO

@dataclass(slots=True)
class Trade:
    buy_id:  int
    sell_id: int
    price:   float
    qty:     int
    ts:      float


class OrderBook:
    def __init__(self, anchor_price=0.0):
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.id_map = {}
        self._id_gen = itertools.count(1)
        self.clock = 0.0
        self.anchor_price = anchor_price

    def _match(self, taker_side, qty):
        trades = []
        book = self.asks if taker_side == "buy" else self.bids

        while qty > 0 and book:
            price, queue = (book.peekitem(0) if taker_side == "buy" else book.peekitem(-1)) # smallest ask for buy, largest bid for sell
            maker = queue[0]
            
            trade_size = min(qty, maker.qty)

            trades.append(Trade(
                buy_id = maker.id if taker_side == "sell" else -1,
                sell_id = maker.id if taker_side == "buy" else -1,
                price = price,
                qty = trade_size,
                ts = self.clock
            ))

            maker.qty -= trade_size
            qty -= trade_size

            if maker.qty == 0: # order fully filled
                queue.popleft()
                self.id_map.pop(maker.id, None)
                if not queue:
                    book.pop(price, None) # remove empty price level

        return trades

    def _insert(self, order):
        book = self.bids if order.side == "buy" else self.asks
        q = book.setdefault(order.price, deque())
        q.append(order)
        self.id_map[order.id] = (order.price, order.side)

    def add_limit(self, side, price, qty):
        oid = next(self._id_gen)
        self._insert(Order(oid, side, price, qty, self.clock))
        return oid
    
    def add_market(self, side, qty):
        return self._match(side, qty)
    
    def cancel_order(self, oid):
        if oid not in self.id_map:
            return False
        
        price, side = self.id_map.pop(oid)
        book = self.bids if side == "buy" else self.asks
        q = book[price]

        for i, o in enumerate(q):
            if o.id == oid:
                del q[i]
                if not q:
                    book.pop(price)
                return True
        return False
    
    def best_bid(self):
        return self.bids.peekitem(-1)[0] if self.bids else math.nan

    def best_ask(self):
        return self.asks.peekitem(0)[0] if self.asks else math.nan
    
    def spread(self):
        return self.best_ask() - self.best_bid() if self.bids and self.asks else math.nan
    
    def mid_price(self):
        if not self.bids or not self.asks:
            return self.anchor_price
        return (self.best_bid() + self.best_ask()) / 2
    
    def depth_snapshot(self, levels=100):
        snapshot = {
            "bids": [],
            "asks": []
        }

        # Top N bids (descending)
        for i, (price, q) in enumerate(reversed(self.bids.items())):
            if i >= levels: break
            qty = sum(order.qty for order in q)
            snapshot["bids"].append((price, qty))

        # Top N asks (ascending)
        for i, (price, q) in enumerate(self.asks.items()):
            if i >= levels: break
            qty = sum(order.qty for order in q)
            snapshot["asks"].append((price, qty))

        return snapshot
