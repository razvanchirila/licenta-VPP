"""
Bottom-up household load: a house consumes what its appliances consume. The appliances are listed by hand
in backend/data/dispozitive.csv (one row per appliance per house; columns explained in backend/data/README.md).

    continuu  putere_w all the time
    zilnic    one block of ore_pe_zi hours (x U(0.9, 1.1) each day) starting at a random time inside interval
    ciclic    cicluri_pe_saptamana runs of durata_ciclu_min (x U(0.9, 1.1)) per 7-day block, on random days,
              each starting at a random time inside interval (the run may end after the interval)
    termic    ore_pe_zi x seasonal factor hours per day (x U(0.9, 1.1)), as half-hour blocks spread evenly over
              interval with random jitter, like a thermostat; factor 1 in its season (sezon), 0.5 in the two
              shoulder seasons, 0 in the opposite one; sezon = tot_anul gives factor 1 all year

Seasons from the month: iarna nov-mar, vara iun-aug, intermediar otherwise. Every mode is energy-consistent:
an appliance of P W running h hours per day draws P x h Wh per day on average. Blocks may cross midnight
(interval "22-6"); they are generated for the day before and after the window too, so the profile is
stationary at the window edges.

Run from backend/:   python -m vpp_core.load_model [--out results/consum] [--seed 0] [--dt 0.25]
Output: consum_case.csv (kWh/day per season, kWh/year, share flexibil), profil_zi.png, consum_anual.png.
"""
from __future__ import annotations

import argparse
import csv
import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from vpp_core.params import CommunityParams

DISPOZITIVE_CSV = Path(__file__).resolve().parents[1] / "data" / "dispozitive.csv"
COLUMNS = ("casa", "dispozitiv", "putere_w", "mod", "ore_pe_zi", "cicluri_pe_saptamana", "durata_ciclu_min",
           "interval", "sezon", "flexibil", "persoane")
MODES = ("continuu", "zilnic", "ciclic", "termic")
SEZOANE = ("tot_anul", "iarna", "vara")
SEASONS = ("iarna", "intermediar", "vara")
SEASON_LABELS = {"iarna": "iarnă (nov–mar)", "intermediar": "primăvară / toamnă", "vara": "vară (iun–aug)"}
SEASON_DAYS = {"iarna": 151, "intermediar": 122, "vara": 92}   # non-leap year
WINTER_MONTHS, SUMMER_MONTHS = (11, 12, 1, 2, 3), (6, 7, 8)
HOURS_JITTER = 0.10          # daily hours / cycle length x U(1 - j, 1 + j)
SHOULDER_FACTOR = 0.5
THERMAL_BLOCK_H = 0.5
MODE_COLORS = {"continuu": "#2a78d6", "zilnic": "#eda100", "ciclic": "#1baf7a", "termic": "#eb6834"}
YEAR = 2023


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


@dataclass(frozen=True)
class Appliance:
    casa: int
    dispozitiv: str
    putere_w: float
    mod: str
    ore_pe_zi: float = 0.0
    cicluri_pe_saptamana: float = 0.0
    durata_ciclu_min: float = 0.0
    interval: tuple[float, float] = (0.0, 24.0)   # hours; end > 24 when the interval wraps past midnight
    sezon: str = "tot_anul"
    flexibil: bool = False
    persoane: int = 1

    @property
    def kw(self) -> float:
        return self.putere_w / 1000.0

    @property
    def interval_h(self) -> float:
        return self.interval[1] - self.interval[0]

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


# ----------------------------------------------------------------------------- CSV

def _number(text: str, name: str) -> float:
    if not text:
        return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        raise ValueError(f"{name} = {text!r} nu este un numar") from None


def _parse_row(row: dict[str, str]) -> Appliance:
    mod, sezon, flexibil = row["mod"].lower(), (row["sezon"] or "tot_anul").lower(), row["flexibil"].lower()
    if mod not in MODES:
        raise ValueError(f"mod = {row['mod']!r}, astept unul din {MODES}")
    if sezon not in SEZOANE:
        raise ValueError(f"sezon = {row['sezon']!r}, astept unul din {SEZOANE}")
    if flexibil not in ("da", "nu"):
        raise ValueError(f"flexibil = {row['flexibil']!r}, astept da sau nu")
    if not row["dispozitiv"]:
        raise ValueError("dispozitiv gol")
    app = Appliance(
        casa=int(_number(row["casa"], "casa")),
        dispozitiv=row["dispozitiv"],
        putere_w=_number(row["putere_w"], "putere_w"),
        mod=mod,
        ore_pe_zi=_number(row["ore_pe_zi"], "ore_pe_zi"),
        cicluri_pe_saptamana=_number(row["cicluri_pe_saptamana"], "cicluri_pe_saptamana"),
        durata_ciclu_min=_number(row["durata_ciclu_min"], "durata_ciclu_min"),
        interval=parse_interval(row["interval"] or "0-24"),
        sezon=sezon,
        flexibil=flexibil == "da",
        persoane=int(_number(row["persoane"] or "1", "persoane")),
    )
    if app.casa < 1:
        raise ValueError("casa trebuie sa fie >= 1")
    if app.putere_w <= 0:
        raise ValueError("putere_w trebuie sa fie > 0")
    if app.persoane < 1:
        raise ValueError("persoane trebuie sa fie >= 1")
    if mod in ("zilnic", "termic"):
        if not 0 < app.ore_pe_zi <= app.interval_h:
            raise ValueError(f"ore_pe_zi trebuie sa fie intre 0 si lungimea intervalului ({app.interval_h:g} h)")
    if mod == "ciclic":
        if app.cicluri_pe_saptamana <= 0 or not 0 < app.durata_ciclu_min <= 24 * 60:
            raise ValueError("ciclic: cicluri_pe_saptamana > 0 si durata_ciclu_min intre 0 si 1440")
    return app


