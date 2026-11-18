from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pytest

from vpp_core.battery import Battery
from vpp_core.dispatch import Dispatch
from vpp_core.forecast import (
    History,
    LoadForecaster,
    PriceForecaster,
    PVForecaster,
    RealisticForecaster,
    appliance_daily_kwh,
    day_type,
    observe,
    published_steps,
)
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, LPWeights, RealisticMPCController, realise
from vpp_core.params import CommunityParams, GridParams, HouseParams, default_community, deye_se_f16
from vpp_core.reporting import make_scenario
from vpp_core.scenario import pv_clear_sky_per_kwp
from vpp_core.simulator import SimState, simulate, validate

C = default_community()
SPD = 96
MONDAY = date(2025, 6, 2)


def _corrupt(scenario, first_reading: int, value: float):
    """Copy where PV and load from step first_reading on, and every price not published at that step, are `value`."""
    first_price = published_steps(scenario.start, first_reading, scenario.dt_h)

    def cut(array, first):
        array = array.copy()
        array[..., first:] = value
        return array

    return replace(scenario, **{name: cut(getattr(scenario, name), first_reading)
                                for name in ("pv_kw", "load_crit_kw", "load_flex_kw")},
                   **{name: cut(getattr(scenario, name), first_price)
                      for name in ("price_import", "price_export", "price_p2p")})


def _history(now: int, pv=None, load=None, prices=None, start: date = MONDAY, n_houses: int = 1):
    pv = np.zeros((n_houses, now)) if pv is None else pv
    load = np.zeros((n_houses, now)) if load is None else load
    n_pub = published_steps(start, now, 0.25)
    prices = np.arange(n_pub, dtype=float) if prices is None else prices[:n_pub]
    return History(start=start, dt_h=0.25, now=now, pv_kw=pv, load_kw=load, price_import=prices,
                   price_export=prices * 0.5, price_p2p=prices * 0.7)


# ---------------------------------------------------------------- no future data

@pytest.mark.parametrize("real", [False, True])
@pytest.mark.parametrize("t", [0, 40, 51, 52, 80, SPD + 30])
@pytest.mark.parametrize("value", [np.nan, 1e6])
def test_forecast_unchanged_when_everything_after_t_is_corrupted(real, t, value):
    scenario = make_scenario("vara", 0, 2, 0.25, real, C)
    forecaster = RealisticForecaster()
    forecaster.reset(C)
    clean = forecaster.predict(observe(scenario, t), SPD)
    dirty = forecaster.predict(observe(_corrupt(scenario, t, value), t), SPD)
    for name in ("pv_kw", "load_kw", "price_import", "price_export", "price_p2p"):
        np.testing.assert_array_equal(getattr(clean, name), getattr(dirty, name), err_msg=name)
    assert np.isfinite(clean.pv_kw).all() and np.isfinite(clean.load_kw).all()


@pytest.mark.parametrize("t", [44, 60, SPD + 70])
def test_realistic_mpc_decision_ignores_the_future(t):
    """The dispatch of step t may use the readings of step t itself only through the physical balance."""
    scenario = make_scenario("iarna", 1, 2, 0.25, True, C)
    state = SimState(t=t, batteries=[Battery(h.battery, h.initial_soc_kwh) if h.battery else None for h in C.houses])
    decisions = []
    for sc in (scenario, _corrupt(scenario, t + 1, 1e6)):
        controller = RealisticMPCController()
        controller.reset(C, sc)
        decisions.append(controller.dispatch(state))
    for name, values in decisions[0].as_dict().items():
        np.testing.assert_array_equal(values, getattr(decisions[1], name), err_msg=name)


def test_history_rejects_future_readings_and_unpublished_prices():
    with pytest.raises(ValueError, match="after the decision"):
        _history(50, pv=np.zeros((1, 52)), load=np.zeros((1, 52)))
    with pytest.raises(ValueError, match="published"):
        History(start=MONDAY, dt_h=0.25, now=50, pv_kw=np.zeros((1, 50)), load_kw=np.zeros((1, 50)),
                price_import=np.zeros(2 * SPD), price_export=np.zeros(2 * SPD), price_p2p=np.zeros(2 * SPD))


