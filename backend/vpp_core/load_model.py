"""
Bottom-up household load: a house consumes what its devices consume. backend/data/dispozitive.csv is the
device catalog, backend/data/case.csv the neighbourhood: one row per house with its people, whether someone is
home during workdays, its heating and the optional devices it owns. House id k > N reuses row ((k - 1) mod N) + 1,
so a larger community repeats the neighbourhood with its own timings.

A device may take several catalog rows (one per `moment`, e.g. plita cina / plita pranz); all its rows share
cine, pe_persoana, tip, putere_w and flexibil. Which devices a house gets:

    cine = toti       every house
    cine = ales       the houses that list it in case.csv
    cine = incalzire  the house whose incalzire names it (gaz = none)

and of their rows only those with acasa = oricand, or da / nu matching the house's acasa_ziua.

    permanent  putere_w all the time
    interval   putere_w over the whole interval; each end moves by U(-0.5, 0.5) h every day
    durata     porniri_pe_saptamana runs of durata_min (x U(0.9, 1.1)) per 7-day block, spread over the
               block's eligible days; each run starts at a random time inside the interval and may end after it
               faze (optional, "minute:W ...", e.g. "10:2000 209:40"): the run goes through these power steps
               instead of putere_w the whole time; the minutes add up to durata_min
    termic     heating, cooling and hot water from vpp_core.thermal, driven by the outdoor temperature, the sun
               and the heat the other devices give off; without weather (Weather) they draw nothing

zile (toate / lucru / weekend) and sezon (tot_anul / iarna / intermediar / vara) restrict the days a row runs.
pe_persoana = da multiplies porniri_pe_saptamana by the people in the house. An interval whose end is at or
before its start wraps past midnight ("18-7"). Seasons from the month: iarna nov-mar, vara iun-aug,
intermediar otherwise. Blocks may cross midnight; the day before and after the window are generated too.

Run from backend/:   python -m vpp_core.load_model [--out results/consum] [--seed 0] [--dt 0.25] [--houses 10]
Output: consum_case.csv, dispozitive_case.csv, profil_zi.png, consum_anual.png.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from vpp_core import thermal
from vpp_core.params import CommunityParams
from vpp_core.thermal import Weather

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DISPOZITIVE_CSV = DATA_DIR / "dispozitive.csv"
CASE_CSV = DATA_DIR / "case.csv"
COLUMNS = ("dispozitiv", "moment", "cine", "pe_persoana", "acasa", "tip", "putere_w", "interval", "durata_min",
           "porniri_pe_saptamana", "zile", "sezon", "flexibil", "sursa", "faze")
HOUSE_COLUMNS = ("casa", "descriere", "persoane", "acasa_ziua", "incalzire", "izolatie", "dispozitive")
TIPURI = ("permanent", "interval", "durata", "termic")
CINE = ("toti", "ales", "incalzire")
ACASA = ("oricand", "da", "nu")
ZILE = ("toate", "lucru", "weekend")
SEZOANE = ("tot_anul", "iarna", "intermediar", "vara")
SEASONS = ("iarna", "intermediar", "vara")
FARA_INCALZIRE = "gaz"
SEASON_LABELS = {"iarna": "iarnă (nov–mar)", "intermediar": "primăvară / toamnă", "vara": "vară (iun–aug)"}
SEASON_DAYS = {"iarna": 151, "intermediar": 122, "vara": 92}   # non-leap year
DAY_SHARE = {"toate": 1.0, "lucru": 5 / 7, "weekend": 2 / 7}
WINTER_MONTHS, SUMMER_MONTHS = (11, 12, 1, 2, 3), (6, 7, 8)
EDGE_JITTER_H = 0.5
DURATION_JITTER = 0.10
TIP_COLORS = {"permanent": "#2a78d6", "interval": "#eda100", "durata": "#1baf7a", "termic": "#eb6834"}
YEAR = 2023


def season_of(day: date) -> str:
    if day.month in WINTER_MONTHS:
        return "iarna"
    return "vara" if day.month in SUMMER_MONTHS else "intermediar"


def parse_interval(text: str) -> tuple[float, float]:
    """'18-23' -> (18, 23); '18-7' -> (18, 31): an end at or before the start wraps past midnight."""
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
    """Inverse of parse_interval: (18, 31) -> '18-7'."""
    start, end = interval
    return f"{start:g}-{end - 24 if end > 24 else end:g}"


@dataclass(frozen=True)
class Program:
    """When one catalog row runs; porniri_pe_saptamana already multiplied by the people."""

    moment: str = ""
    interval: tuple[float, float] | None = None
    durata_min: float = 0.0
    porniri_pe_saptamana: float = 0.0
    zile: str = "toate"
    sezon: str = "tot_anul"
    faze: tuple[tuple[float, float], ...] = ()      # (minutes, W) of one run, in order

    def run_kwh(self, putere_w: float) -> float:
        if self.faze:
            return sum(minutes * watts for minutes, watts in self.faze) / 60_000
        return self.durata_min / 60 * putere_w / 1000

    def runs_on(self, day: date) -> bool:
        weekend = day.weekday() >= 5
        if self.zile == "lucru" and weekend or self.zile == "weekend" and not weekend:
            return False
        return self.sezon == "tot_anul" or self.sezon == season_of(day)

    def in_season(self, season: str) -> bool:
        return self.sezon == "tot_anul" or self.sezon == season

    def describe(self, tip: str) -> str:
        parts = []
        if tip == "durata":
            parts.append(f"{self.porniri_pe_saptamana:.2g}×{self.durata_min:g} min/săpt.")
            if self.faze:
                parts.append("(" + ", ".join(f"{m:g} min {w:g} W" for m, w in self.faze) + ")")
        if self.interval:
            parts.append(format_interval(self.interval))
        if self.zile != "toate":
            parts.append("zile lucrătoare" if self.zile == "lucru" else "weekend")
        if self.sezon != "tot_anul":
            parts.append(SEASON_LABELS[self.sezon].split(" (")[0])
        return " ".join(parts)


@dataclass(frozen=True)
class Appliance:
    """One device of one house, with all the catalog rows that apply to that house."""

    dispozitiv: str
    putere_w: float
    tip: str
    programe: tuple[Program, ...] = (Program(),)
    flexibil: bool = False

    @property
    def kw(self) -> float:
        return self.putere_w / 1000.0

    def kwh_per_day(self, season: str) -> float:
        """Expected energy per day in that season, averaged over the week."""
        kwh = 0.0
        for p in self.programe:
            if not p.in_season(season):
                continue
            if self.tip == "permanent":
                kwh += self.kw * 24 * DAY_SHARE[p.zile]
            elif self.tip == "interval":
                kwh += self.kw * (p.interval[1] - p.interval[0]) * DAY_SHARE[p.zile]
            elif self.tip == "durata":
                kwh += p.porniri_pe_saptamana / 7 * p.run_kwh(self.putere_w)
        return kwh

    def kwh_per_year(self) -> float:
        return sum(self.kwh_per_day(season) * SEASON_DAYS[season] for season in SEASONS)

    def describe(self) -> str:
        if self.tip in ("permanent", "termic"):
            return self.tip
        return "; ".join(p.describe(self.tip) for p in self.programe)


@dataclass(frozen=True)
class CatalogRow:
    dispozitiv: str
    cine: str
    pe_persoana: bool
    acasa: str
    tip: str
    putere_w: float
    program: Program
    flexibil: bool


@dataclass(frozen=True)
class HouseSpec:
    casa: int
    descriere: str
    persoane: int
    acasa_ziua: bool
    incalzire: str
    izolatie: str
    dispozitive: tuple[str, ...]


@dataclass(frozen=True)
class Catalog:
    rows: tuple[CatalogRow, ...]
    houses: tuple[HouseSpec, ...]

    def names(self, cine: str | None = None) -> list[str]:
        """Device names in catalog order, optionally only those with that cine."""
        return list(dict.fromkeys(r.dispozitiv for r in self.rows if cine is None or r.cine == cine))


@dataclass(frozen=True)
class House:
    casa: int
    descriere: str
    persoane: int
    acasa_ziua: bool
    incalzire: str
    izolatie: str
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


def _choice(row: dict[str, str], name: str, options: tuple[str, ...], default: str | None = None) -> str:
    value = row[name].lower() or default
    if value not in options:
        raise ValueError(f"{name} = {row[name]!r}, astept unul din {', '.join(options)}")
    return value


def _parse_phases(text: str, tip: str, durata: float, putere: float) -> tuple[tuple[float, float], ...]:
    """'10:2000 209:40' -> ((10, 2000), (209, 40)): minutes and W of each step of one run."""
    if tip != "durata":
        raise ValueError("faze: doar pentru tip = durata")
    phases = []
    for part in text.split():
        minutes, _, watts = part.partition(":")
        phase = (_number(minutes, f"minutele din {part!r}"), _number(watts, f"puterea din {part!r}"))
        if phase[0] <= 0 or not 0 <= phase[1] <= putere:
            raise ValueError(f"faze: {part!r}, astept minute > 0 si putere intre 0 si putere_w = {putere:g}")
        phases.append(phase)
    if abs(sum(minutes for minutes, _ in phases) - durata) > 0.5:
        raise ValueError(f"faze: minutele adunate trebuie sa fie durata_min = {durata:g}")
    return tuple(phases)


def _parse_row(row: dict[str, str]) -> CatalogRow:
    if not row["dispozitiv"]:
        raise ValueError("dispozitiv gol")
    tip = _choice(row, "tip", TIPURI)
    putere = _number(row["putere_w"], "putere_w")
    if putere <= 0:
        raise ValueError("putere_w trebuie sa fie > 0")
    durata = _number(row["durata_min"], "durata_min")
    porniri = _number(row["porniri_pe_saptamana"], "porniri_pe_saptamana")
    pe_persoana = _yes_no(row["pe_persoana"] or "nu", "pe_persoana")
    interval = parse_interval(row["interval"]) if row["interval"] else None
    if tip in ("permanent", "termic") and (interval or durata or porniri):
        raise ValueError(f"{tip}: interval, durata_min si porniri_pe_saptamana raman goale")
    if tip == "interval" and (not interval or durata or porniri):
        raise ValueError("interval: trebuie interval, fara durata_min si porniri_pe_saptamana")
    if tip == "durata" and (not interval or not 0 < durata <= 24 * 60 or porniri <= 0):
        raise ValueError("durata: trebuie interval, durata_min intre 0 si 1440 si porniri_pe_saptamana > 0")
    if pe_persoana and tip in ("permanent", "interval"):
        raise ValueError(f"pe_persoana = da nu are sens pentru {tip}")
    if tip == "termic" and row["dispozitiv"].lower() not in thermal.ROLES:
        raise ValueError(f"termic: modelul termic stie doar {', '.join(thermal.ROLES)}")
    faze = _parse_phases(row["faze"], tip, durata, putere) if row["faze"] else ()
    program = Program(row["moment"], interval, durata, porniri, _choice(row, "zile", ZILE, "toate"),
                      _choice(row, "sezon", SEZOANE, "tot_anul"), faze)
    return CatalogRow(row["dispozitiv"].lower(), _choice(row, "cine", CINE), pe_persoana,
                      _choice(row, "acasa", ACASA, "oricand"), tip, putere, program,
                      _yes_no(row["flexibil"] or "nu", "flexibil"))


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


def load_rows(path: Path | str = DISPOZITIVE_CSV) -> tuple[CatalogRow, ...]:
    """Reads the device catalog (decimals with '.' or ','); the rows of one device must agree."""
    path = Path(path)
    rows: list[CatalogRow] = []
    first: dict[str, CatalogRow] = {}
    for line, raw in _read_rows(path, COLUMNS):
        try:
            row = _parse_row(raw)
            seen = first.setdefault(row.dispozitiv, row)
            for field in ("cine", "pe_persoana", "tip", "putere_w", "flexibil"):
                if getattr(row, field) != getattr(seen, field):
                    raise ValueError(f"{field} difera de primul rand al dispozitivului {row.dispozitiv!r}")
        except ValueError as error:
            raise ValueError(f"{path.name}, randul {line}: {error}") from None
        rows.append(row)
    if not rows:
        raise ValueError(f"{path.name}: niciun dispozitiv")
    return tuple(rows)


def check_spec(spec: HouseSpec, chosen: Iterable[str], heating: Iterable[str]) -> None:
    """chosen / heating: the catalog's devices with cine = ales / incalzire."""
    chosen, heating = set(chosen), set(heating)
    if spec.persoane < 1:
        raise ValueError("persoane trebuie sa fie un numar intreg >= 1")
    if spec.incalzire != FARA_INCALZIRE and spec.incalzire not in heating:
        raise ValueError(f"incalzire = {spec.incalzire!r}, astept {FARA_INCALZIRE} sau unul din "
                         f"{', '.join(sorted(heating))}")
    if spec.izolatie not in thermal.IZOLATII:
        raise ValueError(f"izolatie = {spec.izolatie!r}, astept unul din {', '.join(thermal.IZOLATII)}")
    unknown = [name for name in spec.dispozitive if name not in chosen]
    if unknown:
        raise ValueError(f"dispozitive necunoscute (cine = ales in catalog): {', '.join(unknown)}")


