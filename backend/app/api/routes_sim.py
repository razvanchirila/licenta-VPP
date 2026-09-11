"""
Simulation API routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/sim", tags=["simulation"])


class SimStepRequest(BaseModel):
    hour: Optional[int] = None  # If not provided, will use next hour
    price: Optional[float] = None  # If not provided, will use generated price


@router.get("/opcom-prices")
def get_opcom_prices(date: Optional[str] = None):
    """
    Get real electricity prices from OPCOM (Romanian energy market)
    
    Args:
        date: Date in format DD/MM/YYYY. If not provided, uses today's date.
    
    Returns:
        Dictionary with price data including both lei/MWh and lei/kWh formats
    """
    from app.sim.opcom import fetch_opcom_prices_raw
    
    try:
        if date:
            # Parse date from DD/MM/YYYY format
            date_parts = date.split('/')
            if len(date_parts) != 3:
                raise ValueError("Date must be in DD/MM/YYYY format")
            day, month, year = map(int, date_parts)
            date_obj = datetime(year, month, day)
        else:
            date_obj = None  # Use today
        
        prices_data = fetch_opcom_prices_raw(date_obj)
        
        return {
            "success": True,
            "data": prices_data,
            "message": f"OPCOM prices fetched successfully for {prices_data['date']}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch OPCOM prices: {str(e)}"
        )


@router.post("/step")
def simulate_step(request: SimStepRequest = None):
    """
    Run one simulation step (1 hour)
    
    This simulates energy flow for all houses for the current hour
    """
    from app.api.state import vpp_state
    from app.sim.vpp_step import simulate_vpp_step
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    if not vpp_state.profiles:
        raise HTTPException(status_code=400, detail="No profiles generated. Call /sim/init first")
    
    request = request or SimStepRequest()
    
    # Determine current hour
    if request.hour is not None:
        current_hour = request.hour % 24
    else:
        current_hour = vpp_state.current_hour
    
    # Get price for this hour
    if request.price is not None:
        price_t = request.price
    else:
        price_t = vpp_state.profiles["prices_24h"][current_hour]
    
    # Get PV production for all houses
    pv_profile_kw = {}
    for house in vpp_state.vpp.houses:
        pv_profile_kw[house.id] = vpp_state.profiles["pv_profiles"][house.id][current_hour]
    
    # Run simulation
    result = simulate_vpp_step(
        vpp=vpp_state.vpp,
        pv_profile_kw=pv_profile_kw,
        price_t=price_t,
        dt_h=1.0
    )
    
    result["timestamp"] = datetime.now().isoformat()
    result["hour"] = current_hour
    
    # Store result
    vpp_state.simulation_history.append(result)
    
    # Advance hour
    vpp_state.current_hour = (current_hour + 1) % 24
    
    return result


@router.post("/day")
def simulate_day():
    """
    Run simulation for a full day (24 hours)
    """
    from app.api.state import vpp_state
    from app.sim.vpp_step import simulate_vpp_step
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    if not vpp_state.profiles:
        raise HTTPException(status_code=400, detail="No profiles generated. Call /sim/init first")
    
    results = []
    
    for hour in range(24):
        price_t = vpp_state.profiles["prices_24h"][hour]
        
        # Get PV production for all houses
        pv_profile_kw = {}
        for house in vpp_state.vpp.houses:
            pv_profile_kw[house.id] = vpp_state.profiles["pv_profiles"][house.id][hour]
        
        # Run simulation
        result = simulate_vpp_step(
            vpp=vpp_state.vpp,
            pv_profile_kw=pv_profile_kw,
            price_t=price_t,
            dt_h=1.0
        )
        
        result["timestamp"] = datetime.now().isoformat()
        result["hour"] = hour
        
        results.append(result)
        vpp_state.simulation_history.append(result)
    
    # Reset to hour 0
    vpp_state.current_hour = 0
    
    return {
        "message": "24-hour simulation completed",
        "results_count": len(results),
        "summary": {
            "total_energy_consumed_kwh": sum(r["P_total_load_kw"] for r in results),
            "total_energy_produced_kwh": sum(r["P_total_pv_kw"] for r in results),
            "total_grid_import_kwh": sum(r["P_grid_import_kw"] for r in results),
            "total_grid_export_kwh": sum(r["P_grid_export_kw"] for r in results),
            "total_internal_trading_kwh": sum(r["P_internal_traded_kw"] for r in results),
            "total_curtailment_kwh": sum(r["P_curtailment_total_kw"] for r in results)
        },
        "hourly_results": results
    }


@router.get("/history")
def get_simulation_history():
    """Get simulation history"""
    from app.api.state import vpp_state
    
    return {
        "history_count": len(vpp_state.simulation_history),
        "current_hour": vpp_state.current_hour,
        "history": vpp_state.simulation_history
    }


@router.post("/reset")
def reset_simulation():
    """Reset simulation state"""
    from app.api.state import vpp_state
    
    vpp_state.current_hour = 0
    vpp_state.simulation_history = []
    
    # Reset all battery SOCs to 50%
    if vpp_state.vpp:
        for house in vpp_state.vpp.houses:
            if house.battery:
                house.battery.soc_kwh = house.battery.capacity_kwh * 0.5
    
    return {"message": "Simulation reset successfully"}


class SpeedRequest(BaseModel):
    interval_seconds: float = 5.0


@router.post("/speed")
def set_simulation_speed(request: SpeedRequest):
    """Change simulation speed (interval between steps in seconds)."""
    from app.services.simulation_loop import simulation_loop
    
    simulation_loop.set_speed(request.interval_seconds)
    return {
        "message": f"Speed set to {simulation_loop.interval_seconds}s",
        "interval_seconds": simulation_loop.interval_seconds
    }


@router.post("/pause")
def pause_simulation():
    """Pause the simulation loop."""
    from app.services.simulation_loop import simulation_loop
    
    simulation_loop.pause()
    return {"message": "Simulation paused", "paused": True}


@router.post("/resume")
def resume_simulation():
    """Resume the simulation loop."""
    from app.services.simulation_loop import simulation_loop
    
    simulation_loop.resume()
    return {"message": "Simulation resumed", "paused": False}


@router.get("/status")
def get_simulation_status():
    """Get current simulation loop status."""
    from app.services.simulation_loop import simulation_loop
    
    return simulation_loop.get_status()


@router.post("/init")
def initialize_simulation(num_houses: int = 10, houses_with_battery_ratio: float = 0.8, use_opcom_prices: bool = False):
    """
    Initialize VPP with houses and generate profiles
    
    Args:
        num_houses: Number of houses to create (default 10)
        houses_with_battery_ratio: Ratio of houses with batteries (default 0.8 = 8/10)
        use_opcom_prices: If True, fetch real prices from OPCOM API (default False)
    """
    from app.api.state import vpp_state
    from app.models.vpp import VPP
    from app.models.house import House
    from app.models.battery import Battery
    from app.models.device import Device
    from app.sim.generator import generate_vpp_profiles_24h
    import random
    
    # Create VPP
    vpp = VPP()
    
    # Calculate how many houses have batteries
    num_with_battery = int(num_houses * houses_with_battery_ratio)
    
    # Create houses
    for i in range(1, num_houses + 1):
        # Create battery if in the first N houses
        battery = Battery() if i <= num_with_battery else None
        
        # Create house
        house = House(
            id=i,
            battery=battery,
            mode=random.choice(["Eco", "Profit"]),
            has_pv=True,
            pv_capacity_kw=10.0
        )
        
        # Add some default devices
        devices = [
            Device(id=1, name="Frigider", power_w=150, critical=True, status_on=True),
            Device(id=2, name="Router", power_w=10, critical=True, status_on=True),
            Device(id=3, name="TV", power_w=100, critical=False, status_on=False),
            Device(id=4, name="Mașină spălat", power_w=1500, critical=False, status_on=False),
            Device(id=5, name="Iluminat", power_w=200, critical=False, status_on=False),
        ]
        
        for device in devices:
            house.add_device(device)
        
        vpp.add_house(house)
    
    # Generate profiles (with optional OPCOM prices)
    profiles = generate_vpp_profiles_24h(num_houses=num_houses, use_opcom=use_opcom_prices)
    
    # Update state
    vpp_state.vpp = vpp
    vpp_state.profiles = profiles
    vpp_state.current_hour = 0
    vpp_state.simulation_history = []
    
    return {
        "message": f"VPP initialized with {num_houses} houses",
        "houses_with_battery": num_with_battery,
        "houses_without_battery": num_houses - num_with_battery,
        "profiles_generated": True,
        "weather_factor": profiles["weather_factor"],
        "price_source": profiles.get("price_source", "Generated"),
        "vpp_state": vpp.to_dict()
    }