def load_appliances(path: Path | str = DISPOZITIVE_CSV) -> list[Appliance]:
    """Reads dispozitive.csv (UTF-8 with BOM, ';' separated, decimals with '.' or ','); blank rows are skipped."""
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        header = [name.strip().lower() for name in reader.fieldnames or []]
        if header != list(COLUMNS):
            raise ValueError(f"{path}: antetul trebuie sa fie {';'.join(COLUMNS)}")
        appliances = []
        for line, raw in enumerate(reader, start=2):
            row = {name.strip().lower(): (value or "").strip() for name, value in raw.items() if name}
            if not any(row.values()):
                continue
            try:
                appliances.append(_parse_row(row))
            except ValueError as error:
                raise ValueError(f"{path.name}, randul {line}: {error}") from None
    return appliances


def by_house(appliances: list[Appliance]) -> dict[int, list[Appliance]]:
    groups: dict[int, list[Appliance]] = {}
    for app in appliances:
        groups.setdefault(app.casa, []).append(app)
    return groups


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
    lo, hi = app.interval
    week_schedule: dict[int, np.ndarray] = {}         # 7-day blocks counted from `start`; day -1 is its own block
    for d in range(-1, n_days + 1):
        day_h = (d + 1) * 24.0
        if app.mod == "zilnic":
            hours = min(app.ore_pe_zi * _jitter(rng), app.interval_h)
            _add_block(buffer, day_h + rng.uniform(lo, hi - hours), hours, app.kw, dt_h)
        elif app.mod == "ciclic":
            week = d // 7
            if week not in week_schedule:
                week_schedule[week] = _cycles_per_day(app.cicluri_pe_saptamana, rng)
            for _ in range(week_schedule[week][d % 7]):
                duration = app.durata_ciclu_min / 60 * _jitter(rng)
                _add_block(buffer, day_h + rng.uniform(lo, hi), duration, app.kw, dt_h)
        else:
            factor = thermal_factor(app.sezon, season_of(start + timedelta(days=d)))
            hours = min(app.ore_pe_zi * factor * _jitter(rng), app.interval_h)
            if hours <= 0:
                continue
            n_blocks = max(1, round(hours / THERMAL_BLOCK_H))
            block, spacing = hours / n_blocks, app.interval_h / n_blocks
            for k in range(n_blocks):
                offset = lo + k * spacing + rng.uniform(0, spacing - block)
                _add_block(buffer, day_h + offset, block, app.kw, dt_h)
    return buffer[spd : spd + n_steps]