# ---------------------------------------------------------------- prices

def test_day_ahead_prices_published_at_13():
    assert published_steps(MONDAY, 51, 0.25) == SPD               # 12:45: only today
    assert published_steps(MONDAY, 52, 0.25) == 2 * SPD           # 13:00: tomorrow too
    assert published_steps(MONDAY, 3 * SPD + 51, 0.25) == 4 * SPD
    assert published_steps(MONDAY, 13, 1.0) == 2 * 24


def test_unpublished_slots_take_the_price_of_7_days_earlier_then_1_day():
    full = np.arange(10 * SPD, dtype=float)
    before = PriceForecaster().predict_series(_history(7 * SPD + 51, prices=full), full[:8 * SPD], SPD)
    tomorrow = np.arange(8 * SPD, 8 * SPD + 51)
    np.testing.assert_array_equal(before[:SPD - 51], np.arange(7 * SPD + 51, 8 * SPD))   # today: published
    np.testing.assert_array_equal(before[SPD - 51:], tomorrow - 7 * SPD)
    after = PriceForecaster().predict_series(_history(7 * SPD + 52, prices=full), full[:9 * SPD], SPD)
    np.testing.assert_array_equal(after, np.arange(7 * SPD + 52, 8 * SPD + 52))         # all published
    short = PriceForecaster().predict_series(_history(51, prices=full), full[:SPD], SPD)
    np.testing.assert_array_equal(short[SPD - 51:], np.arange(51))    # no week back yet: the day before


def test_without_day_ahead_only_the_current_price_is_known():
    scenario = make_scenario("vara", 0, 2, 0.25, False, C)
    history = observe(scenario, 60, day_ahead=False)
    assert len(history.price_import) == history.now + 1


# ---------------------------------------------------------------- load

def test_day_type_uses_the_deer_calendar():
    assert day_type(date(2023, 5, 1)) == 1                       # public holiday, Monday
    assert day_type(date(2023, 5, 2)) == 0
    assert [day_type(MONDAY + timedelta(days=d)) for d in range(7)] == [0, 0, 0, 0, 0, 1, 1]


def test_load_forecast_uses_the_same_day_type():
    """Working days 1 kW (rising by day so the mean is checkable), weekends 3 kW; 14 days from a Monday."""
    days = [MONDAY + timedelta(days=d) for d in range(14)]
    level = np.array([3.0 if day_type(day) else 1.0 + 0.01 * d for d, day in enumerate(days)])
    load = np.repeat(level, SPD)[None, :]
    forecaster = LoadForecaster(n_days=3)
    saturday = forecaster.predict(_history(12 * SPD, load=load[:, :12 * SPD]), SPD)
    np.testing.assert_allclose(saturday, 3.0)
    monday = forecaster.predict(_history(14 * SPD, load=load), SPD)
    np.testing.assert_allclose(monday, np.mean(level[[9, 10, 11]]))       # the last 3 working days
    friday_evening = forecaster.predict(_history(11 * SPD + 80, load=load[:, :11 * SPD + 80]), SPD)
    np.testing.assert_allclose(friday_evening[0, :16], np.mean(level[[8, 9, 10]]))
    np.testing.assert_allclose(friday_evening[0, 16:], 3.0)


def test_load_forecast_falls_back_to_any_day_then_to_the_appliance_energy():
    forecaster = LoadForecaster()
    forecaster.reset(C)
    two_days = np.ones((C.n_houses, 2 * SPD))
    saturday = MONDAY + timedelta(days=5)
    any_type = forecaster.predict(_history(2 * SPD, load=two_days, start=saturday - timedelta(days=2),
                                           n_houses=C.n_houses), SPD)
    np.testing.assert_allclose(any_type, 1.0)
    cold = forecaster.predict(_history(0, n_houses=C.n_houses), SPD)
    np.testing.assert_allclose(cold.sum(axis=1) * 0.25, appliance_daily_kwh(C)["vara"])
    assert cold.std(axis=1).min() > 0                                       # DEER shape, not flat


# ---------------------------------------------------------------- PV

