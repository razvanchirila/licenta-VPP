"""
Bottom-up household load: a house consumes what its appliances consume. backend/data/dispozitive.csv is a
catalog with one row per device type; every house id draws its own composition from it: the number of people
(backend/data/gospodarii.csv), then each device independently with its probabilitate. The composition depends
only on the house id, so house 3 is the same house in every scenario, season and in the app.

    continuu  putere_w all the time
    zilnic    ore_pe_zi hours a day split over the intervals by weight: one block per interval
              (x U(0.9, 1.1) each day) starting at a random time inside it
    ciclic    cicluri_pe_saptamana runs of durata_ciclu_min (x U(0.9, 1.1)) per 7-day block, on random days;
              each run picks an interval with probability = its weight, then a random start inside it
              (the run may end after the interval)
    termic    ore_pe_zi x seasonal factor hours per day (x U(0.9, 1.1)) split over the intervals by weight, as
              half-hour blocks spread evenly over each interval with random jitter, like a thermostat; factor 1
              in its season (sezon), 0.5 in the two shoulder seasons, 0 in the opposite one; tot_anul = 1 all year

intervale: "start-end:weight" separated by spaces, e.g. "8-12:40 17-22:60"; weights are normalised, a missing
one counts as 100; an end at or before the start wraps past midnight ("22-6"). pe_persoana = da: ore_pe_zi and
cicluri_pe_saptamana are per person and get multiplied by the people in the house.

Seasons from the month: iarna nov-mar, vara iun-aug, intermediar otherwise. Every mode is energy-consistent:
an appliance of P W running h hours per day draws P x h Wh per day on average. Blocks may cross midnight;
they are generated for the day before and after the window too, so the profile is stationary at the edges.

Run from backend/:   python -m vpp_core.load_model [--out results/consum] [--seed 0] [--dt 0.25] [--houses 10]
Output: consum_case.csv (people, devices, kWh/day per season, kWh/year, share flexibil), dispozitive_case.csv
(the generated devices of every house with their expected energy), profil_zi.png, consum_anual.png.
"""
from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from vpp_core.params import CommunityParams

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DISPOZITIVE_CSV = DATA_DIR / "dispozitive.csv"
GOSPODARII_CSV = DATA_DIR / "gospodarii.csv"
COLUMNS = ("dispozitiv", "putere_w", "mod", "ore_pe_zi", "cicluri_pe_saptamana", "durata_ciclu_min",
           "intervale", "sezon", "probabilitate", "pe_persoana", "flexibil")
HOUSEHOLD_COLUMNS = ("persoane", "pondere")
MODES = ("continuu", "zilnic", "ciclic", "termic")
SEZOANE = ("tot_anul", "iarna", "vara")
SEASONS = ("iarna", "intermediar", "vara")
SEASON_LABELS = {"iarna": "iarnă (nov–mar)", "intermediar": "primăvară / toamnă", "vara": "vară (iun–aug)"}
SEASON_DAYS = {"iarna": 151, "intermediar": 122, "vara": 92}   # non-leap year
WINTER_MONTHS, SUMMER_MONTHS = (11, 12, 1, 2, 3), (6, 7, 8)
HOURS_JITTER = 0.10          # daily hours / cycle length x U(1 - j, 1 + j)
SHOULDER_FACTOR = 0.5
THERMAL_BLOCK_H = 0.5
DEFAULT_WEIGHT = 100.0
COMPOSITION_SEED = 0
COMPOSITION_TAG = 0xCA5A     # third seed word, so a composition stream is never a house_rng(seed, id) stream
MODE_COLORS = {"continuu": "#2a78d6", "zilnic": "#eda100", "ciclic": "#1baf7a", "termic": "#eb6834"}
YEAR = 2023

Interval = tuple[float, float, float]   # start h, end h (> 24 when it wraps past midnight), weight as written


def season_of(day: date) -> str:
    if day.month in WINTER_MONTHS:
        return "iarna"
    return "vara" if day.month in SUMMER_MONTHS else "intermediar"


def thermal_factor(sezon: str, season: str) -> float:
    if sezon == "tot_anul" or sezon == season:
        return 1.0
    return SHOULDER_FACTOR if season == "intermediar" else 0.0