def specs_to_csv(specs: Iterable[HouseSpec]) -> str:
    """The inverse of load_houses: the text of a case.csv."""
    lines = [";".join(HOUSE_COLUMNS)]
    for s in specs:
        lines.append(";".join([str(s.casa), s.descriere, str(s.persoane), "da" if s.acasa_ziua else "nu",
                               s.incalzire, s.izolatie, ",".join(s.dispozitive)]))
    return "\n".join(lines) + "\n"


def load_houses(rows: tuple[CatalogRow, ...], path: Path | str = CASE_CSV) -> tuple[HouseSpec, ...]:
    """case.csv, checked against the catalog: casa 1..N in order, known devices and heating."""
    path = Path(path)
    chosen = {r.dispozitiv for r in rows if r.cine == "ales"}
    heating = {r.dispozitiv for r in rows if r.cine == "incalzire"}
    houses = []
    for line, row in _read_rows(path, HOUSE_COLUMNS):
        try:
            casa, persoane = _number(row["casa"], "casa"), _number(row["persoane"], "persoane")
            if casa != len(houses) + 1:
                raise ValueError(f"casa = {row['casa']!r}, astept {len(houses) + 1} (casele merg in ordine de la 1)")
            if persoane != int(persoane):
                raise ValueError("persoane trebuie sa fie un numar intreg >= 1")
            devices = tuple(name.strip().lower() for name in row["dispozitive"].split(",") if name.strip())
            spec = HouseSpec(int(casa), row["descriere"], int(persoane), _yes_no(row["acasa_ziua"], "acasa_ziua"),
                             row["incalzire"].lower() or FARA_INCALZIRE,
                             _choice(row, "izolatie", thermal.IZOLATII, "medie"), devices)
            check_spec(spec, chosen, heating)
            houses.append(spec)
        except ValueError as error:
            raise ValueError(f"{path.name}, randul {line}: {error}") from None
    if not houses:
        raise ValueError(f"{path.name}: nicio casa")
    return tuple(houses)


