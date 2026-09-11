"""
Linear program for the community dispatch, solved with HiGHS.

For every house h and step t (all >= 0, kW):
    imp, exp      grid import / export
    ch, dis       battery charge / discharge
    curt          PV curtailment             (<= pv)
    shed          unserved load              (<= load, penalised with VOLL)
    p2p_in/out    energy bought from / sold to neighbours
and the state of charge soc[h, t] (kWh), t = 0..T.

Constraints
    node balance   pv - curt + dis + imp + p2p_in = load - shed + ch + exp + p2p_out
    battery        soc[t+1] = soc[t] + (eta_ch * ch - dis / eta_dis) * dt,  soc_min <= soc <= soc_max
    community      sum_h p2p_in = sum_h p2p_out <= line,  sum_h imp <= imp_max,  sum_h exp <= exp_max
    end of horizon soc[T] >= soc[0]   (the optimiser may not just empty the batteries)

Objective (lei)
    sum_t dt * sum_h [ price_import * imp - price_export * exp
                       + deg_cost * (ch + dis) + voll * shed + eps * (curt + p2p_out) ]

P2P payments are internal to the community, so they cancel out in the objective; the LP
minimises the community's bill and the split between neighbours is a separate question.
"""
from __future__ import annotations

from dataclasses import dataclass

import highspy
import numpy as np

from vpp_core.controllers import Controller
from vpp_core.dispatch import Dispatch
from vpp_core.params import CommunityParams

INF = highspy.kHighsInf
FLOWS = ("imp", "exp", "ch", "dis", "curt", "shed", "p2p_in", "p2p_out")
SOC_MARGIN = 1e-4  # kWh kept away from the SOC limits, absorbs solver tolerance over many steps


@dataclass
class LPWeights:
    deg_cost: float = 0.02   # lei/kWh battery throughput (wear), also avoids useless cycling
    voll: float = 10.0       # lei/kWh value of lost load
    eps: float = 1e-4        # tie-breaker against pointless curtailment / P2P circulation


@dataclass
class LPSolution:
    flows: dict[str, np.ndarray]   # (H, T)
    soc: np.ndarray                # (H, T + 1)
    objective: float
    status: str


class _Builder:
    """Collects the LP as coordinate triplets, then hands it to HiGHS."""

    def __init__(self):
        self.n = 0   # columns
        self.m = 0   # rows
        self.lo, self.hi, self.cost = [], [], []
        self.rows, self.cols, self.vals = [], [], []
        self.row_lo, self.row_hi = [], []

    def add_vars(self, shape, lo, hi, cost=0.0) -> np.ndarray:
        size = int(np.prod(shape))
        idx = np.arange(self.n, self.n + size).reshape(shape)
        self.n += size
        self.lo.append(np.broadcast_to(lo, shape).ravel().astype(float))
        self.hi.append(np.broadcast_to(hi, shape).ravel().astype(float))
        self.cost.append(np.broadcast_to(cost, shape).ravel().astype(float))
        return idx

    def add_rows(self, terms, lo, hi):
        """terms: list of (var_index_array, coef) with equal shapes; one row per element."""
        shape = np.shape(terms[0][0])
        m = int(np.prod(shape))
        row_idx = np.arange(self.m, self.m + m)
        self.m += m
        for var, coef in terms:
            self.rows.append(row_idx)
            self.cols.append(np.asarray(var).ravel())
            self.vals.append(np.broadcast_to(coef, shape).ravel().astype(float))
        self.row_lo.append(np.broadcast_to(lo, shape).ravel().astype(float))
        self.row_hi.append(np.broadcast_to(hi, shape).ravel().astype(float))

    def solve(self):
        rows, cols, vals = (np.concatenate(a) for a in (self.rows, self.cols, self.vals))
        order = np.lexsort((rows, cols))
        rows, cols, vals = rows[order], cols[order], vals[order]
        start = np.concatenate([[0], np.cumsum(np.bincount(cols, minlength=self.n))])

        lp = highspy.HighsLp()
        lp.num_col_ = self.n
        lp.num_row_ = self.m
        lp.col_cost_ = np.concatenate(self.cost)
        lp.col_lower_ = np.concatenate(self.lo)
        lp.col_upper_ = np.concatenate(self.hi)
        lp.row_lower_ = np.concatenate(self.row_lo)
        lp.row_upper_ = np.concatenate(self.row_hi)
        lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_ = start.astype(np.int32)
        lp.a_matrix_.index_ = rows.astype(np.int32)
        lp.a_matrix_.value_ = vals

        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("primal_feasibility_tolerance", 1e-9)
        h.setOptionValue("dual_feasibility_tolerance", 1e-9)
        h.passModel(lp)
        h.run()
        status = h.modelStatusToString(h.getModelStatus())
        x = np.array(h.getSolution().col_value)
        return x, h.getInfo().objective_function_value, status


