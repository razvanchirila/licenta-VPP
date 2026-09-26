"""
LP dispatch of the community (HiGHS), used with perfect foresight (LPController) or in a
rolling horizon with forecasts (MPCController). Variables in kW, soc in kWh, objective in lei:

    min  sum_t dt * sum_h [ price_import * imp - price_export * exp
                            + deg_cost * (ch + dis) + voll * shed + eps * (curtail + p2p_out) ]
         + peak_cost * P_peak,   P_peak >= sum_h imp[h, t] for every t,  P_peak >= peak_floor

P2P payments cancel out inside the community, so they do not appear in the objective.
The peak term is a demand charge; peak_floor is the peak already paid earlier in the
billing period, so only the increment above it is charged.
"""
from __future__ import annotations

from dataclasses import dataclass

import highspy
import numpy as np

from vpp_core.controllers import Controller
from vpp_core.dispatch import Dispatch
from vpp_core.params import CommunityParams, GridParams
from vpp_core.scenario import Scenario
from vpp_core.simulator import SimState

INF = highspy.kHighsInf
SOC_MARGIN = 1e-4  # kWh kept away from the SOC limits, absorbs solver tolerance over many steps


@dataclass
class LPWeights:
    """Objective coefficients, lei/kWh unless stated."""

    deg_cost: float = 0.02   # battery wear per kWh of throughput; see backend/data/README.md
    voll: float = 10.0       # value of lost load
    eps: float = 1e-4        # tie-breaker against pointless curtailment / P2P circulation
    peak_cost: float = 0.0   # lei/kW on the maximum community import (0 = off)


@dataclass
class LPSolution:
    flows: dict[str, np.ndarray]   # FLOWS name -> (n_houses, n_steps) kW
    soc: np.ndarray                # (n_houses, n_steps + 1) kWh
    objective: float               # lei, including penalties and the peak term
    status: str
    peak_kw: float | None = None   # None when peak_cost == 0


@dataclass
class _BatteryColumns:
    """(n_houses, 1) columns, 0 for houses without a battery, broadcastable against (n_houses, n_steps)."""

    has_battery: np.ndarray   # (n_houses,) bool
    p_ch_max: np.ndarray
    p_dis_max: np.ndarray
    eta_ch: np.ndarray
    eta_dis: np.ndarray
    soc_min: np.ndarray
    soc_max: np.ndarray

    @classmethod
    def of(cls, community: CommunityParams) -> _BatteryColumns:
        batteries = [house.battery for house in community.houses]

        def column(attribute: str) -> np.ndarray:
            return np.array([getattr(b, attribute) if b else 0.0 for b in batteries])[:, None]

        return cls(
            has_battery=np.array([b is not None for b in batteries]),
            p_ch_max=column("p_ch_max_kw"), p_dis_max=column("p_dis_max_kw"),
            eta_ch=column("eta_ch"), eta_dis=column("eta_dis"),
            soc_min=column("soc_min_kwh"), soc_max=column("soc_max_kwh"),
        )


