"""Quick comparison of all strategies on a summer and a winter week:  python -m vpp_core.experiments"""
from __future__ import annotations

from datetime import date, timedelta

from vpp_core.controllers import RuleBasedController
from vpp_core.forecast import HISTORY_DAYS
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, MPCController, RealisticMPCController
from vpp_core.params import default_community
from vpp_core.reporting import LABELS, utf8_console
from vpp_core.scenario import generate_scenario, split_past
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
    ("controller", "{:<40}"), ("cost_lei", "{:>9.1f}"), ("import_kwh", "{:>9.1f}"),
    ("export_kwh", "{:>9.1f}"), ("p2p_kwh", "{:>8.1f}"), ("curtail_kwh", "{:>9.1f}"),
    ("shed_kwh", "{:>8.1f}"), ("soc_delta_kwh", "{:>7.1f}"), ("peak_import_kw", "{:>7.1f}"),
    ("scr", "{:>6.1%}"), ("ssr", "{:>6.1%}"),
]


def print_table(rows: list[dict]) -> None:
    print("  ".join(f"{name:>{len(fmt.format(0)) if name != 'controller' else 40}}" for name, fmt in COLUMNS))
    for row in rows:
        print("  ".join(fmt.format(LABELS[row[name]] if name == "controller" else row[name]) for name, fmt in COLUMNS))


def main() -> None:
    utf8_console()
    community = default_community()
    for label, start in (("Vara (iunie)", date(2025, 6, 1)), ("Iarna (ianuarie)", date(2025, 1, 10))):
        full = generate_scenario(community, start=start - timedelta(days=HISTORY_DAYS), n_days=7 + HISTORY_DAYS,
                                 dt_h=0.25, seed=42)
        scenario = split_past(full, HISTORY_DAYS)
        print(f"\n{label}: 7 zile, 10 case, pas 15 min, seed 42")
        controllers = baseline_controllers() + [RealisticMPCController(), MPCController(), LPController()]
        rows = [compute_metrics(simulate(community, scenario, controller))["community"] for controller in controllers]
        print_table(rows)


if __name__ == "__main__":
    main()
