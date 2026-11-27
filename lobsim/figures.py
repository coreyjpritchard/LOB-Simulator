"""Draw the headline figure and write docs/results.csv.

Seed 42. The recorded path drops a burn-in so the empty book is not in the
variance. Lag 1 and lag 2,500 are event counts, the comparison asked for.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from lobsim.legacy import run_legacy, variance_per_event
from lobsim.load import SYMBOLS, load_legacy, load_summary, load_trades
from lobsim.measure import PRIMARY_BAND, band_table, calibrate
from lobsim.model import run

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SEED = 42
EXTRA_SEEDS = (7, 99)
BURN_IN = 20_000
N_EVENTS = 50_000
LAGS = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1_000, 2_500)
HEADLINE_LAG = 2_500
LEGACY_EVENTS = 10_000
LEGACY_BURN = 2_000

BTC_COLOUR = "#0B3A66"
ETH_COLOUR = "#C46B1A"
SIM_COLOUR = "#5B7C99"


def _var_per_event(mids: np.ndarray, lag: int) -> float:
    diff = mids[lag:] - mids[:-lag]
    diff = diff[np.isfinite(diff)]
    if diff.size < 2:
        return float("nan")
    return float(np.var(diff) / lag)


def _profile(rows: list[list[float]]) -> np.ndarray:
    return np.mean(np.asarray(rows, dtype=float), axis=0)


def _mean_finite(values: list[float]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.nanmean(arr))


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    rows: list[dict[str, str]] = []

    def add(symbol: str, name: str, value: float, unit: str, seed: int = SEED) -> None:
        rows.append(
            {
                "symbol": symbol,
                "name": name,
                "value": f"{value:.10g}",
                "unit": unit,
                "seed": str(seed),
            }
        )

    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    real_depth: dict[str, np.ndarray] = {}
    sim_depth: dict[str, np.ndarray] = {}

    for symbol in SYMBOLS:
        summary = load_summary(symbol)
        trades = load_trades(symbol)
        cal = calibrate(summary, trades, PRIMARY_BAND)
        if not cal.closure_ok:
            raise SystemExit(f"{symbol}: stationary closure failed (cancel rate not positive)")
        label = symbol.upper()
        add(label, "mu", cal.mu, "shares/s")
        add(label, "sigma_mean_cluster", cal.sigma, "shares")
        add(label, "sigma_median_print", cal.sigma_median_print, "shares")
        add(label, "alpha", cal.alpha, "shares/tick/s")
        add(label, "delta", cal.delta, "1/s")
        add(label, "epsilon", cal.epsilon, "1")
        add(label, "pc", cal.pc, "ticks")
        add(label, "asymptotic_depth", cal.asymptotic_depth, "shares/tick")
        add(label, "Nc", cal.characteristic_shares, "shares")
        add(label, "real_spread_mean", cal.spread_mean_ticks, "ticks")
        add(label, "real_spread_median", cal.spread_median_ticks, "ticks")
        add(label, "real_spread_p10", float(summary["spread_p10"]) / cal.tick_size, "ticks")
        add(label, "real_spread_p90", float(summary["spread_p90"]) / cal.tick_size, "ticks")
        add(label, "real_depth_band_mean", cal.occupancy / cal.band_ticks, "shares/tick")
        add(label, "band_ticks", float(cal.band_ticks), "ticks")
        add(label, "measured_span_s", cal.measured_span_s, "s")
        add(label, "mid_median", cal.mid_median, "quote")
        add(label, "n_prints", float(cal.n_prints), "prints")
        add(label, "n_clusters", float(cal.n_clusters), "clusters")

        for alt in band_table(summary, trades):
            add(label, f"pc_band_{alt.band_ticks}", alt.pc, "ticks")
            add(label, f"alpha_band_{alt.band_ticks}", alt.alpha, "shares/tick/s")
            add(label, f"epsilon_band_{alt.band_ticks}", alt.epsilon, "1")

        outcome = run(
            cal.alpha,
            cal.mu,
            cal.delta,
            cal.sigma,
            cal.band_ticks,
            seed=SEED,
            n_events=N_EVENTS,
            burn_in=BURN_IN,
        )
        mids = np.asarray(outcome.mids, dtype=float)
        v1 = _var_per_event(mids, 1)
        v_long = _var_per_event(mids, HEADLINE_LAG)
        ratio = v1 / v_long
        half = len(mids) // 2
        ratio_a = _var_per_event(mids[:half], 1) / _var_per_event(mids[:half], HEADLINE_LAG)
        ratio_b = _var_per_event(mids[half:], 1) / _var_per_event(mids[half:], HEADLINE_LAG)
        lags = np.array([lag for lag in LAGS if lag < len(mids)], dtype=int)
        curve = np.array([_var_per_event(mids, int(lag)) for lag in lags])
        curves[symbol] = (lags, curve)
        profile = _profile(outcome.depth)
        sim_depth[symbol] = profile
        real_depth[symbol] = np.asarray(summary["depth_shares_per_tick"], dtype=float)

        add(label, "sim_spread_mean", _mean_finite(outcome.spreads), "ticks")
        add(label, "sim_depth_mean", float(profile.mean()), "shares/tick")
        add(label, "sim_depth_tick0", float(profile[0]), "shares")
        outer = profile[len(profile) // 2 :]
        add(label, "sim_depth_outer", float(outer.mean()), "shares/tick")
        add(label, "var_per_event_lag1", v1, "tick^2/event")
        add(label, "var_per_event_lag2500", v_long, "tick^2/event")
        add(label, "variance_ratio_lag1_over_lag2500", ratio, "1")
        add(label, "variance_ratio_first_half", ratio_a, "1")
        add(label, "variance_ratio_second_half", ratio_b, "1")
        print(
            f"{label} seed {SEED} burn {BURN_IN} record {N_EVENTS} "
            f"epsilon {cal.epsilon:.6g} pc {cal.pc:.4g} ticks"
        )
        print(
            f"  spread real {cal.spread_mean_ticks:.4g} "
            f"sim {_mean_finite(outcome.spreads):.4g} "
            f"depth theory {cal.asymptotic_depth:.4g} "
            f"real-band {cal.occupancy / cal.band_ticks:.4g} "
            f"sim {float(profile.mean()):.4g} touch real {real_depth[symbol][0]:.4g} "
            f"sim {float(profile[0]):.4g}"
        )
        print(
            f"  ratio lag1/lag2500 {ratio:.6g} "
            f"halves {ratio_a:.4g} {ratio_b:.4g}"
        )
        for extra in EXTRA_SEEDS:
            other = run(
                cal.alpha,
                cal.mu,
                cal.delta,
                cal.sigma,
                cal.band_ticks,
                seed=extra,
                n_events=N_EVENTS,
                burn_in=BURN_IN,
            )
            other_mids = np.asarray(other.mids, dtype=float)
            other_ratio = _var_per_event(other_mids, 1) / _var_per_event(other_mids, HEADLINE_LAG)
            add(label, f"variance_ratio_seed_{extra}", other_ratio, "1", seed=extra)
            print(f"  seed {extra} ratio {other_ratio:.6g}")
        add(label, "n_market_in_record", float(outcome.n_market), "events")
        add(label, "market_events_per_2500", 2500.0 * outcome.n_market / N_EVENTS, "events")
        real_touch = float(real_depth[symbol][0])
        add(label, "real_depth_tick0", real_touch, "shares")

        legacy = load_legacy(symbol)
        for burn, name in ((0, "legacy_ratio_no_burn"), (LEGACY_BURN, "legacy_ratio_burn")):
            old = run_legacy(
                alpha=legacy["alpha"],
                mu=legacy["mu"],
                delta=legacy["delta"],
                sigma=legacy["sigma"],
                dp=legacy["dp"],
                n_ticks=int(legacy["n_ticks"]),
                seed=SEED,
                n_events=LEGACY_EVENTS,
                burn_in=burn,
            )
            lv1 = variance_per_event(old.mids, 1)
            lv2 = variance_per_event(old.mids, HEADLINE_LAG)
            add(label, name, lv1 / lv2, "1")
            print(f"  {name} {lv1 / lv2:.6g} (old epsilon {old.epsilon:.6g})")

    _draw_variance(curves)
    _draw_depth(real_depth, sim_depth)
    path = DOCS / "results.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "name", "value", "unit", "seed"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {DOCS / 'variance_per_event.png'}")
    print(f"wrote {DOCS / 'depth_profile.png'}")
    print(f"wrote {path}")


def _style() -> None:
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.labelsize": 13,
            "legend.fontsize": 11,
            "axes.linewidth": 0.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
        }
    )


def _draw_variance(curves: dict[str, tuple[np.ndarray, np.ndarray]]) -> None:
    _style()
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for symbol, colour in (("btcusdt", BTC_COLOUR), ("ethusdt", ETH_COLOUR)):
        lags, curve = curves[symbol]
        ax.plot(lags, curve, marker="o", ms=4.5, lw=1.8, color=colour, label=symbol.upper())
    ax.set_xscale("log")
    ax.set_xlabel("lag (events)")
    ax.set_ylabel("variance per event (tick²)")
    ax.legend(frameon=False)
    fig.savefig(DOCS / "variance_per_event.png")
    plt.close(fig)


def _draw_depth(real: dict[str, np.ndarray], sim: dict[str, np.ndarray]) -> None:
    _style()
    fig, axes = plt.subplots(2, 1, figsize=(6.4, 6.4), sharex=True)
    for ax, symbol, colour in (
        (axes[0], "btcusdt", BTC_COLOUR),
        (axes[1], "ethusdt", ETH_COLOUR),
    ):
        observed = real[symbol][:15]
        ax.plot(
            np.arange(len(observed)),
            observed,
            marker="o",
            ms=4,
            lw=1.6,
            color=colour,
            label="Binance",
        )
        modelled = sim[symbol]
        ax.plot(
            np.arange(len(modelled)),
            modelled,
            marker="s",
            ms=4,
            lw=1.6,
            color=SIM_COLOUR,
            label="simulation",
        )
        ax.set_ylabel("shares per tick")
        ax.legend(frameon=False, title=symbol.upper())
    axes[1].set_xlabel("ticks from the mid")
    fig.savefig(DOCS / "depth_profile.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
