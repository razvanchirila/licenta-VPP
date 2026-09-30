"""
Sensitivity studies: forecast error (MPC), battery wear cost, P2P on/off, community size.

Run from backend/:   python -m vpp_core.sensitivity [--seeds 3] [--days 7] [--dt 0.25]
                                                     [--real [--price-year 2023|2025|2026]]
                                                     [--study all|forecast|deg|p2p|scale]
Output in results/sensitivity/ (results/real/<price year>/sensitivity/ with --real): one CSV and one PNG per study.
"""
from __future__ import annotations

import argparse
import csv
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from vpp_core import data_sources as ds
from vpp_core.controllers import Controller, RuleBasedController
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, MPCController
from vpp_core.params import CommunityParams, default_community, random_community
from vpp_core.reporting import (
    COLORS,
    INK,
    LABELS,
    MUTED,
    SEASON_LABELS,
    SEASONS,
    SHORT_LABELS,
    add_common_arguments,
    make_scenario,
    output_dir,
    plot_style,
    run_parallel,
    season_index,
    seasons_to_run,
    utf8_console,
    weights,
    write_csv,
)
from vpp_core.simulator import simulate

FORECAST_ERRORS = ((0.0, 0.0), (0.1, 0.07), (0.3, 0.2), (0.5, 0.33))   # (pv, load) relative std at 24 h, load = 2/3 pv
DEG_COSTS = (0.0, 0.05, 0.12, 0.20, 0.30, 0.45)                         # lei/kWh of battery throughput
DEG_DEYE = {0.12: "SE-F16 din cicluri", 0.20: "SE-F16 din garanție (valoarea folosită)"}
SCALE_SIZES = (10, 20, 40, 80, 100, 200)
SCALE_SINGLE_SEED_FROM = 80                                             # one seed for the big communities
TWO_SEASONS = ("iarna", "vara")
CONTROLLERS = ("vpp_reguli", "mpc", "optim_lp")
SEASON_COLORS = {"iarna": COLORS["fara_baterie"], "vara": COLORS["baterie_locala"]}
ERROR_KW = {"ecolor": MUTED, "elinewidth": 0.8, "capsize": 2}


@dataclass(frozen=True)
class Settings:
    n_seeds: int = 3
    n_days: int = 7
    dt_h: float = 0.25
    real: bool = False
    workers: int | None = None
    deg_cost: float | None = None          # LP/MPC wear cost for the studies that do not vary it
    scale_sizes: tuple[int, ...] = SCALE_SIZES
    price_year: int = ds.DEFAULT_PRICE_YEAR
    seasons: tuple[str, ...] = tuple(key for key, _, _ in SEASONS)   # the P2P study runs on all of them


def make_controller(name: str, seed: int, deg_cost: float | None = None,
                    pv_error: float = 0.3, load_error: float = 0.2) -> Controller:
    if name == "vpp_reguli":
        return RuleBasedController(apply_alpha=False, name=name)
    if name == "mpc":
        return MPCController(seed=seed, weights=weights(deg_cost), pv_error=pv_error, load_error=load_error, name=name)
    if name == "optim_lp":
        return LPController(weights=weights(deg_cost), name=name)
    raise ValueError(f"unknown controller {name!r}")


def without_p2p(community: CommunityParams) -> CommunityParams:
    return CommunityParams(houses=tuple(replace(h, p2p_enabled=False) for h in community.houses), grid=community.grid)


def run_and_measure(community: CommunityParams, season: str, seed: int, controller: Controller, s: Settings) -> dict:
    """Community metrics plus battery throughput (kWh charged), equivalent full cycles per day and wall time."""
    scenario = make_scenario(season, seed, s.n_days, s.dt_h, s.real, community, s.price_year)
    t0 = time.perf_counter()
    result = simulate(community, scenario, controller)
    wall_s = time.perf_counter() - t0
    m = compute_metrics(result)["community"]
    usable_kwh = sum(h.battery.usable_kwh for h in community.houses if h.battery)
    discharged_kwh = float(result.flows["dis"].sum() * scenario.dt_h)
    return {
        "cost_lei": m["cost_lei"], "ssr": m["ssr"], "peak_import_kw": m["peak_import_kw"], "p2p_kwh": m["p2p_kwh"],
        "throughput_kwh": float(result.flows["ch"].sum() * scenario.dt_h),
        "cycles_per_day": discharged_kwh / usable_kwh / m["days"] if usable_kwh else 0.0,
        "wall_s": wall_s,
    }


