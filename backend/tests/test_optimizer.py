from datetime import date

import numpy as np
import pytest

from conftest import const, make_scenario
from vpp_core.experiments import baseline_controllers
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, LPWeights, MPCController, noisy_forecast
from vpp_core.params import BatteryParams, CommunityParams, GridParams, HouseParams, default_community
from vpp_core.scenario import generate_scenario
from vpp_core.simulator import simulate

NO_WEAR = LPWeights(deg_cost=0.0)


def test_buys_cheap_to_cover_expensive_hours():
    """Spread 0.5 -> 2.0 lei/kWh beats round-trip losses: charge at night, discharge in the evening."""
    c = CommunityParams(houses=(HouseParams(id=1, pv_kwp=0, battery=BatteryParams(), initial_soc_ratio=0.2),))
    price = np.array([0.5] * 12 + [2.0] * 12)
    sc = make_scenario(const(1, 24, 0.0), const(1, 24, 1.0), price_import=price, price_export=[0.1] * 24)
    res = simulate(c, sc, LPController(terminal_soc=False))
    f = res.flows
    assert f["imp"][0, 12:].sum() == pytest.approx(0.0, abs=1e-6)   # evening fully from battery
    assert f["ch"][0, :12].sum() > 0


def test_no_arbitrage_when_spread_below_losses():
    c = CommunityParams(houses=(HouseParams(id=1, pv_kwp=0, battery=BatteryParams(), initial_soc_ratio=0.2),))
    price = np.array([1.0] * 12 + [1.05] * 12)   # 1.05 < 1 / 0.9025
    sc = make_scenario(const(1, 24, 0.0), const(1, 24, 1.0), price_import=price)
    f = simulate(c, sc, LPController(terminal_soc=False)).flows
    assert f["ch"].sum() == pytest.approx(0.0, abs=1e-6)


def test_uses_neighbour_instead_of_grid():
    c = CommunityParams(houses=(HouseParams(id=1), HouseParams(id=2)))
    sc = make_scenario([[5.0] * 24, [0.0] * 24], const(2, 24, 2.0))
    f = simulate(c, sc, LPController()).flows
    assert f["p2p_out"][0] == pytest.approx(np.full(24, 2.0), abs=1e-6)
    assert f["imp"].sum() == pytest.approx(0.0, abs=1e-6)


def test_respects_import_limit_by_shedding():
    houses = tuple(HouseParams(id=i, pv_kwp=0) for i in range(3))
    c = CommunityParams(houses=houses, grid=GridParams(import_max_kw=5.0))
    sc = make_scenario(const(3, 24, 0.0), const(3, 24, 3.0))
    f = simulate(c, sc, LPController()).flows
    assert f["imp"].sum(axis=0) == pytest.approx(np.full(24, 5.0))
    assert f["shed"].sum(axis=0) == pytest.approx(np.full(24, 4.0))


@pytest.mark.parametrize("start", [date(2025, 1, 10), date(2025, 6, 1)])
def test_lp_plan_passes_simulator_and_keeps_soc(start):
    c = default_community()
    sc = generate_scenario(c, start=start, n_days=3, seed=4)
    res = simulate(c, sc, LPController())            # DispatchError if the plan is infeasible
    m = compute_metrics(res)["community"]
    assert m["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    assert (res.soc_kwh[:, -1] >= res.soc_kwh[:, 0] - 1e-6).all()


@pytest.mark.parametrize("start", [date(2025, 1, 10), date(2025, 6, 1)])
def test_lp_not_worse_than_any_rule_based_strategy(start):
    """With perfect foresight the LP is optimal, so it cannot lose to a heuristic.

    A baseline that ends with less stored energy is charged for buying it back at the
    highest price, so both are compared at the same end-of-horizon state.
    """
    c = default_community()
    sc = generate_scenario(c, start=start, n_days=3, seed=4)
    lp = compute_metrics(simulate(c, sc, LPController(NO_WEAR)))["community"]
    worst = sc.price_import.max() / 0.95
    for ctl in baseline_controllers()[:4]:
        m = compute_metrics(simulate(c, sc, ctl))["community"]
        missing = max(0.0, -m["soc_delta_kwh"])
        assert lp["cost_lei"] <= m["cost_lei"] + missing * worst + 1e-6, ctl.name


def test_forecast_exact_now_and_noisier_later():
    rng = np.random.default_rng(0)
    actual = np.ones((200, 96 * 2))
    fc = noisy_forecast(actual, 10, 0.3, 96, rng)
    assert fc.shape == (200, 96 * 2 - 10)
    assert np.allclose(fc[:, 0], 1.0)
    assert fc[:, 1].std() < fc[:, 96].std()
    assert fc[:, 96].std() == pytest.approx(0.3, rel=0.25)


def test_mpc_plan_passes_simulator():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    res = simulate(c, sc, MPCController(horizon_h=12))
    assert compute_metrics(res)["community"]["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)


def test_mpc_with_perfect_forecast_close_to_lp():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    lp = compute_metrics(simulate(c, sc, LPController()))["community"]
    mpc = compute_metrics(simulate(c, sc, MPCController(horizon_h=48, pv_error=0, load_error=0)))["community"]
    assert mpc["cost_lei"] == pytest.approx(lp["cost_lei"], abs=0.5)


def test_mpc_with_forecast_errors_beats_rules():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=3, dt_h=1.0, seed=4)
    rules = compute_metrics(simulate(c, sc, baseline_controllers()[2]))["community"]
    mpc = compute_metrics(simulate(c, sc, MPCController()))["community"]
    assert mpc["cost_lei"] < rules["cost_lei"]