def solve_dispatch(
    community: CommunityParams,
    pv: np.ndarray,
    load: np.ndarray,
    price_import: np.ndarray,
    price_export: np.ndarray,
    dt_h: float,
    soc0: np.ndarray,
    weights: LPWeights = LPWeights(),
    terminal_soc: bool | np.ndarray = True,
) -> LPSolution:
    """terminal_soc: True -> soc[T] >= soc0; an array -> soc[T] >= that target; False -> free."""
    H, T = pv.shape
    houses, g = community.houses, community.grid
    has_b = np.array([h.battery is not None for h in houses])
    bp = [h.battery for h in houses]
    col = lambda f: np.array([f(b) if b else 0.0 for b in bp])[:, None]
    p_ch, p_dis = col(lambda b: b.p_ch_max_kw), col(lambda b: b.p_dis_max_kw)
    eta_ch, eta_dis = col(lambda b: b.eta_ch), col(lambda b: b.eta_dis)
    s_min, s_max = col(lambda b: b.soc_min_kwh), col(lambda b: b.soc_max_kwh)
    p2p_ok = np.array([h.p2p_enabled for h in houses], dtype=float)[:, None]

    w, B, shape = weights, _Builder(), (H, T)
    pi, pe = price_import[None, :] * dt_h, price_export[None, :] * dt_h
    v = {
        "imp": B.add_vars(shape, 0, INF, pi),
        "exp": B.add_vars(shape, 0, INF, -pe),
        "ch": B.add_vars(shape, 0, p_ch, w.deg_cost * dt_h),
        "dis": B.add_vars(shape, 0, p_dis, w.deg_cost * dt_h),
        "curt": B.add_vars(shape, 0, pv, w.eps * dt_h),
        "shed": B.add_vars(shape, 0, load, w.voll * dt_h),
        "p2p_in": B.add_vars(shape, 0, np.where(p2p_ok > 0, INF, 0.0)),
        "p2p_out": B.add_vars(shape, 0, np.where(p2p_ok > 0, INF, 0.0), w.eps * dt_h),
    }

    # SOC bounds: fixed at t=0, [min, max] (with margin) afterwards, >= soc0 at the end
    s0 = soc0[:, None]
    lo = np.where(has_b[:, None], np.minimum(s_min + SOC_MARGIN, s0), 0.0) * np.ones((1, T + 1))
    hi = np.where(has_b[:, None], np.maximum(s_max - SOC_MARGIN, s0), 0.0) * np.ones((1, T + 1))
    lo[:, 0] = hi[:, 0] = soc0
    if terminal_soc is not False:
        target = soc0 if terminal_soc is True else np.asarray(terminal_soc, dtype=float)
        lo[:, -1] = np.maximum(lo[:, -1], np.minimum(target, hi[:, -1]))
    soc = B.add_vars((H, T + 1), lo, hi)

    # node balance: imp + dis + p2p_in - curt + shed - ch - exp - p2p_out = load - pv
    rhs = load - pv
    B.add_rows(
        [(v["imp"], 1), (v["dis"], 1), (v["p2p_in"], 1), (v["curt"], -1), (v["shed"], 1),
         (v["ch"], -1), (v["exp"], -1), (v["p2p_out"], -1)],
        rhs, rhs,
    )
    # battery dynamics (houses with a battery only)
    b = np.flatnonzero(has_b)
    if len(b):
        B.add_rows(
            [(soc[b, 1:], 1), (soc[b, :-1], -1),
             (v["ch"][b], -np.broadcast_to(eta_ch[b] * dt_h, (len(b), T))),
             (v["dis"][b], np.broadcast_to(dt_h / eta_dis[b], (len(b), T)))],
            0, 0,
        )
    # community rows: one per step, summing over houses
    def per_step(var, coef):
        return [(var[i], coef) for i in range(H)]
    B.add_rows(per_step(v["p2p_in"], 1) + per_step(v["p2p_out"], -1), 0, 0)
    for var, limit in ((v["p2p_out"], g.internal_line_kw), (v["imp"], g.import_max_kw), (v["exp"], g.export_max_kw)):
        if np.isfinite(limit):
            B.add_rows(per_step(var, 1), -INF, limit)

    x, obj, status = B.solve()
    if status != "Optimal":
        raise RuntimeError(f"LP not solved: {status}")
    flows = {k: np.clip(x[idx], 0, None) for k, idx in v.items()}
    return LPSolution(flows=flows, soc=x[soc], objective=obj, status=status)


