"""
Dispatch = the decision for one time step: every power flow of every house (kW, >= 0).

Node balance per house (what the simulator enforces):

    (pv - curtail) + dis + imp + p2p_in  ==  (load - shed) + ch + exp + p2p_out
"""
from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

FLOWS = ("curtail", "shed", "ch", "dis", "imp", "exp", "p2p_in", "p2p_out")


@dataclass
class Dispatch:
    curtail: np.ndarray
    shed: np.ndarray
    ch: np.ndarray
    dis: np.ndarray
    imp: np.ndarray
    exp: np.ndarray
    p2p_in: np.ndarray
    p2p_out: np.ndarray

    @classmethod
    def zeros(cls, n_houses: int) -> "Dispatch":
        return cls(**{f: np.zeros(n_houses) for f in FLOWS})

    def residual(self, pv: np.ndarray, load: np.ndarray) -> np.ndarray:
        """Sources minus sinks per house; zero when the node balance holds."""
        sources = (pv - self.curtail) + self.dis + self.imp + self.p2p_in
        sinks = (load - self.shed) + self.ch + self.exp + self.p2p_out
        return sources - sinks

    def as_dict(self) -> dict[str, np.ndarray]:
        return {f.name: getattr(self, f.name) for f in fields(self)}
