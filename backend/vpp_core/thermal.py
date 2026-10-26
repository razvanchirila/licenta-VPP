"""
Thermal loads of a house: space heating (heat pump or electric radiators), cooling (split AC) and hot water
(electric storage boiler). A house heated with gas keeps its setpoint at no electric cost.

Building, one thermal node (the simple hourly method of EN ISO 13790, one capacity):
    C dT/dt = Q_heat - Q_cool + Q_gains - UA (T - T_out)
UA = SPECIFIC_LOSS_W_M2K[izolatie] x FLOOR_M2, C = CAPACITY_WH_M2K[izolatie] x FLOOR_M2.
Above VENT_FROM_C, when it is cooler outside, the windows are opened: the loss coefficient grows by VENT_KW_K.
Gains: the electricity of the other appliances (all of it ends up as heat inside, except the EV, which charges
outside), PEOPLE_W per person while someone is home, SOLAR_APERTURE_M2 x irradiance on the panels' plane.

    heat pump  inverter: the heat that brings T to the setpoint at the end of the step, at most putere_w x COP;
               COP linear in T_out through the datasheet points (7 °C, 4.7) and (-7 °C, 2.8)
    radiators  on/off thermostat, +-0.5 K around the setpoint, putere_w; they heat RADIATOR_SHARE of the house
    AC         like the heat pump, cooling, at most putere_w x EER
    boiler     TANK_L litres, on below BOILER_ON_C until BOILER_MAX_C; each person draws HOT_WATER_KWH a day
               (32 l at 60 °C from 10 °C) as one shower in the morning or the evening; standby losses

Setpoints: heating 21 °C 6-22 and 19 °C at night, 18 °C 8-16 on workdays when nobody is home (radiators 20 / 17);
cooling 26 °C, 30 °C while nobody is home. The state starts at the setpoint and runs the first day once before
the window, so the window does not start cold.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

ROLES = {"pompa de caldura": "pompa", "radiator electric": "radiator", "aer conditionat": "ac", "boiler": "boiler"}
OUTDOOR_DEVICES = ("masina electrica",)
IZOLATII = ("noua", "medie", "veche")
FLOOR_M2 = 120.0
SPECIFIC_LOSS_W_M2K = {"noua": 0.6, "medie": 1.2, "veche": 2.0}
CAPACITY_WH_M2K = {"noua": 45.8, "medie": 45.8, "veche": 72.2}     # 165 / 260 kJ/(m2 K), EN ISO 13790 classes
PEOPLE_W = 80.0
VENT_FROM_C = 24.0
VENT_KW_K = 0.3                             # ~1.5 air changes an hour through open windows
SOLAR_APERTURE_M2 = 2.0
COP_POINTS = ((-7.0, 2.8), (7.0, 4.7))
COP_MIN, COP_MAX = 1.5, 5.5
EER = 4.25
RADIATOR_SHARE = 0.5
HYSTERESIS_K = 0.5
TANK_L = 80.0
WATER_KWH_PER_LK = 1.163e-3
TANK_LOSS_KW_K = 0.0011                     # ~1 kWh/day at 60 °C in a 20 °C room
ROOM_C, COLD_WATER_C = 20.0, 10.0
BOILER_ON_C, BOILER_MAX_C = 55.0, 60.0
HOT_WATER_KWH = 32 * WATER_KWH_PER_LK * (60 - COLD_WATER_C)
SHOWER_H = 1 / 6
HEAT_DAY, HEAT_NIGHT, HEAT_AWAY = 21.0, 19.0, 18.0
RADIATOR_DAY, RADIATOR_NIGHT = 20.0, 17.0
COOL_HOME, COOL_AWAY = 26.0, 30.0


@dataclass(frozen=True)
class Weather:
    temp_out_c: np.ndarray        # (n_steps,)
    solar_w_m2: np.ndarray        # (n_steps,) irradiance on the panels' plane


@dataclass(frozen=True)
class ThermalHouse:
    persoane: int
    acasa_ziua: bool
    izolatie: str = "medie"
    heating: str | None = None    # pompa | radiator | None (gas)
    heating_kw: float = 0.0
    ac_kw: float = 0.0            # 0: no AC
    boiler_kw: float = 0.0        # 0: no electric boiler

    @property
    def ua_kw_k(self) -> float:
        return SPECIFIC_LOSS_W_M2K[self.izolatie] * FLOOR_M2 / 1000

    @property
    def c_kwh_k(self) -> float:
        return CAPACITY_WH_M2K[self.izolatie] * FLOOR_M2 / 1000


def cop(temp_out_c: np.ndarray | float) -> np.ndarray:
    (t0, c0), (t1, c1) = COP_POINTS
    return np.clip(c0 + (np.asarray(temp_out_c) - t0) * (c1 - c0) / (t1 - t0), COP_MIN, COP_MAX)


def away(day: date, hours: np.ndarray, acasa_ziua: bool) -> np.ndarray:
    """(steps,) True while nobody is home: 8-16 on workdays, unless someone stays home."""
    if acasa_ziua or day.weekday() >= 5:
        return np.zeros(len(hours), dtype=bool)
    return (hours >= 8) & (hours < 16)


def setpoints(house: ThermalHouse, day: date, dt_h: float) -> tuple[np.ndarray, np.ndarray]:
    """(heating, cooling) °C for each step of the day."""
    hours = np.arange(round(24 / dt_h)) * dt_h
    out = away(day, hours, house.acasa_ziua)
    night = (hours < 6) | (hours >= 22)
    if house.heating == "radiator":
        heat = np.where(night | out, RADIATOR_NIGHT, RADIATOR_DAY)
    else:
        heat = np.where(out, HEAT_AWAY, np.where(night, HEAT_NIGHT, HEAT_DAY))
    return heat, np.where(out, COOL_AWAY, COOL_HOME)


def _shower_kwh(house: ThermalHouse, start: date, n_days: int, dt_h: float, rng: np.random.Generator) -> np.ndarray:
    """(n_days * spd,) hot water drawn from the tank, one shower per person and day."""
    spd = round(24 / dt_h)
    draws = np.zeros(n_days * spd)
    for d in range(n_days):
        for _ in range(house.persoane):
            lo, hi = (6, 9) if rng.random() < 0.4 else (19, 23)
            first = d * spd + int(rng.uniform(lo, hi) / dt_h)
            kwh = HOT_WATER_KWH * rng.uniform(0.8, 1.2)
            n = max(1, round(SHOWER_H / dt_h))
            draws[first : first + n] += kwh / n
    return draws[: n_days * spd]


def thermal_profiles(
    house: ThermalHouse, start: date, n_days: int, dt_h: float, weather: Weather, gains_kw: np.ndarray,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Electric kW of each thermal role the house has, plus 'temp_in' and 'temp_tank' (°C), each (n_steps,)."""
    spd = round(24 / dt_h)
    n_steps = n_days * spd
    days = [start + timedelta(days=d) for d in range(n_days)]
    heat_sp, cool_sp, home = [], [], []
    for day in days:
        h, c = setpoints(house, day, dt_h)
        heat_sp.append(h)
        cool_sp.append(c)
        home.append(~away(day, np.arange(spd) * dt_h, house.acasa_ziua))
    heat_sp, cool_sp, home = np.concatenate(heat_sp), np.concatenate(cool_sp), np.concatenate(home)
    gains = gains_kw + PEOPLE_W / 1000 * house.persoane * home + SOLAR_APERTURE_M2 * weather.solar_w_m2 / 1000
    showers = _shower_kwh(house, start, n_days, dt_h, rng) if house.boiler_kw else np.zeros(n_steps)

    share = RADIATOR_SHARE if house.heating == "radiator" else 1.0
    ua, cap = house.ua_kw_k * share, house.c_kwh_k * share
    gains = gains * share
    tank_cap = TANK_L * WATER_KWH_PER_LK
    t_out, cops = weather.temp_out_c, cop(weather.temp_out_c)

    out = {"heat": np.zeros(n_steps), "ac": np.zeros(n_steps), "boiler": np.zeros(n_steps),
           "temp_in": np.zeros(n_steps), "temp_tank": np.zeros(n_steps)}
    temp, tank, radiator_on, boiler_on = heat_sp[0], BOILER_MAX_C, False, False
    for burn_in in (True, False):                      # the first day once before the window
        for t in range(spd if burn_in else n_steps):
            loss = ua + (VENT_KW_K * share if temp > VENT_FROM_C and t_out[t] < temp else 0.0)
            free = temp + dt_h / cap * (gains[t] - loss * (temp - t_out[t]))
            heat_needed = (heat_sp[t] - free) * cap / dt_h
            cool_needed = (free - cool_sp[t]) * cap / dt_h
            q_heat = q_cool = 0.0
            if house.heating == "pompa":
                q_heat = min(max(heat_needed, 0.0), house.heating_kw * cops[t])
                electric = q_heat / cops[t]
            elif house.heating == "radiator":
                radiator_on = temp < heat_sp[t] + HYSTERESIS_K if radiator_on else temp < heat_sp[t] - HYSTERESIS_K
                q_heat = electric = house.heating_kw if radiator_on else 0.0
            else:
                q_heat, electric = max(heat_needed, 0.0), 0.0
            if house.ac_kw and cool_needed > 0:
                q_cool = min(cool_needed, house.ac_kw * EER)
            temp = free + dt_h / cap * (q_heat - q_cool)

            tank_loss = TANK_LOSS_KW_K * (tank - ROOM_C)
            drawn = min(showers[t], max(tank - COLD_WATER_C, 0.0) * tank_cap)   # an empty tank gives cold water
            boiler_on = tank < BOILER_MAX_C if boiler_on else tank < BOILER_ON_C
            room = (BOILER_MAX_C - tank) * tank_cap / dt_h + tank_loss + drawn / dt_h
            boiler = min(house.boiler_kw, max(room, 0.0)) if boiler_on and house.boiler_kw else 0.0
            tank += (boiler * dt_h - drawn - tank_loss * dt_h) / tank_cap

            if not burn_in:
                out["heat"][t], out["ac"][t], out["boiler"][t] = electric, q_cool / EER, boiler
                out["temp_in"][t], out["temp_tank"][t] = temp, tank
    result = {"temp_in": out["temp_in"], "temp_tank": out["temp_tank"]}
    if house.heating:
        result[house.heating] = out["heat"]
    if house.ac_kw:
        result["ac"] = out["ac"]
    if house.boiler_kw:
        result["boiler"] = out["boiler"]
    return result
