"""Evaluation metrics from a SimResult: energies in kWh, costs in lei, SCR / SSR as ratios."""
from __future__ import annotations

import numpy as np

from vpp_core.params import HouseParams
from vpp_core.scenario import Scenario
from vpp_core.simulator import SimResult


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator > 1e-12 else 0.0


def _house_metrics(
    house: HouseParams, i: int, energy: dict[str, np.ndarray], scenario: Scenario,
    pv_kwh: np.ndarray, demand_kwh: np.ndarray, served_kwh: np.ndarray, result: SimResult,
) -> dict:
    """`energy` holds the flows in kWh, (n_houses, n_steps)."""
    pv_total = pv_kwh[i].sum()
    used_locally = pv_total - energy["curtail"][i].sum() - energy["exp"][i].sum() - energy["p2p_out"][i].sum()
    bill = (
        (energy["imp"][i] * scenario.price_import).sum()
        - (energy["exp"][i] * scenario.price_export).sum()
        + (energy["p2p_in"][i] * scenario.price_p2p).sum()
        - (energy["p2p_out"][i] * scenario.price_p2p).sum()
    )
    bought = energy["imp"][i].sum() + energy["p2p_in"][i].sum()
    cycles = _ratio(energy["dis"][i].sum(), house.battery.usable_kwh) if house.battery else 0.0
    return {
        "id": house.id,
        "pv_kwh": pv_total,
        "demand_kwh": demand_kwh[i].sum(),
        "shed_kwh": energy["shed"][i].sum(),
        "import_kwh": energy["imp"][i].sum(),
        "export_kwh": energy["exp"][i].sum(),
        "p2p_in_kwh": energy["p2p_in"][i].sum(),
        "p2p_out_kwh": energy["p2p_out"][i].sum(),
        "curtail_kwh": energy["curtail"][i].sum(),
        "battery_loss_kwh": result.losses_kwh[i].sum(),
        "soc_delta_kwh": result.soc_kwh[i, -1] - result.soc_kwh[i, 0],
        "cycles": cycles,
        "cost_lei": bill,
        "scr": _ratio(used_locally, pv_total),
        "ssr": 1 - _ratio(bought, served_kwh[i].sum()),
    }


def _community_metrics(
    result: SimResult, energy: dict[str, np.ndarray], pv_kwh: np.ndarray,
    demand_kwh: np.ndarray, served_kwh: np.ndarray,
) -> dict:
    # Energy balance: PV_used + import = served + export + battery losses + delta SOC
    scenario = result.scenario

    def total(name: str) -> float:
        return float(energy[name].sum())

    pv_total, served_total = float(pv_kwh.sum()), float(served_kwh.sum())
    losses_total = float(result.losses_kwh.sum())
    soc_delta_total = float((result.soc_kwh[:, -1] - result.soc_kwh[:, 0]).sum())
    balance_error = (
        pv_total - total("curtail") + total("imp")
        - served_total - total("exp") - losses_total - soc_delta_total
    )
    return {
        "controller": result.controller,
        "days": scenario.n_steps / scenario.steps_per_day,
        "pv_kwh": pv_total,
        "demand_kwh": float(demand_kwh.sum()),
        "shed_kwh": total("shed"),
        "import_kwh": total("imp"),
        "export_kwh": total("exp"),
        "p2p_kwh": total("p2p_out"),
        "curtail_kwh": total("curtail"),
        "battery_loss_kwh": losses_total,
        "soc_delta_kwh": soc_delta_total,
        "cost_lei": float(
            (energy["imp"] * scenario.price_import).sum() - (energy["exp"] * scenario.price_export).sum()
        ),
        "peak_import_kw": float(result.flows["imp"].sum(axis=0).max()),
        "peak_export_kw": float(result.flows["exp"].sum(axis=0).max()),
        "scr": _ratio(pv_total - total("curtail") - total("exp"), pv_total),
        "ssr": 1 - _ratio(total("imp"), served_total),
        "balance_error_kwh": balance_error,
    }


def compute_metrics(result: SimResult) -> dict:
    """{"community": {...}, "houses": [{...} per house]}."""
    scenario, dt_h = result.scenario, result.scenario.dt_h
    energy = {name: kw * dt_h for name, kw in result.flows.items()}   # kWh per step, (n_houses, n_steps)
    pv_kwh = scenario.pv_kw * dt_h
    demand_kwh = scenario.load_kw * dt_h
    served_kwh = demand_kwh - energy["shed"]

    houses = [
        _house_metrics(house, i, energy, scenario, pv_kwh, demand_kwh, served_kwh, result)
        for i, house in enumerate(result.community.houses)
    ]
    community = _community_metrics(result, energy, pv_kwh, demand_kwh, served_kwh)
    return {"community": community, "houses": houses}
