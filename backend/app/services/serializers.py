"""ORM rows -> the JSON objects of the API; routes never build these dicts themselves."""
from __future__ import annotations

from app.db.models import (
    BatteryModel,
    DeviceModel,
    HouseModel,
    TradeTransactionModel,
    TradingPreferencesModel,
    UserModel,
    VPPReserveModel,
    WalletModel,
    WalletTransactionModel,
)
from vpp_core.load_model import describe_intervals, parse_intervals


def user_dict(u: UserModel) -> dict:
    return {
        "user_id": u.id,
        "username": u.username,
        "house_id": u.house_id,
        "house_name": u.house.name if u.house else None,
        "is_admin": u.is_admin,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def device_dict(d: DeviceModel) -> dict:
    schedule = None
    if d.mode:
        schedule = {"mode": d.mode, "hours_per_day": d.hours_per_day, "cycles_per_week": d.cycles_per_week,
                    "cycle_minutes": d.cycle_minutes, "interval": describe_intervals(parse_intervals(d.interval)),
                    "season": d.season}
    return {
        "id": d.id,
        "house_id": d.house_id,
        "name": d.name,
        "power_w": d.power_w,
        "critical": d.critical,
        "status_on": d.status_on,
        "schedule": schedule,
        "current_power_kw": round(d.current_power_kw, 4) if d.status_on else 0.0,
        "accumulated_energy_kwh": round(d.accumulated_energy_kwh, 4),
        "last_state_change_ts": d.last_state_change_ts.isoformat() if d.last_state_change_ts else None,
    }


def battery_dict(b: BatteryModel, reserve_kwh: float = 0.0) -> dict:
    return {
        "capacity_kwh": b.capacity_kwh,
        "soc_kwh": round(b.soc_kwh, 3),
        "soc_percent": round(100.0 * b.soc_kwh / b.capacity_kwh, 1),
        "soc_min_kwh": round(b.soc_min_kwh, 3),
        "soc_max_kwh": b.capacity_kwh,
        "available_kwh": round(max(0.0, b.soc_kwh - b.soc_min_kwh), 3),
        "vpp_reserve_kwh": round(reserve_kwh, 3),
        "p_ch_max_kw": b.p_ch_max_kw,
        "p_dis_max_kw": b.p_dis_max_kw,
        "eta_ch": b.eta_ch,
        "eta_dis": b.eta_dis,
    }


def prefs_dict(p: TradingPreferencesModel) -> dict:
    return {
        "house_id": p.house_id,
        "selling_enabled": p.selling_enabled,
        "buying_enabled": p.buying_enabled,
        "price_mode": p.price_mode,
        "fixed_price_lei_kwh": p.fixed_price_lei_kwh,
        "discount_percent": p.discount_percent,
        "min_sell_price_lei_kwh": p.min_sell_price_lei_kwh,
    }


def house_dict(h: HouseModel, last_step: dict | None = None) -> dict:
    """Needs the house loaded with its relations (HouseRepository.*_with_relations)."""
    devices = list(h.devices)
    on = [d for d in devices if d.status_on]
    reserve = h.vpp_reserve.reserved_kwh if h.vpp_reserve else 0.0
    return {
        "id": h.id,
        "name": h.name,
        "mode": h.mode,
        "has_pv": h.has_pv,
        "pv_capacity_kw": h.pv_capacity_kw,
        "has_battery": h.battery is not None,
        "battery": battery_dict(h.battery, reserve) if h.battery else None,
        "devices": [device_dict(d) for d in devices],
        "device_count": len(devices),
        "L_crit_kw": round(sum(d.current_power_kw for d in on if d.critical), 3),
        "L_noncrit_kw": round(sum(d.current_power_kw for d in on if not d.critical), 3),
        "trading": prefs_dict(h.trading_preferences) if h.trading_preferences else None,
        "wallet_balance_lei": round(h.wallet.balance_lei, 2) if h.wallet else None,
        "user": h.user.username if h.user else None,
        "last_step": last_step,
    }


def wallet_dict(w: WalletModel) -> dict:
    return {
        "house_id": w.house_id,
        "balance_lei": round(w.balance_lei, 2),
        "total_earned_lei": round(w.total_earned_lei, 2),
        "total_spent_lei": round(w.total_spent_lei, 2),
        "net_balance_lei": round(w.total_earned_lei - w.total_spent_lei, 2),
        "transaction_count": w.transaction_count,
    }


def wallet_tx_dict(t: WalletTransactionModel) -> dict:
    return {
        "id": t.id,
        "wallet_id": t.wallet_id,
        "transaction_type": t.transaction_type,
        "amount_lei": round(t.amount_lei, 4),
        "description": t.description,
        "reference_id": t.reference_id,
        "balance_after": round(t.balance_after, 2),
        "sim_timestamp": t.sim_timestamp.isoformat() if t.sim_timestamp else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def trade_dict(t: TradeTransactionModel, perspective_house_id: int | None = None) -> dict:
    d = {
        "id": t.id,
        "seller_house_id": t.seller_house_id,
        "buyer_house_id": t.buyer_house_id,
        "energy_kwh": round(t.energy_kwh, 4),
        "price_lei_kwh": round(t.price_lei_kwh, 4),
        "total_value_lei": round(t.total_value_lei, 4),
        "grid_price_lei_kwh": round(t.grid_price_lei_kwh, 4),
        "status": t.status,
        "reason": t.reason,
        "sim_timestamp": t.sim_timestamp.isoformat() if t.sim_timestamp else None,
    }
    if perspective_house_id == t.seller_house_id:
        d["transaction_type"], d["counterparty_house_id"] = "sell", t.buyer_house_id
    elif perspective_house_id == t.buyer_house_id:
        d["transaction_type"], d["counterparty_house_id"] = "buy", t.seller_house_id
    return d


def reserve_dict(r: VPPReserveModel) -> dict:
    return {
        "house_id": r.house_id,
        "reserved_kwh": round(r.reserved_kwh, 4),
        "base_rate_lei_kwh": r.base_rate_lei_kwh,
    }
