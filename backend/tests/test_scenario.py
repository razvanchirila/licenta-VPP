from datetime import date

import numpy as np
import pytest

from vpp_core.load_model import compose_houses
from vpp_core.params import default_community
from vpp_core.scenario import generate_scenario

C = default_community()


def test_same_seed_same_scenario():
    a = generate_scenario(C, seed=7)
    b = generate_scenario(C, seed=7)
    for name in ("pv_kw", "load_crit_kw", "load_flex_kw", "price_import"):
        np.testing.assert_array_equal(getattr(a, name), getattr(b, name))


def test_different_seed_different_scenario():
    assert not np.array_equal(generate_scenario(C, seed=1).pv_kw, generate_scenario(C, seed=2).pv_kw)


def test_shapes_and_signs():
    s = generate_scenario(C, n_days=3, dt_h=0.5)
    assert s.pv_kw.shape == (10, 144)
    assert s.price_import.shape == (144,)
    assert (s.pv_kw >= 0).all() and (s.load_kw > 0).all()
    assert (s.price_import > s.price_export).all()


def test_no_pv_at_night():
    s = generate_scenario(C, n_days=2, dt_h=1.0)
    night = [0, 1, 2, 23, 24, 25, 26, 47]
    assert np.allclose(s.pv_kw[:, night], 0)


@pytest.mark.parametrize(
    "start, lo, hi",
    [(date(2025, 6, 1), 3.5, 6.5), (date(2025, 1, 10), 0.5, 2.2)],
)
def test_pv_yield_plausible_for_romania(start, lo, hi):
    """Average daily yield in kWh/kWp over several seeds (RO: ~5 in June, ~1.3 in January)."""
    yields = []
    for seed in range(10):
        s = generate_scenario(C, start=start, n_days=7, seed=seed)
        yields.append(s.pv_kw.sum() * s.dt_h / (7 * 100))
    assert lo < np.mean(yields) < hi


def test_pv_never_exceeds_installed_power():
    s = generate_scenario(C, weather="clear")
    assert s.pv_kw.max() < 10.0


def test_daily_load_plausible():
    """June: each house near the expected summer energy of its appliances (bounds were 4-16 for the old curve)."""
    s = generate_scenario(C, n_days=14, seed=3)
    per_house_day = s.load_kw.sum(axis=1) * s.dt_h / 14
    expected = [house.kwh_per_day("vara") for house in compose_houses(range(1, 11))]
    np.testing.assert_allclose(per_house_day, expected, rtol=0.15)
    assert (per_house_day > 2).all() and (per_house_day < 20).all()
    old = generate_scenario(C, n_days=14, seed=3, load_source="sintetic")
    per_house_day = old.load_kw.sum(axis=1) * old.dt_h / 14
    assert (per_house_day > 4).all() and (per_house_day < 16).all()


def test_dt_must_divide_day():
    with pytest.raises(ValueError):
        generate_scenario(C, dt_h=0.7)