def _row(task: dict, metrics: dict) -> dict:
    return {**{k: v for k, v in task.items() if k != "settings"}, **metrics}


def _describe(row: dict) -> str:
    fields = " ".join(f"{k}={v}" for k, v in row.items()
                      if k in ("season", "seed", "controller", "pv_error", "deg_cost", "p2p", "n_houses"))
    return f"{fields:<55} cost {row['cost_lei']:8.1f} lei  ({row['wall_s']:.1f} s)"


def _select(rows: list[dict], **filters) -> list[dict]:
    return [r for r in rows if all(r[k] == v for k, v in filters.items())]


def _mean_std(rows: list[dict], metric: str, **filters) -> tuple[float, float]:
    values = np.array([r[metric] for r in _select(rows, **filters)])
    return float(values.mean()), float(values.std(ddof=1)) if len(values) > 1 else 0.0


def _series(rows: list[dict], metric: str, xs, key: str, **filters) -> tuple[list[float], list[float]]:
    """(means, stds) of `metric` at each x, where x is the value of column `key`."""
    stats = [_mean_std(rows, metric, **{key: x}, **filters) for x in xs]
    return [m for m, _ in stats], [sd for _, sd in stats]


# --- 1. forecast error ---------------------------------------------------------------------------------------

def forecast_tasks(s: Settings) -> list[dict]:
    tasks = []
    for season in TWO_SEASONS:
        for seed in range(s.n_seeds):
            tasks += [{"settings": s, "season": season, "seed": seed, "controller": "mpc",
                       "pv_error": pv, "load_error": load} for pv, load in FORECAST_ERRORS]
            tasks += [{"settings": s, "season": season, "seed": seed, "controller": name,
                       "pv_error": None, "load_error": None} for name in ("optim_lp", "vpp_reguli")]
    return tasks


def forecast_run_one(task: dict) -> dict:
    s = task["settings"]
    errors = {} if task["pv_error"] is None else {"pv_error": task["pv_error"], "load_error": task["load_error"]}
    controller = make_controller(task["controller"], task["seed"], s.deg_cost, **errors)
    return _row(task, run_and_measure(default_community(), task["season"], task["seed"], controller, s))


def _extra_vs_lp(rows: list[dict], season: str, controller: str, pv_error: float | None) -> tuple[float, float]:
    """Cost above the perfect-foresight LP of the same seed (the seed spread is ~100 lei, the effect a few lei)."""
    diffs = []
    for seed in sorted({r["seed"] for r in rows}):
        lp = _select(rows, season=season, seed=seed, controller="optim_lp")[0]["cost_lei"]
        run = _select(rows, season=season, seed=seed, controller=controller, pv_error=pv_error)[0]
        diffs.append(run["cost_lei"] - lp)
    return float(np.mean(diffs)), float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0


