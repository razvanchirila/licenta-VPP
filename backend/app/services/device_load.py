"""
A house consumes what its switched-on devices consume. Devices seeded from the composition load_model
generates for the house (mode set, per-person values already multiplied) follow the schedule
vpp_core.load_model draws for each day, the thermal ones (heat pump, radiators, AC, boiler) the thermal model
under that day's weather; devices added by hand draw power_w while on.
Each day is drawn with house_profiles on house_rng(seed + ordinal(day), house_id), the stream
generate_scenario uses for that day, so a house with its seeded devices consumes exactly what the
scenario generators would give it.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from app.db.models import DeviceModel, HouseModel
from vpp_core.load_model import Appliance, House, house_profiles, house_rng, programs_from_json
from vpp_core.thermal import Weather


def appliance_of(device: DeviceModel) -> Appliance:
    return Appliance(
        dispozitiv=device.name, putere_w=device.power_w, tip=device.mode, programe=programs_from_json(device.program),
        flexibil=not device.critical,
    )


def house_of(house: HouseModel, scheduled: list[DeviceModel]) -> House:
    return House(house.id, house.description, house.people, house.home_daytime, house.heating, house.insulation,
                 tuple(appliance_of(d) for d in scheduled))


def _schedule_key(house: HouseModel, devices: list[DeviceModel]) -> tuple:
    return (house.people, house.home_daytime, house.insulation,
            tuple((d.id, d.name, d.power_w, d.mode, d.program) for d in devices))


class DeviceProfiles:
    """kW schedules of the scheduled devices and the indoor temperature, one day at a time, cached per
    (day, house, seed)."""

    def __init__(self, dt_h: float):
        self.dt_h = dt_h
        self._cache: dict[tuple[date, int, int], tuple[tuple, dict[str, np.ndarray]]] = {}

    @property
    def steps_per_day(self) -> int:
        return round(24 / self.dt_h)

    def keep_days(self, days: tuple[date, ...]) -> None:
        self._cache = {key: value for key, value in self._cache.items() if key[0] in days}

    def _day(self, house: HouseModel, day: date, seed: int, weather: Weather | None) -> dict[str, np.ndarray]:
        scheduled = [d for d in house.devices if d.mode]
        key = _schedule_key(house, scheduled)
        cached = self._cache.get((day, house.id, seed))
        if cached is None or cached[0] != key:
            rng = house_rng(seed + day.toordinal(), house.id)
            cached = (key, house_profiles(house_of(house, scheduled), day, 1, self.dt_h, rng, weather))
            self._cache[(day, house.id, seed)] = cached
        return cached[1]

    def device_kw(self, house: HouseModel, days: tuple[date, ...], seed: int,
                  weather: dict[date, Weather] | None = None) -> dict[int, np.ndarray]:
        """device id -> (len(days) * steps_per_day,) kW the device draws while it is on."""
        weather = weather or {}
        per_day = [self._day(house, day, seed, weather.get(day)) for day in days]
        n_steps = len(days) * self.steps_per_day
        out = {}
        for d in house.devices:
            if d.mode:
                out[d.id] = np.concatenate([profiles[d.name] for profiles in per_day])
            else:
                out[d.id] = np.full(n_steps, d.power_w / 1000.0)
        return out

    def temp_in(self, house: HouseModel, days: tuple[date, ...], seed: int,
                weather: dict[date, Weather] | None = None) -> np.ndarray | None:
        """(len(days) * steps_per_day,) indoor °C, None without weather."""
        weather = weather or {}
        per_day = [self._day(house, day, seed, weather.get(day)) for day in days]
        if any("temp_in" not in profiles for profiles in per_day):
            return None
        return np.concatenate([profiles["temp_in"] for profiles in per_day])


def house_load(house: HouseModel, kw: dict[int, np.ndarray], n_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible) kW of the switched-on devices."""
    critical, flexible = np.zeros(n_steps), np.zeros(n_steps)
    for d in house.devices:
        if d.status_on:
            target = critical if d.critical else flexible
            target += kw[d.id]
    return critical, flexible
