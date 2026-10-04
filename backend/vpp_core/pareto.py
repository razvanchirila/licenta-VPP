"""
Cost / peak trade-off of the MPC demand charge: one MPC run per (season, seed, peak_cost).

Run from backend/:   python -m vpp_core.pareto [--seeds 3] [--days 7] [--dt 0.25] [--deg 0.45]
                                                [--real [--price-year 2023|2025|2026]]
"""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np

from vpp_core import data_sources as ds
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import RealisticMPCController
from vpp_core.params import default_community
from vpp_core.reporting import (
    COLORS,
    INK,
    LABELS,
    MUTED,
    SEASON_LABELS,
    add_common_arguments,
    make_scenario,
    output_dir,
    plot_style,
    run_parallel,
    seasons_to_run,
    utf8_console,
    weights,
    write_csv,
)
from vpp_core.simulator import simulate

PEAK_COSTS = (0.0, 0.5, 1.0, 2.0, 4.0, 6.0, 10.0, 20.0)   # lei/kW
PARETO_SEASONS = ("iarna", "toamna")   # the seasons where import is large enough for the peak to matter
SEASON_COLORS = {"iarna": COLORS["fara_baterie"], "toamna": COLORS["baterie_locala"]}
CSV_KEYS = ["season", "seed", "peak_cost", "cost_lei", "peak_import_kw", "ssr"]


def run_one(task: tuple[str, int, float, int, float, bool, float | None, int]) -> dict:
    season, seed, peak_cost, n_days, dt_h, real, deg_cost, price_year = task
    community = default_community()
    scenario = make_scenario(season, seed, n_days, dt_h, real, price_year=price_year)
    t0 = time.perf_counter()
    controller = RealisticMPCController(weights=weights(deg_cost, peak_cost=peak_cost), name="mpc_varf")
    metrics = compute_metrics(simulate(community, scenario, controller))["community"]
    return {
        "season": season, "seed": seed, "peak_cost": peak_cost, "cost_lei": metrics["cost_lei"],
        "peak_import_kw": metrics["peak_import_kw"], "ssr": metrics["ssr"], "runtime_s": time.perf_counter() - t0,
    }


def _describe(row: dict) -> str:
    return (f"{row['season']:<8} seed {row['seed']:<3} varf {row['peak_cost']:5.1f} lei/kW  "
            f"cost {row['cost_lei']:8.1f} lei  varf {row['peak_import_kw']:5.1f} kW  ({row['runtime_s']:.1f} s)")


def run_all(n_seeds: int, n_days: int, dt_h: float, workers: int | None,
            real: bool = False, deg_cost: float | None = None, price_year: int = ds.DEFAULT_PRICE_YEAR,
            seasons: tuple[str, ...] = PARETO_SEASONS) -> list[dict]:
    tasks = [(season, seed, peak_cost, n_days, dt_h, real, deg_cost, price_year)
             for peak_cost in PEAK_COSTS for season in seasons for seed in range(n_seeds)]
    rows = run_parallel(run_one, tasks, _describe, workers)
    return sorted(rows, key=lambda row: (PARETO_SEASONS.index(row["season"]), row["peak_cost"], row["seed"]))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return [{key: (value if key == "season" else float(value)) for key, value in row.items()}
                for row in csv.DictReader(file)]


def means(rows: list[dict]) -> dict[str, list[tuple[float, float, float]]]:
    """season -> [(peak_cost, mean cost, mean peak)], for the seasons that have rows."""
    out = {}
    for season in PARETO_SEASONS:
        points = []
        for peak_cost in PEAK_COSTS:
            selected = [r for r in rows if r["season"] == season and r["peak_cost"] == peak_cost]
            if selected:
                points.append((peak_cost, float(np.mean([r["cost_lei"] for r in selected])),
                               float(np.mean([r["peak_import_kw"] for r in selected]))))
        if points:
            out[season] = points
    return out


def pareto_plot(rows: list[dict], n_days: int, path: Path) -> None:
    """Log x so the peak_cost = 0 point (~40 kW) does not squash the 1-8 kW region."""
    plt = plot_style()
    data = means(rows)
    fig, axes = plt.subplots(1, len(data), figsize=(4 * len(data), 3.8))
    for ax, (season, points) in zip(np.atleast_1d(axes), data.items(), strict=True):
        peaks = [peak for _, _, peak in points]
        costs = [cost for _, cost, _ in points]
        ax.plot(peaks, costs, "-o", color=SEASON_COLORS[season], lw=1.4, ms=4)
        for i, (peak_cost, cost, peak) in enumerate(points):
            ax.annotate(f"{peak_cost:g}", (peak, cost), xytext=(0, 7 if i % 2 else -11), textcoords="offset points",
                        fontsize=7, color=INK, ha="center")
        ax.set_xscale("log")
        ax.set_xticks([1, 2, 5, 10, 20, 50], ["1", "2", "5", "10", "20", "50"])
        ax.set_title(SEASON_LABELS[season], fontsize=10, color=INK, loc="left")
        ax.set_xlabel("Vârf import săptămânal realizat [kW]")
        low, high = min(costs), max(costs)
        ax.set_ylim(low - 0.25 * (high - low) - 1, high + 0.25 * (high - low) + 1)
    np.atleast_1d(axes)[0].set_ylabel(f"Cost energie [lei / {n_days} zile]")
    fig.suptitle(f"{LABELS['mpc_varf']}: etichetele sunt taxa [lei/kW], medie pe seed-uri",
                 fontsize=9, color=MUTED, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def print_table(rows: list[dict]) -> None:
    print(f"\n{'anotimp':<10} {'cost varf [lei/kW]':>18} {'cost [lei]':>12} {'varf [kW]':>10}")
    for season, points in means(rows).items():
        for peak_cost, cost, peak in points:
            print(f"{season:<10} {peak_cost:>18g} {cost:>12.1f} {peak:>10.2f}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    utf8_console()
    add_common_arguments(parser, default_seeds=3)
    parser.add_argument("--plot-only", action="store_true", help="doar graficul, din pareto.csv existent")
    args = parser.parse_args(argv)
    out = output_dir(args)

    if args.plot_only:
        rows = read_csv(out / "pareto.csv")
    else:
        covered = seasons_to_run(args)
        seasons = tuple(season for season in PARETO_SEASONS if season in covered)
        rows = run_all(args.seeds, args.days, args.dt, args.workers, args.real, args.deg, args.price_year, seasons)
        write_csv(rows, CSV_KEYS, out / "pareto.csv")
    pareto_plot(rows, args.days, out / "pareto.png")
    print_table(rows)
    print(f"\nRezultate scrise in {out}")


if __name__ == "__main__":
    main()