def load_catalog(path: Path | str = DISPOZITIVE_CSV, houses: Path | str = CASE_CSV) -> Catalog:
    rows = load_rows(path)
    return Catalog(rows, load_houses(rows, houses))


def programs_to_json(programe: tuple[Program, ...]) -> str:
    return json.dumps([{"moment": p.moment, "interval": format_interval(p.interval) if p.interval else "",
                        "durata_min": p.durata_min, "porniri_pe_saptamana": p.porniri_pe_saptamana,
                        "zile": p.zile, "sezon": p.sezon, "faze": [list(phase) for phase in p.faze]}
                       for p in programe], ensure_ascii=False)


def programs_from_json(text: str) -> tuple[Program, ...]:
    return tuple(Program(p["moment"], parse_interval(p["interval"]) if p["interval"] else None, p["durata_min"],
                         p["porniri_pe_saptamana"], p["zile"], p["sezon"], tuple(map(tuple, p.get("faze", []))))
                 for p in json.loads(text or "[]"))


# ----------------------------------------------------------------------------- composition

def house_spec(house_id: int, catalog: Catalog) -> HouseSpec:
    return catalog.houses[(house_id - 1) % len(catalog.houses)]


def compose_house(house_id: int, catalog: Catalog) -> House:
    return compose_spec(house_id, house_spec(house_id, catalog), catalog)


