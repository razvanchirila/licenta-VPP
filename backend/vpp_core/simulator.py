"""
Runs a controller over a scenario and enforces physics at every step.

The controller proposes a Dispatch; the simulator rejects it (DispatchError) if any
house breaks its node balance, a battery limit, or a community limit. So every result
that comes out of simulate() is energy-consistent by construction.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vpp_core.battery import Battery, PhysicalLimitError
from vpp_core.dispatch import FLOWS, Dispatch
from vpp_core.params import CommunityParams
from vpp_core.scenario import Scenario

TOL = 1e-6


class DispatchError(ValueError):
    pass


@dataclass
class SimState:
    t: int
    batteries: list[Battery | None]

    @property
    def soc_kwh(self) -> np.ndarray:
        return np.array([b.soc_kwh if b else 0.0 for b in self.batteries])

    def max_charge_kw(self, dt_h: float) -> np.ndarray:
        return np.array([b.max_charge_kw(dt_h) if b else 0.0 for b in self.batteries])

    def max_discharge_kw(self, dt_h: float) -> np.ndarray:
        return np.array([b.max_discharge_kw(dt_h) if b else 0.0 for b in self.batteries])


@dataclass
class SimResult:
    community: CommunityParams
    scenario: Scenario
    controller: str
    flows: dict[str, np.ndarray]   # each (H, T), kW
    soc_kwh: np.ndarray            # (H, T + 1)
    losses_kwh: np.ndarray         # (H, T)


def validate(d: Dispatch, community: CommunityParams, sc: Scenario, t: int) -> None:
    H = community.n_houses
    pv, load = sc.pv_kw[:, t], sc.load_kw[:, t]
    for name, arr in d.as_dict().items():
        if arr.shape != (H,):
            raise DispatchError(f"t={t}: {name} has shape {arr.shape}, expected {(H,)}")
        if (arr < -TOL).any() or not np.isfinite(arr).all():
            raise DispatchError(f"t={t}: {name} must be finite and >= 0")
    if (d.curtail > pv + TOL).any():
        raise DispatchError(f"t={t}: curtailment larger than available PV")
    if (d.shed > load + TOL).any():
        raise DispatchError(f"t={t}: shed load larger than demand")

    res = d.residual(pv, load)
    bad = np.abs(res) > TOL * (1 + np.abs(pv) + np.abs(load))
    if bad.any():
        i = int(np.argmax(np.abs(res)))
        raise DispatchError(f"t={t}: node balance broken for house index {i} (residual {res[i]:.6f} kW)")

    for i, h in enumerate(community.houses):
        if h.battery is None and (d.ch[i] > TOL or d.dis[i] > TOL):
            raise DispatchError(f"t={t}: house {h.id} has no battery")
        if not h.p2p_enabled and (d.p2p_in[i] > TOL or d.p2p_out[i] > TOL):
            raise DispatchError(f"t={t}: house {h.id} does not take part in P2P")

    g = community.grid
    if abs(d.p2p_in.sum() - d.p2p_out.sum()) > TOL * H:
        raise DispatchError(f"t={t}: P2P bought != P2P sold")
    if d.p2p_out.sum() > g.internal_line_kw + TOL:
        raise DispatchError(f"t={t}: internal line limit exceeded")
    if d.imp.sum() > g.import_max_kw + TOL:
        raise DispatchError(f"t={t}: community import limit exceeded")
    if d.exp.sum() > g.export_max_kw + TOL:
        raise DispatchError(f"t={t}: community export limit exceeded")


def simulate(community: CommunityParams, scenario: Scenario, controller) -> SimResult:
    if scenario.n_houses != community.n_houses:
        raise ValueError("scenario and community have different numbers of houses")
    H, T, dt = community.n_houses, scenario.n_steps, scenario.dt_h

    batteries = [Battery(h.battery, h.initial_soc_kwh) if h.battery else None for h in community.houses]
    state = SimState(t=0, batteries=batteries)
    flows = {f: np.zeros((H, T)) for f in FLOWS}
    soc = np.zeros((H, T + 1))
    losses = np.zeros((H, T))
    soc[:, 0] = state.soc_kwh

    controller.reset(community, scenario)
    for t in range(T):
        state.t = t
        d = controller.dispatch(state)
        validate(d, community, scenario, t)
        for name in FLOWS:
            arr = np.clip(getattr(d, name), 0, None)
            setattr(d, name, arr)
            flows[name][:, t] = arr
        for i, b in enumerate(batteries):
            if b is None:
                continue
            losses[i, t] = b.losses_kwh(d.ch[i], d.dis[i], dt)
            try:
                b.apply(d.ch[i], d.dis[i], dt)
            except PhysicalLimitError as e:
                raise DispatchError(f"t={t}: house {community.houses[i].id}: {e}") from e
        soc[:, t + 1] = state.soc_kwh

    return SimResult(
        community=community,
        scenario=scenario,
        controller=getattr(controller, "name", type(controller).__name__),
        flows=flows,
        soc_kwh=soc,
        losses_kwh=losses,
    )
