"""
VPP API routes
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/vpp", tags=["vpp"])


@router.get("/state")
def get_vpp_state():
    """Get current VPP state"""
    from app.api.state import vpp_state
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    return vpp_state.vpp.to_dict()


@router.get("/stats")
def get_vpp_stats():
    """Get detailed VPP statistics"""
    from app.api.state import vpp_state
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    vpp = vpp_state.vpp
    
    # Calculate current consumption and production from devices
    total_crit_kw = 0
    total_noncrit_kw = 0
    total_battery_soc = 0
    total_battery_capacity = 0
    
    for house in vpp.houses:
        total_crit_kw += house.compute_L_crit_kw()
        total_noncrit_kw += house.compute_L_noncrit_kw()
        if house.battery:
            total_battery_soc += house.battery.soc_kwh
            total_battery_capacity += house.battery.capacity_kwh
    
    return {
        **vpp.to_dict(),
        "total_L_crit_kw": round(total_crit_kw, 2),
        "total_L_noncrit_kw": round(total_noncrit_kw, 2),
        "avg_battery_soc_percent": round(
            (total_battery_soc / total_battery_capacity * 100) if total_battery_capacity > 0 else 0,
            1
        )
    }


@router.get("/debug/houses")
def get_houses_debug():
    """Debug endpoint - shows consumption and battery for each house"""
    from app.api.state import vpp_state
    from app.services.simulation_loop import simulation_loop
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    vpp = vpp_state.vpp
    sim_hour = simulation_loop.clock.hour
    
    # Get current PV production for this hour
    pv_profiles = vpp_state.profiles.get("pv_profiles", {}) if vpp_state.profiles else {}
    
    houses_debug = []
    for house in vpp.houses:
        # Count active devices
        active_devices = [d for d in house.devices if d.status_on]
        total_power_kw = sum(d.get_power_kw() for d in active_devices)
        
        # Get PV for this house at current hour
        pv_kw = pv_profiles.get(house.id, [0]*24)[sim_hour] if pv_profiles else 0
        
        # Calculate deficit/surplus
        deficit_kw = max(0, total_power_kw - pv_kw)
        surplus_kw = max(0, pv_kw - total_power_kw)
        
        houses_debug.append({
            "house_id": house.id,
            "mode": house.mode,
            "active_devices": len(active_devices),
            "total_devices": len(house.devices),
            "L_crit_kw": round(house.compute_L_crit_kw(), 3),
            "L_noncrit_kw": round(house.compute_L_noncrit_kw(), 3),
            "total_consumption_kw": round(total_power_kw, 3),
            "pv_production_kw": round(pv_kw, 3),
            "deficit_kw": round(deficit_kw, 3),
            "surplus_kw": round(surplus_kw, 3),
            "battery_soc_kwh": round(house.battery.soc_kwh, 2) if house.battery else None,
            "battery_soc_percent": round(house.battery.get_soc_percent(), 1) if house.battery else None,
            "devices": [
                {"name": d.name, "power_kw": d.get_power_kw(), "on": d.status_on}
                for d in house.devices
            ]
        })
    
    return {
        "sim_hour": sim_hour,
        "sim_time": simulation_loop.clock.time_str,
        "houses": houses_debug
    }


@router.get("/debug/math/{house_id}")
def get_house_math_debug(house_id: int):
    """
    Debug endpoint - shows detailed math calculations for a house.
    
    Useful for verifying that energy calculations are correct.
    """
    from app.api.state import vpp_state
    from app.services.simulation_loop import simulation_loop
    from app.sim.house_step import get_price_zone
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    house = vpp_state.vpp.get_house(house_id)
    if not house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    # Get simulation parameters
    dt_h = simulation_loop.clock.dt_hours  # 10 min = 0.1667 hours
    sim_hour = simulation_loop.clock.hour
    
    # Get profiles
    pv_profiles = vpp_state.profiles.get("pv_profiles", {}) if vpp_state.profiles else {}
    prices = vpp_state.profiles.get("prices_24h", [1.0]*24) if vpp_state.profiles else [1.0]*24
    
    pv_kw = pv_profiles.get(house_id, [0]*24)[sim_hour] if pv_profiles else 0
    price_t = prices[sim_hour]
    price_zone = get_price_zone(price_t)
    
    # Calculate loads
    L_crit_kw = house.compute_L_crit_kw()
    L_noncrit_kw = house.compute_L_noncrit_kw()
    
    # REAL consumption = critical + non-critical (actual device consumption)
    L_total_kw = L_crit_kw + L_noncrit_kw
    
    # Alpha is a RECOMMENDATION factor - tells user what they SHOULD reduce to
    # It does NOT automatically reduce consumption
    alpha = house.apply_mode_and_price(price_zone)
    L_recommended_kw = L_crit_kw + (L_noncrit_kw * alpha)
    
    # Calculate energy flows based on REAL consumption
    deficit_kw = max(0, L_total_kw - pv_kw)
    surplus_kw = max(0, pv_kw - L_total_kw)
    
    # Battery calculations
    battery_info = None
    if house.battery:
        batt = house.battery
        available_discharge_kw = batt.get_available_discharge_power(dt_h)
        available_charge_kw = batt.get_available_charge_power(dt_h)
        
        # What will happen this step
        if deficit_kw > 0:
            discharge_kw = min(deficit_kw, available_discharge_kw)
            energy_discharged_kwh = discharge_kw * dt_h
            new_soc_kwh = batt.soc_kwh - energy_discharged_kwh
        else:
            discharge_kw = 0
            energy_discharged_kwh = 0
            new_soc_kwh = batt.soc_kwh
        
        if surplus_kw > 0:
            charge_kw = min(surplus_kw, available_charge_kw)
            energy_charged_kwh = charge_kw * dt_h
            new_soc_kwh = batt.soc_kwh + energy_charged_kwh
        else:
            charge_kw = 0
            energy_charged_kwh = 0
        
        # Time estimates
        usable_capacity = batt.soc_kwh - batt.soc_min_kwh
        if deficit_kw > 0 and discharge_kw > 0:
            steps_until_empty = usable_capacity / energy_discharged_kwh if energy_discharged_kwh > 0 else float('inf')
            hours_until_empty = steps_until_empty * (simulation_loop.sim_minutes_per_step / 60)
        else:
            steps_until_empty = float('inf')
            hours_until_empty = float('inf')
        
        battery_info = {
            "capacity_kwh": batt.capacity_kwh,
            "current_soc_kwh": round(batt.soc_kwh, 4),
            "current_soc_percent": round(batt.get_soc_percent(), 2),
            "min_soc_kwh": batt.soc_min_kwh,
            "usable_capacity_kwh": round(usable_capacity, 4),
            "max_discharge_kw": batt.p_dis_max_kw,
            "max_charge_kw": batt.p_ch_max_kw,
            "available_discharge_kw": round(available_discharge_kw, 4),
            "available_charge_kw": round(available_charge_kw, 4),
            "this_step": {
                "discharge_power_kw": round(discharge_kw, 4),
                "charge_power_kw": round(charge_kw, 4),
                "energy_discharged_kwh": round(energy_discharged_kwh, 6),
                "energy_charged_kwh": round(energy_charged_kwh, 6),
                "predicted_new_soc_kwh": round(new_soc_kwh, 4),
                "predicted_new_soc_percent": round((new_soc_kwh / batt.capacity_kwh) * 100, 2)
            },
            "estimates": {
                "steps_until_empty": round(steps_until_empty, 1) if steps_until_empty != float('inf') else "N/A (charging or no deficit)",
                "sim_hours_until_empty": round(hours_until_empty, 2) if hours_until_empty != float('inf') else "N/A",
                "real_minutes_until_empty": round(steps_until_empty * simulation_loop.interval_seconds / 60, 1) if steps_until_empty != float('inf') else "N/A"
            }
        }
    
    return {
        "house_id": house_id,
        "mode": house.mode,
        "simulation": {
            "sim_time": simulation_loop.clock.time_str,
            "sim_hour": sim_hour,
            "dt_hours": round(dt_h, 4),
            "dt_minutes": simulation_loop.sim_minutes_per_step,
            "real_interval_seconds": simulation_loop.interval_seconds,
            "total_steps": simulation_loop.total_steps
        },
        "price": {
            "current_price": round(price_t, 4),
            "price_zone": price_zone
        },
        "loads": {
            "L_crit_kw": round(L_crit_kw, 4),
            "L_noncrit_kw": round(L_noncrit_kw, 4),
            "L_total_kw": round(L_total_kw, 4),
            "alpha_factor": round(alpha, 2),
            "L_recommended_kw": round(L_recommended_kw, 4),
            "over_recommended_kw": round(max(0, L_total_kw - L_recommended_kw), 4),
            "explanation": f"REAL consumption = {L_crit_kw:.3f} + {L_noncrit_kw:.3f} = {L_total_kw:.3f} kW",
            "recommendation": f"RECOMMENDED = {L_crit_kw:.3f} + ({L_noncrit_kw:.3f} × {alpha:.1f}) = {L_recommended_kw:.3f} kW"
        },
        "pv": {
            "production_kw": round(pv_kw, 4)
        },
        "energy_balance": {
            "deficit_kw": round(deficit_kw, 4),
            "surplus_kw": round(surplus_kw, 4),
            "explanation": f"{'Deficit' if deficit_kw > 0 else 'Surplus'}: |{L_total_kw:.3f} - {pv_kw:.3f}| = {max(deficit_kw, surplus_kw):.3f} kW"
        },
        "battery": battery_info,
        "devices": [
            {
                "name": d.name,
                "power_w": d.power_w,
                "power_kw": round(d.get_power_kw(), 4),
                "status_on": d.status_on,
                "critical": d.critical,
                "accumulated_kwh": round(d.accumulated_energy_kwh, 4)
            }
            for d in house.devices
        ]
    }