def parse_interval(text: str) -> tuple[float, float]:
    """'18-23' -> (18, 23); '22-6' -> (22, 30): an end at or before the start wraps past midnight."""
    try:
        start, end = (float(part.replace(",", ".")) for part in text.strip().split("-"))
    except ValueError:
        raise ValueError(f"interval {text!r}: astept forma 'ora_start-ora_sfarsit', de exemplu 18-23") from None
    if not (0 <= start < 24 and 0 < end <= 24):
        raise ValueError(f"interval {text!r}: orele trebuie sa fie intre 0 si 24")
    if end <= start:
        end += 24
    return start, end


def format_interval(interval: tuple[float, float]) -> str:
    """Inverse of parse_interval: (22, 30) -> '22-6'."""
    start, end = interval
    return f"{start:g}-{end - 24 if end > 24 else end:g}"


def parse_intervals(text: str) -> tuple[Interval, ...]:
    """'8-12:40 17-22:60' -> ((8, 12, 40), (17, 22, 60)); '8-21' -> ((8, 21, 100),)."""
    parts = text.split()
    if not parts:
        raise ValueError("intervale gol: astept de exemplu 8-21 sau 8-12:40 17-22:60")
    intervals = []
    for part in parts:
        span, _, weight = part.partition(":")
        start, end = parse_interval(span)
        value = _number(weight, f"ponderea din {part!r}") if weight else DEFAULT_WEIGHT
        if value <= 0:
            raise ValueError(f"interval {part!r}: ponderea trebuie sa fie > 0")
        intervals.append((start, end, value))
    return tuple(intervals)


def format_intervals(intervals: tuple[Interval, ...]) -> str:
    """Inverse of parse_intervals (a single interval is written without its weight)."""
    if len(intervals) == 1:
        return format_interval(intervals[0][:2])
    return " ".join(f"{format_interval((start, end))}:{weight:.12g}" for start, end, weight in intervals)


def describe_intervals(intervals: tuple[Interval, ...]) -> str:
    """For people: '8-12 (40%), 17-22 (60%)'; a single interval stays '8-21'."""
    if len(intervals) == 1:
        return format_interval(intervals[0][:2])
    total = sum(weight for _, _, weight in intervals)
    return ", ".join(f"{format_interval((start, end))} ({100 * weight / total:.0f}%)"
                     for start, end, weight in intervals)


@dataclass(frozen=True)
class Appliance:
    """One device of one house; ore_pe_zi and cicluri_pe_saptamana are for the whole house."""

    dispozitiv: str
    putere_w: float
    mod: str
    ore_pe_zi: float = 0.0
    cicluri_pe_saptamana: float = 0.0
    durata_ciclu_min: float = 0.0
    intervale: tuple[Interval, ...] = ((0.0, 24.0, DEFAULT_WEIGHT),)
    sezon: str = "tot_anul"
    flexibil: bool = False

    @property
    def kw(self) -> float:
        return self.putere_w / 1000.0

    @property
    def windows(self) -> list[tuple[float, float, float]]:
        """(start, end, share) with the weights normalised to sum 1."""
        total = sum(weight for _, _, weight in self.intervale)
        return [(start, end, weight / total) for start, end, weight in self.intervale]

    def hours_per_day(self, season: str) -> float:
        """Expected running hours per day in that season (the mean of the random draws)."""
        if self.mod == "continuu":
            return 24.0
        if self.mod == "zilnic":
            return self.ore_pe_zi
        if self.mod == "ciclic":
            return self.cicluri_pe_saptamana / 7 * self.durata_ciclu_min / 60
        return self.ore_pe_zi * thermal_factor(self.sezon, season)

    def kwh_per_day(self, season: str) -> float:
        return self.kw * self.hours_per_day(season)

    def kwh_per_year(self) -> float:
        return sum(self.kwh_per_day(season) * SEASON_DAYS[season] for season in SEASONS)


@dataclass(frozen=True)
class CatalogDevice:
    """A row of dispozitive.csv: the device for one person when pe_persoana, the chance a house owns it."""

    appliance: Appliance
    probabilitate: float = 1.0
    pe_persoana: bool = False

    def for_people(self, persoane: int) -> Appliance:
        if not self.pe_persoana:
            return self.appliance
        app = self.appliance
        return replace(app, ore_pe_zi=app.ore_pe_zi * persoane,
                       cicluri_pe_saptamana=app.cicluri_pe_saptamana * persoane)


