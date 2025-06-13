from OrderBook import OrderBook
import random
import math

class ZeroIntelligenceLOB:
    def __init__(self, alpha, mu, delta, sigma, dp, snapshot, n_ticks=100):
        # The following three rates are independent poisson processes
        self.alpha = alpha # limit order arrival (shares/price/time)
        self.mu = mu       # market order arrival (shares/time)
        self.delta = delta # cancellation rate (1/time)


        self.sigma = sigma # constant order size (shares) 
        self.dp = dp       # tick size (price) dp -> 0 for continuous price

        self.anchor_price = 0.0 #(float(snapshot['bids'][0][0]) + float(snapshot['asks'][0][0])) / 2
        self.book = OrderBook()
        self.clock = 0.0 # simulation clock

        self.history = []

        self.n_ticks = n_ticks # number of ticks around the mid price to consider for limit orders

        #self._init_fill_book(snapshot)

    @property
    def epsilon(self):
        return 2 * self.delta * self.sigma / self.mu

    @property
    def pc(self):
        return self.mu / (2 * self.alpha)

    @property
    def Nc(self):
        return self.mu / (2 * self.delta)
    
    def _init_fill_book(self, snapshot):
        # initialize the order book with real data to prevent massive spreads at the start
        for price_str, qty_str in snapshot['bids']:
            price = float(price_str)
            price = math.log(price / self.anchor_price)
            qty   = float(qty_str)
            # you may wish to split large qty into multiple σ‐sized orders
            self.book.add_limit('buy',  price, qty)

        for price_str, qty_str in snapshot['asks']:
            price = float(price_str)
            price = math.log(price / self.anchor_price)
            qty   = float(qty_str)
            self.book.add_limit('sell', price, qty)


    def next_event(self):
        lmbda = self.alpha_total() + self.mu + self.delta_total()
        self.clock += random.expovariate(lmbda)
        self.book.clock = self.clock
        u = random.random() * lmbda 

        if u < self.mu:
            self.handle_market()
            #self.record_state("market")
        elif u < self.mu + self.alpha_total():
            self.handle_limit()
            #self.record_state("limit")
        else:
            self.handle_cancel()
            #self.record_state("cancel")

    def price_range(self):
        return self.n_ticks #* self.dp # +- self.n_ticks around the mid price

    def alpha_total(self):
        return 2 * self.alpha * self.price_range()

    def delta_total(self):
        return self.delta * len(self.book.id_map) 

    def handle_market(self):
        side = random.choice(["buy", "sell"]) # random incoming market order
        self.book.add_market(side, self.sigma) # constant order size

    def handle_limit(self):
        side = random.choice(["buy", "sell"]) # random incoming limit order
        best_opp = self.book.best_ask() if side == "buy" else self.book.best_bid()
        
        if math.isnan(best_opp): # book is empty
            mid = self.anchor_price
        else:
            mid = self.book.mid_price()

        offset = random.randint(1, self.n_ticks) * self.dp
        #print(mid, offset)
        if side == "buy":
            price = mid - offset
        else:
            price = mid + offset

        #price = round(max(price, 0.0)) #/self.dp) * self.dp  # prevent negative prices and round to nearest tick size - actually this is log price so no need to round
        self.book.add_limit(side, price, self.sigma)


    def handle_cancel(self):
        # randomly cancel an order
        if not self.book.id_map:
            return
        oid = random.choice(list(self.book.id_map.keys()))
        self.book.cancel_order(oid)

    def record_state(self): #, event_type):
        state = {
            "time": self.clock,
            #"event_type": event_type,
            "best_bid": self.book.best_bid(),
            "best_ask": self.book.best_ask(),
            "mid_price": self.book.mid_price(),
            "spread": self.book.spread(),
            "book_snapshot": self.book.depth_snapshot(levels=self.n_ticks)
        }
        self.history.append(state)
