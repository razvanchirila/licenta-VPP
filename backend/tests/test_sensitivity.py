import warnings

import numpy as np
import pytest

from vpp_core import load_model as lm
from vpp_core import sensitivity as sens
from vpp_core.params import MODULE_PROBABILITIES, PV_KWP_CHOICES, deye_se_f16, random_community
from vpp_core.reporting import make_scenario

TINY = sens.Settings(n_seeds=1, n_days=1, dt_h=1.0, real=False, workers=0, scale_sizes=(2, 10))


def test_random_community_count_limits_and_batteries():
    c = random_community(25, seed=1)
    assert c.n_houses == 25
    assert [h.id for h in c.houses] == list(range(1, 26))
    assert (c.grid.import_max_kw, c.grid.export_max_kw, c.grid.internal_line_kw) == (125.0, 100.0, 75.0)
    for h in c.houses:
        assert h.pv_kwp in PV_KWP_CHOICES
        assert h.initial_soc_ratio == 0.5
        if h.battery:
            assert h.battery in (deye_se_f16(1), deye_se_f16(2))


def test_random_community_reproducible_by_seed():
    assert random_community(30, seed=3) == random_community(30, seed=3)
    assert random_community(30, seed=3) != random_community(30, seed=4)


def test_random_community_battery_share_and_modes():
    c = random_community(1000, seed=0)
    modules = np.array([0 if h.battery is None else round(h.battery.capacity_kwh / 16) for h in c.houses])
    for n, probability in enumerate(MODULE_PROBABILITIES):
        assert abs(np.mean(modules == n) - probability) < 0.05
    assert {h.mode for h in c.houses} == {"Eco", "Profit"}


def test_random_community_profiles_come_from_the_appliance_list():
    ids = sorted(lm.by_house(lm.load_appliances()))
    c = random_community(200, seed=0)
    drawn = [h.profile_id for h in c.houses]
    assert set(drawn) == set(ids)                        # 200 draws reach all 10 templates
    assert min(np.bincount(drawn)[1:]) >= 8
    assert [h.profile_id for h in random_community(200, seed=1).houses] != drawn
    assert {h.profile_id for h in random_community(50, seed=0, profile_ids=(3, 7)).houses} == {3, 7}


def test_random_community_pv_and_batteries_do_not_depend_on_the_profiles():
    """The profile ids are drawn after everything else, so the communities of the older scale studies are kept."""
    rng = np.random.default_rng(5)
    expected = []
    for _ in range(12):
        modules = int(rng.choice(len(MODULE_PROBABILITIES), p=MODULE_PROBABILITIES))
        expected.append((float(rng.choice(PV_KWP_CHOICES)), deye_se_f16(modules), rng.random() < 0.5))
    c = random_community(12, seed=5)
    assert [(h.pv_kwp, h.battery, h.mode == "Eco") for h in c.houses] == expected
    other = random_community(12, seed=5, profile_ids=(1,))
    assert [(h.pv_kwp, h.battery, h.mode) for h in other.houses] == [(h.pv_kwp, h.battery, h.mode) for h in c.houses]


def test_scale_scenario_uses_device_load_for_every_house():
    community = random_community(40, seed=2)
    with warnings.catch_warnings():
        warnings.simplefilter("error")                   # no "case lipsesc" fallback warning
        scenario = make_scenario("iarna", 2, 1, 0.5, False, community)
    crit, flex = lm.community_load(community, lm.DISPOZITIVE_CSV, scenario.start, 1, 0.5, 2)
    np.testing.assert_array_equal(scenario.load_crit_kw, crit)
    np.testing.assert_array_equal(scenario.load_flex_kw, flex)


def test_random_community_rejects_empty():
    with pytest.raises(ValueError):
        random_community(0)


def test_without_p2p_disables_every_house():
    c = sens.without_p2p(random_community(5, seed=0))
    assert not any(h.p2p_enabled for h in c.houses)


@pytest.mark.parametrize("name", list(sens.STUDIES))
def test_study_rows_have_expected_keys_and_chart_renders(name, tmp_path):
    rows = sens.run_study(name, TINY)
    keys = sens.STUDIES[name].keys
    assert rows and all(set(keys) <= set(row) for row in rows)
    assert all(np.isfinite(row["cost_lei"]) and row["wall_s"] >= 0 for row in rows)
    sens.STUDIES[name].chart(rows, TINY, tmp_path / f"{name}.png")
    assert (tmp_path / f"{name}.png").stat().st_size > 0


def test_forecast_study_has_mpc_levels_and_references():
    rows = sens.run_study("forecast", TINY)
    mpc_levels = {r["pv_error"] for r in rows if r["controller"] == "mpc"}
    assert mpc_levels == {pv for pv, _ in sens.FORECAST_ERRORS}
    assert {r["controller"] for r in rows} == {"mpc", "optim_lp", "vpp_reguli"}
    assert len(rows) == len(sens.TWO_SEASONS) * (len(sens.FORECAST_ERRORS) + 2)


def test_deg_study_throughput_and_cycles():
    rows = sens.run_study("deg", TINY)
    assert {r["deg_cost"] for r in rows} == set(sens.DEG_COSTS)
    for row in rows:
        assert row["throughput_kwh"] >= 0 and row["cycles_per_day"] >= 0


def test_p2p_study_no_exchange_when_disabled():
    rows = sens.run_study("p2p", TINY)
    assert all(row["p2p_kwh"] == pytest.approx(0.0, abs=1e-6) for row in rows if row["p2p"] == 0)
    assert len(rows) == 4 * len(sens.CONTROLLERS) * 2


def test_scale_study_cost_per_house_and_sizes():
    rows = sens.run_study("scale", TINY)
    assert {r["n_houses"] for r in rows} == {2, 10}
    for row in rows:
        assert row["cost_per_house"] == pytest.approx(row["cost_lei"] / row["n_houses"])
