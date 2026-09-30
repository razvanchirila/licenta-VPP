"""
The real-data evaluation side by side for the price years: monthly bill per house and mean import price of
each simulated week. Reads results/real/<year>/summary.csv (evaluation) and case.csv (houses_report); a year
or a season without results is left out.

Run from backend/:   python -m vpp_core.compare_years [--dir results/real]
Output: comparatie_ani.csv and comparatie_ani.png in the same folder.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

import numpy as np

from vpp_core import data_sources as ds
from vpp_core.evaluation import read_summary_csv
from vpp_core.houses_report import read_case_csv
from vpp_core.reporting import (
    COLORS,
    INK,
    LABELS,
    MUTED,
    RESULTS_REAL_DIR,
    SEASON_LABELS,
    SEASON_STARTS_REAL,
    SEASONS,
    plot_style,
    utf8_console,
    write_csv,
)
from vpp_core.scenario_real import NETWORK_ADDER, SUPPLY_MARGIN, VAT

COMPARED = ("fara_baterie", "mpc")
KEYS = [
    "season", "an", "zile", "pzu_mediu_lei_kwh", "pzu_min_lei_kwh", "pzu_max_lei_kwh", "ore_pzu_negativ",
    "pret_import_mediu_lei_kwh", "pret_export_mediu_lei_kwh",
    *[f"cost_luna_casa_{name}_lei" for name in COMPARED], "economie_mpc_lei",
    *[f"cost_comunitate_{name}_lei" for name in COMPARED], *[f"import_{name}_kwh" for name in COMPARED],
]


def week_prices(season: str, year: int, n_days: int) -> dict:
    """PZU and tariff statistics of the simulated window (lei/kWh); same formulas as scenario_real."""
    first = SEASON_STARTS_REAL[season].timetuple().tm_yday - 1
    pzu = ds.load_prices_lei_kwh(year)[first : first + n_days]
    return {
        "pzu_mediu_lei_kwh": float(pzu.mean()), "pzu_min_lei_kwh": float(pzu.min()),
        "pzu_max_lei_kwh": float(pzu.max()), "ore_pzu_negativ": int((pzu < 0).sum()),
        "pret_import_mediu_lei_kwh": float(((pzu + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT)).mean()),
        "pret_export_mediu_lei_kwh": float((pzu + SUPPLY_MARGIN).mean()),
    }


def collect(real_dir: Path) -> list[dict]:
    """One row per (season, year) that has results, ordered by season then year."""
    rows = []
    for year in ds.PRICE_YEARS:
        folder = real_dir / str(year)
        if not (folder / "summary.csv").exists() or not (folder / "case.csv").exists():
            continue
        summary, case = read_summary_csv(folder / "summary.csv"), read_case_csv(folder / "case.csv")
        for season, _, _ in SEASONS:
            houses = {name: [r for r in case if r["season"] == season and r["controller"] == name]
                      for name in COMPARED}
            if not all(houses.values()) or any((season, name) not in summary for name in COMPARED):
                continue
            n_days = round(houses[COMPARED[0]][0]["days"])
            row = {"season": season, "an": year, "zile": n_days, **week_prices(season, year, n_days)}
            for name in COMPARED:
                row[f"cost_luna_casa_{name}_lei"] = float(np.mean([r["cost_luna_lei"] for r in houses[name]]))
                row[f"cost_comunitate_{name}_lei"] = summary[(season, name)]["cost_lei_mean"]
                row[f"import_{name}_kwh"] = summary[(season, name)]["import_kwh_mean"]
            row["economie_mpc_lei"] = row["cost_luna_casa_fara_baterie_lei"] - row["cost_luna_casa_mpc_lei"]
            rows.append(row)
    order = [key for key, _, _ in SEASONS]
    return sorted(rows, key=lambda r: (order.index(r["season"]), r["an"]))


def chart(rows: list[dict], path: Path) -> None:
    from matplotlib.patches import Patch

    plt = plot_style()
    years = sorted({r["an"] for r in rows})
    seasons = [key for key, _, _ in SEASONS if any(r["season"] == key for r in rows)]
    by_key = {(r["season"], r["an"]): r for r in rows}
    slot = 0.84 / len(years)
    bar = slot * 0.42
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.4, 6.6), sharex=True, gridspec_kw={"height_ratios": [2.1, 1]})
    centres, tick_labels = [], []
    for i, season in enumerate(seasons):
        for k, year in enumerate(years):
            x = i + (k - (len(years) - 1) / 2) * slot
            centres.append(x)
            tick_labels.append(str(year))
            row = by_key.get((season, year))
            if row is None:
                for ax in (top, bottom):
                    ax.annotate("fără\ndate", (x, 0), xytext=(0, 4), textcoords="offset points", ha="center",
                                va="bottom", fontsize=7, color=MUTED)
                continue
            for j, name in enumerate(COMPARED):
                value = row[f"cost_luna_casa_{name}_lei"]
                xb = x + (j - 0.5) * bar
                top.bar(xb, value, bar * 0.92, color=COLORS[name])
                top.annotate(f"{value:.0f}", (xb, value), xytext=(0, 2 if value >= 0 else -2),
                             textcoords="offset points", ha="center", va="bottom" if value >= 0 else "top",
                             fontsize=6.5, color=INK)
            price = row["pret_import_mediu_lei_kwh"]
            bottom.bar(x, price, 2 * bar * 0.96, color=MUTED)
            bottom.annotate(f"{price:.2f}", (x, price), xytext=(0, 2), textcoords="offset points", ha="center",
                            va="bottom", fontsize=7, color=INK)
    top.axhline(0, color=MUTED, linewidth=0.8)
    top.set_ylabel("Cost pe casă pe lună [lei]")
    top.margins(y=0.12)
    top.legend(handles=[Patch(color=COLORS[name], label=LABELS[name]) for name in COMPARED], loc="upper right")
    bottom.set_ylabel("Preț mediu de import\n[lei/kWh, cu TVA]")
    bottom.set_ylim(0, max(r["pret_import_mediu_lei_kwh"] for r in rows) * 1.22)
    bottom.set_xticks(centres, tick_labels, fontsize=8)
    bottom.set_xlim(-0.56, len(seasons) - 0.44)
    for ax in (top, bottom):
        ax.grid(axis="x", visible=False)
    names = bottom.secondary_xaxis("bottom")
    names.set_xticks(range(len(seasons)), [SEASON_LABELS[season] for season in seasons])
    names.tick_params(length=0, pad=18)
    names.spines["bottom"].set_visible(False)
    n_days = rows[0]["zile"]
    fig.suptitle(f"Aceeași comunitate și aceeași producție PV ({ds.YEAR}), prețuri PZU din "
                 f"{', '.join(map(str, years))}: o săptămână pe anotimp,\ncost pe {n_days} zile x 30/{n_days}, "
                 "medie pe case și pe seed-uri; negativ = venit", fontsize=9, color=MUTED, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def print_table(rows: list[dict]) -> None:
    print(f"\n{'anotimp':<11} {'an':>5} {'PZU mediu':>10} {'import mediu':>13} {'doar PV':>9} {'MPC':>9}"
          "    [lei/kWh, lei/kWh cu TVA, lei pe casa pe luna]")
    for row in rows:
        start = SEASON_STARTS_REAL[row["season"]]
        end = start + timedelta(days=row["zile"] - 1)
        print(f"{row['season']:<11} {row['an']:>5} {row['pzu_mediu_lei_kwh']:>10.3f} "
              f"{row['pret_import_mediu_lei_kwh']:>13.3f} {row['cost_luna_casa_fara_baterie_lei']:>9.1f} "
              f"{row['cost_luna_casa_mpc_lei']:>9.1f}    {start:%d.%m}-{end:%d.%m}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    utf8_console()
    parser.add_argument("--dir", type=Path, default=RESULTS_REAL_DIR, help="folderul cu subfolderele pe ani")
    args = parser.parse_args(argv)
    rows = collect(args.dir)
    if not rows:
        parser.error(f"niciun an cu summary.csv si case.csv in {args.dir}; ruleaza intai evaluation si "
                     "houses_report cu --real --price-year")
    write_csv(rows, KEYS, args.dir / "comparatie_ani.csv")
    chart(rows, args.dir / "comparatie_ani.png")
    print_table(rows)
    print(f"\nRezultate scrise in {args.dir}")


if __name__ == "__main__":
    main()
