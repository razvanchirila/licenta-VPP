"""
RuleBasedController tests. The 'regression' tests reproduce the bugs found in the
competition code (analysis report 01) and check they cannot happen anymore.
"""
from datetime import date

import numpy as np
import pytest
from conftest import const, make_scenario
from hypothesis import given, settings
from hypothesis import strategies as st

from vpp_core.controllers import RuleBasedController
from vpp_core.experiments import baseline_controllers
from vpp_core.metrics import compute_metrics
from vpp_core.params import BatteryParams, CommunityParams, GridParams, HouseParams, default_community
from vpp_core.scenario import generate_scenario
from vpp_core.simulator import simulate

RISING = np.linspace(0.8, 1.5, 24)  # first 6 hours are the 'cheap' quartile


def one_house(**kw):
    return CommunityParams(houses=(HouseParams(id=1, battery=BatteryParams(), **kw),))


# --- regressions -------------------------------------------------------------------

def test_regression_charge_power_budget_shared_by_pv_and_arbitrage():
    """Old code: 5 kW from PV + 5 kW from grid on a 5 kW battery, and 2 kWh lost."""
    c = one_house(mode="Profit", initial_soc_ratio=0.6)
    sc = make_scenario(const(1, 24, 9.0), const(1, 24, 1.0), price_import=RISING)
    res = simulate(c, sc, RuleBasedController(apply_alpha=False))
    f = res.flows
    assert f["ch"][0, 0] == pytest.approx(5.0)
    assert f["imp"][0, 0] == pytest.approx(0.0)       # no budget left for grid charging
    assert f["exp"][0, 0] == pytest.approx(3.0)
    assert res.soc_kwh[0, 1] - res.soc_kwh[0, 0] == pytest.approx(5.0 * 0.95)