@dataclass(frozen=True)
class Catalog:
    devices: tuple[CatalogDevice, ...]
    persoane: tuple[int, ...] = (1,)
    ponderi: tuple[float, ...] = (1.0,)    # chance of each persoane value, sums to 1


@dataclass(frozen=True)
class House:
    casa: int
    persoane: int
    appliances: tuple[Appliance, ...]

    def kwh_per_day(self, season: str) -> float:
        return sum(app.kwh_per_day(season) for app in self.appliances)

    def kwh_per_year(self) -> float:
        return sum(app.kwh_per_year() for app in self.appliances)


# ----------------------------------------------------------------------------- CSV

def _number(text: str, name: str) -> float:
    if not text:
        return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        raise ValueError(f"{name} = {text!r} nu este un numar") from None


def _yes_no(text: str, name: str) -> bool:
    value = text.lower()
    if value not in ("da", "nu"):
        raise ValueError(f"{name} = {text!r}, astept da sau nu")
    return value == "da"


def _check_fits(app: Appliance, hours: float, people: str = "") -> None:
    """zilnic / termic: the hours that fall in each interval must fit in it."""
    for start, end, share in app.windows:
        if hours * share > end - start + 1e-9:
            raise ValueError(f"{people}{hours * share:g} h din ore_pe_zi cad in intervalul "
                             f"{format_interval((start, end))}, care are doar {end - start:g} h")


def _parse_row(row: dict[str, str]) -> CatalogDevice:
    mod, sezon = row["mod"].lower(), (row["sezon"] or "tot_anul").lower()
    if mod not in MODES:
        raise ValueError(f"mod = {row['mod']!r}, astept unul din {MODES}")
    if sezon not in SEZOANE:
        raise ValueError(f"sezon = {row['sezon']!r}, astept unul din {SEZOANE}")
    if not row["dispozitiv"]:
        raise ValueError("dispozitiv gol")
    if not row["probabilitate"]:
        raise ValueError("probabilitate lipseste (0 = nicio casa, 1 = toate casele)")
    app = Appliance(
        dispozitiv=row["dispozitiv"],
        putere_w=_number(row["putere_w"], "putere_w"),
        mod=mod,
        ore_pe_zi=_number(row["ore_pe_zi"], "ore_pe_zi"),
        cicluri_pe_saptamana=_number(row["cicluri_pe_saptamana"], "cicluri_pe_saptamana"),
        durata_ciclu_min=_number(row["durata_ciclu_min"], "durata_ciclu_min"),
        intervale=parse_intervals(row["intervale"] or "0-24"),
        sezon=sezon,
        flexibil=_yes_no(row["flexibil"], "flexibil"),
    )
    device = CatalogDevice(app, _number(row["probabilitate"], "probabilitate"),
                           _yes_no(row["pe_persoana"] or "nu", "pe_persoana"))
    if app.putere_w <= 0:
        raise ValueError("putere_w trebuie sa fie > 0")
    if not 0 <= device.probabilitate <= 1:
        raise ValueError("probabilitate trebuie sa fie intre 0 si 1")
    if mod in ("zilnic", "termic"):
        if app.ore_pe_zi <= 0:
            raise ValueError("ore_pe_zi trebuie sa fie > 0")
        _check_fits(app, app.ore_pe_zi)
    if mod == "ciclic":
        if app.cicluri_pe_saptamana <= 0 or not 0 < app.durata_ciclu_min <= 24 * 60:
            raise ValueError("ciclic: cicluri_pe_saptamana > 0 si durata_ciclu_min intre 0 si 1440")
    return device


