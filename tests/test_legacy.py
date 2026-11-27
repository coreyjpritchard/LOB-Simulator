from lobsim.legacy import run_legacy, variance_per_event
from lobsim.load import load_legacy


def test_eth_empty_book_ratio_matches_the_old_notebook_path():
    params = load_legacy("ethusdt")
    old = run_legacy(
        alpha=params["alpha"],
        mu=params["mu"],
        delta=params["delta"],
        sigma=params["sigma"],
        dp=params["dp"],
        n_ticks=int(params["n_ticks"]),
        seed=42,
        n_events=10_000,
        burn_in=0,
    )
    ratio = variance_per_event(old.mids, 1) / variance_per_event(old.mids, 2_500)
    assert ratio == 416.5935166335227
    assert old.epsilon == params["epsilon"]