def test_regression_import_limit_applied_before_state_changes():
    """Old code: batteries kept energy bought above the limit; unserved load not reported."""
    houses = tuple(HouseParams(id=i, battery=BatteryParams(), mode="Profit", initial_soc_ratio=0.2) for i in range(3))
    c = CommunityParams(houses=houses, grid=GridParams(import_max_kw=5.0))
    sc = make_scenario(const(3, 24, 0.0), const(3, 24, 3.0), price_import=RISING)
    res = simulate(c, sc, RuleBasedController(apply_alpha=False))
    assert res.flows["imp"].sum(axis=0).max() <= 5.0 + 1e-9
    assert res.flows["shed"][:, 0].sum() == pytest.approx(4.0)
    assert res.flows["ch"].sum() == pytest.approx(0.0)     # no headroom -> no arbitrage
    m = compute_metrics(res)["community"]
    assert m["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)


def test_regression_house_outside_p2p_still_uses_battery_and_export():
    """Old code: a non-selling house with SOC >= 50% curtailed its whole surplus."""
    c = one_house(p2p_enabled=False, initial_soc_ratio=0.6)
    sc = make_scenario(const(1, 24, 9.0), const(1, 24, 1.0))
    f = simulate(c, sc, RuleBasedController(apply_alpha=False)).flows
    assert f["ch"][0, 0] == pytest.approx(5.0)
    assert f["exp"][0, 0] == pytest.approx(3.0)
    assert f["curtail"][0, 0] == pytest.approx(0.0)


def test_regression_internal_line_limit_in_kw_for_any_dt():
    """Old code compared kWh with kW: at dt=10 min a 10 kW line carried 1.67 kW."""
    c = CommunityParams(
        houses=(HouseParams(id=1), HouseParams(id=2)),
        grid=GridParams(internal_line_kw=10.0),
    )
    sc = make_scenario([[20.0] * 144, [0.0] * 144], [[0.0] * 144, [15.0] * 144], dt_h=1 / 6)
    f = simulate(c, sc, RuleBasedController(apply_alpha=False)).flows
    assert f["p2p_out"][0] == pytest.approx(np.full(144, 10.0))
    assert f["imp"][1] == pytest.approx(np.full(144, 5.0))


def test_regression_arbitrage_happens_with_generated_prices():
    """Old code: fixed 0.50 lei threshold was never reached, arbitrage was dead code."""
    c = default_community()
    sc = generate_scenario(c, start=date(2025, 1, 10), n_days=3, seed=1)
    f = simulate(c, sc, RuleBasedController(apply_alpha=False)).flows
    profit = [i for i, h in enumerate(c.houses) if h.mode == "Profit" and h.battery]
    grid_charge = np.minimum(f["ch"][profit], f["imp"][profit])
    assert grid_charge.sum() > 1.0


def test_regression_alpha_actually_reduces_load():
    """Old code: alpha was only a 'recommendation', Eco and Profit behaved identically."""
    c = CommunityParams(houses=(HouseParams(id=1, mode="Eco"), HouseParams(id=2, mode="Profit")))
    sc = make_scenario(const(2, 24, 0.0), const(2, 24, 0.2), flex=const(2, 24, 1.0), price_import=RISING)
    f = simulate(c, sc, RuleBasedController(apply_alpha=True)).flows
    assert f["shed"][0, -1] == pytest.approx(0.7)   # expensive hour: Eco keeps 30 %
    assert f["shed"][1, -1] == pytest.approx(0.9)   # Profit keeps 10 %
    assert f["shed"][0, 0] == pytest.approx(0.0)    # cheap hour: Eco keeps everything


# --- behaviour ----------------------------------------------------------------------

def test_p2p_moves_surplus_to_neighbour_before_export():
    c = CommunityParams(houses=(HouseParams(id=1), HouseParams(id=2)))
    sc = make_scenario([[6.0] * 24, [0.0] * 24], const(2, 24, 2.0))
    f = simulate(c, sc, RuleBasedController(apply_alpha=False)).flows
    assert f["p2p_out"][0, 0] == pytest.approx(2.0)
    assert f["exp"][0, 0] == pytest.approx(2.0)
    assert f["imp"][1, 0] == pytest.approx(0.0)


def test_export_limit_causes_curtailment():
    c = CommunityParams(houses=(HouseParams(id=1), HouseParams(id=2)), grid=GridParams(export_max_kw=4.0))
    sc = make_scenario(const(2, 24, 5.0), const(2, 24, 1.0))
    f = simulate(c, sc, RuleBasedController(apply_alpha=False)).flows
    assert f["exp"][:, 0].sum() == pytest.approx(4.0)
    assert f["curtail"][:, 0].sum() == pytest.approx(4.0)


def test_no_battery_baseline_never_touches_batteries():
    c = default_community()
    sc = generate_scenario(c, n_days=2)
    res = simulate(c, sc, baseline_controllers()[0])
    assert res.flows["ch"].sum() == 0 and res.flows["dis"].sum() == 0
    assert np.allclose(res.soc_kwh, res.soc_kwh[:, :1])


# --- property: every configuration is physically consistent -------------------------

@settings(max_examples=40, deadline=None)
@given(
    seed=st.integers(0, 10_000),
    n_houses=st.integers(1, 12),
    battery_share=st.floats(0, 1),
    profit_share=st.floats(0, 1),
    p2p_share=st.floats(0, 1),
    import_max=st.floats(1, 200),
    export_max=st.floats(0, 200),
    line=st.floats(0, 100),
    dt=st.sampled_from([1.0, 0.5, 0.25]),
    month=st.integers(1, 12),
    ctl=st.integers(0, 4),
)
def test_any_configuration_is_consistent(seed, n_houses, battery_share, profit_share, p2p_share,
                                         import_max, export_max, line, dt, month, ctl):
    rng = np.random.default_rng(seed)
    houses = tuple(
        HouseParams(
            id=i,
            pv_kwp=float(rng.uniform(0, 12)),
            battery=BatteryParams(capacity_kwh=float(rng.uniform(5, 25))) if rng.random() < battery_share else None,
            mode="Profit" if rng.random() < profit_share else "Eco",
            p2p_enabled=bool(rng.random() < p2p_share),
            initial_soc_ratio=float(rng.uniform(0.2, 1.0)),
        )
        for i in range(n_houses)
    )
    c = CommunityParams(houses=houses, grid=GridParams(import_max, export_max, line))
    sc = generate_scenario(c, start=date(2025, month, 15), n_days=1, dt_h=dt, seed=seed)
    res = simulate(c, sc, baseline_controllers()[ctl])   # raises DispatchError on any violation
    m = compute_metrics(res)["community"]
    assert m["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    assert 0 <= m["scr"] <= 1 + 1e-9