def house_load_profile(
    appliances: list[Appliance], start: date, n_days: int, dt_h: float, rng: np.random.Generator
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
    community: CommunityParams, path: Path | str, start: date, n_days: int, dt_h: float, seed: int,
    fallback: tuple[np.ndarray, np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible), each (n_houses, n_steps) kW; house i uses casa = HouseParams.id in the CSV.
    Houses missing from the CSV take their rows from `fallback` (with one warning) or raise without it."""
    groups = by_house(load_appliances(path))
    n_steps = n_days * _steps_per_day(dt_h)
    critical, flexible = np.zeros((community.n_houses, n_steps)), np.zeros((community.n_houses, n_steps))
    missing = []
    for i, house in enumerate(community.houses):
        if house.id not in groups:
            missing.append(house.id)
            continue
        critical[i], flexible[i] = house_load_profile(groups[house.id], start, n_days, dt_h, house_rng(seed, house.id))
    if missing:
        if fallback is None:
            raise ValueError(f"casele {missing} lipsesc din {Path(path).name}")
        shown = ", ".join(map(str, missing[:10])) + (", ..." if len(missing) > 10 else "")
        warnings.warn(f"{len(missing)} case lipsesc din {Path(path).name} ({shown}): pentru ele se foloseste "
                      "profilul de consum anterior", stacklevel=2)
        rows = [i for i, house in enumerate(community.houses) if house.id in missing]
        critical[rows], flexible[rows] = fallback[0][rows], fallback[1][rows]
    return critical, flexible


# ----------------------------------------------------------------------------- validation report

def simulate_year(appliances: list[Appliance], dt_h: float, seed: int) -> dict[int, dict[str, np.ndarray]]:
    """house -> mode -> (365 * spd,) kW for YEAR, plus 'flexibil' and 'total'."""
    start = date(YEAR, 1, 1)
    result = {}
    for house_id, apps in sorted(by_house(appliances).items()):
        rng = house_rng(seed, house_id)
        series = {mode: np.zeros(365 * _steps_per_day(dt_h)) for mode in MODES}
        flexible = np.zeros_like(series["continuu"])
        for app in apps:
            profile = appliance_profile(app, start, 365, dt_h, rng)
            series[app.mod] += profile
            if app.flexibil:
                flexible += profile
        series["flexibil"] = flexible
        series["total"] = sum(series[mode] for mode in MODES)
        result[house_id] = series
    return result


def house_rows(appliances: list[Appliance], year: dict[int, dict[str, np.ndarray]], dt_h: float) -> list[dict]:
    spd = _steps_per_day(dt_h)
    days = [date(YEAR, 1, 1) + timedelta(days=d) for d in range(365)]
    season_days = {season: [d for d, day in enumerate(days) if season_of(day) == season] for season in SEASONS}
    groups = by_house(appliances)
    rows = []
    for house_id, series in year.items():
        daily = series["total"].reshape(365, spd).sum(axis=1) * dt_h
        annual = float(series["total"].sum() * dt_h)
        row = {"casa": house_id, "persoane": groups[house_id][0].persoane, "dispozitive": len(groups[house_id])}
        for season in SEASONS:
            row[f"kwh_zi_{season}"] = float(daily[season_days[season]].mean())
        row["kwh_an"] = annual
        for mode in MODES:
            row[f"kwh_an_{mode}"] = float(series[mode].sum() * dt_h)
        row["cota_flexibil"] = float(series["flexibil"].sum() * dt_h / annual) if annual else 0.0
        row["kwh_an_calculat"] = sum(app.kwh_per_year() for app in groups[house_id])
        rows.append(row)
    return rows


CSV_KEYS = ["casa", "persoane", "dispozitive", *[f"kwh_zi_{season}" for season in SEASONS], "kwh_an",
            *[f"kwh_an_{mode}" for mode in MODES], "cota_flexibil", "kwh_an_calculat"]
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
    fig, ax = plt.subplots(figsize=(8, 3.6))
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
    ax.set_title("Consum anual pe casă din lista de dispozitive (dispozitive.csv), pe categorii",
                 fontsize=9, loc="left", color=INK)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def print_rows(rows: list[dict]) -> None:
    print(f"{'casa':>4} {'pers':>4} {'iarna':>7} {'interm':>7} {'vara':>7} {'kWh/an':>8} {'calc':>8} {'flex':>6}")
    for row in rows:
        print(f"{row['casa']:>4} {row['persoane']:>4} {row['kwh_zi_iarna']:>7.1f} {row['kwh_zi_intermediar']:>7.1f} "
              f"{row['kwh_zi_vara']:>7.1f} {row['kwh_an']:>8.0f} {row['kwh_an_calculat']:>8.0f} "
              f"{100 * row['cota_flexibil']:>5.0f}%")
    mean_winter = np.mean([row["kwh_zi_iarna"] for row in rows])
    print(f"medie pe casa: {np.mean([r['kwh_an'] for r in rows]):.0f} kWh/an, iarna {mean_winter:.1f} kWh/zi")


def main(argv: list[str] | None = None) -> None:
    from vpp_core.reporting import RESULTS_DIR, utf8_console, write_csv

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "consum")
    parser.add_argument("--csv", type=Path, default=DISPOZITIVE_CSV, help="alt fisier dispozitive.csv")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dt", type=float, default=0.25, help="pasul de timp in ore")
    args = parser.parse_args(argv)
    utf8_console()
    args.out.mkdir(parents=True, exist_ok=True)
    appliances = load_appliances(args.csv)
    year = simulate_year(appliances, args.dt, args.seed)
    rows = house_rows(appliances, year, args.dt)
    write_csv(rows, CSV_KEYS, args.out / "consum_case.csv")
    daily_profile_chart(year, args.dt, args.out / "profil_zi.png")
    annual_chart(rows, args.out / "consum_anual.png")
    print_rows(rows)
    print(f"\nRezultate scrise in {args.out}")


if __name__ == "__main__":
    main()
