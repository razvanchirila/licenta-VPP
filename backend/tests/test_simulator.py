import numpy as np
import pytest

from conftest import const, make_scenario
from vpp_core.controllers import Controller
from vpp_core.dispatch import Dispatch
from vpp_core.params import BatteryParams, CommunityParams, GridParams, HouseParams
from vpp_core.simulator import DispatchError, simulate


class Fixed(Controller):
    """Returns the same (possibly invalid) dispatch every step."""
    def __init__(self, **flows):
        self.flows = flows

    def dispatch(self, state):
        d = Dispatch.zeros(self.community.n_houses)
        for k, v in self.flows.items():
            setattr(d, k, np.array(v, dtype=float))
        return d


def community(n=2, battery=False, grid=GridParams(), p2p=True):
    return CommunityParams(
        houses=tuple(HouseParams(id=i, battery=BatteryParams() if battery else None, p2p_enabled=p2p) for i in range(n)),
        grid=grid,
    )


def test_valid_dispatch_passes():
    sc = make_scenario(const(2, 24, 3.0), const(2, 24, 1.0))
    res = simulate(community(), sc, Fixed(exp=[2.0, 2.0]))
    assert res.flows["exp"].sum() == pytest.approx(2 * 2 * 24)


def test_rejects_broken_node_balance():
    sc = make_scenario(const(2, 24, 3.0), const(2, 24, 1.0))
    with pytest.raises(DispatchError, match="node balance"):
        simulate(community(), sc, Fixed(exp=[1.0, 2.0]))  # 1 kW of house 0 disappears


def test_rejects_negative_flow():
    sc = make_scenario(const(2, 24, 1.0), const(2, 24, 1.0))
    with pytest.raises(DispatchError):
        simulate(community(), sc, Fixed(imp=[-1.0, 0.0], exp=[-1.0, 0.0]))


def test_rejects_unbalanced_p2p():
    sc = make_scenario([[3.0] * 24, [0.0] * 24], const(2, 24, 1.0))
    with pytest.raises(DispatchError, match="P2P"):
        simulate(community(), sc, Fixed(p2p_out=[2.0, 0.0], p2p_in=[0.0, 0.5], imp=[0.0, 0.5]))


def test_rejects_import_over_community_limit():
    sc = make_scenario(const(2, 24, 0.0), const(2, 24, 3.0))
    with pytest.raises(DispatchError, match="import limit"):
        simulate(community(grid=GridParams(import_max_kw=5)), sc, Fixed(imp=[3.0, 3.0]))


def test_rejects_battery_on_house_without_one():
    sc = make_scenario(const(2, 24, 3.0), const(2, 24, 1.0))
    with pytest.raises(DispatchError, match="no battery"):
        simulate(community(), sc, Fixed(ch=[2.0, 2.0]))


def test_rejects_battery_over_power_limit():
    sc = make_scenario(const(1, 24, 12.0), const(1, 24, 1.0))
    with pytest.raises(DispatchError, match="charge"):
        simulate(community(n=1, battery=True), sc, Fixed(ch=[11.0]))


def test_rejects_p2p_for_non_participant():
    sc = make_scenario([[3.0] * 24, [0.0] * 24], const(2, 24, 1.0))
    with pytest.raises(DispatchError, match="P2P"):
        simulate(community(p2p=False), sc, Fixed(p2p_out=[1.0, 0.0], p2p_in=[0.0, 1.0], exp=[1.0, 0.0]))
