# LOB Simulator

**On a Smith, Farmer, Gillemot and Krishnamurthy (2003) book calibrated to Binance ETH/USDT, seed 42, the mid-price variance per event at lag 1 is 3.30 times the value at lag 2,500 (20,000 events burned in, 50,000 recorded). Seeds 7 and 99 give 3.77 and 4.67. The reported figure of about 400 times is the empty book at start-up: the old notebook path, with `random` seeded at 42 and no burn-in, gives 416.6, and 2.36 once 2,000 events are dropped. Granularity is ε = 0.185 for BTC/USDT and 0.282 for ETH/USDT. The old script's 0.00102 and 0.0122 are not that parameter.**

The capture is Binance spot on 13 June 2025, BTC/USDT 14:10:57–14:15:57 UTC and ETH/USDT 17:27:18–17:32:18 UTC, two different five-minute windows. One tick is 0.01 USDT. Full precision is in [`docs/results.csv`](docs/results.csv).

![Variance per event of the simulated mid against event lag, on a log lag axis. ETH/USDT falls from about 0.006 tick squared at lag 1 to under 0.002 at lag 2,500. BTC/USDT falls from about 0.0022 to about 0.0006. Both are still sloping down at the right edge.](docs/variance_per_event.png)

**How to read this.** The vertical axis is the variance of the simulated mid-price change, divided by the lag in events, after the burn-in. The mid is in ticks (1 tick = 0.01 USDT) and the horizontal axis is the lag, on a log scale. The takeaway is that this slope falls by a factor of 3.30 on ETH/USDT and 3.74 on BTC/USDT between lag 1 and lag 2,500 at seed 42, which is a mild version of the negative autocorrelation in Smith et al. (2003), figure 11: a market order shoves the mid, and later limit orders inside the spread pull it back. Most events do not move the mid. In this run a lag of 2,500 events contains 88 ETH market orders and 77 BTC market orders.

**What it does not show.** It is not a 400-fold gap, and it is not measured on Binance prices. The curve is still falling at lag 2,500, so this is not the paper's long-time diffusion rate. The ratio moves with the seed (ETH 3.30, 3.77, 4.67) and between the two halves of the seed-42 path (3.50 and 3.86).

## Results

Seed 42 unless a row says otherwise. Simulator: 20,000 events discarded, then 50,000 recorded. Calibration band: 10 ticks on each side of the mid. Dated from the capture above.

| | BTC/USDT | ETH/USDT |
|---|---:|---:|
| ε = 2δσ/μ | 0.185 | 0.282 |
| Old script's ε (not used) | 0.001024 | 0.01218 |
| μ, trade shares per second | 0.282 | 7.025 |
| σ, mean same-timestamp cluster | 0.0377 | 0.828 |
| Median print (not the σ used) | 0.00046 | 0.0084 |
| α, shares per tick per second | 0.232 | 5.052 |
| δ, per second | 0.690 | 1.199 |
| Real spread, mean / median (ticks) | 1.45 / 1 | 1.02 / 1 |
| Dimensional spread pc = μ/(2α) (ticks) | 0.607 | 0.695 |
| Simulated mean spread (ticks) | 1.08 | 1.20 |
| Asymptotic depth α/δ (shares per tick) | 0.337 | 4.21 |
| Real depth, mean over the 10 ticks | 0.327 | 4.12 |
| Simulated mean depth | 0.315 | 3.86 |
| Real / simulated depth on the inside tick | 3.19 / 0.165 | 30.3 / 2.08 |
| Nc = μ/(2δ), a share count, not a depth | 0.204 | 2.93 |
| Variance ratio, lag 1 / lag 2,500 | 3.74 | 3.30 |
| Same ratio, seeds 7 and 99 | 3.43 and 2.65 | 3.77 and 4.67 |
| Old code, no burn-in, 10,000 events | 874 | 416.6 |
| Old code, 2,000 events burned in | 3.02 | 2.36 |

The 10th and 90th percentiles of the real spread are one tick on both symbols. The BTC mean of 1.45 ticks is a thin tail of wider spreads, not the typical book.