def _read_rows(path: Path, columns: tuple[str, ...]) -> Iterator[tuple[int, dict[str, str]]]:
    """(line, row) of a ';' separated UTF-8 file (BOM allowed) with exactly `columns`; blank rows skipped."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        header = [name.strip().lower() for name in reader.fieldnames or []]
        if header != list(columns):
            raise ValueError(f"{path}: antetul trebuie sa fie {';'.join(columns)}")
        for line, raw in enumerate(reader, start=2):
            row = {name.strip().lower(): (value or "").strip() for name, value in raw.items() if name}
            if any(row.values()):
                yield line, row


def load_devices(path: Path | str = DISPOZITIVE_CSV, max_people: int = 1) -> tuple[CatalogDevice, ...]:
    """Reads the catalog (decimals with '.' or ','); a pe_persoana device must also fit for max_people."""
    path = Path(path)
    devices = []
    for line, row in _read_rows(path, COLUMNS):
        try:
            device = _parse_row(row)
            app = device.appliance
            if device.pe_persoana and app.mod in ("zilnic", "termic"):
                _check_fits(app, app.ore_pe_zi * max_people, f"pentru {max_people} persoane: ")
        except ValueError as error:
            raise ValueError(f"{path.name}, randul {line}: {error}") from None
        devices.append(device)
    if not devices:
        raise ValueError(f"{path.name}: niciun dispozitiv")
    return tuple(devices)


def load_households(path: Path | str = GOSPODARII_CSV) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """gospodarii.csv -> (people options, their normalised weights)."""
    path = Path(path)
    people, weights = [], []
    for line, row in _read_rows(path, HOUSEHOLD_COLUMNS):
        try:
            count, weight = _number(row["persoane"], "persoane"), _number(row["pondere"], "pondere")
            if count < 1 or count != int(count):
                raise ValueError("persoane trebuie sa fie un numar intreg >= 1")
            if weight <= 0:
                raise ValueError("pondere trebuie sa fie > 0")
            if int(count) in people:
                raise ValueError(f"persoane = {int(count)} apare de doua ori")
        except ValueError as error:
            raise ValueError(f"{path.name}, randul {line}: {error}") from None
        people.append(int(count))
        weights.append(weight)
    if not people:
        raise ValueError(f"{path.name}: niciun rand")
    total = sum(weights)
    return tuple(people), tuple(weight / total for weight in weights)


def load_catalog(path: Path | str = DISPOZITIVE_CSV, households: Path | str = GOSPODARII_CSV) -> Catalog:
    people, weights = load_households(households)
    return Catalog(load_devices(path, max(people)), people, weights)


# ----------------------------------------------------------------------------- composition

def composition_rng(house_id: int) -> np.random.Generator:
    return np.random.default_rng([COMPOSITION_TAG, COMPOSITION_SEED, house_id])


def compose_house(house_id: int, catalog: Catalog) -> House:
    """The people, then one independent draw per catalog device; depends only on house_id and the catalog."""
    rng = composition_rng(house_id)
    persoane = catalog.persoane[int(rng.choice(len(catalog.persoane), p=catalog.ponderi))]
    owned = rng.random(len(catalog.devices)) < np.array([device.probabilitate for device in catalog.devices])
    appliances = tuple(device.for_people(persoane) for device, has in zip(catalog.devices, owned, strict=True) if has)
    return House(house_id, persoane, appliances)


def compose_houses(house_ids: Iterable[int], catalog: Catalog | None = None) -> list[House]:
    catalog = catalog or load_catalog()
    return [compose_house(house_id, catalog) for house_id in house_ids]


# ----------------------------------------------------------------------------- profiles

def _steps_per_day(dt_h: float) -> int:
    steps = round(24 / dt_h)
    if dt_h <= 0 or abs(steps * dt_h - 24) > 1e-9:
        raise ValueError("24 h must be a whole number of steps")
    return steps


def _add_block(arr: np.ndarray, start_h: float, duration_h: float, kw: float, dt_h: float) -> None:
    """kw over [start_h, start_h + duration_h), hours from arr[0]; edge steps get their fraction, energy exact."""
    if duration_h <= 0:
        return
    end_h = start_h + duration_h
    first, last = max(int(np.floor(start_h / dt_h)), 0), min(int(np.ceil(end_h / dt_h)), len(arr))
    if last <= first:
        return
    edges = np.arange(first, last + 1) * dt_h
    overlap = np.clip(np.minimum(edges[1:], end_h) - np.maximum(edges[:-1], start_h), 0, None)
    arr[first:last] += kw * overlap / dt_h


def _jitter(rng: np.random.Generator) -> float:
    return rng.uniform(1 - HOURS_JITTER, 1 + HOURS_JITTER)


def _cycles_per_day(cycles_per_week: float, rng: np.random.Generator) -> np.ndarray:
    """(7,) cycles on each day of a week block: whole weeks get exactly the count, a fraction is drawn."""
    whole = int(cycles_per_week)
    n = whole + int(rng.random() < cycles_per_week - whole)
    counts = np.full(7, n // 7)
    if n % 7:
        counts[rng.choice(7, n % 7, replace=False)] += 1
    return counts


def appliance_profile(app: Appliance, start: date, n_days: int, dt_h: float, rng: np.random.Generator) -> np.ndarray:
    """(n_days * steps_per_day,) kW of one appliance from `start`."""
    spd = _steps_per_day(dt_h)
    n_steps = n_days * spd
    if app.mod == "continuu":
        return np.full(n_steps, app.kw)
    buffer = np.zeros(n_steps + 2 * spd)              # one day before and after, for blocks crossing midnight
    windows = app.windows
    shares = np.array([share for _, _, share in windows])
    week_schedule: dict[int, np.ndarray] = {}         # 7-day blocks counted from `start`; day -1 is its own block
    for d in range(-1, n_days + 1):
        day_h = (d + 1) * 24.0
        if app.mod == "zilnic":
            for lo, hi, share in windows:
                hours = min(app.ore_pe_zi * share * _jitter(rng), hi - lo)
                _add_block(buffer, day_h + rng.uniform(lo, hi - hours), hours, app.kw, dt_h)
        elif app.mod == "ciclic":
            week = d // 7
            if week not in week_schedule:
                week_schedule[week] = _cycles_per_day(app.cicluri_pe_saptamana, rng)
            for _ in range(week_schedule[week][d % 7]):
                duration = app.durata_ciclu_min / 60 * _jitter(rng)
                lo, hi, _ = windows[int(rng.choice(len(windows), p=shares)) if len(windows) > 1 else 0]
                _add_block(buffer, day_h + rng.uniform(lo, hi), duration, app.kw, dt_h)
        else:
            factor = thermal_factor(app.sezon, season_of(start + timedelta(days=d)))
            if factor == 0:
                continue
            for lo, hi, share in windows:
                hours = min(app.ore_pe_zi * factor * share * _jitter(rng), hi - lo)
                n_blocks = max(1, round(hours / THERMAL_BLOCK_H))
                block, spacing = hours / n_blocks, (hi - lo) / n_blocks
                for k in range(n_blocks):
                    offset = lo + k * spacing + rng.uniform(0, spacing - block)
                    _add_block(buffer, day_h + offset, block, app.kw, dt_h)
    return buffer[spd : spd + n_steps]


def house_load_profile(
    appliances: Iterable[Appliance], start: date, n_days: int, dt_h: float, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible) kW, each (n_days * steps_per_day,): flexibil = da goes to the flexible part."""
    n_steps = n_days * _steps_per_day(dt_h)
    critical, flexible = np.zeros(n_steps), np.zeros(n_steps)
    for app in appliances:
        target = flexible if app.flexibil else critical
        target += appliance_profile(app, start, n_days, dt_h, rng)
    return critical, flexible


