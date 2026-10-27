"""
LP dispatch of the community (HiGHS), used with perfect foresight (LPController) or in a
rolling horizon with forecasts (MPCController: the true future plus noise; RealisticMPCController:
forecasts from past readings and published prices only, see forecast.py). Variables in kW, soc in kWh,
objective in lei:

    min  sum_t dt * sum_h [ price_import * imp - price_export * exp
                            + deg_cost * (ch + dis) + voll * shed + eps * (curtail + p2p_out) ]
         + peak_cost * P_peak,   P_peak >= sum_h imp[h, t] for every t,  P_peak >= peak_floor

P2P payments cancel out inside the community, so they do not appear in the objective.
The peak term is a demand charge; peak_floor is the peak already paid earlier in the
billing period, so only the increment above it is charged.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import highspy
import numpy as np

from vpp_core.controllers import Controller
from vpp_core.dispatch import Dispatch
from vpp_core.forecast import History, RealisticForecaster
from vpp_core.params import CommunityParams, GridParams
from vpp_core.scenario import Scenario
from vpp_core.simulator import SimState

INF = highspy.kHighsInf
SOC_MARGIN = 1e-4  # kWh kept away from the SOC limits, absorbs solver tolerance over many steps


@dataclass
class LPWeights:
    """Objective coefficients, lei/kWh unless stated."""

    deg_cost: float = 0.20   # battery wear per kWh of throughput (Deye SE-F16 warranty); see backend/data/README.md
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


def _add_inverter_limits(builder: _LPBuilder, var: dict[str, np.ndarray], community: CommunityParams,
                         pv: np.ndarray) -> None:
    # (pv - curtail) + dis - ch <= inv  and  ch - dis - (pv - curtail) <= inv, per house and step
    limited = np.array([np.isfinite(house.inverter_kw) for house in community.houses])
    if not limited.any():
        return
    inverter = np.array([house.inverter_kw for house in community.houses])[limited][:, None]
    rows = np.flatnonzero(limited)
    builder.add_rows(
        [(var["curtail"][rows], -1), (var["dis"][rows], 1), (var["ch"][rows], -1)], -INF, inverter - pv[rows],
    )
    builder.add_rows(
        [(var["curtail"][rows], 1), (var["dis"][rows], -1), (var["ch"][rows], 1)], -INF, inverter + pv[rows],
    )


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
    _add_inverter_limits(builder, var, community, pv)
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


REALISATIONS = ("exchange", "battery")


def realise(plan: Dispatch, community: CommunityParams, pv: np.ndarray, load: np.ndarray, price_export: float,
            state: SimState, dt_h: float, forecast_error: np.ndarray | None = None) -> Dispatch:
    """A plan made on forecasts, applied to the PV and load measured in the step. With forecast_error =
    (load - load forecast) - (pv - pv forecast) per house, the battery takes that error on top of its set-point
    (as far as it can), so the house exchanges with the others and the grid what was planned, like a hybrid
    inverter following an exchange target; without it the battery set-points are kept and the grid takes the
    error. Then kept inside the limits the simulator checks: inverter (curtail PV, then less discharge or
    charge), community export or a negative export price (curtail, then less discharge), community import
    (less charge, more discharge, then shed). P2P is the ex-post sharing of the measured surpluses and
    deficits, pro rata, as an energy community settles it."""
    grid = community.grid
    inverter = np.array([house.inverter_kw for house in community.houses])
    p2p_allowed = np.array([house.p2p_enabled for house in community.houses], dtype=float)
    max_ch, max_dis = state.max_charge_kw(dt_h), state.max_discharge_kw(dt_h)
    if forecast_error is None:
        ch, dis = np.clip(plan.ch, 0, max_ch), np.clip(plan.dis, 0, max_dis)
    else:
        battery = plan.ch - plan.dis - forecast_error
        ch, dis = np.clip(battery, 0, max_ch), np.clip(-battery, 0, max_dis)

    # (pv - curtail) + dis - ch <= inverter  and  ch - dis - (pv - curtail) <= inverter
    over = pv + dis - ch - inverter
    curtail = np.clip(np.minimum(over, pv), 0, None)
    dis = dis - np.clip(over - curtail, 0, None)
    ch = ch - np.clip(ch - dis - (pv - curtail) - inverter, 0, None)

    def exchange(ch, dis, curtail):
        net = load - (pv - curtail) + ch - dis
        deficit, surplus = np.clip(net, 0, None), np.clip(-net, 0, None)
        offered, wanted = surplus * p2p_allowed, deficit * p2p_allowed
        traded = min(offered.sum(), wanted.sum(), grid.internal_line_kw)
        p2p_out = offered * (traded / offered.sum()) if traded > 0 else np.zeros_like(net)
        p2p_in = wanted * (traded / wanted.sum()) if traded > 0 else np.zeros_like(net)
        return deficit - p2p_in, surplus - p2p_out, p2p_in, p2p_out

    imp, exp, p2p_in, p2p_out = exchange(ch, dis, curtail)
    # over the community import limit every battery helps (less charge, then more discharge shared over P2P)
    # before any house sheds
    excess = imp.sum() - grid.import_max_kw
    if excess > 0:
        if ch.sum() > 0:
            ch = ch * (1 - min(1.0, excess / ch.sum()))
        excess = exchange(ch, dis, curtail)[0].sum() - grid.import_max_kw
        room = np.clip(np.minimum(max_dis - dis, inverter - ((pv - curtail) + dis - ch)), 0, None) * (ch <= 0)
        if excess > 0 and room.sum() > 0:
            dis = dis + room * min(1.0, excess / room.sum())
        imp, exp, p2p_in, p2p_out = exchange(ch, dis, curtail)

    if price_export < 0:
        cut = exp.copy()
    elif exp.sum() > grid.export_max_kw:
        cut = exp * (1 - grid.export_max_kw / exp.sum())
    else:
        cut = np.zeros_like(exp)
    from_pv = np.minimum(cut, pv - curtail)
    curtail, dis, exp = curtail + from_pv, dis - (cut - from_pv), exp - cut

    shed = np.zeros_like(imp)
    if imp.sum() > grid.import_max_kw:
        shed = imp * (1 - grid.import_max_kw / imp.sum())
        imp = imp - shed
    return Dispatch(curtail=curtail, shed=shed, ch=ch, dis=dis, imp=imp, exp=exp, p2p_in=p2p_in, p2p_out=p2p_out)


class MPCController(Controller):
    """Rolling horizon: forecast, solve the LP, apply the first step, repeat.
    Each window must end with soc >= initial soc, or >= the current soc when that is out of reach.
    billing_period_days=None means the peak memory (peak_floor) covers the whole run; peak_memory=False
    pays each window's peak from zero.
    Without a forecaster the forecast is the true future with noise (noisy_forecast: exact at step t,
    prices known for the whole horizon), the near-perfect reference. With a RealisticForecaster the LP
    sees only forecaster.predict(History) and the plan's first step goes through realise();
    history_source replaces the scenario as the source of the History (the live loop); realisation picks
    what absorbs the forecast error of the step (REALISATIONS: the battery or the grid, see realise)."""

    def __init__(self, horizon_h: float = 24.0, pv_error: float = 0.3, load_error: float = 0.2,
                 weights: LPWeights = LPWeights(), seed: int = 0, name: str = "mpc_ideal",
                 billing_period_days: int | None = None, peak_memory: bool = True,
                 forecaster: RealisticForecaster | None = None,
                 history_source: Callable[[int], History] | None = None, realisation: str = "exchange"):
        if realisation not in REALISATIONS:
            raise ValueError(f"realisation must be one of {REALISATIONS}")
        self.horizon_h = horizon_h
        self.pv_error = pv_error          # relative std of the forecast error after 24 h
        self.load_error = load_error
        self.weights = weights
        self.seed = seed
        self.name = name
        self.billing_period_days = billing_period_days
        self.peak_memory = peak_memory
        self.forecaster = forecaster
        self.history_source = history_source
        self.realisation = realisation
        self.peak_so_far_kw = 0.0

    def reset(self, community: CommunityParams, scenario: Scenario) -> None:
        super().reset(community, scenario)
        self.rng = np.random.default_rng(self.seed)
        self.terminal_target = np.array([house.initial_soc_kwh for house in community.houses])
        self.peak_so_far_kw = 0.0
        if self.forecaster is not None:
            self.forecaster.reset(community)

    def _window_end(self, t: int) -> int:
        return min(self.scenario.n_steps, t + max(1, round(self.horizon_h / self.scenario.dt_h)))

    def _forecast_window(self, t: int) -> tuple[int, np.ndarray, np.ndarray]:
        scenario = self.scenario
        end = self._window_end(t)
        pv = noisy_forecast(scenario.pv_kw[:, :end], t, self.pv_error, scenario.steps_per_day, self.rng)
        load = noisy_forecast(scenario.load_kw[:, :end], t, self.load_error, scenario.steps_per_day, self.rng)
        return end, pv, load

    def _inputs(self, t: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(pv, load, price_import, price_export) the LP sees for the window that starts at t."""
        scenario = self.scenario
        if self.forecaster is None:
            end, pv, load = self._forecast_window(t)
            return pv, load, scenario.price_import[t:end], scenario.price_export[t:end]
        end = self._window_end(t)
        history = self.history_source(t) if self.history_source else self.forecaster.observe(scenario, t)
        forecast = self.forecaster.predict(history, end - t)
        perfect = self.forecaster.perfect
        return (
            scenario.pv_kw[:, t:end] if "pv" in perfect else forecast.pv_kw,
            scenario.load_kw[:, t:end] if "load" in perfect else forecast.load_kw,
            scenario.price_import[t:end] if "price" in perfect else forecast.price_import,
            scenario.price_export[t:end] if "price" in perfect else forecast.price_export,
        )

    def dispatch(self, state: SimState) -> Dispatch:
        scenario, t = self.scenario, state.t
        if self.billing_period_days and t % (self.billing_period_days * scenario.steps_per_day) == 0:
            self.peak_so_far_kw = 0.0
        pv, load, price_import, price_export = self._inputs(t)
        args = (self.community, pv, load, price_import, price_export, scenario.dt_h, state.soc_kwh, self.weights)
        peak_floor = self.peak_so_far_kw if self.peak_memory else 0.0
        try:
            solution = solve_dispatch(*args, terminal_soc=self.terminal_target, peak_floor=peak_floor)
        except RuntimeError:
            # a short window at the end of the run cannot always refill a battery the forecast errors emptied;
            # not ending below the current SOC is always feasible (battery idle)
            target = np.minimum(self.terminal_target, state.soc_kwh)
            solution = solve_dispatch(*args, terminal_soc=target, peak_floor=peak_floor)
        dispatch = Dispatch.from_flows(solution.flows, 0)
        if self.forecaster is not None and not {"pv", "load"} <= set(self.forecaster.perfect):
            actual_pv, actual_load = scenario.pv_kw[:, t], scenario.load_kw[:, t]
            error = (actual_load - load[:, 0]) - (actual_pv - pv[:, 0]) if self.realisation == "exchange" else None
            dispatch = realise(dispatch, self.community, actual_pv, actual_load, float(scenario.price_export[t]),
                               state, scenario.dt_h, error)
        # the simulator applies the dispatch unchanged (clip at 0 only), so this is the realised import
        self.peak_so_far_kw = max(self.peak_so_far_kw, float(np.clip(dispatch.imp, 0, None).sum()))
        return dispatch


class RealisticMPCController(MPCController):
    """The MPC an operator can actually run: RealisticForecaster (forecast.py) unless another is given."""

    def __init__(self, horizon_h: float = 24.0, weights: LPWeights = LPWeights(), name: str = "mpc",
                 billing_period_days: int | None = None, peak_memory: bool = True,
                 forecaster: RealisticForecaster | None = None,
                 history_source: Callable[[int], History] | None = None, realisation: str = "exchange"):
        super().__init__(horizon_h=horizon_h, weights=weights, name=name, billing_period_days=billing_period_days,
                         peak_memory=peak_memory, forecaster=forecaster or RealisticForecaster(),
                         history_source=history_source, realisation=realisation)