def compose_spec(house_id: int, spec: HouseSpec, catalog: Catalog) -> House:
    """The devices of a house described by `spec` (a row of case.csv or one edited in the app)."""
    owned = set(catalog.names("toti")) | set(spec.dispozitive) | {spec.incalzire}
    home = "da" if spec.acasa_ziua else "nu"
    appliances = []
    for name in catalog.names():
        if name not in owned:
            continue
        rows = [r for r in catalog.rows if r.dispozitiv == name and r.acasa in ("oricand", home)]
        if not rows:
            continue
        head = rows[0]
        factor = spec.persoane if head.pe_persoana else 1
        programs = tuple(replace(r.program, porniri_pe_saptamana=r.program.porniri_pe_saptamana * factor)
                         for r in rows)
        appliances.append(Appliance(name, head.putere_w, head.tip, programs, head.flexibil))
    return House(house_id, spec.descriere, spec.persoane, spec.acasa_ziua, spec.incalzire, spec.izolatie,
                 tuple(appliances))


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


def _runs_per_day(per_week: float, eligible: list[int], rng: np.random.Generator) -> dict[int, int]:
    """Runs on each eligible day of a 7-day block: the whole count exactly, a fraction drawn."""
    whole = int(per_week)
    n = whole + int(rng.random() < per_week - whole)
    if not eligible or not n:
        return {}
    counts = dict.fromkeys(eligible, n // len(eligible))
    for slot in rng.choice(eligible, n % len(eligible), replace=False):
        counts[int(slot)] += 1
    return counts


def appliance_profile(app: Appliance, start: date, n_days: int, dt_h: float, rng: np.random.Generator) -> np.ndarray:
    """(n_days * steps_per_day,) kW of one appliance from `start`."""
    spd = _steps_per_day(dt_h)
    n_steps = n_days * spd
    if app.tip == "termic":
        return np.zeros(n_steps)
    if app.tip == "permanent" and all(p.zile == "toate" and p.sezon == "tot_anul" for p in app.programe):
        return np.full(n_steps, app.kw)
    buffer = np.zeros(n_steps + 2 * spd)              # one day before and after, for blocks crossing midnight
    days = range(-1, n_days + 1)
    for p in app.programe:
        if app.tip == "durata":
            for week in range(-1, n_days // 7 + 1):   # whole 7-day blocks counted from `start`
                eligible = [d for d in range(7 * week, 7 * week + 7) if p.runs_on(start + timedelta(days=d))]
                for d, runs in _runs_per_day(p.porniri_pe_saptamana, eligible, rng).items():
                    if not -1 <= d <= n_days:
                        continue
                    for _ in range(runs):
                        stretch = rng.uniform(1 - DURATION_JITTER, 1 + DURATION_JITTER)
                        at = (d + 1) * 24.0 + rng.uniform(*p.interval)
                        for minutes, watts in p.faze or ((p.durata_min, app.putere_w),):
                            _add_block(buffer, at, minutes / 60 * stretch, watts / 1000, dt_h)
                            at += minutes / 60 * stretch
            continue
        for d in days:
            if not p.runs_on(start + timedelta(days=d)):
                continue
            if app.tip == "permanent":
                _add_block(buffer, (d + 1) * 24.0, 24.0, app.kw, dt_h)
            else:
                lo = p.interval[0] + rng.uniform(-EDGE_JITTER_H, EDGE_JITTER_H)
                hi = p.interval[1] + rng.uniform(-EDGE_JITTER_H, EDGE_JITTER_H)
                _add_block(buffer, (d + 1) * 24.0 + lo, hi - lo, app.kw, dt_h)
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


def thermal_house(house: House) -> thermal.ThermalHouse:
    kw = {thermal.ROLES[app.dispozitiv]: app.kw for app in house.appliances if app.tip == "termic"}
    heating = next((role for role in ("pompa", "radiator") if role in kw), None)
    return thermal.ThermalHouse(house.persoane, house.acasa_ziua, house.izolatie, heating,
                                kw.get(heating, 0.0), kw.get("ac", 0.0), kw.get("boiler", 0.0))


def house_profiles(
    house: House, start: date, n_days: int, dt_h: float, rng: np.random.Generator, weather: Weather | None = None,
) -> dict[str, np.ndarray]:
    """device name -> kW, each (n_days * steps_per_day,), plus 'temp_in' when there is weather. The thermal
    devices run after the others, on the same stream, with the others' heat as gains."""
    profiles = {app.dispozitiv: appliance_profile(app, start, n_days, dt_h, rng) for app in house.appliances}
    if weather is None:
        return profiles
    gains = sum((kw for name, kw in profiles.items() if name not in thermal.OUTDOOR_DEVICES),
                np.zeros(n_days * _steps_per_day(dt_h)))
    roles = thermal.thermal_profiles(thermal_house(house), start, n_days, dt_h, weather, gains, rng)
    for app in house.appliances:
        if app.tip == "termic":
            profiles[app.dispozitiv] = roles[thermal.ROLES[app.dispozitiv]]
    profiles["temp_in"] = roles["temp_in"]
    return profiles


def house_rng(seed: int, house_id: int) -> np.random.Generator:
    """One stream per house, so a house's profile does not depend on which other houses are simulated."""
    return np.random.default_rng([seed, house_id])


def community_load(
    community: CommunityParams, start: date, n_days: int, dt_h: float, seed: int, catalog: Catalog | None = None,
    weather: Weather | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible), each (n_houses, n_steps) kW: each house id with its own stream."""
    houses = compose_houses((house.id for house in community.houses), catalog)
    n_steps = n_days * _steps_per_day(dt_h)
    critical, flexible = np.zeros((community.n_houses, n_steps)), np.zeros((community.n_houses, n_steps))
    for i, house in enumerate(houses):
        profiles = house_profiles(house, start, n_days, dt_h, house_rng(seed, house.casa), weather)
        for app in house.appliances:
            (flexible if app.flexibil else critical)[i] += profiles[app.dispozitiv]
    return critical, flexible


# ----------------------------------------------------------------------------- validation report

def simulate_year(houses: list[House], dt_h: float, seed: int, weather: Weather | None = None,
                  ) -> dict[int, dict[str, np.ndarray]]:
    """house -> tip -> (365 * spd,) kW for YEAR, plus 'flexibil', 'total' and 'temp_in' when there is weather."""
    start = date(YEAR, 1, 1)
    result = {}
    for house in houses:
        profiles = house_profiles(house, start, 365, dt_h, house_rng(seed, house.casa), weather)
        series = {tip: np.zeros(365 * _steps_per_day(dt_h)) for tip in TIPURI}
        flexible = np.zeros_like(series["permanent"])
        for app in house.appliances:
            series[app.tip] += profiles[app.dispozitiv]
            if app.flexibil:
                flexible += profiles[app.dispozitiv]
        series["flexibil"] = flexible
        series["total"] = sum(series[tip] for tip in TIPURI)
        if "temp_in" in profiles:
            series["temp_in"] = profiles["temp_in"]
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
        row = {"casa": house.casa, "descriere": house.descriere, "persoane": house.persoane,
               "acasa_ziua": "da" if house.acasa_ziua else "nu", "incalzire": house.incalzire,
               "dispozitive": len(house.appliances)}
        for season in SEASONS:
            row[f"kwh_zi_{season}"] = float(daily[season_days[season]].mean())
        row["kwh_an"] = annual
        for tip in TIPURI:
            row[f"kwh_an_{tip}"] = float(series[tip].sum() * dt_h)
        row["varf_kw"] = float(series["total"].max())
        row["temp_min_c"] = float(series["temp_in"].min()) if "temp_in" in series else float("nan")
        row["temp_max_c"] = float(series["temp_in"].max()) if "temp_in" in series else float("nan")
        row["cota_flexibil"] = float(series["flexibil"].sum() * dt_h / annual) if annual else 0.0
        row["kwh_an_calculat"] = house.kwh_per_year()
        row["lista"] = ", ".join(app.dispozitiv for app in house.appliances)
        rows.append(row)
    return rows


def device_rows(houses: list[House]) -> list[dict]:
    """Expected values of every device of every house, per-person counts already multiplied."""
    rows = []
    for house in houses:
        for app in house.appliances:
            row = {"casa": house.casa, "persoane": house.persoane, "dispozitiv": app.dispozitiv, "tip": app.tip,
                   "putere_w": app.putere_w, "program": app.describe(), "flexibil": "da" if app.flexibil else "nu"}
            for season in SEASONS:
                row[f"kwh_zi_{season}"] = app.kwh_per_day(season)
            row["kwh_an"] = app.kwh_per_year()
            rows.append(row)
    return rows


CSV_KEYS = ["casa", "descriere", "persoane", "acasa_ziua", "incalzire", "dispozitive",
            *[f"kwh_zi_{season}" for season in SEASONS], "kwh_an", *[f"kwh_an_{tip}" for tip in TIPURI],
            "varf_kw", "temp_min_c", "temp_max_c", "cota_flexibil", "kwh_an_calculat", "lista"]
DEVICE_KEYS = ["casa", "persoane", "dispozitiv", "tip", "putere_w", "program", "flexibil",
               *[f"kwh_zi_{season}" for season in SEASONS], "kwh_an"]
PROFILE_HOUSES = (1, 7, 9)


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
        ax.plot(hours, mean_profile, color=TIP_COLORS["durata"], linewidth=1.6, label="model din dispozitive")
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
    for tip in TIPURI:
        values = np.array([row[f"kwh_an_{tip}"] for row in rows])
        ax.bar(x, values, 0.7, bottom=bottom, color=TIP_COLORS[tip], label=tip)
        bottom += values
    for xi, row in zip(x, rows, strict=True):
        ax.text(xi, row["kwh_an"] + 40, f"{row['kwh_an']:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(x, [f"Casa {row['casa']}\n({row['persoane']} pers.)" for row in rows])
    ax.set_ylabel("Consum anual [kWh]")
    ax.set_ylim(0, bottom.max() * 1.12)
    ax.grid(axis="x", visible=False)
    ax.set_title("Consum anual pe casă, din dispozitive.csv și case.csv, pe tipuri de dispozitive",
                 fontsize=9, loc="left", color=INK)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def print_rows(rows: list[dict]) -> None:
    print(f"{'casa':>4} {'pers':>4} {'disp':>4} {'iarna':>7} {'interm':>7} {'vara':>7} {'kWh/an':>8} {'termic':>7} "
          f"{'varf':>6} {'Tmin':>5} {'Tmax':>5} {'flex':>6}")
    for row in rows:
        print(f"{row['casa']:>4} {row['persoane']:>4} {row['dispozitive']:>4} {row['kwh_zi_iarna']:>7.1f} "
              f"{row['kwh_zi_intermediar']:>7.1f} {row['kwh_zi_vara']:>7.1f} {row['kwh_an']:>8.0f} "
              f"{row['kwh_an_termic']:>7.0f} {row['varf_kw']:>6.1f} {row['temp_min_c']:>5.1f} "
              f"{row['temp_max_c']:>5.1f} {100 * row['cota_flexibil']:>5.0f}%")
    print()
    for row in rows:
        print(f"casa {row['casa']} ({row['descriere']}): {row['lista']}")
    annual = np.array([row["kwh_an"] for row in rows])
    print(f"\nmedie pe casa: {annual.mean():.0f} kWh/an (min {annual.min():.0f}, max {annual.max():.0f})")


def main(argv: list[str] | None = None) -> None:
    from vpp_core.reporting import RESULTS_DIR, utf8_console, write_csv
    from vpp_core.scenario_real import real_weather

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "consum")
    parser.add_argument("--csv", type=Path, default=DISPOZITIVE_CSV, help="alt catalog dispozitive.csv")
    parser.add_argument("--case", type=Path, default=CASE_CSV, help="alt fisier case.csv")
    parser.add_argument("--houses", type=int, default=10, help="casele 1..N")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dt", type=float, default=0.25, help="pasul de timp in ore")
    args = parser.parse_args(argv)
    utf8_console()
    args.out.mkdir(parents=True, exist_ok=True)
    houses = compose_houses(range(1, args.houses + 1), load_catalog(args.csv, args.case))
    year = simulate_year(houses, args.dt, args.seed, real_weather(0, 365, args.dt))
    rows = house_rows(houses, year, args.dt)
    write_csv(rows, CSV_KEYS, args.out / "consum_case.csv")
    write_csv(device_rows(houses), DEVICE_KEYS, args.out / "dispozitive_case.csv")
    daily_profile_chart(year, args.dt, args.out / "profil_zi.png")
    annual_chart(rows, args.out / "consum_anual.png")
    print_rows(rows)
    print(f"\nRezultate scrise in {args.out}")


if __name__ == "__main__":
    main()
