"""
Evaluation metrics (all energies in kWh, costs in lei).

- SCR (self-consumption rate): share of the available PV that was used inside the house/community.
- SSR (self-sufficiency rate): share of the served load not covered from outside
  (grid for the community; grid + neighbours for one house).
"""
from __future__ import annotations

import numpy as np

from vpp_core.simulator import SimResult


def _ratio(a: float, b: float) -> float:
    return float(a / b) if b > 1e-12 else 0.0


def compute_metrics(res: SimResult) -> dict:
    sc, f, dt = res.scenario, res.flows, res.scenario.dt_h
    e = {k: v * dt for k, v in f.items()}            # kWh per step, (H, T)
    pv = sc.pv_kw * dt
    demand = sc.load_kw * dt
    served = demand - e["shed"]
    soc_delta = res.soc_kwh[:, -1] - res.soc_kwh[:, 0]

    houses = []
    for i, h in enumerate(res.community.houses):
        pv_i = pv[i].sum()
        used_locally = pv_i - e["curtail"][i].sum() - e["exp"][i].sum() - e["p2p_out"][i].sum()
        cost = (
            (e["imp"][i] * sc.price_import).sum()
            - (e["exp"][i] * sc.price_export).sum()
            + (e["p2p_in"][i] * sc.price_p2p).sum()
            - (e["p2p_out"][i] * sc.price_p2p).sum()
        )
        cycles = _ratio(e["dis"][i].sum(), h.battery.usable_kwh) if h.battery else 0.0
        houses.append({
            "id": h.id,
            "pv_kwh": pv_i,
            "demand_kwh": demand[i].sum(),
            "shed_kwh": e["shed"][i].sum(),
            "import_kwh": e["imp"][i].sum(),
            "export_kwh": e["exp"][i].sum(),
            "p2p_in_kwh": e["p2p_in"][i].sum(),
            "p2p_out_kwh": e["p2p_out"][i].sum(),
            "curtail_kwh": e["curtail"][i].sum(),
            "battery_loss_kwh": res.losses_kwh[i].sum(),
            "soc_delta_kwh": soc_delta[i],
            "cycles": cycles,
            "cost_lei": cost,
            "scr": _ratio(used_locally, pv_i),
            "ssr": 1 - _ratio(e["imp"][i].sum() + e["p2p_in"][i].sum(), served[i].sum()),
        })

    imp_t, exp_t = f["imp"].sum(axis=0), f["exp"].sum(axis=0)
    tot = lambda k: float(e[k].sum())
    pv_tot, served_tot = float(pv.sum()), float(served.sum())
    # Community energy balance: PV_used + import = served + export + battery losses + delta SOC
    balance_error = (
        pv_tot - tot("curtail") + tot("imp")
        - served_tot - tot("exp") - float(res.losses_kwh.sum()) - float(soc_delta.sum())
    )
    community = {
        "controller": res.controller,
        "days": sc.n_steps / sc.steps_per_day,
        "pv_kwh": pv_tot,
        "demand_kwh": float(demand.sum()),
        "shed_kwh": tot("shed"),
        "import_kwh": tot("imp"),
        "export_kwh": tot("exp"),
        "p2p_kwh": tot("p2p_out"),
        "curtail_kwh": tot("curtail"),
        "battery_loss_kwh": float(res.losses_kwh.sum()),
        "soc_delta_kwh": float(soc_delta.sum()),
        "cost_lei": float((e["imp"] * sc.price_import).sum() - (e["exp"] * sc.price_export).sum()),
        "peak_import_kw": float(imp_t.max()),
        "peak_export_kw": float(exp_t.max()),
        "scr": _ratio(pv_tot - tot("curtail") - tot("exp"), pv_tot),
        "ssr": 1 - _ratio(tot("imp"), served_tot),
        "balance_error_kwh": balance_error,
    }
    return {"community": community, "houses": houses}