def house_rng(seed: int, house_id: int) -> np.random.Generator:
    """One stream per house, so a house's profile does not depend on which other houses are simulated."""
    return np.random.default_rng([seed, house_id])


def community_load(
    community: CommunityParams, start: date, n_days: int, dt_h: float, seed: int, catalog: Catalog | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible), each (n_houses, n_steps) kW: the composition of each house id, run with the
    timing stream of that id, so a house's load does not depend on which other houses are simulated."""
    houses = compose_houses((house.id for house in community.houses), catalog)
    n_steps = n_days * _steps_per_day(dt_h)
    critical, flexible = np.zeros((community.n_houses, n_steps)), np.zeros((community.n_houses, n_steps))
    for i, house in enumerate(houses):
        critical[i], flexible[i] = house_load_profile(house.appliances, start, n_days, dt_h,
                                                      house_rng(seed, house.casa))
    return critical, flexible


# ----------------------------------------------------------------------------- validation report

def simulate_year(houses: list[House], dt_h: float, seed: int) -> dict[int, dict[str, np.ndarray]]:
    """house -> mode -> (365 * spd,) kW for YEAR, plus 'flexibil' and 'total'."""
    start = date(YEAR, 1, 1)
    result = {}
    for house in houses:
        rng = house_rng(seed, house.casa)
        series = {mode: np.zeros(365 * _steps_per_day(dt_h)) for mode in MODES}
        flexible = np.zeros_like(series["continuu"])
        for app in house.appliances:
            profile = appliance_profile(app, start, 365, dt_h, rng)
            series[app.mod] += profile
            if app.flexibil:
                flexible += profile
        series["flexibil"] = flexible
        series["total"] = sum(series[mode] for mode in MODES)
        result[house.casa] = series
    return result


