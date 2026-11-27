from lobsim.load import SYMBOLS, load_summary, load_trades
from lobsim.measure import PRIMARY_BAND, calibrate


def test_committed_windows_calibrate():
    for symbol in SYMBOLS:
        summary = load_summary(symbol)
        trades = load_trades(symbol)
        cal = calibrate(summary, trades, PRIMARY_BAND)
        assert cal.closure_ok
        assert cal.mu > 0
        assert cal.pc > 0
        assert summary["spread_median"] == 0.01
        assert trades
