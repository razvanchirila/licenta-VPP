import math

import pytest

from vpp_core.params import DEFAULT_MODULES, BatteryParams, HouseParams, default_community, deye_se_f16


def test_deye_modules():
    """Deye SE-F16: 16 kWh, DoD 90 %, 160 A ~ 8 kW per module; two in parallel are capped by the 10 kW inverter."""
    assert deye_se_f16(0) is None
    one = deye_se_f16(1)
    assert (one.capacity_kwh, one.soc_min_ratio, one.p_ch_max_kw, one.p_dis_max_kw) == (16.0, 0.1, 8.0, 8.0)
    assert one.usable_kwh == pytest.approx(14.4)
    assert one == BatteryParams()
    two = deye_se_f16(2)
    assert (two.capacity_kwh, two.soc_min_ratio, two.p_ch_max_kw, two.p_dis_max_kw) == (32.0, 0.1, 10.0, 10.0)
    with pytest.raises(ValueError):
        deye_se_f16(-1)


def test_default_community_layout():
    c = default_community()
    assert DEFAULT_MODULES == (1, 1, 1, 1, 1, 2, 2, 2, 0, 0)
    assert [h.battery for h in c.houses] == [deye_se_f16(n) for n in DEFAULT_MODULES]
    assert all(h.pv_kwp == 10.0 and h.inverter_kw == 10.0 and h.p2p_enabled for h in c.houses)
    assert [h.mode for h in c.houses] == ["Eco" if i % 2 else "Profit" for i in range(1, 11)]
    assert sum(h.battery.capacity_kwh for h in c.houses if h.battery) == 5 * 16 + 3 * 32


def test_inverter_must_be_positive_but_may_be_unlimited():
    assert HouseParams(id=1, inverter_kw=math.inf).inverter_kw == math.inf
    with pytest.raises(ValueError):
        HouseParams(id=1, inverter_kw=0.0)
