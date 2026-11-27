import math
import random

from lobsim.model import ZeroIntelligence, run


def test_paper_scales():
    model = ZeroIntelligence(0.2, 1.0, 0.05, 0.4, 10, random.Random(0))
    assert model.epsilon == 2 * 0.05 * 0.4 / 1.0
    assert model.pc == 1.0 / (2 * 0.2)
    assert model.asymptotic_depth == 0.2 / 0.05
    assert model.characteristic_shares == 1.0 / (2 * 0.05)


def test_seed_fixes_the_path():
    a = run(0.2, 1.0, 0.05, 0.4, 8, seed=42, n_events=300, burn_in=50)
    b = run(0.2, 1.0, 0.05, 0.4, 8, seed=42, n_events=300, burn_in=50)
    assert a.mids == b.mids
    assert any(math.isfinite(spread) and spread > 0 for spread in a.spreads)
