"""Shared pieces of evaluation.py and pareto.py: seasons, scenario factory, parallel runner, CSV, CLI, chart style."""
from __future__ import annotations

import argparse
import csv
import sys
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

from vpp_core import data_sources as ds
from vpp_core.optimizer import LPWeights
from vpp_core.params import CommunityParams, default_community
from vpp_core.scenario import Scenario, generate_scenario
from vpp_core.scenario_real import generate_scenario_real

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
RESULTS_REAL_DIR = RESULTS_DIR / "real"

# key, chart label, first day of the simulated week
SEASONS = (
    ("iarna", "Iarnă", date(2025, 1, 10)),
    ("primavara", "Primăvară", date(2025, 4, 10)),
    ("vara", "Vară", date(2025, 7, 10)),
    ("toamna", "Toamnă", date(2025, 10, 10)),
)
SEASON_LABELS = {key: label for key, label, _ in SEASONS}
# same weeks in 2023, the PV and calendar year of the real data; prices: the same days of the price year
SEASON_STARTS_REAL = {"iarna": date(2023, 1, 10), "primavara": date(2023, 4, 10),
                      "vara": date(2023, 7, 10), "toamna": date(2023, 10, 10)}

COLORS = {
    "fara_baterie": "#2a78d6", "baterie_locala": "#eb6834", "vpp_reguli": "#1baf7a",
    "mpc": "#eda100", "mpc_varf": "#e87ba4", "optim_lp": "#008300",
}
# controller name (code, CSV) -> what the reader sees; all are control strategies on the same neighbourhood
LABELS = {
    "fara_baterie": "doar PV (bateria nefolosită)",
    "baterie_locala": "baterie individuală",
    "vpp_reguli": "VPP cu reguli",
    "vpp_reguli_p2p_intai": "VPP cu reguli, P2P întâi",
    "vpp_reguli_spec_alpha": "VPP cu reguli (α din specificație)",
    "mpc": "VPP optimizat (MPC)",
    "mpc_varf": "VPP optimizat (MPC) + taxă de vârf",
    "optim_lp": "optim teoretic (LP, prognoză perfectă)",
}
SHORT_LABELS = {
    **LABELS,
    "fara_baterie": "doar PV",
    "vpp_reguli_spec_alpha": "VPP cu reguli (α)",
    "mpc_varf": "MPC + taxă de vârf",
    "optim_lp": "optim teoretic",
}
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"


def season_index(key: str) -> int:
    return [k for k, _, _ in SEASONS].index(key)


def seasons_with_prices(price_year: int, n_days: int) -> tuple[str, ...]:
    """Season keys whose real-data week is covered by the prices of `price_year` (a year in progress stops early)."""
    last = ds.last_price_day(price_year)
    return tuple(key for key, start in SEASON_STARTS_REAL.items()
                 if (start + timedelta(days=n_days - 1)).replace(year=price_year) <= last)


def make_scenario(
    season: str, seed: int, n_days: int, dt_h: float, real: bool, community: CommunityParams | None = None,
    price_year: int = ds.DEFAULT_PRICE_YEAR,
) -> Scenario:
    community = default_community() if community is None else community
    if real:
        return generate_scenario_real(community, start=SEASON_STARTS_REAL[season], n_days=n_days, dt_h=dt_h, seed=seed,
                                      price_year=price_year)
    start = next(s for k, _, s in SEASONS if k == season)
    return generate_scenario(community, start=start, n_days=n_days, dt_h=dt_h, seed=seed)


def weights(deg_cost: float | None = None, **overrides) -> LPWeights:
    return LPWeights(**overrides) if deg_cost is None else LPWeights(deg_cost=deg_cost, **overrides)


def run_parallel(run_one: Callable, tasks: Sequence, describe: Callable[[dict], str], workers: int | None) -> list:
    """Results come back in completion order; workers=0 runs in-process (tests)."""
    results, t0 = [], time.perf_counter()
    if workers == 0:
        return [run_one(task) for task in tasks]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            print(f"[{i:3d}/{len(tasks)}] {describe(result)}", flush=True)
            results.append(result)
    print(f"{len(tasks)} simulari in {time.perf_counter() - t0:.0f} s")
    return results


def format_value(value):
    return f"{value:.6g}" if isinstance(value, float) else value


def write_csv(rows: list[dict], keys: list[str], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_value(row[key]) for key in keys})


def read_csv(path: Path, text_keys: tuple[str, ...] = ("season", "controller", "eticheta")) -> list[dict]:
    """Inverse of write_csv: text columns stay text, "" becomes None, everything else float."""
    def parse(key: str, value: str):
        if key in text_keys:
            return value
        return None if value == "" else float(value)

    with path.open(encoding="utf-8") as file:
        return [{key: parse(key, value) for key, value in row.items()} for row in csv.DictReader(file)]


def add_common_arguments(parser: argparse.ArgumentParser, default_seeds: int) -> None:
    parser.add_argument("--seeds", type=int, default=default_seeds, help="numar de seed-uri (0 .. N-1)")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--dt", type=float, default=0.25, help="pasul de timp in ore")
    parser.add_argument("--workers", type=int, default=None, help="procese in paralel (implicit: toate nucleele)")
    parser.add_argument("--out", type=Path, default=None, help="implicit results/ (sau results/real/<an>/ cu --real)")
    parser.add_argument(
        "--real", action="store_true", help="scenariu din date reale (PV PVGIS 2023, PZU Ember din --price-year)"
    )
    parser.add_argument(
        "--price-year", type=int, choices=ds.PRICE_YEARS, default=ds.DEFAULT_PRICE_YEAR,
        help="anul preturilor PZU, doar cu --real (implicit %(default)s)",
    )
    parser.add_argument(
        "--deg", type=float, default=None, help="cost de degradare baterie lei/kWh pentru LP/MPC (implicit LPWeights)"
    )


def utf8_console() -> None:
    """Windows pipes default to cp1252, which cannot print the Romanian labels."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def output_dir(args: argparse.Namespace) -> Path:
    default = RESULTS_REAL_DIR / str(args.price_year) if args.real else RESULTS_DIR
    out = args.out if args.out is not None else default
    out.mkdir(parents=True, exist_ok=True)
    return out


def seasons_to_run(args: argparse.Namespace) -> tuple[str, ...]:
    """All four seasons, minus the real-data weeks that --price-year does not cover (said on the console)."""
    keys = tuple(key for key, _, _ in SEASONS)
    if not args.real:
        return keys
    covered = seasons_with_prices(args.price_year, args.days)
    skipped = [key for key in keys if key not in covered]
    if skipped:
        print(f"Preturile {args.price_year} se termina pe {ds.last_price_day(args.price_year):%d.%m.%Y}: "
              f"fara {', '.join(skipped)}")
    return covered


def data_label(real: bool, price_year: int) -> str:
    return f"PV {ds.YEAR}, prețuri PZU {price_year}" if real else "scenarii sintetice"


def plot_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK, "ytick.labelcolor": INK, "legend.frameon": False, "figure.dpi": 150,
        "savefig.dpi": 150,
    })
    return plt