class _LPBuilder:
    """Collects columns and rows of a sparse LP, then hands the whole model to HiGHS in one call."""

    def __init__(self) -> None:
        self.n_cols = 0
        self.n_rows = 0
        self.col_lower: list[np.ndarray] = []
        self.col_upper: list[np.ndarray] = []
        self.col_cost: list[np.ndarray] = []
        self.row_lower: list[np.ndarray] = []
        self.row_upper: list[np.ndarray] = []
        self.entry_rows: list[np.ndarray] = []     # (row, col, value) triplets
        self.entry_cols: list[np.ndarray] = []
        self.entry_vals: list[np.ndarray] = []

    def add_vars(self, shape: tuple[int, ...], lower, upper, cost=0.0) -> np.ndarray:
        """One variable per element; returns their column indices with that shape."""
        size = int(np.prod(shape))
        indices = np.arange(self.n_cols, self.n_cols + size).reshape(shape)
        self.n_cols += size
        self.col_lower.append(np.broadcast_to(lower, shape).ravel().astype(float))
        self.col_upper.append(np.broadcast_to(upper, shape).ravel().astype(float))
        self.col_cost.append(np.broadcast_to(cost, shape).ravel().astype(float))
        return indices

    def add_rows(self, terms: list[tuple[np.ndarray, float | np.ndarray]], lower, upper) -> None:
        """One constraint per element: lower <= sum_k coef_k * var_k <= upper; terms share one shape."""
        shape = np.shape(terms[0][0])
        size = int(np.prod(shape))
        row_indices = np.arange(self.n_rows, self.n_rows + size)
        self.n_rows += size
        for variables, coefficient in terms:
            self.entry_rows.append(row_indices)
            self.entry_cols.append(np.asarray(variables).ravel())
            self.entry_vals.append(np.broadcast_to(coefficient, shape).ravel().astype(float))
        self.row_lower.append(np.broadcast_to(lower, shape).ravel().astype(float))
        self.row_upper.append(np.broadcast_to(upper, shape).ravel().astype(float))

    def _highs_model(self) -> highspy.HighsLp:
        rows, cols, vals = (np.concatenate(parts) for parts in (self.entry_rows, self.entry_cols, self.entry_vals))
        order = np.lexsort((rows, cols))
        rows, cols, vals = rows[order], cols[order], vals[order]
        col_start = np.concatenate([[0], np.cumsum(np.bincount(cols, minlength=self.n_cols))])

        lp = highspy.HighsLp()
        lp.num_col_ = self.n_cols
        lp.num_row_ = self.n_rows
        lp.col_cost_ = np.concatenate(self.col_cost)
        lp.col_lower_ = np.concatenate(self.col_lower)
        lp.col_upper_ = np.concatenate(self.col_upper)
        lp.row_lower_ = np.concatenate(self.row_lower)
        lp.row_upper_ = np.concatenate(self.row_upper)
        lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_ = col_start.astype(np.int32)
        lp.a_matrix_.index_ = rows.astype(np.int32)
        lp.a_matrix_.value_ = vals
        return lp

    def solve(self) -> tuple[np.ndarray, float, str]:
        solver = highspy.Highs()
        solver.setOptionValue("output_flag", False)
        solver.setOptionValue("primal_feasibility_tolerance", 1e-9)
        solver.setOptionValue("dual_feasibility_tolerance", 1e-9)
        solver.passModel(self._highs_model())
        solver.run()
        status = solver.modelStatusToString(solver.getModelStatus())
        values = np.array(solver.getSolution().col_value)
        return values, solver.getInfo().objective_function_value, status


def _add_flow_variables(
    builder: _LPBuilder, community: CommunityParams, battery: _BatteryColumns,
    pv: np.ndarray, load: np.ndarray, price_import: np.ndarray, price_export: np.ndarray,
    dt_h: float, weights: LPWeights,
) -> dict[str, np.ndarray]:
    shape = pv.shape
    cost_import = price_import[None, :] * dt_h        # lei per kW in one step
    cost_export = price_export[None, :] * dt_h
    p2p_allowed = np.array([house.p2p_enabled for house in community.houses], dtype=float)[:, None]
    p2p_upper = np.where(p2p_allowed > 0, INF, 0.0)
    return {
        "imp": builder.add_vars(shape, 0, INF, cost_import),
        "exp": builder.add_vars(shape, 0, INF, -cost_export),
        "ch": builder.add_vars(shape, 0, battery.p_ch_max, weights.deg_cost * dt_h),
        "dis": builder.add_vars(shape, 0, battery.p_dis_max, weights.deg_cost * dt_h),
        "curtail": builder.add_vars(shape, 0, pv, weights.eps * dt_h),
        "shed": builder.add_vars(shape, 0, load, weights.voll * dt_h),
        "p2p_in": builder.add_vars(shape, 0, p2p_upper),
        "p2p_out": builder.add_vars(shape, 0, p2p_upper, weights.eps * dt_h),
    }


def _add_soc_variables(
    builder: _LPBuilder, battery: _BatteryColumns, soc0: np.ndarray, n_steps: int,
    terminal_soc: bool | np.ndarray,
) -> np.ndarray:
    """soc[h, t], t = 0..T: fixed to soc0 at t = 0, >= terminal target at t = T."""
    n_houses = len(soc0)
    soc0_column = soc0[:, None]
    has_battery = battery.has_battery[:, None]
    lower_bound = np.where(has_battery, np.minimum(battery.soc_min + SOC_MARGIN, soc0_column), 0.0)
    upper_bound = np.where(has_battery, np.maximum(battery.soc_max - SOC_MARGIN, soc0_column), 0.0)
    lower = lower_bound * np.ones((1, n_steps + 1))
    upper = upper_bound * np.ones((1, n_steps + 1))
    lower[:, 0] = upper[:, 0] = soc0
    if terminal_soc is not False:
        target = soc0 if terminal_soc is True else np.asarray(terminal_soc, dtype=float)
        lower[:, -1] = np.maximum(lower[:, -1], np.minimum(target, upper[:, -1]))
    return builder.add_vars((n_houses, n_steps + 1), lower, upper)