def house_rows(houses: list[House], year: dict[int, dict[str, np.ndarray]], dt_h: float) -> list[dict]:
    spd = _steps_per_day(dt_h)
    days = [date(YEAR, 1, 1) + timedelta(days=d) for d in range(365)]
    season_days = {season: [d for d, day in enumerate(days) if season_of(day) == season] for season in SEASONS}
    rows = []
    for house in houses:
        series = year[house.casa]
        daily = series["total"].reshape(365, spd).sum(axis=1) * dt_h
        annual = float(series["total"].sum() * dt_h)
        row = {"casa": house.casa, "persoane": house.persoane, "dispozitive": len(house.appliances)}
        for season in SEASONS:
            row[f"kwh_zi_{season}"] = float(daily[season_days[season]].mean())
        row["kwh_an"] = annual
        for mode in MODES:
            row[f"kwh_an_{mode}"] = float(series[mode].sum() * dt_h)
        row["cota_flexibil"] = float(series["flexibil"].sum() * dt_h / annual) if annual else 0.0
        row["kwh_an_calculat"] = house.kwh_per_year()
        row["lista"] = ", ".join(app.dispozitiv for app in house.appliances)
        rows.append(row)
    return rows


def device_rows(houses: list[House]) -> list[dict]:
    """Expected values of every generated device, per-person counts already multiplied."""
    rows = []
    for house in houses:
        for app in house.appliances:
            row = {"casa": house.casa, "persoane": house.persoane, "dispozitiv": app.dispozitiv,
                   "putere_w": app.putere_w, "mod": app.mod, "ore_pe_zi": app.ore_pe_zi,
                   "cicluri_pe_saptamana": app.cicluri_pe_saptamana, "durata_ciclu_min": app.durata_ciclu_min,
                   "intervale": describe_intervals(app.intervale), "sezon": app.sezon,
                   "flexibil": "da" if app.flexibil else "nu"}
            for season in SEASONS:
                row[f"kwh_zi_{season}"] = app.kwh_per_day(season)
            row["kwh_an"] = app.kwh_per_year()
            rows.append(row)
    return rows


CSV_KEYS = ["casa", "persoane", "dispozitive", *[f"kwh_zi_{season}" for season in SEASONS], "kwh_an",
            *[f"kwh_an_{mode}" for mode in MODES], "cota_flexibil", "kwh_an_calculat", "lista"]
DEVICE_KEYS = ["casa", "persoane", "dispozitiv", "putere_w", "mod", "ore_pe_zi", "cicluri_pe_saptamana",
               "durata_ciclu_min", "intervale", "sezon", "flexibil", *[f"kwh_zi_{season}" for season in SEASONS],
               "kwh_an"]
PROFILE_HOUSES = (1, 2, 4)


