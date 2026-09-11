import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vpp_core.battery import Battery, PhysicalLimitError
from vpp_core.params import BatteryParams

P = BatteryParams(capacity_kwh=20, soc_min_ratio=0.2, p_ch_max_kw=5, p_dis_max_kw=5, eta_ch=0.95, eta_dis=0.95)


def test_charge_applies_efficiency():
    b = Battery(P, 10.0)
    b.apply(5.0, 0.0, 1.0)
    assert b.soc_kwh == pytest.approx(10.0 + 5 * 0.95)


def test_discharge_applies_efficiency():
    b = Battery(P, 10.0)
    b.apply(0.0, 3.8, 1.0)
    assert b.soc_kwh == pytest.approx(10.0 - 3.8 / 0.95)


def test_power_limit_is_per_step():
    b = Battery(P, 6.0)
    with pytest.raises(PhysicalLimitError):
        b.apply(10.0, 0.0, 1.0)  # the old model allowed 5 kW from PV + 5 kW from grid


def test_soc_limits_enforced():
    with pytest.raises(PhysicalLimitError):
        Battery(P, 19.5).apply(5.0, 0.0, 1.0)
    with pytest.raises(PhysicalLimitError):
        Battery(P, 4.5).apply(0.0, 5.0, 1.0)


def test_initial_soc_validated():
    with pytest.raises(PhysicalLimitError):
        Battery(P, 25.0)


def test_max_powers_respect_space_and_energy():
    b = Battery(P, 19.0)
    assert b.max_charge_kw(1.0) == pytest.approx(1.0 / 0.95)
    assert b.max_discharge_kw(0.25) == pytest.approx(5.0)
    b = Battery(P, 4.5)
    assert b.max_discharge_kw(1.0) == pytest.approx(0.5 * 0.95)


def test_losses_match_soc_accounting():
    b = Battery(P, 10.0)
    ch, dis, dt = 4.0, 1.0, 0.5
    soc0 = b.soc_kwh
    loss = b.losses_kwh(ch, dis, dt)
    b.apply(ch, dis, dt)
    assert (ch - dis) * dt == pytest.approx(b.soc_kwh - soc0 + loss)


@settings(max_examples=200, deadline=None)
@given(
    soc0=st.floats(4.0, 20.0),
    dt=st.sampled_from([1.0, 0.5, 0.25, 1 / 6]),
    steps=st.lists(st.tuples(st.floats(0, 1), st.floats(0, 1), st.booleans()), min_size=1, max_size=50),
)
def test_feasible_requests_keep_soc_in_bounds(soc0, dt, steps):
    b = Battery(P, soc0)
    expected = soc0
    for frac, _, charging in steps:
        ch = frac * b.max_charge_kw(dt) if charging else 0.0
        dis = 0.0 if charging else frac * b.max_discharge_kw(dt)
        expected += (P.eta_ch * ch - dis / P.eta_dis) * dt
        b.apply(ch, dis, dt)
        assert P.soc_min_kwh - 1e-9 <= b.soc_kwh <= P.soc_max_kwh + 1e-9
    assert b.soc_kwh == pytest.approx(expected, abs=1e-6)
