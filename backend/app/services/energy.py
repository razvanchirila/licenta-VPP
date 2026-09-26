"""
Per-house energy figures for /api/me/energy/*, aggregated in SQL over house_steps. Quantities are
kWh (power x dt_h) or lei; "reference cost" is the same load with no PV, battery or P2P.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HouseStepModel as S

FLOWS = ("pv", "load", "device", "shed", "curtail", "ch", "dis", "imp", "exp", "p2p_in", "p2p_out")
MONTHS_RO = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PEAK_HOURS = range(17, 22)


def _kwh(col):
    return func.coalesce(func.sum(col * S.dt_h), 0.0)


def _totals_columns() -> list:
    cols = [_kwh(getattr(S, f"{k}_kw")).label(f"{k}_kwh") for k in FLOWS]
    cols += [
        _kwh(S.imp_kw * S.price_import).label("import_cost_lei"),
        _kwh(S.exp_kw * S.price_export).label("export_income_lei"),
        _kwh(S.p2p_in_kw * S.price_p2p).label("p2p_cost_lei"),
        _kwh(S.p2p_out_kw * S.price_p2p).label("p2p_income_lei"),
        _kwh(S.load_kw * S.price_import).label("reference_cost_lei"),
        func.count(S.id).label("steps"),
    ]
    return cols


def _in_range(house_id: int, start: datetime, end: datetime):
    return (S.house_id == house_id, S.sim_timestamp >= start, S.sim_timestamp < end)


def summarize(row) -> dict:
    d = {k: round(float(getattr(row, f"{k}_kwh")), 3) for k in FLOWS}
    cost = (float(row.import_cost_lei) - float(row.export_income_lei)
            + float(row.p2p_cost_lei) - float(row.p2p_income_lei))
    reference = float(row.reference_cost_lei)
    served = d["load"] - d["shed"]
    direct_pv = max(0.0, served - d["imp"] - d["dis"] - d["p2p_in"])
    return {
        "steps": int(row.steps),
        "consumed_kwh": round(served, 3),
        "shed_kwh": d["shed"],
        "device_kwh": d["device"],
        "produced_kwh": round(d["pv"] - d["curtail"], 3),
        "pv_available_kwh": d["pv"],
        "curtailed_kwh": d["curtail"],
        "from_grid_kwh": d["imp"],
        "to_grid_kwh": d["exp"],
        "from_battery_kwh": d["dis"],
        "to_battery_kwh": d["ch"],
        "from_neighbours_kwh": d["p2p_in"],
        "to_neighbours_kwh": d["p2p_out"],
        "from_solar_kwh": round(direct_pv, 3),
        "cost_lei": round(cost, 2),
        "reference_cost_lei": round(reference, 2),
        "savings_lei": round(reference - cost, 2),
    }


EMPTY_TOTALS = {"steps": 0, "consumed_kwh": 0.0, "shed_kwh": 0.0, "device_kwh": 0.0, "produced_kwh": 0.0,
                "pv_available_kwh": 0.0, "curtailed_kwh": 0.0, "from_grid_kwh": 0.0, "to_grid_kwh": 0.0,
                "from_battery_kwh": 0.0, "to_battery_kwh": 0.0, "from_neighbours_kwh": 0.0,
                "to_neighbours_kwh": 0.0, "from_solar_kwh": 0.0, "cost_lei": 0.0, "reference_cost_lei": 0.0,
                "savings_lei": 0.0}


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, datetime.min.time())
    return start, start + timedelta(days=1)


async def period_totals(session: AsyncSession, house_id: int, start: datetime, end: datetime) -> dict:
    row = (await session.execute(select(*_totals_columns()).where(*_in_range(house_id, start, end)))).one()
    return summarize(row)


async def daily_totals(session: AsyncSession, house_id: int, first_day: date, last_day: date) -> list[dict]:
    day = func.date(S.sim_timestamp)
    start, _ = day_bounds(first_day)
    _, end = day_bounds(last_day)
    rows = (await session.execute(
        select(day.label("day"), *_totals_columns()).where(*_in_range(house_id, start, end)).group_by(day).order_by(day)
    )).all()
    by_day = {str(r.day)[:10]: summarize(r) for r in rows}
    out = []
    for offset in range((last_day - first_day).days + 1):
        key = (first_day + timedelta(days=offset)).isoformat()
        entry = by_day.get(key, EMPTY_TOTALS)
        out.append({"date": key, "has_data": entry["steps"] > 0, **entry})
    return out


async def monthly_totals(session: AsyncSession, house_id: int, start: datetime, end: datetime) -> dict[str, dict]:
    ym = func.strftime("%Y-%m", S.sim_timestamp)
    rows = (await session.execute(
        select(ym.label("ym"), *_totals_columns()).where(*_in_range(house_id, start, end)).group_by(ym).order_by(ym)
    )).all()
    return {r.ym: summarize(r) for r in rows}


def chart_range(period: str, ref: date, steps_per_day: int) -> tuple[date, date, int]:
    """(first day, day after the last, steps per point) for period day | week | month."""
    if period == "day":
        return ref, ref + timedelta(days=1), 1
    if period == "week":
        monday = ref - timedelta(days=ref.weekday())
        return monday, monday + timedelta(days=7), max(1, steps_per_day // 24 * 3)   # 3-hour points
    first = ref.replace(day=1)
    return first, (first + timedelta(days=32)).replace(day=1), steps_per_day           # daily points


async def step_points(session: AsyncSession, house_id: int, start: datetime, end: datetime,
                      bucket_steps: int = 1) -> list[dict]:
    """Flows in kW, each point the average of `bucket_steps` consecutive steps."""
    cols = (S.sim_timestamp, S.pv_kw, S.load_kw, S.shed_kw, S.ch_kw, S.dis_kw, S.imp_kw, S.exp_kw,
            S.p2p_in_kw, S.p2p_out_kw, S.soc_kwh, S.price_import)
    rows = (await session.execute(
        select(*cols).where(*_in_range(house_id, start, end)).order_by(S.sim_timestamp)
    )).all()
    bucket_steps = max(1, bucket_steps)
    points = []
    for k in range(0, len(rows), bucket_steps):
        chunk = rows[k:k + bucket_steps]

        def avg(attr: str, rows=chunk) -> float:
            return round(sum(getattr(r, attr) for r in rows) / len(rows), 3)

        points.append({
            "timestamp": chunk[0].sim_timestamp.isoformat(),
            "solar": avg("pv_kw"), "consumption": avg("load_kw"), "shed": avg("shed_kw"),
            "battery": round(avg("ch_kw") - avg("dis_kw"), 3),      # > 0 charging
            "grid": round(avg("imp_kw") - avg("exp_kw"), 3),        # > 0 importing
            "p2p": round(avg("p2p_in_kw") - avg("p2p_out_kw"), 3),  # > 0 buying
            "solar_to_battery": avg("ch_kw"), "battery_to_load": avg("dis_kw"),
            "grid_to_load": avg("imp_kw"), "solar_to_grid": avg("exp_kw"),
            "soc_kwh": round(chunk[-1].soc_kwh, 3), "price_import": round(chunk[0].price_import, 4),
        })
    return points


async def hourly_sources(session: AsyncSession, house_id: int, start: datetime, end: datetime) -> list[dict]:
    """Served load per hour by source, kWh; solar is the remainder."""
    hour = func.strftime("%Y-%m-%dT%H", S.sim_timestamp)
    rows = (await session.execute(
        select(hour.label("hour"), _kwh(S.load_kw - S.shed_kw).label("served"), _kwh(S.imp_kw).label("grid"),
               _kwh(S.dis_kw).label("battery"), _kwh(S.p2p_in_kw).label("p2p"))
        .where(*_in_range(house_id, start, end)).group_by(hour).order_by(hour)
    )).all()
    out = []
    for r in rows:
        served, grid, batt, p2p = float(r.served), float(r.grid), float(r.battery), float(r.p2p)
        out.append({"hour": int(r.hour[-2:]), "served": served, "grid": grid, "battery": batt, "p2p": p2p,
                    "solar": max(0.0, served - grid - batt - p2p)})
    return out


async def impact(session: AsyncSession, house_id: int, day: date) -> dict:
    start, end = day_bounds(day)
    hours = await hourly_sources(session, house_id, start, end)
    sources = ("solar", "battery", "grid", "p2p")
    total = {k: sum(h[k] for h in hours) for k in ("served", *sources)}
    served = total["served"] or 1.0

    def split(rows: list[dict]) -> dict:
        return {k: round(sum(h[k] for h in rows), 2) for k in sources}

    peak = [h for h in hours if h["hour"] in PEAK_HOURS]
    off_peak = [h for h in hours if h["hour"] not in PEAK_HOURS]

    six_months_ago = datetime.combine(day.replace(day=1), datetime.min.time()) - timedelta(days=160)
    months = await monthly_totals(session, house_id, six_months_ago, end)
    monthly = []
    for back in range(5, -1, -1):
        month_index = day.month - 1 - back            # may be negative: previous year
        year, month = day.year + month_index // 12, month_index % 12 + 1
        entry = months.get(f"{year:04d}-{month:02d}")
        monthly.append({"month": MONTHS_RO[month - 1], "year": year, "savings": entry["savings_lei"] if entry else 0.0,
                        "has_data": entry is not None, "current": (year, month) == (day.year, day.month)})
    return {
        "date": day.isoformat(),
        **{f"{k}_percent": round(100 * total[k] / served, 1) for k in sources},
        **{f"{k}_kwh": round(total[k], 2) for k in sources},
        "peak": split(peak), "off_peak": split(off_peak),
        "monthly_savings": monthly,
    }
