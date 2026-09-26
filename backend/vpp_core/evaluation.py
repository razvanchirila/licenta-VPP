"""
Full evaluation: 4 seasons x N seeds x 6 strategies; tables and charts in results/.

Run from backend/:   python -m vpp_core.evaluation [--seeds 5] [--days 7] [--dt 0.25] [--real] [--deg 0.45]
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from vpp_core.controllers import Controller, RuleBasedController
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, MPCController
from vpp_core.params import default_community
from vpp_core.reporting import (
    COLORS,
    INK,
    MUTED,
    SEASON_STARTS_REAL,
    SEASONS,
    add_common_arguments,
    make_scenario,
    output_dir,
    plot_style,
    run_parallel,
    season_index,
    weights,
    write_csv,
)
from vpp_core.simulator import simulate

CONTROLLERS = ("fara_baterie", "baterie_locala", "vpp_reguli", "mpc", "mpc_varf", "optim_lp")
CONTROLLER_LABELS = {
    "fara_baterie": "fără baterie",
    "baterie_locala": "baterie locală",
    "vpp_reguli": "VPP reguli",
    "mpc": "MPC",
    "mpc_varf": "MPC + cost vârf",
    "optim_lp": "LP (prognoză perfectă)",
}

# lei/kW of weekly peak import for "mpc_varf": ~3 kWh at the dearest hour per extra kW,
# enough to spread night charging over the cheap zone without forbidding arbitrage (see pareto.py)
PEAK_COST = 6.0

TS_SEASON, TS_SEED, TS_DAYS = "iarna", 42, 2   # the time-series plot

METRICS = (
    "cost_lei", "import_kwh", "export_kwh", "p2p_kwh", "curtail_kwh", "shed_kwh",
    "battery_loss_kwh", "soc_delta_kwh", "peak_import_kw", "peak_export_kw", "scr", "ssr",
)


def make_controller(name: str, seed: int, deg_cost: float | None = None) -> Controller:
    if name == "fara_baterie":
        return RuleBasedController(use_battery=False, p2p=False, arbitrage=False, apply_alpha=False, name=name)
    if name == "baterie_locala":
        return RuleBasedController(p2p=False, arbitrage=False, apply_alpha=False, name=name)
    if name == "vpp_reguli":
        return RuleBasedController(apply_alpha=False, name=name)
    if name == "mpc":
        return MPCController(seed=seed, weights=weights(deg_cost), name=name)
    if name == "mpc_varf":
        return MPCController(seed=seed, weights=weights(deg_cost, peak_cost=PEAK_COST), name=name)
    if name == "optim_lp":
        return LPController(weights=weights(deg_cost), name=name)
    raise ValueError(f"unknown controller {name!r}")


def run_one(task: tuple[str, int, str, int, float, bool, float | None]) -> dict:
    season, seed, controller_name, n_days, dt_h, real, deg_cost = task
    community = default_community()
    scenario = make_scenario(season, seed, n_days, dt_h, real)
    t0 = time.perf_counter()
    result = simulate(community, scenario, make_controller(controller_name, seed, deg_cost))
    metrics = compute_metrics(result)["community"]
    metrics.update(season=season, seed=seed, controller=controller_name, runtime_s=time.perf_counter() - t0)
    series = {
        "pv_kw": scenario.pv_kw.sum(axis=0),
        "load_kw": scenario.load_kw.sum(axis=0),
        "imp_kw": result.flows["imp"].sum(axis=0),
        "soc_kwh": result.soc_kwh.sum(axis=0)[1:],
    }
    return {"metrics": metrics, "series": series}


def _describe(result: dict) -> str:
    m = result["metrics"]
    return (f"{m['season']:<10} seed {m['seed']:<3} {m['controller']:<15} "
            f"cost {m['cost_lei']:8.1f} lei  varf {m['peak_import_kw']:5.1f} kW  ({m['runtime_s']:.1f} s)")


def run_all(n_seeds: int, n_days: int, dt_h: float, workers: int | None,
            real: bool = False, deg_cost: float | None = None) -> list[dict]:
    tasks = [
        (season, seed, controller, n_days, dt_h, real, deg_cost)
        for controller in ("mpc", "mpc_varf", "optim_lp", "vpp_reguli", "baterie_locala", "fara_baterie")
        for season, _, _ in SEASONS
        for seed in range(n_seeds)
    ]
    if TS_SEED >= n_seeds:   # extra runs for the time-series plot only
        tasks += [
            (TS_SEASON, TS_SEED, controller, n_days, dt_h, real, deg_cost)
            for controller in ("vpp_reguli", "mpc")
        ]
    return run_parallel(run_one, tasks, _describe, workers)


def write_metrics_csv(rows: list[dict], path: Path) -> None:
    keys = ["season", "seed", "controller", "days", "pv_kwh", "demand_kwh", *METRICS, "balance_error_kwh", "runtime_s"]
    def _sort_key(row: dict) -> tuple:
        return season_index(row["season"]), row["seed"], CONTROLLERS.index(row["controller"])

    rows = sorted(rows, key=_sort_key)
    write_csv(rows, keys, path)


def summarize(rows: list[dict], n_seeds: int) -> dict[tuple[str, str], dict]:
    """(season, controller) -> {'n', '<metric>_mean', '<metric>_std'} over seeds < n_seeds."""
    summary = {}
    for season, _, _ in SEASONS:
        for controller in CONTROLLERS:
            selected = [
                r
                for r in rows
                if r["season"] == season and r["controller"] == controller and r["seed"] < n_seeds
            ]
            if not selected:
                continue
            stats = {"season": season, "controller": controller, "n": len(selected)}
            for metric in METRICS:
                values = np.array([r[metric] for r in selected])
                stats[f"{metric}_mean"] = float(values.mean())
                stats[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            summary[(season, controller)] = stats
    return summary


def write_summary_csv(summary: dict, path: Path) -> None:
    keys = ["season", "controller", "n"] + [f"{metric}_{stat}" for metric in METRICS for stat in ("mean", "std")]
    write_csv(list(summary.values()), keys, path)


def _mean_std(stats: dict, metric: str, fmt: str) -> str:
    return f"{stats[metric + '_mean']:{fmt}} +- {stats[metric + '_std']:{fmt}}"


def print_summary(summary: dict) -> None:
    print(f"\n{'anotimp':<10} {'strategie':<15} {'cost [lei]':>16} {'SSR':>14} {'SCR':>14} {'varf import [kW]':>18}")
    for (season, controller), stats in summary.items():
        print(f"{season:<10} {controller:<15} {_mean_std(stats, 'cost_lei', '6.1f'):>16} "
              f"{_mean_std(stats, 'ssr', '4.2f'):>14} "
              f"{_mean_std(stats, 'scr', '4.2f'):>14} {_mean_std(stats, 'peak_import_kw', '5.1f'):>18}")


def grouped_bar(summary: dict, metric: str, ylabel: str, path: Path, scale: float = 1.0) -> None:
    plt = plot_style()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    n_bars, width = len(CONTROLLERS), 0.8 / len(CONTROLLERS)
    x = np.arange(len(SEASONS))
    for j, controller in enumerate(CONTROLLERS):
        means = [summary[(season, controller)][f"{metric}_mean"] * scale for season, _, _ in SEASONS]
        stds = [summary[(season, controller)][f"{metric}_std"] * scale for season, _, _ in SEASONS]
        ax.bar(x + (j - (n_bars - 1) / 2) * width, means, width * 0.92, yerr=stds, color=COLORS[controller],
               label=CONTROLLER_LABELS[controller], error_kw={"ecolor": MUTED, "elinewidth": 0.8, "capsize": 2})
    ax.set_xticks(x, [label for _, label, _ in SEASONS])
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def timeseries_plot(results: list[dict], dt_h: float, path: Path, real: bool = False) -> None:
    plt = plot_style()
    series_of = {r["metrics"]["controller"]: r["series"] for r in results
                 if r["metrics"]["season"] == TS_SEASON and r["metrics"]["seed"] == TS_SEED}
    n_steps = round(TS_DAYS * 24 / dt_h)
    hours = (np.arange(n_steps) + 0.5) * dt_h
    fig, axes = plt.subplots(2, 2, figsize=(10, 5.2), sharex="col", sharey="row",
                             gridspec_kw={"height_ratios": [2.2, 1]})
    for col, controller in enumerate(("vpp_reguli", "mpc")):
        series = series_of[controller]
        top, bottom = axes[0, col], axes[1, col]
        top.plot(hours, series["pv_kw"][:n_steps], color="#eda100", lw=1.4, label="PV disponibil")
        top.plot(hours, series["load_kw"][:n_steps], color="#2a78d6", lw=1.4, label="Consum")
        top.plot(hours, series["imp_kw"][:n_steps], color="#eb6834", lw=1.4, label="Import din rețea")
        bottom.plot(hours, series["soc_kwh"][:n_steps], color="#1baf7a", lw=1.4, label="Energie stocată (total)")
        top.set_title(CONTROLLER_LABELS[controller], fontsize=10, color=INK, loc="left")
        bottom.set_xlabel("Ora [h]")
        bottom.set_xticks(np.arange(0, TS_DAYS * 24 + 1, 6))
        top.set_xlim(0, TS_DAYS * 24)
    axes[0, 0].set_ylabel("Putere [kW]")
    axes[1, 0].set_ylabel("SOC total [kWh]")
    axes[0, 0].legend(loc="upper left", ncol=3)
    axes[1, 0].legend(loc="upper left")
    source = f"date reale, {SEASON_STARTS_REAL[TS_SEASON]:%d.%m.%Y}" if real else f"seed {TS_SEED}"
    fig.suptitle(f"Iarnă, {source}, primele {TS_DAYS} zile (comunitate, 10 case)", fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def make_charts(summary: dict, results: list[dict], n_days: int, dt_h: float, out: Path, real: bool = False) -> None:
    grouped_bar(summary, "cost_lei", f"Cost [lei / {n_days} zile]", out / "cost.png")
    grouped_bar(summary, "ssr", "Autarhie (SSR) [%]", out / "ssr.png", scale=100)
    grouped_bar(summary, "scr", "Autoconsum (SCR) [%]", out / "scr.png", scale=100)
    grouped_bar(summary, "peak_import_kw", "Vârf import [kW]", out / "varf_import.png")
    grouped_bar(summary, "curtail_kwh", "Energie PV limitată [kWh]", out / "curtailment.png")
    timeseries_plot(results, dt_h, out / "serie_timp_iarna.png", real)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    add_common_arguments(parser, default_seeds=5)
    args = parser.parse_args(argv)
    out = output_dir(args)

    results = run_all(args.seeds, args.days, args.dt, args.workers, args.real, args.deg)
    rows = [r["metrics"] for r in results if r["metrics"]["seed"] < args.seeds]
    summary = summarize(rows, args.seeds)
    write_metrics_csv(rows, out / "metrics.csv")
    write_summary_csv(summary, out / "summary.csv")
    make_charts(summary, results, args.days, args.dt, out, args.real)
    print_summary(summary)
    print(f"\nRezultate scrise in {out}")


if __name__ == "__main__":
    main()
