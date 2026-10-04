"""
A house consumes what its switched-on devices consume. Devices seeded from the composition load_model
generates for the house (mode set, per-person values already multiplied) follow the schedule
vpp_core.load_model draws for each day; devices added by hand draw power_w while on.
Schedules are drawn in device order from house_rng(seed + ordinal(day), house_id), the same stream
generate_scenario uses for that day, so a house with its seeded devices consumes exactly what the
scenario generators would give it.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from app.db.models import DeviceModel, HouseModel
from vpp_core.load_model import Appliance, appliance_profile, house_rng, parse_intervals


def appliance_of(device: DeviceModel) -> Appliance:
    return Appliance(
        dispozitiv=device.name, putere_w=device.power_w, mod=device.mode, ore_pe_zi=device.hours_per_day,
        cicluri_pe_saptamana=device.cycles_per_week, durata_ciclu_min=device.cycle_minutes,
        intervale=parse_intervals(device.interval), sezon=device.season, flexibil=not device.critical,
    )


def _schedule_key(devices: list[DeviceModel]) -> tuple:
    return tuple((d.id, d.power_w, d.mode, d.hours_per_day, d.cycles_per_week, d.cycle_minutes, d.interval, d.season)
                 for d in devices)


class DeviceProfiles:
    """kW schedules of the scheduled devices, one day at a time, cached per (day, house, seed)."""

    def __init__(self, dt_h: float):
        self.dt_h = dt_h
        self._cache: dict[tuple[date, int, int], tuple[tuple, dict[int, np.ndarray]]] = {}

    @property
    def steps_per_day(self) -> int:
        return round(24 / self.dt_h)

    def keep_days(self, days: tuple[date, ...]) -> None:
        self._cache = {key: value for key, value in self._cache.items() if key[0] in days}

    def _day(self, house: HouseModel, day: date, seed: int) -> dict[int, np.ndarray]:
        scheduled = [d for d in house.devices if d.mode]
        key = _schedule_key(scheduled)
        cached = self._cache.get((day, house.id, seed))
        if cached is None or cached[0] != key:
            rng = house_rng(seed + day.toordinal(), house.id)
            profiles = {d.id: appliance_profile(appliance_of(d), day, 1, self.dt_h, rng) for d in scheduled}
            cached = (key, profiles)
            self._cache[(day, house.id, seed)] = cached
        return cached[1]

    def device_kw(self, house: HouseModel, days: tuple[date, ...], seed: int) -> dict[int, np.ndarray]:
        """device id -> (len(days) * steps_per_day,) kW the device draws while it is on."""
        per_day = [self._day(house, day, seed) for day in days]
        n_steps = len(days) * self.steps_per_day
        out = {}
        for d in house.devices:
            if d.mode:
                out[d.id] = np.concatenate([profiles[d.id] for profiles in per_day])
            else:
                out[d.id] = np.full(n_steps, d.power_w / 1000.0)
        return out


def house_load(house: HouseModel, kw: dict[int, np.ndarray], n_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible) kW of the switched-on devices."""
    critical, flexible = np.zeros(n_steps), np.zeros(n_steps)
    for d in house.devices:
        if d.status_on:
            target = critical if d.critical else flexible
            target += kw[d.id]
    return critical, flexible
