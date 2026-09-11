"""
Baseline comparison. Run from vpp_simulator/:  python -m vpp_core.experiments
"""
from __future__ import annotations

from datetime import date

from vpp_core.controllers import RuleBasedController
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, MPCController
from vpp_core.params import default_community
from vpp_core.scenario import generate_scenario
from vpp_core.simulator import simulate


def baseline_controllers() -> list[RuleBasedController]:
    return [
        RuleBasedController(use_battery=False, p2p=False, arbitrage=False, apply_alpha=False, name="fara_baterie"),
        RuleBasedController(p2p=False, arbitrage=False, apply_alpha=False, name="baterie_locala"),
        RuleBasedController(apply_alpha=False, name="vpp_reguli"),
        RuleBasedController(apply_alpha=False, p2p_before_battery=True, name="vpp_reguli_p2p_intai"),
        RuleBasedController(apply_alpha=True, name="vpp_reguli_spec_alpha"),
    ]


COLUMNS = [
    ("controller", "{:<24}"), ("cost_lei", "{:>9.1f}"), ("import_kwh", "{:>9.1f}"),
    ("export_kwh", "{:>9.1f}"), ("p2p_kwh", "{:>8.1f}"), ("curtail_kwh", "{:>9.1f}"),
    ("shed_kwh", "{:>8.1f}"), ("soc_delta_kwh", "{:>7.1f}"), ("peak_import_kw", "{:>7.1f}"),
    ("scr", "{:>6.1%}"), ("ssr", "{:>6.1%}"),
]


def print_table(rows: list[dict]) -> None:
    print("  ".join(f"{name:>{len(fmt.format(0)) if name != 'controller' else 24}}" for name, fmt in COLUMNS))
    for r in rows:
        print("  ".join(fmt.format(r[name]) for name, fmt in COLUMNS))


def main() -> None:
    community = default_community()
    for label, start in (("Vara (iunie)", date(2025, 6, 1)), ("Iarna (ianuarie)", date(2025, 1, 10))):
        sc = generate_scenario(community, start=start, n_days=7, dt_h=0.25, seed=42)
        print(f"\n{label}: 7 zile, 10 case, pas 15 min, seed 42")
        controllers = baseline_controllers() + [MPCController(), LPController()]
        print_table([compute_metrics(simulate(community, sc, c))["community"] for c in controllers])


if __name__ == "__main__":
    main()
