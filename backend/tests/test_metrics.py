from datetime import date

import pytest

from conftest import const, make_scenario
from vpp_core.controllers import RuleBasedController
from vpp_core.experiments import baseline_controllers
from vpp_core.metrics import compute_metrics
from vpp_core.params import CommunityParams, HouseParams, default_community
from vpp_core.scenario import generate_scenario
from vpp_core.simulator import simulate


def test_hand_computed_example():
    """1 house, no battery: 3 kW PV, 1 kW load for 24 h -> 2 kW exported."""
    c = CommunityParams(houses=(HouseParams(id=1),))
    sc = make_scenario(const(1, 24, 3.0), const(1, 24, 1.0), price_export=[0.3] * 24)
    m = compute_metrics(simulate(c, sc, RuleBasedController(apply_alpha=False)))
    com, h = m["community"], m["houses"][0]
    assert com["export_kwh"] == pytest.approx(48.0)
    assert com["cost_lei"] == pytest.approx(-48.0 * 0.3)
    assert com["scr"] == pytest.approx(1 / 3)
    assert com["ssr"] == pytest.approx(1.0)
    assert h["cost_lei"] == pytest.approx(com["cost_lei"])


def test_p2p_payments_cancel_at_community_level():
    c = CommunityParams(houses=(HouseParams(id=1), HouseParams(id=2)))
    sc = make_scenario([[6.0] * 24, [0.0] * 24], const(2, 24, 2.0))
    m = compute_metrics(simulate(c, sc, RuleBasedController(apply_alpha=False)))
    assert sum(h["cost_lei"] for h in m["houses"]) == pytest.approx(m["community"]["cost_lei"])
    assert m["houses"][1]["ssr"] == pytest.approx(0.0)      # everything bought (from neighbour)
    assert m["community"]["ssr"] == pytest.approx(1.0)      # nothing from the grid


@pytest.mark.parametrize("start", [date(2025, 1, 10), date(2025, 4, 10), date(2025, 6, 1)])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_energy_balance_closes_for_all_baselines(start, seed):
    c = default_community()
    sc = generate_scenario(c, start=start, n_days=3, seed=seed)
    for ctl in baseline_controllers():
        m = compute_metrics(simulate(c, sc, ctl))["community"]
        assert m["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6), ctl.name


@pytest.mark.parametrize("start", [date(2025, 1, 10), date(2025, 6, 1)])
def test_battery_improves_self_sufficiency(start):
    c = default_community()
    sc = generate_scenario(c, start=start, n_days=7, seed=5)
    no_batt, local = baseline_controllers()[:2]
    m0 = compute_metrics(simulate(c, sc, no_batt))["community"]
    m1 = compute_metrics(simulate(c, sc, local))["community"]
    assert m1["ssr"] > m0["ssr"]
    assert m1["import_kwh"] < m0["import_kwh"]
