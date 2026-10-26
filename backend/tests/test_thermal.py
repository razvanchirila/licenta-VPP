"""Thermal model: heat pump, radiators, AC and boiler against hand calculations."""
from datetime import date

import numpy as np
import pytest

from vpp_core import thermal as th

DT = 1 / 12
MONDAY = date(2023, 1, 2)


def weather(temp, n_days=1, solar=0.0):
    n = round(24 / DT) * n_days
    return th.Weather(np.full(n, float(temp)), np.full(n, float(solar)))


def run(house, temp, n_days=1, gains=0.0, solar=0.0, start=MONDAY, seed=0):
    n = round(24 / DT) * n_days
    return th.thermal_profiles(house, start, n_days, DT, weather(temp, n_days, solar), np.full(n, gains),
                               np.random.default_rng(seed))


def test_cop_follows_the_datasheet_points():
    assert th.cop(7.0) == pytest.approx(4.7)
    assert th.cop(-7.0) == pytest.approx(2.8)
    assert th.cop(0.0) == pytest.approx(3.75)
    assert th.cop(-40.0) == th.COP_MIN and th.cop(40.0) == th.COP_MAX


def test_heat_pump_holds_the_setpoint_and_balances_the_losses():
    house = th.ThermalHouse(2, True, "medie", "pompa", 2.5)
    out = run(house, 0.0, n_days=2)
    heat, night = th.setpoints(house, MONDAY, DT)
    warm = out["temp_in"][: len(heat)][heat == 21][round(2 / DT):]                  # after 2 h of warming up
    np.testing.assert_allclose(warm, 21, atol=1e-6)
    steady = slice(round(10 / DT), round(21 / DT))                          # between the morning and the evening
    q = out["pompa"][steady] * th.cop(0.0)
    people = th.PEOPLE_W / 1000 * 2
    assert q == pytest.approx(house.ua_kw_k * 21 - people, rel=1e-6)        # UA (21 - 0) minus the people's heat
    assert out["pompa"].max() <= 2.5 + 1e-9


def test_better_insulation_needs_less_heat():
    use = {iz: run(th.ThermalHouse(2, True, iz, "pompa", 2.5), -5.0, n_days=3)["pompa"].sum() for iz in th.IZOLATII}
    assert use["noua"] < use["medie"] < use["veche"]


def test_nobody_home_lowers_the_setpoint_on_workdays_only():
    house = th.ThermalHouse(2, False, "medie", "pompa", 2.5)
    heat, cool = th.setpoints(house, MONDAY, DT)
    assert heat[round(12 / DT)] == th.HEAT_AWAY and cool[round(12 / DT)] == th.COOL_AWAY
    assert heat[round(18 / DT)] == th.HEAT_DAY and heat[round(3 / DT)] == th.HEAT_NIGHT
    saturday = th.setpoints(house, date(2023, 1, 7), DT)[0]
    assert saturday[round(12 / DT)] == th.HEAT_DAY


def test_radiators_switch_on_and_off_around_the_setpoint():
    house = th.ThermalHouse(2, True, "medie", "radiator", 4.0)
    out = run(house, 0.0, n_days=2)
    assert set(np.round(out["radiator"], 6)) <= {0.0, 4.0}
    day = out["temp_in"][round(9 / DT) : round(21 / DT)]
    assert day.min() > th.RADIATOR_DAY - th.HYSTERESIS_K - 0.2 and day.max() < th.RADIATOR_DAY + th.HYSTERESIS_K + 0.2


def test_gas_heating_draws_no_electricity():
    out = run(th.ThermalHouse(1, True, "veche"), -10.0)
    assert set(out) == {"temp_in", "temp_tank"}
    assert out["temp_in"].min() >= th.HEAT_NIGHT - 1e-6


def test_ac_cools_only_above_the_setpoint():
    house = th.ThermalHouse(2, True, "medie", None, 0.0, ac_kw=0.8)
    assert run(house, 20.0)["ac"].sum() == 0
    hot = run(house, 34.0, solar=600)
    assert hot["ac"].max() <= 0.8 + 1e-9 and hot["ac"].sum() > 0
    assert hot["temp_in"].max() <= th.COOL_HOME + 0.5


def test_open_windows_cool_a_house_without_ac():
    house = th.ThermalHouse(2, True, "noua")
    n = round(24 / DT) * 3
    temp = np.where(np.arange(n) % round(24 / DT) < round(12 / DT), 16.0, 32.0)
    out = th.thermal_profiles(house, date(2023, 7, 3), 3, DT, th.Weather(temp, np.full(n, 300.0)),
                              np.zeros(n), np.random.default_rng(0))
    assert out["temp_in"].max() < 31


def test_boiler_energy_is_the_showers_plus_the_losses():
    house = th.ThermalHouse(3, True, boiler_kw=1.8)
    out = run(house, 0.0, n_days=14)
    per_day = out["boiler"].sum() * DT / 14
    expected = 3 * th.HOT_WATER_KWH + th.TANK_LOSS_KW_K * (57 - th.ROOM_C) * 24
    assert per_day == pytest.approx(expected, rel=0.1)
    assert out["boiler"].max() <= 1.8 + 1e-9
    assert out["temp_tank"].min() >= th.COLD_WATER_C and out["temp_tank"].max() <= th.BOILER_MAX_C + 1e-6