def _clear(n_days: int, start: date = MONDAY) -> np.ndarray:
    hours = (np.arange(SPD) + 0.5) * 0.25
    doy = np.array([(start + timedelta(days=d)).timetuple().tm_yday for d in range(n_days)])
    return pv_clear_sky_per_kwp(hours[None, :], doy[:, None], 46.5).ravel()


@pytest.mark.parametrize("morning", [0.3, 1.0])
def test_pv_forecast_follows_the_sky_of_the_morning(morning):
    one_house = CommunityParams(houses=(HouseParams(id=1, pv_kwp=10.0),))
    clear = 10.0 * _clear(3)
    now = 2 * SPD + 44                                                      # 11:00 on the third day
    readings = clear[:now].copy()
    readings[2 * SPD:] *= morning
    forecaster = PVForecaster()
    forecaster.reset(one_house)
    forecast = forecaster.predict(_history(now, pv=readings[None, :]), 2 * SPD)[0]
    afternoon = slice(4, 20)                                                # 12:00 - 16:00 today
    ratio = forecast[afternoon].sum() / clear[now:][afternoon].sum()
    assert ratio == pytest.approx(morning, abs=0.06)
    tomorrow = 10.0 * _clear(4)[3 * SPD:]
    np.testing.assert_allclose(forecast[SPD - 44:SPD - 44 + SPD].sum(), tomorrow.sum(), rtol=0.03)


def test_pv_forecast_cold_start_and_no_panels():
    houses = CommunityParams(houses=(HouseParams(id=1, pv_kwp=10.0), HouseParams(id=2, pv_kwp=0.0)))
    forecaster = PVForecaster()
    forecaster.reset(houses)
    forecast = forecaster.predict(_history(0, n_houses=2), SPD)
    np.testing.assert_allclose(forecast[0], 0.5 * 10.0 * _clear(1), rtol=1e-9)
    assert (forecast[1] == 0).all()


# ---------------------------------------------------------------- realisation

def test_realise_keeps_the_house_exchange_when_the_battery_can_absorb_the_error():
    house = HouseParams(id=1, pv_kwp=10.0, battery=deye_se_f16(1), initial_soc_ratio=0.5)
    community = CommunityParams(houses=(house, HouseParams(id=2, pv_kwp=0.0)), grid=GridParams(40.0, 40.0, 30.0))
    state = SimState(t=0, batteries=[Battery(house.battery, house.initial_soc_kwh), None])
    plan = Dispatch.zeros(2)
    plan.ch[0] = 3.0                                          # forecast: 5 kW PV, 1 kW load, 1 kW sold
    pv, load = np.array([3.5, 0.0]), np.array([1.0, 0.5])     # actual: 1.5 kW less PV
    error = (load - np.array([1.0, 0.5])) - (pv - np.array([5.0, 0.0]))
    held = realise(plan, community, pv, load, 0.5, state, 0.25, error)
    assert held.ch[0] == pytest.approx(1.5) and held.p2p_out[0] + held.exp[0] == pytest.approx(1.0)
    fixed = realise(plan, community, pv, load, 0.5, state, 0.25)
    assert fixed.ch[0] == pytest.approx(3.0) and fixed.p2p_out[0] + fixed.exp[0] == pytest.approx(0.0)
    assert fixed.p2p_in[1] + fixed.imp[1] == pytest.approx(0.5)
    scenario = make_scenario("vara", 0, 1, 0.25, False, community)
    for dispatch in (held, fixed):
        validate(dispatch, community, replace(scenario, pv_kw=np.tile(pv[:, None], scenario.n_steps),
                                              load_crit_kw=np.tile(load[:, None], scenario.n_steps),
                                              load_flex_kw=np.zeros((2, scenario.n_steps))), 0)


