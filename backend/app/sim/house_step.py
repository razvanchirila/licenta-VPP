"""
House simulation step - implements energy management logic for a single house
"""
from app.models.house import House
from app.config import PRICE_LOW_THRESHOLD, PRICE_HIGH_THRESHOLD


def get_price_zone(price_t: float) -> str:
    """
    Determine price zone based on thresholds
    
    Args:
        price_t: Current price in lei/kWh
    
    Returns:
        "cheap", "normal", or "expensive"
    """
    if price_t < PRICE_LOW_THRESHOLD:
        return "cheap"
    elif price_t > PRICE_HIGH_THRESHOLD:
        return "expensive"
    else:
        return "normal"


def get_soc_zone(house: House) -> str:
    """
    Determine battery SOC zone
    
    Args:
        house: House instance
    
    Returns:
        "low", "medium", or "high" (or None if no battery)
    """
    if not house.battery:
        return None
    
    soc_ratio = house.battery.get_soc_ratio()
    if soc_ratio < 0.3:
        return "low"
    elif soc_ratio > 0.8:
        return "high"
    else:
        return "medium"


def simulate_house_step(
    house: House,
    pv_prod_kw: float,
    price_t: float,
    can_export_grid: bool = True,
    p_grid_export_max_kw: float = 1500.0,
    dt_h: float = 1.0
) -> dict:
    """
    Simulate one time step for a house
    
    This implements the algorithm from the specification:
    1. Calculate loads (critical, non-critical, effective)
    2. Use PV production to meet load
    3. Handle deficit: battery -> grid
    4. Handle surplus: battery -> grid -> internal trading
    5. Curtailment if necessary
    
    Args:
        house: House instance
        pv_prod_kw: PV production for this time step (kW)
        price_t: Current electricity price (lei/kWh)
        can_export_grid: Whether export to grid is allowed
        p_grid_export_max_kw: Maximum export to grid (kW)
        dt_h: Time step duration (hours)
    
    Returns:
        Dictionary with energy flows and state
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Determine zones
    price_zone = get_price_zone(price_t)
    soc_zone = get_soc_zone(house)
    
    # Debug logging for house consumption
    L_crit_raw = house.compute_L_crit_kw()
    L_noncrit_raw = house.compute_L_noncrit_kw()
    active_devices = sum(1 for d in house.devices if d.status_on)
    total_devices = len(house.devices)
    
    logger.debug(
        f"House {house.id}: {active_devices}/{total_devices} devices ON, "
        f"L_crit={L_crit_raw:.3f}kW, L_noncrit={L_noncrit_raw:.3f}kW, "
        f"PV={pv_prod_kw:.3f}kW, price_zone={price_zone}"
    )
    
    # Calculate loads
    L_crit_kw = house.compute_L_crit_kw()
    L_noncrit_kw = house.compute_L_noncrit_kw()
    
    # REAL consumption = critical + non-critical (what devices actually consume)
    L_total_kw = L_crit_kw + L_noncrit_kw
    
    # Alpha is just a RECOMMENDATION factor, not automatic reduction
    # It tells the user what they SHOULD reduce to, not what they ARE consuming
    alpha = house.apply_mode_and_price(price_zone)
    L_recommended_kw = L_crit_kw + (L_noncrit_kw * alpha)
    
    # Initialize result dictionary
    result = {
        "house_id": house.id,
        "price_zone": price_zone,
        "soc_zone": soc_zone,
        "L_crit_kw": L_crit_kw,
        "L_noncrit_kw": L_noncrit_kw,
        "alpha": alpha,
        "L_recommended_kw": L_recommended_kw,  # What user SHOULD consume
        "L_total_kw": L_total_kw,  # What user ACTUALLY consumes
        "pv_prod_kw": pv_prod_kw,
        "P_from_pv_to_load_kw": 0,
        "P_from_batt_kw": 0,
        "P_from_grid_load_kw": 0,
        "P_to_batt_from_pv_kw": 0,
        "P_to_grid_export_kw": 0,
        "P_to_grid_charge_kw": 0,
        "surplus_after_grid_kw": 0,
        "curtailment_kw": 0,
        "battery_soc_kwh": house.battery.soc_kwh if house.battery else 0,
        "battery_soc_percent": house.battery.get_soc_percent() if house.battery else 0
    }
    
    # Step 1: Use PV to meet load
    if pv_prod_kw >= L_total_kw:
        # PV covers all load
        result["P_from_pv_to_load_kw"] = L_total_kw
        surplus_kw = pv_prod_kw - L_total_kw
        deficit_kw = 0
    else:
        # PV doesn't cover all load
        result["P_from_pv_to_load_kw"] = pv_prod_kw
        surplus_kw = 0
        deficit_kw = L_total_kw - pv_prod_kw
    
    # Step 2: Handle deficit (battery -> grid)
    if deficit_kw > 0:
        if house.battery:
            # Try to use battery
            P_batt_available_kw = house.battery.get_available_discharge_power(dt_h)
            P_from_batt_kw = min(deficit_kw, P_batt_available_kw)
            
            if P_from_batt_kw > 0:
                soc_before = house.battery.soc_kwh
                house.battery.discharge(P_from_batt_kw, dt_h)
                result["P_from_batt_kw"] = P_from_batt_kw
                deficit_kw -= P_from_batt_kw
                logger.debug(
                    f"House {house.id}: Battery discharge {P_from_batt_kw:.3f}kW for {dt_h:.4f}h, "
                    f"SOC: {soc_before:.2f} -> {house.battery.soc_kwh:.2f} kWh"
                )
        
        # Remaining deficit from grid
        if deficit_kw > 0:
            result["P_from_grid_load_kw"] = deficit_kw
    
    # Step 3: Handle surplus - SUSTAINABLE PRIORITY
    # If battery is above threshold (50%), offer surplus to neighbors FIRST
    # Priority when battery >= 50%: 1) P2P to neighbors, 2) Battery, 3) Grid
    # Priority when battery < 50%: 1) Battery, 2) P2P, 3) Grid
    
    BATTERY_SHARING_THRESHOLD = 0.5  # 50% - above this, prioritize neighbors
    
    if surplus_kw > 0:
        battery_soc_ratio = house.battery.get_soc_ratio() if house.battery else 0
        
        if house.battery and battery_soc_ratio < BATTERY_SHARING_THRESHOLD:
            # Battery is low - charge it first, then share what's left
            P_batt_space_kw = house.battery.get_available_charge_power(dt_h)
            P_to_batt_from_pv_kw = min(surplus_kw, P_batt_space_kw)
            
            if P_to_batt_from_pv_kw > 0:
                house.battery.charge(P_to_batt_from_pv_kw, dt_h)
                result["P_to_batt_from_pv_kw"] = P_to_batt_from_pv_kw
                surplus_kw -= P_to_batt_from_pv_kw
            
            # Remaining surplus available for P2P
            result["surplus_for_p2p_kw"] = surplus_kw
        else:
            # Battery is OK (>= 50%) - offer ALL surplus to neighbors first
            # VPP will handle P2P trading, then return unused surplus for battery
            result["surplus_for_p2p_kw"] = surplus_kw
            result["P_to_batt_from_pv_kw"] = 0  # Will be set after P2P at VPP level
            # Store battery space for later use
            if house.battery:
                result["battery_space_kw"] = house.battery.get_available_charge_power(dt_h)
        
        # Don't export to grid here - let VPP handle it after P2P
        result["P_to_grid_export_kw"] = 0
        result["surplus_after_grid_kw"] = surplus_kw  # For backward compatibility
    
    # Step 4: Arbitrage - charge battery from grid during cheap prices
    # Only if in Profit mode, price is cheap, and battery has space
    if house.battery and house.mode == "Profit" and price_zone == "cheap" and soc_zone != "high":
        P_batt_space_kw = house.battery.get_available_charge_power(dt_h)
        if P_batt_space_kw > 0 and house.battery.get_soc_ratio() < 0.8:
            # Charge battery from grid (up to max charge power)
            P_to_grid_charge_kw = min(P_batt_space_kw, house.battery.p_ch_max_kw)
            house.battery.charge(P_to_grid_charge_kw, dt_h)
            result["P_to_grid_charge_kw"] = P_to_grid_charge_kw
    
    # Update final battery state
    if house.battery:
        result["battery_soc_kwh"] = house.battery.soc_kwh
        result["battery_soc_percent"] = house.battery.get_soc_percent()
    
    return result
