"""Runs a controller over a scenario; every SimResult is energy-consistent by construction."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vpp_core.battery import Battery, PhysicalLimitError
from vpp_core.dispatch import FLOWS, Dispatch
from vpp_core.params import CommunityParams
from vpp_core.scenario import Scenario

TOL = 1e-6   # kW tolerance for the feasibility checks


class DispatchError(ValueError):
    """A dispatch violates a physical or community limit."""


@dataclass
class SimState:
    """What a controller may look at when deciding step t."""

    t: int
    batteries: list[Battery | None]   # None for houses without a battery

    @property
    def soc_kwh(self) -> np.ndarray:
        """(n_houses,) kWh, 0 without a battery."""
        return np.array([battery.soc_kwh if battery else 0.0 for battery in self.batteries])

    def max_charge_kw(self, dt_h: float) -> np.ndarray:
        return np.array([battery.max_charge_kw(dt_h) if battery else 0.0 for battery in self.batteries])

    def max_discharge_kw(self, dt_h: float) -> np.ndarray:
        return np.array([battery.max_discharge_kw(dt_h) if battery else 0.0 for battery in self.batteries])


@dataclass
class SimResult:
    community: CommunityParams
    scenario: Scenario
    controller: str
    flows: dict[str, np.ndarray]   # FLOWS name -> (n_houses, n_steps) kW
    soc_kwh: np.ndarray            # (n_houses, n_steps + 1), soc[:, 0] is the initial SOC
    losses_kwh: np.ndarray         # (n_houses, n_steps) kWh


def _check_shapes_and_signs(dispatch: Dispatch, n_houses: int, t: int) -> None:
    for name, values in dispatch.as_dict().items():
        if values.shape != (n_houses,):
            raise DispatchError(f"t={t}: {name} has shape {values.shape}, expected {(n_houses,)}")
        if (values < -TOL).any() or not np.isfinite(values).all():
            raise DispatchError(f"t={t}: {name} must be finite and >= 0")


def _check_node_balance(dispatch: Dispatch, pv: np.ndarray, load: np.ndarray, t: int) -> None:
    if (dispatch.curtail > pv + TOL).any():
        raise DispatchError(f"t={t}: curtailment larger than available PV")
    if (dispatch.shed > load + TOL).any():
        raise DispatchError(f"t={t}: shed load larger than demand")
    residual = dispatch.residual(pv, load)
    broken = np.abs(residual) > TOL * (1 + np.abs(pv) + np.abs(load))
    if broken.any():
        worst = int(np.argmax(np.abs(residual)))
        raise DispatchError(
            f"t={t}: node balance broken for house index {worst} (residual {residual[worst]:.6f} kW)"
        )


def _check_house_rules(dispatch: Dispatch, community: CommunityParams, t: int) -> None:
    for i, house in enumerate(community.houses):
        if house.battery is None and (dispatch.ch[i] > TOL or dispatch.dis[i] > TOL):
            raise DispatchError(f"t={t}: house {house.id} has no battery")
        if not house.p2p_enabled and (dispatch.p2p_in[i] > TOL or dispatch.p2p_out[i] > TOL):
            raise DispatchError(f"t={t}: house {house.id} does not take part in P2P")


def _check_community_limits(dispatch: Dispatch, community: CommunityParams, t: int) -> None:
    grid = community.grid
    if abs(dispatch.p2p_in.sum() - dispatch.p2p_out.sum()) > TOL * community.n_houses:
        raise DispatchError(f"t={t}: P2P bought != P2P sold")
    if dispatch.p2p_out.sum() > grid.internal_line_kw + TOL:
        raise DispatchError(f"t={t}: internal line limit exceeded")
    if dispatch.imp.sum() > grid.import_max_kw + TOL:
        raise DispatchError(f"t={t}: community import limit exceeded")
    if dispatch.exp.sum() > grid.export_max_kw + TOL:
        raise DispatchError(f"t={t}: community export limit exceeded")


def validate(dispatch: Dispatch, community: CommunityParams, scenario: Scenario, t: int) -> None:
    """Battery power / SOC limits are checked in Battery.apply instead (they depend on the SOC)."""
    pv, load = scenario.pv_kw[:, t], scenario.load_kw[:, t]
    _check_shapes_and_signs(dispatch, community.n_houses, t)
    _check_node_balance(dispatch, pv, load, t)
    _check_house_rules(dispatch, community, t)
    _check_community_limits(dispatch, community, t)


def _apply_to_batteries(
    dispatch: Dispatch, batteries: list[Battery | None], community: CommunityParams, dt_h: float, t: int
) -> np.ndarray:
    """Returns (n_houses,) losses in kWh."""
    losses = np.zeros(len(batteries))
    for i, battery in enumerate(batteries):
        if battery is None:
            continue
        losses[i] = battery.losses_kwh(dispatch.ch[i], dispatch.dis[i], dt_h)
        try:
            battery.apply(dispatch.ch[i], dispatch.dis[i], dt_h)
        except PhysicalLimitError as error:
            raise DispatchError(f"t={t}: house {community.houses[i].id}: {error}") from error
    return losses


def simulate(community: CommunityParams, scenario: Scenario, controller) -> SimResult:
    if scenario.n_houses != community.n_houses:
        raise ValueError("scenario and community have different numbers of houses")
    n_houses, n_steps, dt_h = community.n_houses, scenario.n_steps, scenario.dt_h

    batteries = [
        Battery(house.battery, house.initial_soc_kwh) if house.battery else None
        for house in community.houses
    ]
    state = SimState(t=0, batteries=batteries)
    flows = {name: np.zeros((n_houses, n_steps)) for name in FLOWS}
    soc = np.zeros((n_houses, n_steps + 1))
    losses = np.zeros((n_houses, n_steps))
    soc[:, 0] = state.soc_kwh

    controller.reset(community, scenario)
    for t in range(n_steps):
        state.t = t
        dispatch = controller.dispatch(state)
        validate(dispatch, community, scenario, t)
        for name in FLOWS:                       # solver noise: tiny negatives become 0
            values = np.clip(getattr(dispatch, name), 0, None)
            setattr(dispatch, name, values)
            flows[name][:, t] = values
        losses[:, t] = _apply_to_batteries(dispatch, batteries, community, dt_h, t)
        soc[:, t + 1] = state.soc_kwh

    return SimResult(
        community=community,
        scenario=scenario,
        controller=getattr(controller, "name", type(controller).__name__),
        flows=flows,
        soc_kwh=soc,
        losses_kwh=losses,
    )