def daily_profile_chart(year: dict[int, dict[str, np.ndarray]], dt_h: float, path: Path) -> None:
    """Mean winter-workday profile of PROFILE_HOUSES against the DEER profile scaled to the same daily energy."""
    from vpp_core import data_sources as ds
    from vpp_core.reporting import INK, MUTED, plot_style

    plt = plot_style()
    spd = _steps_per_day(dt_h)
    days = [date(YEAR, 1, 1) + timedelta(days=d) for d in range(365)]
    winter_workdays = [d for d, day in enumerate(days) if ds.deer_day_type(day) == 2]
    deer = ds.load_deer_weights()[:, 2]
    deer = deer.reshape(spd, -1).sum(axis=1) if spd <= 96 else np.repeat(deer / (spd // 96), spd // 96)
    hours = (np.arange(spd) + 0.5) * dt_h
    houses = [h for h in PROFILE_HOUSES if h in year]
    fig, axes = plt.subplots(1, len(houses), figsize=(3.2 * len(houses) + 0.6, 3.2), sharey=True, squeeze=False)
    for ax, house_id in zip(axes[0], houses, strict=True):
        series = year[house_id]["total"].reshape(365, spd)[winter_workdays]
        mean_profile = series.mean(axis=0)
        daily_kwh = mean_profile.sum() * dt_h
        ax.plot(hours, mean_profile, color=MODE_COLORS["ciclic"], linewidth=1.6, label="model din dispozitive")
        ax.plot(hours, deer * daily_kwh / dt_h, color=MUTED, linestyle="--", linewidth=1.2,
                label="profil DEER, aceeași energie")
        ax.set_title(f"Casa {house_id}: {daily_kwh:.1f} kWh/zi", fontsize=10, color=INK, loc="left")
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 6))
        ax.set_xlabel("Ora")
    axes[0, 0].set_ylabel("Putere medie [kW]")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Profil zilnic mediu, zile lucrătoare de iarnă {YEAR} (medie pe {len(winter_workdays)} zile)",
                 fontsize=9, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def annual_chart(rows: list[dict], path: Path) -> None:
    from vpp_core.reporting import INK, plot_style

    plt = plot_style()
    fig, ax = plt.subplots(figsize=(max(8, 0.8 * len(rows)), 3.6))
    x = np.arange(len(rows))
    bottom = np.zeros(len(rows))
    for mode in MODES:
        values = np.array([row[f"kwh_an_{mode}"] for row in rows])
        ax.bar(x, values, 0.7, bottom=bottom, color=MODE_COLORS[mode], label=mode)
        bottom += values
    for xi, row in zip(x, rows, strict=True):
        ax.text(xi, row["kwh_an"] + 40, f"{row['kwh_an']:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x, [f"Casa {row['casa']}\n({row['persoane']} pers.)" for row in rows])
    ax.set_ylabel("Consum anual [kWh]")
    ax.set_ylim(0, bottom.max() * 1.12)
    ax.grid(axis="x", visible=False)
    ax.set_title("Consum anual pe casă, case generate din catalogul dispozitive.csv, pe categorii",
                 fontsize=9, loc="left", color=INK)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def print_rows(rows: list[dict]) -> None:
    print(f"{'casa':>4} {'pers':>4} {'disp':>4} {'iarna':>7} {'interm':>7} {'vara':>7} {'kWh/an':>8} {'calc':>8} "
          f"{'flex':>6}")
    for row in rows:
        print(f"{row['casa']:>4} {row['persoane']:>4} {row['dispozitive']:>4} {row['kwh_zi_iarna']:>7.1f} "
              f"{row['kwh_zi_intermediar']:>7.1f} {row['kwh_zi_vara']:>7.1f} {row['kwh_an']:>8.0f} "
              f"{row['kwh_an_calculat']:>8.0f} {100 * row['cota_flexibil']:>5.0f}%")
    print()
    for row in rows:
        print(f"casa {row['casa']}: {row['lista']}")
    annual = np.array([row["kwh_an"] for row in rows])
    mean_winter = np.mean([row["kwh_zi_iarna"] for row in rows])
    print(f"\nmedie pe casa: {annual.mean():.0f} kWh/an (min {annual.min():.0f}, max {annual.max():.0f}, "
          f"abatere standard {annual.std():.0f}), iarna {mean_winter:.1f} kWh/zi")


def main(argv: list[str] | None = None) -> None:
    from vpp_core.reporting import RESULTS_DIR, utf8_console, write_csv

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "consum")
    parser.add_argument("--csv", type=Path, default=DISPOZITIVE_CSV, help="alt catalog dispozitive.csv")
    parser.add_argument("--gospodarii", type=Path, default=GOSPODARII_CSV, help="alt fisier gospodarii.csv")
    parser.add_argument("--houses", type=int, default=10, help="casele 1..N")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dt", type=float, default=0.25, help="pasul de timp in ore")
    args = parser.parse_args(argv)
    utf8_console()
    args.out.mkdir(parents=True, exist_ok=True)
    houses = compose_houses(range(1, args.houses + 1), load_catalog(args.csv, args.gospodarii))
    year = simulate_year(houses, args.dt, args.seed)
    rows = house_rows(houses, year, args.dt)
    write_csv(rows, CSV_KEYS, args.out / "consum_case.csv")
    write_csv(device_rows(houses), DEVICE_KEYS, args.out / "dispozitive_case.csv")
    daily_profile_chart(year, args.dt, args.out / "profil_zi.png")
    annual_chart(rows, args.out / "consum_anual.png")
    print_rows(rows)
    print(f"\nRezultate scrise in {args.out}")


if __name__ == "__main__":
    main()