pc depends on how wide a band α is averaged over, because arrivals are not uniform. BTC pc is 0.062, 0.306, 0.607 and 1.20 ticks at bands of 1, 5, 10 and 20 ticks. ETH pc is 0.106, 0.417, 0.695 and 1.11. The headline uses 10 ticks. ε barely moves with the band (BTC stays at 0.185; ETH goes from 0.249 to 0.286).

![Two panels of shares per tick against distance from the mid. On both BTC/USDT and ETH/USDT the Binance book is a spike on the inside tick, about 3.2 BTC and 30 ETH, then almost empty. The simulation is a low hump near 0.3 BTC and 4 ETH across ten ticks, and does not have the spike.](docs/depth_profile.png)

**How to read this.** The vertical axis is shares resting on one side, Binance averaged over the measured window and the simulation averaged over the recorded path. Distance is in ticks from the mid. The takeaway is that the real book keeps its size on the best quote, while the simulated book is nearly flat. The mechanism is the placement rule: the model draws limit orders uniformly on ten ticks, so depth sits near the paper's asymptotic value α/δ, whereas Binance arrivals in this window are concentrated at the touch.

**What it does not show.** It does not confirm the depth scaling. Average depth over the ten ticks is close to α/δ because δ was set from those standing shares and the measured arrivals (see Method). The shape is the part that can fail, and it fails: the inside tick holds 3.19 BTC against a simulated 0.16, and 30.3 ETH against 2.08. The simulated curve stops at nine ticks because that is the placement window.

## What is in the repository

```
lobsim/book.py            price-time priority book on an integer tick grid
lobsim/model.py           Smith et al. (2003) zero-intelligence book
lobsim/measure.py         μ, σ, α, δ, ε, pc and depth from the committed summaries
lobsim/flow.py            rebuild those summaries from a local diff capture
lobsim/legacy.py          the old notebook path, seeded, so the 417 can be rerun
lobsim/figures.py         docs/variance_per_event.png, docs/depth_profile.png, docs/results.csv
lobsim/build_inputs.py    optional: local pickle + Vision zip -> data/
scripts/capture_binance.py  record a partial-book stream into data/raw/ (gitignored)
data/                     trade extracts, book summaries, old parameter files
tests/
calibrated.ipynb          short demo; it does not regenerate the table
```

## Reproduce

