"""
VPP simulation step - implements neighborhood-level energy management
"""
from typing import Dict, List
from app.models.vpp import VPP
from app.sim.house_step import simulate_house_step
from app.config import INTERNAL_PRICE_DISCOUNT


def simulate_vpp_step(
    vpp: VPP,
    pv_profile_kw: Dict[int, float],
    price_t: float,
    dt_h: float = 1.0
) -> dict:
    """
    Simulate one time step for the entire VPP (neighborhood)
    
    This orchestrates all houses and implements:
    1. Run individual house simulations
    2. Aggregate totals
    3. Apply grid limits
    4. Perform internal trading between houses
    5. Calculate curtailment
    
    Args:
        vpp: VPP instance
        pv_profile_kw: Dictionary mapping house_id to PV production (kW)
        price_t: Current electricity price (lei/kWh)
        dt_h: Time step duration (hours)
    
    Returns:
        Dictionary with VPP state and all house results
    """
    
    # Step 1: Simulate each house individually
    house_results = []
    for house in vpp.houses:
        pv_prod_kw = pv_profile_kw.get(house.id, 0.0)
        result = simulate_house_step(
            house=house,
            pv_prod_kw=pv_prod_kw,
            price_t=price_t,
            can_export_grid=True,
            p_grid_export_max_kw=vpp.p_grid_export_max_kw,
            dt_h=dt_h
        )
        house_results.append(result)
    
    # Step 2: Calculate initial totals (before P2P)
    P_total_pv_kw = sum(r["pv_prod_kw"] for r in house_results)
    P_total_load_kw = sum(r["L_total_kw"] for r in house_results)
    
    # Step 3: Internal P2P trading FIRST (before grid export)
    # Priority: Neighbors first, then grid
    house_lookup = {h.id: h for h in vpp.houses}
    
    # Collect producers (houses with surplus AND selling enabled)
    # Use surplus_for_p2p_kw which is surplus after battery, before grid
    producers = []
    for r in house_results:
        surplus = r.get("surplus_for_p2p_kw", r.get("surplus_after_grid_kw", 0))
        if surplus > 0:
            house = house_lookup.get(r["house_id"])
            if house and house.selling_enabled:
                selling_price = house.get_trading_price(price_t)
                producers.append({
                    "result": r,
                    "house": house,
                    "selling_price": selling_price,
                    "available_surplus": surplus
                })
    
    # Collect consumers (houses with deficit AND buying enabled)
    consumers = []
    for r in house_results:
        if r["P_from_grid_load_kw"] > 0:
            house = house_lookup.get(r["house_id"])
            if house and house.buying_enabled:
                consumers.append({
                    "result": r,
                    "house": house,
                    "deficit": r["P_from_grid_load_kw"]
                })
    
    P_internal_traded_kw = 0.0
    internal_trades = []
    
    if producers and consumers:
        # Sort producers by price ascending (cheapest first)
        producers.sort(key=lambda p: p["selling_price"])
        
        # Sort consumers by deficit descending (highest need first)
        consumers.sort(key=lambda c: c["deficit"], reverse=True)
        
        max_trade_kwh = vpp.p_internal_line_limit_kw * dt_h
        
        for consumer in consumers:
            consumer_result = consumer["result"]
            remaining_need = consumer_result["P_from_grid_load_kw"]
            
            if remaining_need <= 0:
                continue
            
            for producer in producers:
                if remaining_need <= 0:
                    break
                
                producer_result = producer["result"]
                # Use tracked available_surplus from producer dict
                available_surplus = producer["available_surplus"]
                selling_price = producer["selling_price"]
                
                if available_surplus <= 0:
                    continue
                
                # Skip if seller price exceeds grid price (buyer should import from grid)
                if selling_price >= price_t:
                    continue
                
                # Skip self-trading
                if producer_result["house_id"] == consumer_result["house_id"]:
                    continue
                
                # Check line limit
                remaining_capacity = max_trade_kwh - P_internal_traded_kw
                if remaining_capacity <= 0:
                    break
                
                # Calculate trade amount
                transfer_kw = min(
                    available_surplus,
                    remaining_need,
                    remaining_capacity
                )
                
                if transfer_kw > 0.001:  # Minimum trade threshold
                    # Update producer's available surplus
                    producer["available_surplus"] -= transfer_kw
                    producer_result["P_internal_export_kw"] = producer_result.get("P_internal_export_kw", 0) + transfer_kw
                    
                    # Update consumer - reduce grid import need
                    consumer_result["P_from_grid_load_kw"] -= transfer_kw
                    consumer_result["P_internal_import_kw"] = consumer_result.get("P_internal_import_kw", 0) + transfer_kw
                    
                    # Calculate trade value
                    energy_kwh = transfer_kw * dt_h
                    total_value = energy_kwh * selling_price
                    
                    # Record trade with per-house pricing
                    internal_trades.append({
                        "from_house_id": producer_result["house_id"],
                        "to_house_id": consumer_result["house_id"],
                        "power_kw": transfer_kw,
                        "energy_kwh": energy_kwh,
                        "price_per_kwh": selling_price,
                        "total_value_lei": total_value,
                        "grid_price_per_kwh": price_t,
                        "savings_lei": energy_kwh * (price_t - selling_price)
                    })
                    
                    P_internal_traded_kw += transfer_kw
                    remaining_need -= transfer_kw
    
    # Step 4: After P2P - charge batteries with remaining surplus, then grid export
    P_grid_export_total_kw = 0.0
    for producer in producers:
        remaining_surplus = producer["available_surplus"]
        house = producer["house"]
        result = producer["result"]
        
        if remaining_surplus > 0:
            # First, charge battery with remaining surplus (if battery has space)
            battery_space = result.get("battery_space_kw", 0)
            if battery_space > 0 and house.battery:
                charge_kw = min(remaining_surplus, battery_space)
                house.battery.charge(charge_kw, dt_h)
                result["P_to_batt_from_pv_kw"] = result.get("P_to_batt_from_pv_kw", 0) + charge_kw
                result["battery_soc_kwh"] = house.battery.soc_kwh
                result["battery_soc_percent"] = house.battery.get_soc_percent()
                remaining_surplus -= charge_kw
            
            # Then, export remaining to grid
            if remaining_surplus > 0:
                export_kw = min(remaining_surplus, vpp.p_grid_export_max_kw - P_grid_export_total_kw)
                result["P_to_grid_export_kw"] = export_kw
                result["surplus_after_grid_kw"] = remaining_surplus - export_kw
                P_grid_export_total_kw += export_kw
            else:
                result["P_to_grid_export_kw"] = 0
                result["surplus_after_grid_kw"] = 0
    
    # Step 5: Apply global grid import limits
    P_grid_import_total_kw = sum(r["P_from_grid_load_kw"] + r["P_to_grid_charge_kw"] for r in house_results)
    if P_grid_import_total_kw > vpp.p_grid_import_max_kw:
        scale_factor = vpp.p_grid_import_max_kw / P_grid_import_total_kw
        for result in house_results:
            result["P_from_grid_load_kw"] *= scale_factor
            result["P_to_grid_charge_kw"] *= scale_factor
        P_grid_import_total_kw = vpp.p_grid_import_max_kw
    
    # Step 6: Curtailment (any remaining surplus that couldn't be used)
    P_curtailment_total_kw = 0.0
    for result in house_results:
        if result.get("surplus_after_grid_kw", 0) > 0:
            result["curtailment_kw"] = result["surplus_after_grid_kw"]
            P_curtailment_total_kw += result["curtailment_kw"]
            result["surplus_after_grid_kw"] = 0  # Mark as handled
    
    # Step 7: Aggregate results
    consum_net_kw = P_total_load_kw - P_total_pv_kw
    
    # Determine neighborhood state
    if consum_net_kw > 500:  # Threshold for "high consumption"
        neighborhood_state = "consum ridicat"
    else:
        neighborhood_state = "consum scăzut"
    
    # Recalculate actual grid import after internal trading
    P_grid_import_after_trading = sum(r["P_from_grid_load_kw"] + r["P_to_grid_charge_kw"] for r in house_results)
    
    return {
        "timestamp": None,  # Will be set by caller
        "price_per_kwh": price_t,
        "dt_hours": dt_h,
        
        # Aggregates
        "P_total_pv_kw": round(P_total_pv_kw, 2),
        "P_total_load_kw": round(P_total_load_kw, 2),
        "consum_net_kw": round(consum_net_kw, 2),
        "neighborhood_state": neighborhood_state,
        
        # Grid interactions
        "P_grid_import_kw": round(P_grid_import_after_trading, 2),
        "P_grid_export_kw": round(P_grid_export_total_kw, 2),
        
        # Internal P2P trading
        "P_internal_traded_kw": round(P_internal_traded_kw, 2),
        "internal_trades_count": len(internal_trades),
        "internal_trades": internal_trades,
        "total_p2p_value_lei": round(sum(t.get("total_value_lei", 0) for t in internal_trades), 2),
        "total_p2p_savings_lei": round(sum(t.get("savings_lei", 0) for t in internal_trades), 2),
        
        # Curtailment
        "P_curtailment_total_kw": round(P_curtailment_total_kw, 2),
        
        # Battery stats
        "total_battery_soc_kwh": round(sum(r["battery_soc_kwh"] for r in house_results), 2),
        "avg_battery_soc_percent": round(
            sum(r["battery_soc_percent"] for r in house_results if r["battery_soc_percent"] > 0) / 
            len([r for r in house_results if r["battery_soc_percent"] > 0])
            if any(r["battery_soc_percent"] > 0 for r in house_results) else 0,
            1
        ),
        
        # Individual house results
        "houses": house_results
    }
