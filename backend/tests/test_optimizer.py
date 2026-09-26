from datetime import date

import numpy as np
import pytest
from conftest import const, make_scenario

from vpp_core.experiments import baseline_controllers
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, LPWeights, MPCController, noisy_forecast, solve_dispatch
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


def test_peak_cost_zero_is_identical_to_default():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    a = simulate(c, sc, LPController()).flows
    b = simulate(c, sc, LPController(LPWeights(peak_cost=0.0))).flows
    for k in a:
        assert a[k] == pytest.approx(b[k], abs=1e-9)


def test_peak_cost_lowers_peak_import_and_plan_is_feasible():
    """A demand charge spreads the night-time charging over more hours; the plan must
    still pass the strict simulator and the bill can only go up (the LP is optimal)."""
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=3, seed=4)
    free = compute_metrics(simulate(c, sc, LPController()))["community"]
    res = simulate(c, sc, LPController(LPWeights(peak_cost=50.0)))       # DispatchError if infeasible
    capped = compute_metrics(res)["community"]
    assert capped["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    assert capped["peak_import_kw"] < 0.5 * free["peak_import_kw"]
    assert capped["cost_lei"] >= free["cost_lei"] - 1e-6


def test_mpc_with_peak_cost_lowers_peak():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    free = compute_metrics(simulate(c, sc, MPCController(horizon_h=12)))["community"]
    res = simulate(c, sc, MPCController(horizon_h=12, weights=LPWeights(peak_cost=50.0)))
    capped = compute_metrics(res)["community"]
    assert capped["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    assert capped["peak_import_kw"] < free["peak_import_kw"]


def _bill(m: dict, peak_cost: float) -> float:
    """What the community actually pays with a demand charge: energy + peak_cost * weekly peak."""
    return m["cost_lei"] + peak_cost * m["peak_import_kw"]


def test_peak_floor_respected_and_inactive_below_natural_peak():
    """With peak_floor below the natural peak the constraint is slack: identical flows and the
    same P_peak. With peak_floor above it, P_peak sits exactly on the floor (the LP has no
    reason to raise a variable that costs money)."""
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    soc0 = np.array([h.initial_soc_kwh for h in c.houses])
    w = LPWeights(peak_cost=20.0)
    args = (c, sc.pv_kw, sc.load_kw, sc.price_import, sc.price_export, sc.dt_h, soc0, w)
    base = solve_dispatch(*args)
    assert base.peak_kw == pytest.approx(base.flows["imp"].sum(axis=0).max(), abs=1e-6)
    low = solve_dispatch(*args, peak_floor=0.5 * base.peak_kw)
    assert low.peak_kw == pytest.approx(base.peak_kw, abs=1e-6)
    for k in base.flows:
        assert low.flows[k] == pytest.approx(base.flows[k], abs=1e-6)
    high = solve_dispatch(*args, peak_floor=2.0 * base.peak_kw)
    assert high.peak_kw == pytest.approx(2.0 * base.peak_kw, abs=1e-6)
    assert high.flows["imp"].sum(axis=0).max() <= high.peak_kw + 1e-6
    assert high.objective <= base.objective + w.peak_cost * base.peak_kw + 1e-6   # the floor is a sunk cost
    assert solve_dispatch(*args[:-1], LPWeights(peak_cost=0.0), peak_floor=99.0).peak_kw is None


def test_mpc_peak_memory_matches_lp_and_beats_per_window():
    """Demand charge with memory, perfect forecast, horizon = whole scenario.

    At every step the controller minimises (remaining energy cost + peak_cost * max(peak so
    far, future peak)); the tail of the previous optimal plan stays feasible with the same
    objective, so by induction the realised bill equals the perfect-foresight LP optimum.
    The per-window variant produces a plan that is feasible for that same LP (it also ends
    at the initial SOC), so its bill cannot be lower. Both inequalities are exact up to
    solver tolerance and the eps tie-breaker; battery wear is switched off because the
    metric cost_lei does not include it.
    """
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    pc = 6.0
    w = LPWeights(deg_cost=0.0, peak_cost=pc)
    lp = compute_metrics(simulate(c, sc, LPController(w)))["community"]
    mem = compute_metrics(
        simulate(c, sc, MPCController(horizon_h=48, pv_error=0, load_error=0, weights=w))
    )["community"]
    win = compute_metrics(
        simulate(c, sc, MPCController(horizon_h=48, pv_error=0, load_error=0, weights=w, peak_memory=False))
    )["community"]
    assert _bill(mem, pc) == pytest.approx(_bill(lp, pc), abs=0.05)
    assert _bill(mem, pc) <= _bill(win, pc) + 0.05
    assert mem["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)


def test_mpc_peak_memory_reset_and_billing_period():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=2, dt_h=1.0, seed=4)
    ctl = MPCController(horizon_h=12, weights=LPWeights(peak_cost=6.0))
    a = simulate(c, sc, ctl)
    assert ctl.peak_so_far_kw == pytest.approx(a.flows["imp"].sum(axis=0).max())
    ctl.reset(c, sc)
    assert ctl.peak_so_far_kw == 0.0
    b = simulate(c, sc, ctl)               # reset inside simulate -> same run again
    for k in a.flows:
        assert a.flows[k] == pytest.approx(b.flows[k], abs=1e-9)
    # a 1-day billing period forgets day 1 at the start of day 2
    daily = MPCController(horizon_h=12, weights=LPWeights(peak_cost=6.0), billing_period_days=1)
    res = simulate(c, sc, daily)
    assert daily.peak_so_far_kw == pytest.approx(res.flows["imp"].sum(axis=0)[sc.steps_per_day:].max())


def test_mpc_with_forecast_errors_beats_rules():
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=3, dt_h=1.0, seed=4)
    rules = compute_metrics(simulate(c, sc, baseline_controllers()[2]))["community"]
    mpc = compute_metrics(simulate(c, sc, MPCController()))["community"]
    assert mpc["cost_lei"] < rules["cost_lei"]
