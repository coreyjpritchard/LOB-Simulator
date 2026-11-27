from lobsim.flow import Diff, flow_from_diffs
from lobsim.measure import Calibration, TradePrint, calibrate


def test_positive_net_is_a_lower_bound_arrival():
    diffs = [
        Diff(0.0, ((10.0, 1.0),), ((11.0, 1.0),)),
        Diff(1.0, ((10.0, 3.0),), ()),
        Diff(2.0, ((10.0, 3.0),), ()),
    ]
    totals = flow_from_diffs(diffs, [], tick=1.0, burn_in_s=0.0, n_bins=4, clock_shift_s=0.0)
    assert totals.positive_dq_shares[0] == 1.0
    assert totals.spread_mean == 1.0


def test_calibration_uses_the_paper_definitions():
    summary = {
        "symbol": "TEST",
        "measured_span_s": 10.0,
        "tick_size": 0.01,
        "positive_dq_shares": [10.0, 0.0],
        "exec_shares": [2.0, 0.0],
        "depth_shares_per_tick": [4.0, 1.0],
        "flow_start_unix": 0.0,
        "flow_end_unix": 10.0,
        "clock_shift_s": 0.0,
        "spread_mean": 0.02,
        "spread_median": 0.01,
        "mid_median": 100.0,
    }
    trades = [
        TradePrint(1.0, 100.0, 3.0, False),
        TradePrint(1.0, 100.0, 1.0, False),
        TradePrint(2.0, 100.01, 6.0, True),
    ]
    cal = calibrate(summary, trades, band=2)
    assert isinstance(cal, Calibration)
    # one cluster of 4 at t=1 (same timestamp and side) and one of 6 at t=2
    assert cal.n_clusters == 2
    assert cal.sigma == 5.0
    assert cal.mu == 1.0  # 10 shares / 10 seconds
    assert cal.alpha == 0.5  # 10 shares over 10s, spread over 2 ticks
    assert cal.pc == 1.0 / (2 * 0.5)
    assert cal.closure_ok
    # adds 1.0/s, executions 0.2/s, occupancy 5 shares
    assert cal.delta == (1.0 - 0.2) / 5.0
    assert cal.epsilon == 2 * cal.delta * cal.sigma / cal.mu
