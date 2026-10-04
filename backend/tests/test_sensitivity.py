import numpy as np
import pytest

from vpp_core import load_model as lm
from vpp_core import sensitivity as sens
from vpp_core.forecast import HISTORY_DAYS
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


def test_random_community_draws_pv_battery_and_mode_per_house():
    """The draw order of the older scale studies, so their communities are kept."""
    rng = np.random.default_rng(5)
    expected = []
    for _ in range(12):
        modules = int(rng.choice(len(MODULE_PROBABILITIES), p=MODULE_PROBABILITIES))
        expected.append((float(rng.choice(PV_KWP_CHOICES)), deye_se_f16(modules), rng.random() < 0.5))
    c = random_community(12, seed=5)
    assert [(h.pv_kwp, h.battery, h.mode == "Eco") for h in c.houses] == expected


def test_scale_scenario_uses_device_load_for_every_house():
    community = random_community(40, seed=2)
    scenario = make_scenario("iarna", 2, 1, 0.5, False, community)
    days = HISTORY_DAYS + 1                              # the week is generated with its meter history in front
    crit, flex = lm.community_load(community, scenario.past.start, days, 0.5, 2)
    np.testing.assert_array_equal(scenario.load_crit_kw, crit[:, -48:])
    np.testing.assert_array_equal(scenario.load_flex_kw, flex[:, -48:])
    np.testing.assert_array_equal(scenario.past.load_flex_kw, flex[:, :-48])


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


def test_forecast_study_has_every_variant_and_references():
    rows = sens.run_study("forecast", TINY)
    assert {r["variant"] for r in rows if r["controller"] in ("mpc", "mpc_ideal")} == set(sens.FORECAST_VARIANTS)
    assert {r["controller"] for r in rows if r["variant"] == "zgomot"} == {"mpc_ideal"}
    assert {r["controller"] for r in rows} == {"mpc", "mpc_ideal", "optim_lp", "vpp_reguli"}
    assert len(rows) == len(sens.TWO_SEASONS) * (len(sens.FORECAST_VARIANTS) + 2)
    lp = {r["season"]: r["cost_lei"] for r in rows if r["controller"] == "optim_lp"}
    perfect = {r["season"]: r["cost_lei"] for r in rows if r["variant"] == "perfecta"}
    for season in sens.TWO_SEASONS:                 # 1 day, horizon 24 h: the perfect-forecast MPC is the LP
        assert perfect[season] == pytest.approx(lp[season], abs=0.5)


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
