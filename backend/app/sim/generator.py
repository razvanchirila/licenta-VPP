"""
Data generator - creates realistic profiles for PV production, consumption, and prices
"""
import math
import random
from typing import List, Tuple


def generate_price_profile_24h(
    base_price: float = 1.0,
    night_discount: float = 0.6,
    peak_multiplier: float = 1.5
) -> List[float]:
    """
    Generate 24-hour electricity price profile
    
    Prices are:
    - Low during night (0-6h): 60% of base
    - Normal during day (7-17h): 100% of base
    - High during evening peak (18-22h): 150% of base
    - Medium late night (23h): 80% of base
    
    Args:
        base_price: Base price in lei/kWh (default ~1.0 lei/kWh)
        night_discount: Discount multiplier for night hours
        peak_multiplier: Multiplier for peak hours
    
    Returns:
        List of 24 hourly prices in lei/kWh
    """
    prices = []
    for hour in range(24):
        if 0 <= hour < 6:
            # Night - cheap
            price = base_price * night_discount
        elif 6 <= hour < 7:
            # Morning transition
            price = base_price * 0.8
        elif 7 <= hour < 17:
            # Day - normal
            price = base_price
        elif 17 <= hour < 18:
            # Evening ramp-up
            price = base_price * 1.2
        elif 18 <= hour < 23:
            # Evening peak - expensive
            price = base_price * peak_multiplier
        else:  # 23h
            # Late night transition
            price = base_price * 0.8
        
        # Add small random variation (±5%)
        price *= (1.0 + random.uniform(-0.05, 0.05))
        prices.append(round(price, 4))
    
    return prices


def generate_pv_profile_24h(
    pv_capacity_kw: float = 10.0,
    peak_hour: int = 13,
    sunrise_hour: int = 7,
    sunset_hour: int = 19,
    weather_factor: float = 1.0
) -> List[float]:
    """
    Generate 24-hour PV production profile
    
    Uses a sine curve to simulate solar production:
    - Zero at night
    - Peaks around 13:00
    - Gradual ramp up and down
    
    Args:
        pv_capacity_kw: PV system capacity in kW
        peak_hour: Hour of maximum production
        sunrise_hour: Hour when sun rises
        sunset_hour: Hour when sun sets
        weather_factor: Weather multiplier (0.0-1.0, where 1.0 is perfect sun)
    
    Returns:
        List of 24 hourly production values (kW)
    """
    production = []
    daylight_hours = sunset_hour - sunrise_hour
    
    for hour in range(24):
        if hour < sunrise_hour or hour >= sunset_hour:
            # Night - no production
            power = 0.0
        else:
            # Day - sine curve
            # Map hour to 0-π range
            hour_in_day = hour - sunrise_hour
            angle = (hour_in_day / daylight_hours) * math.pi
            
            # Sine curve (0 at sunrise/sunset, peak at noon)
            normalized_power = math.sin(angle)
            
            # Apply capacity and weather
            power = pv_capacity_kw * normalized_power * weather_factor
            
            # Add small random variation (±10%)
            power *= (1.0 + random.uniform(-0.10, 0.10))
            power = max(0, power)  # Ensure non-negative
        
        production.append(round(power, 3))
    
    return production


def generate_load_profile_house_24h(
    base_critical_kw: float = 0.5,
    base_noncritical_kw: float = 1.5
) -> Tuple[List[float], List[float]]:
    """
    Generate 24-hour load profile for a house
    
    Returns separate profiles for critical and non-critical loads
    
    Critical load (always on): fridges, routers, minimal lighting
    - Relatively constant throughout day
    - Small variations
    
    Non-critical load: TV, washing machine, extra lighting, cooking
    - Low at night
    - Moderate during day
    - High in morning (7-9h) and evening (18-22h)
    
    Args:
        base_critical_kw: Base critical load (kW)
        base_noncritical_kw: Base non-critical load (kW)
    
    Returns:
        Tuple of (L_crit_24h, L_noncrit_24h) lists
    """
    L_crit = []
    L_noncrit = []
    
    for hour in range(24):
        # Critical load - mostly constant with small variation
        crit = base_critical_kw * (1.0 + random.uniform(-0.15, 0.15))
        L_crit.append(round(crit, 3))
        
        # Non-critical load - varies by time of day
        if 0 <= hour < 6:
            # Night - very low (people sleeping)
            noncrit = base_noncritical_kw * 0.2
        elif 6 <= hour < 9:
            # Morning peak (breakfast, preparation)
            noncrit = base_noncritical_kw * 1.5
        elif 9 <= hour < 17:
            # Day - moderate (some people at home)
            noncrit = base_noncritical_kw * 0.8
        elif 17 <= hour < 23:
            # Evening peak (cooking, entertainment)
            noncrit = base_noncritical_kw * 1.8
        else:  # 23h
            # Late evening
            noncrit = base_noncritical_kw * 0.6
        
        # Add variation
        noncrit *= (1.0 + random.uniform(-0.20, 0.20))
        noncrit = max(0, noncrit)
        L_noncrit.append(round(noncrit, 3))
    
    return L_crit, L_noncrit


def generate_weather_factor() -> float:
    """
    Generate a random weather factor for PV production
    
    Returns:
        Weather factor between 0.3 (very cloudy) and 1.0 (perfect sun)
    """
    # Most days are decent (0.7-1.0), some are cloudy
    if random.random() < 0.8:
        # Good weather
        return random.uniform(0.7, 1.0)
    else:
        # Poor weather
        return random.uniform(0.3, 0.7)


def generate_vpp_profiles_24h(num_houses: int = 10, use_opcom: bool = False) -> dict:
    """
    Generate profiles for all houses in the VPP for 24 hours
    
    Args:
        num_houses: Number of houses in the neighborhood
        use_opcom: If True, fetch real prices from OPCOM API. If False, generate synthetic prices.
    
    Returns:
        Dictionary with:
        - prices_24h: List of 24 hourly prices
        - pv_profiles: Dict mapping house_id to 24 PV values
        - load_profiles: Dict mapping house_id to tuple of (L_crit_24h, L_noncrit_24h)
        - price_source: "OPCOM" or "Generated"
    """
    # Get price profile - either from OPCOM or generated
    price_source = "Generated"
    if use_opcom:
        try:
            from app.sim.opcom import fetch_opcom_prices
            prices_24h = fetch_opcom_prices()
            price_source = "OPCOM"
        except Exception as e:
            # Fallback to generated prices if OPCOM fails
            print(f"Warning: Failed to fetch OPCOM prices ({str(e)}), using generated prices instead")
            prices_24h = generate_price_profile_24h()
    else:
        prices_24h = generate_price_profile_24h()
    
    # Generate weather (same for all houses in neighborhood)
    weather = generate_weather_factor()
    
    # Generate individual profiles for each house
    pv_profiles = {}
    load_profiles = {}
    
    for house_id in range(1, num_houses + 1):
        # PV profile (10 kW capacity, same weather)
        pv_profiles[house_id] = generate_pv_profile_24h(
            pv_capacity_kw=10.0,
            weather_factor=weather
        )
        
        # Load profile (with some variation between houses)
        base_crit = random.uniform(0.4, 0.7)  # 400-700W
        base_noncrit = random.uniform(1.2, 2.0)  # 1.2-2.0 kW
        load_profiles[house_id] = generate_load_profile_house_24h(
            base_critical_kw=base_crit,
            base_noncritical_kw=base_noncrit
        )
    
    return {
        "prices_24h": prices_24h,
        "pv_profiles": pv_profiles,
        "load_profiles": load_profiles,
        "weather_factor": weather,
        "price_source": price_source
    }