def _add_node_balance(builder: _LPBuilder, var: dict[str, np.ndarray], pv: np.ndarray, load: np.ndarray) -> None:
    # imp + dis + p2p_in - curtail + shed - ch - exp - p2p_out = load - pv
    net_load = load - pv
    builder.add_rows(
        [(var["imp"], 1), (var["dis"], 1), (var["p2p_in"], 1), (var["curtail"], -1), (var["shed"], 1),
         (var["ch"], -1), (var["exp"], -1), (var["p2p_out"], -1)],
        net_load, net_load,
    )


def _add_battery_dynamics(
    builder: _LPBuilder, var: dict[str, np.ndarray], soc: np.ndarray, battery: _BatteryColumns, dt_h: float
) -> None:
    # soc[t+1] - soc[t] - eta_ch * dt * ch + dt / eta_dis * dis = 0
    with_battery = np.flatnonzero(battery.has_battery)
    if len(with_battery) == 0:
        return
    n_steps = var["ch"].shape[1]
    charge_coef = -np.broadcast_to(battery.eta_ch[with_battery] * dt_h, (len(with_battery), n_steps))
    discharge_coef = np.broadcast_to(dt_h / battery.eta_dis[with_battery], (len(with_battery), n_steps))
    builder.add_rows(
        [(soc[with_battery, 1:], 1), (soc[with_battery, :-1], -1),
         (var["ch"][with_battery], charge_coef), (var["dis"][with_battery], discharge_coef)],
        0, 0,
    )


def _sum_over_houses(variables: np.ndarray, coefficient: float) -> list[tuple[np.ndarray, float]]:
    return [(variables[h], coefficient) for h in range(variables.shape[0])]


def _add_community_limits(builder: _LPBuilder, var: dict[str, np.ndarray], grid: GridParams) -> None:
    # sum_h p2p_in = sum_h p2p_out <= line,  sum_h imp <= imp_max,  sum_h exp <= exp_max
    builder.add_rows(_sum_over_houses(var["p2p_in"], 1) + _sum_over_houses(var["p2p_out"], -1), 0, 0)
    for flow, limit in (("p2p_out", grid.internal_line_kw), ("imp", grid.import_max_kw), ("exp", grid.export_max_kw)):
        if np.isfinite(limit):
            builder.add_rows(_sum_over_houses(var[flow], 1), -INF, limit)


def _add_peak_charge(
    builder: _LPBuilder, var: dict[str, np.ndarray], weights: LPWeights, peak_floor: float
) -> np.ndarray | None:
    # P_peak >= peak_floor,  sum_h imp[h, t] - P_peak <= 0 for every t
    if weights.peak_cost <= 0:
        return None
    n_steps = var["imp"].shape[1]
    peak = builder.add_vars((1,), max(0.0, float(peak_floor)), INF, weights.peak_cost)
    builder.add_rows(_sum_over_houses(var["imp"], 1) + [(np.full(n_steps, peak[0]), -1)], -INF, 0)
    return peak


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
    peak_floor: float = 0.0,
) -> LPSolution:
    """pv, load: (n_houses, T) kW; prices: (T,) lei/kWh; soc0: (n_houses,) kWh.
    terminal_soc: True -> soc[T] >= soc0; array -> soc[T] >= target; False -> free."""
    battery = _BatteryColumns.of(community)
    builder = _LPBuilder()

    var = _add_flow_variables(builder, community, battery, pv, load, price_import, price_export, dt_h, weights)
    soc = _add_soc_variables(builder, battery, soc0, pv.shape[1], terminal_soc)
    _add_node_balance(builder, var, pv, load)
    _add_battery_dynamics(builder, var, soc, battery, dt_h)
    _add_community_limits(builder, var, community.grid)
    peak = _add_peak_charge(builder, var, weights, peak_floor)

    values, objective, status = builder.solve()
    if status != "Optimal":
        raise RuntimeError(f"LP not solved: {status}")
    flows = {name: np.clip(values[indices], 0, None) for name, indices in var.items()}
    return LPSolution(
        flows=flows, soc=values[soc], objective=objective, status=status,
        peak_kw=None if peak is None else float(values[peak[0]]),
    )