class LPController(Controller):
    """Solves the whole scenario once with perfect foresight, then replays the plan.

    This is the best any strategy can do on the scenario (an upper bound for MPC).
    """

    def __init__(self, weights: LPWeights = LPWeights(), terminal_soc: bool = True, name: str = "optim_lp"):
        self.weights = weights
        self.terminal_soc = terminal_soc
        self.name = name

    def reset(self, community, scenario):
        super().reset(community, scenario)
        soc0 = np.array([h.initial_soc_kwh for h in community.houses])
        self.solution = solve_dispatch(
            community, scenario.pv_kw, scenario.load_kw, scenario.price_import, scenario.price_export,
            scenario.dt_h, soc0, self.weights, self.terminal_soc,
        )

    def dispatch(self, state) -> Dispatch:
        return _step(self.solution.flows, state.t)


def _step(f: dict[str, np.ndarray], t: int) -> Dispatch:
    return Dispatch(
        curtail=f["curt"][:, t], shed=f["shed"][:, t], ch=f["ch"][:, t], dis=f["dis"][:, t],
        imp=f["imp"][:, t], exp=f["exp"][:, t], p2p_in=f["p2p_in"][:, t], p2p_out=f["p2p_out"][:, t],
    )


def noisy_forecast(actual: np.ndarray, t: int, sigma_day: float, steps_per_day: int,
                   rng: np.random.Generator) -> np.ndarray:
    """Forecast of actual[:, t:] made at step t: exact for step t (measured), then a
    multiplicative error that grows like a random walk, reaching sigma_day after 24 h."""
    H, n = actual.shape[0], actual.shape[1] - t
    steps = rng.normal(0, sigma_day / np.sqrt(steps_per_day), (H, n))
    steps[:, 0] = 0.0
    err = np.cumsum(steps, axis=1)
    return np.clip(actual[:, t:] * (1 + err), 0, None)


class MPCController(Controller):
    """Model predictive control: at every step, re-solve the LP over the next horizon using
    forecasts, apply only the first step, repeat. Current PV and load are measured exactly;
    later steps carry forecast errors. Day-ahead prices (PZU) are known.

    Each window must end with the batteries at least at their initial charge, so the
    controller does not empty them just because the horizon ends.
    """

    def __init__(self, horizon_h: float = 24.0, pv_error: float = 0.3, load_error: float = 0.2,
                 weights: LPWeights = LPWeights(), seed: int = 0, name: str = "mpc"):
        self.horizon_h = horizon_h
        self.pv_error = pv_error
        self.load_error = load_error
        self.weights = weights
        self.seed = seed
        self.name = name

    def reset(self, community, scenario):
        super().reset(community, scenario)
        self.rng = np.random.default_rng(self.seed)
        self.target = np.array([h.initial_soc_kwh for h in community.houses])

    def dispatch(self, state) -> Dispatch:
        sc, t = self.scenario, state.t
        end = min(sc.n_steps, t + max(1, round(self.horizon_h / sc.dt_h)))
        spd = sc.steps_per_day
        pv = noisy_forecast(sc.pv_kw[:, :end], t, self.pv_error, spd, self.rng)
        load = noisy_forecast(sc.load_kw[:, :end], t, self.load_error, spd, self.rng)
        sol = solve_dispatch(
            self.community, pv, load, sc.price_import[t:end], sc.price_export[t:end],
            sc.dt_h, state.soc_kwh, self.weights, terminal_soc=self.target,
        )
        return _step(sol.flows, 0)