With [uv](https://docs.astral.sh/uv/) and `make` (Python 3.11 or newer, versions in `uv.lock`):

```bash
uv sync
make reproduce
```

`make reproduce` runs `uv sync --extra dev`, `pytest`, then `python -m lobsim.figures`. That rewrites the two figures and `docs/results.csv` from the committed summaries, the trade extracts and seed 42. It does not download anything and it does not need the raw book. On this machine it takes a few seconds.

The notebook is a short look at the objects: `uv run python -c "import lobsim"`, or open `calibrated.ipynb`. The numbers in the table are not computed there.

## Method

The model is the zero-intelligence continuous double auction of Smith, Farmer, Gillemot and Krishnamurthy (2003). Three independent Poisson flows: limit orders at density α shares per tick per unit time on each side, placed uniformly on the `n_ticks` ticks strictly inside the opposite best quote; market orders at total share rate μ, each of size σ, buy or sell with equal probability; each resting order cancelled whole at rate δ. Prices here are integer ticks. Over a few ticks that is the same grid as the paper's log-price, up to the constant factor (tick / mid).

The scales used in the table are the paper's, not the names in the old code:

- ε = 2δσ/μ, the nondimensional order size (Table II).
- pc = μ/(2α), the characteristic price. The text's balance of limit flow inside the spread against market orders gives a spread of this size. Table IV writes the spread as (μ/α) times a function of ε and of the tick, and figure 10 puts the mean near 0.45 pc plus a weak slope when the tick is negligible. Nc = μ/(2δ) is a characteristic number of shares. It is not a depth. The old code exposed Nc and called the surrounding discussion "depth".
- Asymptotic depth d = α/δ shares per tick (Table IV). It is exact for an infinite book with no tick, far from the mid, where market orders do not reach.

Calibration, over the 10-tick band, after a 45-second burn-in of the reconstructed book (about 255 seconds remain):

- μ is Vision aggTrade share volume per second in that flow window.
- σ is the mean size of prints that share an exchange timestamp and an aggressor side, so μ/σ is the rate of those clusters. A sweep across prices at one timestamp is one cluster.
- α is the positive part of the 100 ms net quantity change, per second, divided by the width of the band. An add and a cancel in the same bin at the same price are invisible, so α is a lower bound and pc is an upper bound on the dimensional spread.
- δ comes from the stationary closure: cancellation share rate = arrival share rate − execution share rate, then divided by shares standing in the band. Up to that execution term, α/δ equals the average depth in the band. The real-versus-theory depth column is that identity, not a test. The simulated depth is a test, and the shape is the one that fails.

Executions are lined up with a clock shift of −0.59 s (BTC) and −0.35 s (ETH), the lag of book receipt time minus trade time that best matches large prints to a drop at that price. Arrivals do not use the shift. Executions are small next to arrivals (about 17 BTC against 592 BTC of positive net change in the band, and 296 ETH against 12,885), so the shift does not drive ε or pc.

The old files in `data/legacy/` counted new price-quantity pairs in each diff as if the message were a snapshot, took μ as the rate of mid changes, set δ = α/2, and put σ in the numerator of ε. Rerunning that arithmetic reproduces 0.001024 and 0.01218. Those are the figures that were previously quoted. They are not estimates of 2δσ/μ for this book.

## Data

Trade prints are an extract of Binance Vision aggTrades for 13 June 2025, under the Vision Dataset Terms (CC BY-NC-SA 4.0), with attribution to Binance Vision. Details, zip URLs and the checksum check are in [`data/PROVENANCE.txt`](data/PROVENANCE.txt).

The book summaries are 40-bin aggregates from a diff-depth websocket capture already made on that day. The raw messages are not in the tree. Live REST from the machine that produced this table returned HTTP 451, so the book was not recaptured. `scripts/capture_binance.py` records a partial-book stream (`<symbol>@depth20@100ms`), which is an actual top-of-book snapshot each message, to `data/raw/` (gitignored). Rebuilding the aggregates from a local diff pickle and a Vision zip is `python -m lobsim.build_inputs`.

## Honest limits

- Order flow is Poisson, orders have one fixed size, and there are no informed traders. The print-size distribution is heavy: the median BTC print is 0.00046 BTC against a mean cluster of 0.0377. ε scales with σ, so a different convention for "an order" moves ε. The σ used here is the one that preserves both share volume and the cluster count.
- One venue, Binance spot, and about four minutes of book after the burn-in. BTC and ETH are not the same five minutes.
- The capture is 100 ms diffs of absolute quantities, not an order-by-order feed. Gross arrivals and cancellations inside a bin are not identified. α is a lower bound.
- Arrivals are not uniform in price. pc changes by more than an order of magnitude between a 1-tick band and a 20-tick band. The model then places orders uniformly on the 10-tick band it was given, which the depth figure shows is the wrong shape.
- The tick is larger than pc (pc is 0.61 and 0.70 ticks). The continuous spread formula is outside the regime of the paper's figure 10. The simulated spread sits at 1.08 and 1.20 ticks, above pc, which is what a one-tick floor does. It is not a fit to the 0.45 pc curve.
- Even with α understated, the real mean spread (1.45 and 1.02 ticks) is wider than pc. A higher true α would make pc smaller and the gap larger.
- Average depth versus α/δ is not an independent check. The inside of the book is.
- The variance ratio has not settled by lag 2,500, and it moves with the seed. Quoting 3.30 without the other seeds overstates how sharp it is.
- The old notebook called `numpy.random.seed`. The simulator drew from the `random` module, so that line did not fix the path. The 417 above seeds `random` at 42 on the old rules.
- No fees, no latency, no other venues, and cancellations remove a whole order rather than one share.

## References

- Smith, Farmer, Gillemot, Krishnamurthy (2003). Statistical theory of the continuous double auction. Quantitative Finance 3(6). doi:10.1088/1469-7688/3/6/307

MIT licence.

Built with the help of AI coding tools; all results are reproducible from the scripts in this repo.
