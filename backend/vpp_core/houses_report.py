"""
Per-house, per-month view of the evaluation: 4 seasons x N seeds x 6 strategies, one row per house.

Run from backend/:   python -m vpp_core.houses_report [--seeds 5] [--days 7] [--dt 0.25]
                                                       [--real [--price-year 2023|2025|2026]]
Output: results/case.csv and results/case_luna.png (results/real/<price year>/... with --real).
Monthly cost = cost of the simulated period x MONTH_DAYS / days (a 30-day month, linear extrapolation).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from vpp_core import data_sources as ds
from vpp_core.evaluation import make_controller
from vpp_core.metrics import compute_metrics
from vpp_core.params import CommunityParams, HouseParams, default_community
from vpp_core.reporting import (
    COLORS,
    INK,
    LABELS,
    MUTED,
    SEASON_LABELS,
    SEASONS,
    SHORT_LABELS,
    add_common_arguments,
    data_label,
    make_scenario,
    output_dir,
    plot_style,
    read_csv,
    run_parallel,
    season_index,
    seasons_to_run,
    utf8_console,
    write_csv,
)
from vpp_core.simulator import simulate

CONTROLLERS = ("fara_baterie", "baterie_locala", "vpp_reguli", "mpc", "mpc_ideal", "optim_lp")
MONTH_DAYS = 30
CHART_SEASONS = ("iarna", "vara")

DAILY = ("consum", "pv", "import", "export", "p2p_in", "p2p_out")
KEYS = [
    "season", "controller", "house", "eticheta", "module", "baterie_kwh", "n", "days",
    *[f"{name}_kwh_zi" for name in DAILY], "cost_lei", "cost_luna_lei",
]


@dataclass(frozen=True)
class Settings:
    n_seeds: int = 5
    n_days: int = 7
    dt_h: float = 0.25
    real: bool = False
    workers: int | None = None
    deg_cost: float | None = None
    controllers: tuple[str, ...] = CONTROLLERS
    seasons: tuple[str, ...] = tuple(key for key, _, _ in SEASONS)
    community: CommunityParams | None = None
    price_year: int = ds.DEFAULT_PRICE_YEAR


def modules_of(house: HouseParams) -> int:
    return 0 if house.battery is None else round(house.battery.capacity_kwh / 16)


def format_house_label(house_id: int, modules: int, battery_kwh: float) -> str:
    if modules == 0:
        return f"Casa {house_id} (fără stocare)"
    return f"Casa {house_id} ({modules} {'modul' if modules == 1 else 'module'}, {battery_kwh:.0f} kWh)"


def house_label(house: HouseParams) -> str:
    return format_house_label(house.id, modules_of(house), 0.0 if house.battery is None else house.battery.capacity_kwh)


def monthly(cost: float, days: float) -> float:
    return cost * MONTH_DAYS / days


def house_rows(metrics: dict, community: CommunityParams, days: float) -> list[dict]:
    """One row per house from compute_metrics(...)['houses']: kWh/day and the cost extrapolated to a month."""
    rows = []
    for house, m in zip(community.houses, metrics["houses"], strict=True):
        daily = {
            "consum": m["demand_kwh"], "pv": m["pv_kwh"], "import": m["import_kwh"], "export": m["export_kwh"],
            "p2p_in": m["p2p_in_kwh"], "p2p_out": m["p2p_out_kwh"],
        }
        rows.append({
            "house": house.id, "eticheta": house_label(house), "module": modules_of(house),
            "baterie_kwh": 0.0 if house.battery is None else house.battery.capacity_kwh, "days": days,
            **{f"{name}_kwh_zi": value / days for name, value in daily.items()},
            "cost_lei": m["cost_lei"], "cost_luna_lei": monthly(m["cost_lei"], days),
        })
    return rows


def run_one(task: tuple[str, int, str, Settings]) -> list[dict]:
    season, seed, controller_name, s = task
    community = default_community() if s.community is None else s.community
    scenario = make_scenario(season, seed, s.n_days, s.dt_h, s.real, community, s.price_year)
    result = simulate(community, scenario, make_controller(controller_name, seed, s.deg_cost))
    metrics = compute_metrics(result)
    rows = house_rows(metrics, community, scenario.n_steps / scenario.steps_per_day)
    for row in rows:
        row.update(season=season, seed=seed, controller=controller_name)
    return rows


def _describe(rows: list[dict]) -> str:
    r = rows[0]
    total = sum(row["cost_lei"] for row in rows)
    return f"{r['season']:<10} seed {r['seed']:<3} {r['controller']:<15} cost comunitate {total:8.1f} lei"


def run_all(s: Settings) -> list[dict]:
    tasks = [(season, seed, controller, s)
             for controller in s.controllers for season in s.seasons for seed in range(s.n_seeds)]
    return [row for rows in run_parallel(run_one, tasks, _describe, s.workers) for row in rows]


def aggregate(rows: list[dict]) -> list[dict]:
    """Mean over seeds for each (season, controller, house), ordered like the CSV."""
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        groups.setdefault((row["season"], row["controller"], row["house"]), []).append(row)
    numeric = [key for key in KEYS if key.endswith("_kwh_zi") or key in ("cost_lei", "cost_luna_lei")]
    out = []
    for (season, controller, house), group in groups.items():
        first = group[0]
        row = {
            "season": season, "controller": controller, "house": house, "eticheta": first["eticheta"],
            "module": first["module"], "baterie_kwh": first["baterie_kwh"], "n": len(group), "days": first["days"],
            **{key: float(np.mean([r[key] for r in group])) for key in numeric},
        }
        if same_as_pv(row):
            row.update(cost_lei=None, cost_luna_lei=None)
        out.append(row)
    return sorted(out, key=lambda r: (season_index(r["season"]), CONTROLLERS.index(r["controller"]), r["house"]))


def same_as_pv(row: dict) -> bool:
    """A house without a battery behaves the same under "baterie individuală" as under "doar PV"."""
    return row["controller"] == "baterie_locala" and row["module"] == 0


def monthly_chart(summary: list[dict], s: Settings, path: Path) -> None:
    plt = plot_style()
    controllers = [c for c in CONTROLLERS if c in s.controllers]
    seasons = [season for season in CHART_SEASONS if season in s.seasons]
    fig, axes = plt.subplots(len(seasons), 1, figsize=(8, 3.4 * len(seasons)), squeeze=False)
    n_bars, width = len(controllers), 0.8 / len(controllers)
    for ax, season in zip(axes[:, 0], seasons, strict=True):
        houses = sorted({r["house"] for r in summary if r["season"] == season})
        labels = {r["house"]: format_house_label(int(r["house"]), int(r["module"]), r["baterie_kwh"])
                  for r in summary if r["season"] == season}
        x = np.arange(len(houses))
        for j, controller in enumerate(controllers):
            by_house = {r["house"]: r["cost_luna_lei"] for r in summary
                        if r["season"] == season and r["controller"] == controller}
            shown = [i for i, h in enumerate(houses) if by_house[h] is not None]
            ax.bar(x[shown] + (j - (n_bars - 1) / 2) * width, [by_house[houses[i]] for i in shown], width * 0.92,
                   color=COLORS[controller], label=LABELS[controller])
        ax.set_xticks(x, [labels[h] for h in houses], rotation=30, ha="right")
        ax.set_ylabel("Cost pe lună [lei]")
        ax.set_title(SEASON_LABELS[season], fontsize=10, color=INK, loc="left")
        ax.grid(axis="x", visible=False)
        ax.axhline(0, color=MUTED, linewidth=0.8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Factura lunară pe casă ({data_label(s.real, s.price_year)}): "
                 f"cost pe {s.n_days} zile x {MONTH_DAYS}/{s.n_days}, "
                 f"medie pe {s.n_seeds} seed-uri; negativ = venit", fontsize=9, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def print_monthly(summary: list[dict], season: str) -> None:
    controllers = [c for c in CONTROLLERS if any(r["controller"] == c for r in summary)]
    print(f"\n{season}: cost pe casa pe luna [lei]")
    print(f"{'casa':<28}" + "".join(f"{SHORT_LABELS[c]:>22}" for c in controllers))
    for house in sorted({r["house"] for r in summary}):
        row = next(r for r in summary if r["season"] == season and r["house"] == house)
        costs = {r["controller"]: r["cost_luna_lei"] for r in summary if r["season"] == season and r["house"] == house}
        label = format_house_label(int(house), int(row["module"]), row["baterie_kwh"])
        print(f"{label:<28}" + "".join(f"{'–' if costs[c] is None else f'{costs[c]:.1f}':>22}" for c in controllers))
    if any(same_as_pv(r) for r in summary):
        print(f"– : casa nu are baterie, deci strategia coincide cu «{SHORT_LABELS['fara_baterie']}»")


def read_case_csv(path: Path) -> list[dict]:
    rows = read_csv(path)
    for row in rows:
        row.update(house=int(row["house"]), module=int(row["module"]), n=int(row["n"]))
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    utf8_console()
    add_common_arguments(parser, default_seeds=5)
    parser.add_argument("--plot-only", action="store_true", help="doar graficul, din case.csv existent")
    args = parser.parse_args(argv)
    out = output_dir(args)
    s = Settings(n_seeds=args.seeds, n_days=args.days, dt_h=args.dt, real=args.real,
                 workers=args.workers, deg_cost=args.deg, price_year=args.price_year)
    if args.plot_only:
        summary = read_case_csv(out / "case.csv")
    else:
        s = replace(s, seasons=seasons_to_run(args))
        summary = aggregate(run_all(s))
        write_csv(summary, KEYS, out / "case.csv")
    s = replace(s, seasons=tuple(key for key, _, _ in SEASONS if any(r["season"] == key for r in summary)))
    monthly_chart(summary, s, out / "case_luna.png")
    for season in CHART_SEASONS:
        if season in s.seasons:
            print_monthly(summary, season)
    print(f"\nRezultate scrise in {out}")


if __name__ == "__main__":
    main()
