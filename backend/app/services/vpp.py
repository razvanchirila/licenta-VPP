from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BatteryModel, DeviceModel, HouseModel
from app.db.models import HouseStepModel as S
from app.db.models import TradeTransactionModel as Trade
from app.services.simulation_loop import SimulationLoop


async def community_state(session: AsyncSession, sim: SimulationLoop) -> dict:
    houses = (await session.execute(select(
        func.count(HouseModel.id),
        func.coalesce(func.sum(case((HouseModel.has_pv, HouseModel.pv_capacity_kw), else_=0.0)), 0.0),
    ))).one()
    batteries = (await session.execute(select(
        func.count(BatteryModel.id),
        func.coalesce(func.sum(BatteryModel.capacity_kwh), 0.0),
        func.coalesce(func.sum(BatteryModel.soc_kwh), 0.0),
    ))).one()
    load = (await session.execute(select(
        func.coalesce(func.sum(case((DeviceModel.critical, DeviceModel.current_power_kw), else_=0.0)), 0.0),
        func.coalesce(func.sum(case((DeviceModel.critical, 0.0), else_=DeviceModel.current_power_kw)), 0.0),
    ).where(DeviceModel.status_on))).one()

    n_houses, pv_kw = int(houses[0]), float(houses[1])
    n_batt, cap, soc = int(batteries[0]), float(batteries[1]), float(batteries[2])
    cfg = sim.config
    return {
        "total_houses": n_houses,
        "houses_with_battery": n_batt,
        "houses_without_battery": n_houses - n_batt,
        "total_pv_capacity_kw": round(pv_kw, 2),
        "total_battery_capacity_kwh": round(cap, 2),
        "total_battery_soc_kwh": round(soc, 2),
        "avg_battery_soc_percent": round(100 * soc / cap, 1) if cap else 0.0,
        "total_L_crit_kw": round(float(load[0]), 3),
        "total_L_noncrit_kw": round(float(load[1]), 3),
        "p_grid_import_max_kw": cfg.import_max_kw,
        "p_grid_export_max_kw": cfg.export_max_kw,
        "p_internal_line_limit_kw": cfg.internal_line_kw,
        "controller": cfg.controller,
        "sim_datetime": sim.sim_datetime.isoformat(),
        "last_step": {k: v for k, v in (sim.last_result or {}).items() if k != "houses"} or None,
    }


async def today_totals(session: AsyncSession, day: date) -> dict:
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    in_day = (S.sim_timestamp >= start, S.sim_timestamp < end)

    def kwh(col):
        return func.coalesce(func.sum(col * S.dt_h), 0.0)

    row = (await session.execute(
        select(kwh(S.pv_kw - S.curtail_kw).label("pv"), kwh(S.load_kw - S.shed_kw).label("load"),
               kwh(S.shed_kw).label("shed"), kwh(S.curtail_kw).label("curtail"), kwh(S.imp_kw).label("imp"),
               kwh(S.exp_kw).label("exp"), kwh(S.p2p_out_kw).label("p2p"), kwh(S.ch_kw).label("ch"),
               kwh(S.dis_kw).label("dis"), kwh(S.imp_kw * S.price_import).label("import_cost"),
               kwh(S.exp_kw * S.price_export).label("export_income"))
        .where(*in_day)
    )).one()
    # peak import of the community = max over steps of the sum over houses
    per_step = select(func.sum(S.imp_kw).label("imp_kw")).where(*in_day).group_by(S.sim_timestamp).subquery()
    peak = (await session.execute(select(func.coalesce(func.max(per_step.c.imp_kw), 0.0)))).scalar()
    trades = (await session.execute(
        select(func.count(Trade.id), func.coalesce(func.sum(Trade.total_value_lei), 0.0))
        .where(Trade.sim_timestamp >= start, Trade.sim_timestamp < end, Trade.status == "settled")
    )).one()

    pv, load = float(row.pv), float(row.load)
    return {
        "date": day.isoformat(),
        "pv_kwh": round(pv, 2), "load_kwh": round(load, 2), "shed_kwh": round(float(row.shed), 2),
        "curtail_kwh": round(float(row.curtail), 2), "import_kwh": round(float(row.imp), 2),
        "export_kwh": round(float(row.exp), 2), "p2p_kwh": round(float(row.p2p), 2),
        "charge_kwh": round(float(row.ch), 2), "discharge_kwh": round(float(row.dis), 2),
        "cost_lei": round(float(row.import_cost) - float(row.export_income), 2),
        "peak_import_kw": round(float(peak or 0.0), 2),
        "self_consumption": round(1 - float(row.exp) / pv, 3) if pv > 1e-9 else None,
        "self_sufficiency": round(1 - float(row.imp) / load, 3) if load > 1e-9 else None,
        "trades_settled": int(trades[0]), "trades_value_lei": round(float(trades[1]), 2),
    }