def forecast_chart(rows: list[dict], s: Settings, path: Path) -> None:
    plt = plot_style()
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.6))
    x = [100 * pv for pv, _ in FORECAST_ERRORS]
    for ax, season in zip(axes, TWO_SEASONS, strict=True):
        stats = [_extra_vs_lp(rows, season, "mpc", pv) for pv, _ in FORECAST_ERRORS]
        means, stds = [m for m, _ in stats], [sd for _, sd in stats]
        ax.errorbar(x, means, yerr=stds, fmt="-o", color=SEASON_COLORS[season], lw=1.4, ms=4,
                    ecolor=MUTED, elinewidth=0.8, capsize=2,
                    label=f"{SHORT_LABELS['mpc']}, {SEASON_LABELS[season].lower()}")
        for xi, mean in zip(x, means, strict=True):
            ax.annotate(f"{mean + 0.0:+.1f}", (xi, mean), xytext=(0, 7), textcoords="offset points", fontsize=7,
                        color=INK, ha="center")
        ax.axhline(0, color=COLORS["optim_lp"], ls="--", lw=1.3, label=SHORT_LABELS["optim_lp"])
        rules, _ = _extra_vs_lp(rows, season, "vpp_reguli", None)
        ax.axhline(rules, color=COLORS["vpp_reguli"], ls=":", lw=1.3,
                   label=f"{SHORT_LABELS['vpp_reguli']} (+{rules:.0f})")
        ax.set_title(SEASON_LABELS[season], fontsize=10, color=INK, loc="left")
        ax.set_xticks(x)
        ax.set_xlabel("Eroare de prognoză PV la 24 h [%]")
        ax.legend(loc="center right")
    axes[0].set_ylabel(f"Cost peste optimul teoretic [lei / {s.n_days} zile]")
    fig.suptitle(f"{LABELS['mpc']} cu erori de prognoză (consum: 2/3 din eroarea PV)\n"
                 "diferență față de optimul teoretic (LP) pe același seed, medie ± abatere standard",
                 fontsize=9, color=MUTED, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# --- 2. battery wear cost ------------------------------------------------------------------------------------

def deg_tasks(s: Settings) -> list[dict]:
    return [{"settings": s, "season": season, "seed": seed, "controller": name, "deg_cost": deg}
            for season in TWO_SEASONS for seed in range(s.n_seeds) for name in ("mpc", "optim_lp") for deg in DEG_COSTS]


def deg_run_one(task: dict) -> dict:
    s = task["settings"]
    controller = make_controller(task["controller"], task["seed"], task["deg_cost"])
    return _row(task, run_and_measure(default_community(), task["season"], task["seed"], controller, s))


def deg_chart(rows: list[dict], s: Settings, path: Path) -> None:
    plt = plot_style()
    fig, axes = plt.subplots(2, 2, figsize=(8, 6), sharex=True)
    panels = (("cost_lei", f"Cost [lei / {s.n_days} zile]"),
              ("throughput_kwh", f"Energie încărcată [kWh / {s.n_days} zile]"))
    for row_axes, season in zip(axes, TWO_SEASONS, strict=True):
        for ax, (metric, label) in zip(row_axes, panels, strict=True):
            for name in ("mpc", "optim_lp"):
                means, stds = _series(rows, metric, DEG_COSTS, "deg_cost", season=season, controller=name)
                ax.errorbar(DEG_COSTS, means, yerr=stds, fmt="-o", color=COLORS[name], lw=1.4, ms=4,
                            ecolor=MUTED, elinewidth=0.8, capsize=2, label=SHORT_LABELS[name])
            for (deg, text), style in zip(DEG_DEYE.items(), ("--", "-"), strict=True):
                ax.axvline(deg, color=MUTED, ls=style, lw=0.9, label=f"{deg:.2f}: {text}")
            ax.set_title(f"{SEASON_LABELS[season]}: {label}", fontsize=10, color=INK, loc="left")
            ax.set_xticks(DEG_COSTS, [f"{d:g}" for d in DEG_COSTS])
    for ax in axes[1]:
        ax.set_xlabel("Cost de degradare a bateriei [lei/kWh]")
    axes[0, 0].legend(loc="upper left", fontsize=7)
    fig.suptitle("(a) cost net, (b) energie încărcată în baterii; medie ± abatere standard pe seed-uri; "
                 "liniile verticale: estimările Deye SE-F16", fontsize=9, color=MUTED, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# --- 3. P2P on / off -----------------------------------------------------------------------------------------

def p2p_tasks(s: Settings) -> list[dict]:
    return [{"settings": s, "season": season, "seed": seed, "controller": name, "p2p": p2p}
            for season in s.seasons for seed in range(s.n_seeds) for name in CONTROLLERS for p2p in (1, 0)]


def p2p_run_one(task: dict) -> dict:
    s = task["settings"]
    community = default_community() if task["p2p"] else without_p2p(default_community())
    controller = make_controller(task["controller"], task["seed"], s.deg_cost)
    return _row(task, run_and_measure(community, task["season"], task["seed"], controller, s))


def p2p_chart(rows: list[dict], s: Settings, path: Path) -> None:
    from matplotlib.patches import Patch
    plt = plot_style()
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    seasons = [key for key, _, _ in SEASONS if _select(rows, season=key)]
    x, width = np.arange(len(seasons)), 0.8 / (2 * len(CONTROLLERS))
    for ax, (metric, label, scale) in zip(
        axes, (("cost_lei", f"Cost [lei / {s.n_days} zile]", 1.0), ("ssr", "Autarhie (SSR) [%]", 100.0)), strict=True
    ):
        for j, name in enumerate(CONTROLLERS):
            for k, p2p in enumerate((1, 0)):
                means, stds = _series(rows, metric, seasons, "season", controller=name, p2p=p2p)
                style = ({"color": COLORS[name]} if p2p
                         else {"facecolor": "white", "edgecolor": COLORS[name], "hatch": "///", "linewidth": 0.8})
                ax.bar(x + (2 * j + k - (2 * len(CONTROLLERS) - 1) / 2) * width, np.array(means) * scale, width * 0.92,
                       yerr=np.array(stds) * scale, error_kw=ERROR_KW, **style)
        ax.set_ylabel(label)
        ax.grid(axis="x", visible=False)
        ax.axhline(0, color=MUTED, linewidth=0.8)
    axes[1].set_xticks(x, [SEASON_LABELS[key] for key in seasons])
    handles = [Patch(color=COLORS[name], label=SHORT_LABELS[name]) for name in CONTROLLERS]
    handles.append(Patch(facecolor="white", edgecolor=INK, hatch="///", label="fără P2P (hașurat)"))
    axes[0].legend(handles=handles, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# --- 4. community size ---------------------------------------------------------------------------------------

def scale_tasks(s: Settings) -> list[dict]:
    """Largest MPC runs first, so the pool does not end on one long job."""
    tasks = []
    for n in sorted(s.scale_sizes, reverse=True):
        for name in CONTROLLERS:
            for seed in range(1 if n >= SCALE_SINGLE_SEED_FROM else s.n_seeds):
                tasks.append({"settings": s, "season": "iarna", "seed": seed, "controller": name, "n_houses": n})
    return tasks


def scale_run_one(task: dict) -> dict:
    s, n = task["settings"], task["n_houses"]
    controller = make_controller(task["controller"], task["seed"], s.deg_cost)
    metrics = run_and_measure(random_community(n, task["seed"]), task["season"], task["seed"], controller, s)
    return _row(task, {**metrics, "cost_per_house": metrics["cost_lei"] / n})


def scale_chart(rows: list[dict], s: Settings, path: Path) -> None:
    plt = plot_style()
    sizes = sorted(s.scale_sizes)
    fig, (left, right) = plt.subplots(1, 2, figsize=(8, 3.6))
    for name in CONTROLLERS:
        # seed 0 is the only seed run at every size (same winter sky), the other seeds are shown as faint points
        seed0 = [_select(rows, n_houses=n, controller=name, seed=0)[0]["cost_per_house"] for n in sizes]
        left.plot(sizes, seed0, "-o", color=COLORS[name], lw=1.4, ms=4, label=SHORT_LABELS[name])
        others = [r for r in rows if r["controller"] == name and r["seed"] != 0]
        left.plot([r["n_houses"] for r in others], [r["cost_per_house"] for r in others], "o",
                  color=COLORS[name], ms=3, alpha=0.35)
    for name in ("mpc", "optim_lp"):
        means, _ = _series(rows, "wall_s", sizes, "n_houses", controller=name)
        right.plot(sizes, means, "-o", color=COLORS[name], lw=1.4, ms=4, label=SHORT_LABELS[name])
    for ax in (left, right):
        ax.set_xscale("log")
        ax.set_xticks(sizes, [str(n) for n in sizes], minor=False)
        ax.set_xticks([], minor=True)
        ax.set_xlabel("Număr de case")
        ax.legend(loc="best")
    right.set_yscale("log")
    left.set_title(f"(a) Cost pe casă [lei / {s.n_days} zile], iarnă, seed 0", fontsize=10, color=INK, loc="left")
    right.set_title(f"(b) Timp de rulare [s], {s.n_days} zile, pas {60 * s.dt_h:.0f} min", fontsize=10, color=INK,
                    loc="left")
    fig.suptitle("Comunități aleatoare: PV 5-12 kWp, 0 / 1 / 2 module SE-F16 (20 / 50 / 30 % din case),\n"
                 "consum după una din casele din dispozitive.csv, limite de rețea ~ n; punctele mici: seed 1-2",
                 fontsize=9, color=MUTED, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# --- driver --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Study:
    tasks: Callable[[Settings], list[dict]]
    run_one: Callable[[dict], dict]
    chart: Callable[[list[dict], Settings, Path], None]
    keys: tuple[str, ...]
    sort_key: Callable[[dict], tuple]


def _order(row: dict) -> tuple:
    return season_index(row["season"]), row["seed"], CONTROLLERS.index(row["controller"])


STUDIES = {
    "forecast": Study(forecast_tasks, forecast_run_one, forecast_chart,
                      ("season", "seed", "controller", "pv_error", "load_error", "cost_lei", "ssr", "peak_import_kw"),
                      lambda r: (*_order(r), -1.0 if r["pv_error"] is None else r["pv_error"])),
    "deg": Study(deg_tasks, deg_run_one, deg_chart,
                 ("season", "seed", "controller", "deg_cost", "cost_lei", "throughput_kwh", "cycles_per_day", "ssr",
                  "peak_import_kw"),
                 lambda r: (*_order(r), r["deg_cost"])),
    "p2p": Study(p2p_tasks, p2p_run_one, p2p_chart,
                 ("season", "seed", "controller", "p2p", "cost_lei", "ssr", "p2p_kwh", "peak_import_kw"),
                 lambda r: (*_order(r), -r["p2p"])),
    "scale": Study(scale_tasks, scale_run_one, scale_chart,
                   ("n_houses", "seed", "controller", "cost_lei", "cost_per_house", "ssr", "peak_import_kw", "p2p_kwh",
                    "wall_s"),
                   lambda r: (r["n_houses"], r["seed"], CONTROLLERS.index(r["controller"]))),
}


def run_study(name: str, s: Settings) -> list[dict]:
    study = STUDIES[name]
    rows = run_parallel(study.run_one, study.tasks(s), _describe, s.workers)
    return sorted(rows, key=study.sort_key)


def read_rows(path: Path) -> list[dict]:
    def parse(key: str, value: str):
        if key in ("season", "controller"):
            return value
        if value == "":
            return None
        return int(value) if key in ("seed", "p2p", "n_houses") else float(value)

    with path.open(encoding="utf-8") as file:
        return [{key: parse(key, value) for key, value in row.items()} for row in csv.DictReader(file)]


def print_means(name: str, rows: list[dict]) -> None:
    """Mean over seeds of the study's main metrics, one line per setting."""
    group = {"forecast": ("season", "controller", "pv_error"), "deg": ("season", "controller", "deg_cost"),
             "p2p": ("season", "controller", "p2p"), "scale": ("n_houses", "controller")}[name]
    metrics = {"forecast": ("cost_lei", "ssr"), "deg": ("cost_lei", "throughput_kwh", "cycles_per_day"),
               "p2p": ("cost_lei", "ssr", "p2p_kwh"), "scale": ("cost_per_house", "ssr", "wall_s")}[name]
    print(f"\n{name}: " + "  ".join(f"{m}" for m in metrics))
    seen = []
    for row in rows:
        key = tuple(row[k] for k in group)
        if key in seen:
            continue
        seen.append(key)
        values = [_mean_std(rows, m, **dict(zip(group, key, strict=True)))[0] for m in metrics]
        print("  " + " ".join(f"{k}={v}" for k, v in zip(group, key, strict=True)).ljust(50)
              + "  ".join(f"{v:10.3f}" for v in values))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    utf8_console()
    add_common_arguments(parser, default_seeds=3)
    parser.add_argument("--study", choices=("all", *STUDIES), default="all")
    parser.add_argument("--plot-only", action="store_true", help="doar graficele, din CSV-urile existente")
    args = parser.parse_args(argv)
    out = output_dir(args) / "sensitivity"
    out.mkdir(exist_ok=True)
    seasons = tuple(key for key, _, _ in SEASONS) if args.plot_only else seasons_to_run(args)
    settings = Settings(args.seeds, args.days, args.dt, args.real, args.workers, args.deg,
                        price_year=args.price_year, seasons=seasons)
    for name in STUDIES if args.study == "all" else (args.study,):
        if args.plot_only:
            rows = read_rows(out / f"{name}.csv")
        else:
            rows = run_study(name, settings)
            write_csv(rows, list(STUDIES[name].keys), out / f"{name}.csv")
        STUDIES[name].chart(rows, settings, out / f"{name}.png")
        print_means(name, rows)
    print(f"\nRezultate scrise in {out}")


if __name__ == "__main__":
    main()