class LPController(Controller):
    """Perfect foresight: solves the whole scenario once, then replays the plan."""

    def __init__(self, weights: LPWeights = LPWeights(), terminal_soc: bool = True, name: str = "optim_lp"):
        self.weights = weights
        self.terminal_soc = terminal_soc
        self.name = name

    def reset(self, community: CommunityParams, scenario: Scenario) -> None:
        super().reset(community, scenario)
        soc0 = np.array([house.initial_soc_kwh for house in community.houses])
        self.solution = solve_dispatch(
            community, scenario.pv_kw, scenario.load_kw, scenario.price_import, scenario.price_export,
            scenario.dt_h, soc0, self.weights, self.terminal_soc,
        )

    def dispatch(self, state: SimState) -> Dispatch:
        return Dispatch.from_flows(self.solution.flows, state.t)


def noisy_forecast(actual: np.ndarray, t: int, sigma_day: float, steps_per_day: int,
                   rng: np.random.Generator) -> np.ndarray:
    """(n_houses, n_steps - t): exact at step t, then a multiplicative random-walk error, sigma_day after 24 h."""
    n_houses, n_ahead = actual.shape[0], actual.shape[1] - t
    increments = rng.normal(0, sigma_day / np.sqrt(steps_per_day), (n_houses, n_ahead))
    increments[:, 0] = 0.0
    relative_error = np.cumsum(increments, axis=1)
    return np.clip(actual[:, t:] * (1 + relative_error), 0, None)


class MPCController(Controller):
    """Rolling horizon: forecast, solve the LP, apply the first step, repeat.
    Each window must end with soc >= initial soc. billing_period_days=None means the peak
    memory (peak_floor) covers the whole run; peak_memory=False pays each window's peak from zero."""

    def __init__(self, horizon_h: float = 24.0, pv_error: float = 0.3, load_error: float = 0.2,
                 weights: LPWeights = LPWeights(), seed: int = 0, name: str = "mpc",
                 billing_period_days: int | None = None, peak_memory: bool = True):
        self.horizon_h = horizon_h
        self.pv_error = pv_error          # relative std of the forecast error after 24 h
        self.load_error = load_error
        self.weights = weights
        self.seed = seed
        self.name = name
        self.billing_period_days = billing_period_days
        self.peak_memory = peak_memory
        self.peak_so_far_kw = 0.0

    def reset(self, community: CommunityParams, scenario: Scenario) -> None:
        super().reset(community, scenario)
        self.rng = np.random.default_rng(self.seed)
        self.terminal_target = np.array([house.initial_soc_kwh for house in community.houses])
        self.peak_so_far_kw = 0.0

    def _forecast_window(self, t: int) -> tuple[int, np.ndarray, np.ndarray]:
        scenario = self.scenario
        end = min(scenario.n_steps, t + max(1, round(self.horizon_h / scenario.dt_h)))
        pv = noisy_forecast(scenario.pv_kw[:, :end], t, self.pv_error, scenario.steps_per_day, self.rng)
        load = noisy_forecast(scenario.load_kw[:, :end], t, self.load_error, scenario.steps_per_day, self.rng)
        return end, pv, load

    def dispatch(self, state: SimState) -> Dispatch:
        scenario, t = self.scenario, state.t
        if self.billing_period_days and t % (self.billing_period_days * scenario.steps_per_day) == 0:
            self.peak_so_far_kw = 0.0
        end, pv, load = self._forecast_window(t)
        solution = solve_dispatch(
            self.community, pv, load, scenario.price_import[t:end], scenario.price_export[t:end],
            scenario.dt_h, state.soc_kwh, self.weights, terminal_soc=self.terminal_target,
            peak_floor=self.peak_so_far_kw if self.peak_memory else 0.0,
        )
        dispatch = Dispatch.from_flows(solution.flows, 0)
        # the simulator applies the dispatch unchanged (clip at 0 only), so this is the realised import
        self.peak_so_far_kw = max(self.peak_so_far_kw, float(np.clip(dispatch.imp, 0, None).sum()))
        return dispatch