def test_realise_enforces_the_community_limits():
    houses = tuple(HouseParams(id=i, pv_kwp=10.0, battery=deye_se_f16(1)) for i in range(1, 4))
    community = CommunityParams(houses=houses, grid=GridParams(import_max_kw=4.0, export_max_kw=5.0))
    state = SimState(t=0, batteries=[Battery(h.battery, h.initial_soc_kwh) for h in houses])
    plan = Dispatch.zeros(3)
    plan.ch[:] = 2.0
    night = realise(plan, community, np.zeros(3), np.full(3, 2.0), 0.5, state, 0.25)
    assert night.imp.sum() == pytest.approx(4.0) and night.ch.sum() == pytest.approx(0.0)
    assert night.dis.sum() == pytest.approx(2.0) and night.shed.sum() == pytest.approx(0.0)
    noon = realise(Dispatch.zeros(3), community, np.full(3, 9.0), np.full(3, 1.0), 0.5, state, 0.25)
    assert noon.exp.sum() == pytest.approx(5.0) and noon.curtail.sum() == pytest.approx(19.0)
    negative = realise(Dispatch.zeros(3), community, np.full(3, 9.0), np.full(3, 1.0), -0.1, state, 0.25)
    assert negative.exp.sum() == pytest.approx(0.0)


def test_realise_over_the_import_limit_neighbours_discharge_before_a_house_sheds():
    houses = (HouseParams(id=1, pv_kwp=0.0), *(HouseParams(id=i, pv_kwp=0.0, battery=deye_se_f16(1)) for i in (2, 3)))
    community = CommunityParams(houses=houses, grid=GridParams(import_max_kw=3.0, export_max_kw=5.0))
    state = SimState(t=0, batteries=[None, *(Battery(h.battery, h.initial_soc_kwh) for h in houses[1:])])
    load = np.array([4.0, 1.0, 1.0])
    night = realise(Dispatch.zeros(3), community, np.zeros(3), load, 0.5, state, 0.25)
    assert night.shed.sum() == pytest.approx(0.0) and night.imp.sum() == pytest.approx(3.0)
    assert night.dis.sum() == pytest.approx(3.0) and night.p2p_in[0] > 0
    scenario = make_scenario("iarna", 0, 1, 0.25, False, community)
    validate(night, community, replace(scenario, pv_kw=np.zeros((3, scenario.n_steps)),
                                       load_crit_kw=np.tile(load[:, None], scenario.n_steps),
                                       load_flex_kw=np.zeros((3, scenario.n_steps))), 0)


# ---------------------------------------------------------------- the realistic MPC on the simulator

def _total_cost(res, deg_cost: float, worst_price: float, voll: float = 10.0) -> float:
    """Bill + wear + unserved load at VOLL + the stored energy the run ends short of, at the worst price."""
    m = compute_metrics(res)["community"]
    throughput = float((res.flows["ch"] + res.flows["dis"]).sum() * res.scenario.dt_h)
    return m["cost_lei"] + deg_cost * throughput + voll * m["shed_kwh"] + max(0.0, -m["soc_delta_kwh"]) * worst_price


@pytest.mark.parametrize(("season", "real"), [("iarna", False), ("vara", False), ("iarna", True), ("vara", True)])
@pytest.mark.parametrize("realisation", ["exchange", "battery"])
def test_realistic_mpc_passes_simulator_and_costs_more_than_the_lp(season, real, realisation):
    scenario = make_scenario(season, 2, 2, 0.5, real, C)
    lp = simulate(C, scenario, LPController())
    mpc = simulate(C, scenario, RealisticMPCController(horizon_h=12, realisation=realisation))   # DispatchError
    assert compute_metrics(mpc)["community"]["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    deg, worst = LPWeights().deg_cost, scenario.price_import.max() / 0.95
    gap = _total_cost(mpc, deg, worst) - _total_cost(lp, deg, worst)
    assert gap > 0.0
    assert gap < 0.5 * abs(_total_cost(lp, deg, worst)) + 60.0


def test_mpc_end_of_run_with_an_empty_battery_falls_back_to_the_current_soc():
    """Last step, battery at its minimum: soc >= initial is out of reach in one step, so the window keeps the SOC."""
    scenario = make_scenario("iarna", 0, 1, 0.25, True, C)
    controller = RealisticMPCController()
    controller.reset(C, scenario)
    batteries = [Battery(h.battery, h.battery.soc_min_kwh) if h.battery else None for h in C.houses]
    t = scenario.n_steps - 1
    dispatch = controller.dispatch(SimState(t=t, batteries=batteries))
    validate(dispatch, C, scenario, t)
    for battery, ch, dis in zip(batteries, dispatch.ch, dispatch.dis, strict=True):
        if battery is not None:
            battery.apply(ch, dis, scenario.dt_h)
