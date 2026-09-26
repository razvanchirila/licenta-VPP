"""Dispatch = the decision of one time step: every power flow of every house (kW, >= 0)."""
from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

FLOWS = ("curtail", "shed", "ch", "dis", "imp", "exp", "p2p_in", "p2p_out")


@dataclass
class Dispatch:
    """Every array has shape (n_houses,), kW."""

    curtail: np.ndarray
    shed: np.ndarray
    ch: np.ndarray
    dis: np.ndarray
    imp: np.ndarray
    exp: np.ndarray
    p2p_in: np.ndarray
    p2p_out: np.ndarray

    @classmethod
    def zeros(cls, n_houses: int) -> Dispatch:
        return cls(**{name: np.zeros(n_houses) for name in FLOWS})

    @classmethod
    def from_flows(cls, flows: dict[str, np.ndarray], t: int) -> Dispatch:
        """Column t of (n_houses, n_steps) flow arrays keyed by FLOWS."""
        return cls(**{name: flows[name][:, t] for name in FLOWS})

    def residual(self, pv: np.ndarray, load: np.ndarray) -> np.ndarray:
        # (pv - curtail) + dis + imp + p2p_in == (load - shed) + ch + exp + p2p_out
        sources = (pv - self.curtail) + self.dis + self.imp + self.p2p_in
        sinks = (load - self.shed) + self.ch + self.exp + self.p2p_out
        return sources - sinks

    def as_dict(self) -> dict[str, np.ndarray]:
        return {flow.name: getattr(self, flow.name) for flow in fields(self)}
