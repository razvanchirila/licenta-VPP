"""Database initialization and seeding script for VPP Simulator."""
import asyncio
import logging
import random
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .database import init_db, get_session_context, close_db
from .models import (
    HouseModel, BatteryModel, DeviceModel,
    TradingPreferencesModel, WalletModel, VPPReserveModel
)
from .repositories import HouseRepository, DeviceRepository

logger = logging.getLogger(__name__)


# Default device templates - NO LONGER USED (devices are added manually by users)
# Kept for reference only
DEFAULT_DEVICES = [
    {"name": "Frigider", "power_w": 150.0, "critical": True, "status_on": True},
    {"name": "Router", "power_w": 10.0, "critical": True, "status_on": True},
    {"name": "TV", "power_w": 100.0, "critical": False, "status_on": False},
    {"name": "Mașină spălat", "power_w": 1500.0, "critical": False, "status_on": False},
    {"name": "Iluminat", "power_w": 200.0, "critical": False, "status_on": False},
]


async def seed_houses(
    session: AsyncSession,
    num_houses: int = 10,
    houses_with_battery_ratio: float = 0.8,
    create_default_devices: bool = False  # NEW: disabled by default
) -> List[HouseModel]:
    """
    Seed the database with initial houses and batteries only.
    Devices are NOT created automatically - users add them manually.
    
    Args:
        session: Database session
        num_houses: Number of houses to create
        houses_with_battery_ratio: Ratio of houses with batteries
        create_default_devices: If True, create default devices (disabled by default)
    
    Returns:
        List of created house models
    """
    house_repo = HouseRepository(session)
    
    # Check if houses already exist - NEVER overwrite existing data
    existing_houses = await house_repo.get_all()
    if existing_houses:
        logger.info(f"Database already has {len(existing_houses)} houses, preserving existing data")
        return existing_houses
    
    num_with_battery = int(num_houses * houses_with_battery_ratio)
    houses = []
    
    logger.info(f"Seeding {num_houses} houses ({num_with_battery} with batteries), NO default devices...")

    for i in range(1, num_houses + 1):
        # Create house
        house = HouseModel(
            id=i,
            name=f"Casa {i}",
            mode=random.choice(["Eco", "Profit"]),
            has_pv=True,
            pv_capacity_kw=10.0
        )
        session.add(house)
        await session.flush()
        
        # Create battery if in the first N houses
        if i <= num_with_battery:
            battery = BatteryModel(
                house_id=house.id,
                capacity_kwh=20.0,
                soc_kwh=10.0,  # 50% initial SOC
                soc_min_kwh=4.0,  # 20% of capacity
                soc_max_kwh=20.0,
                p_ch_max_kw=5.0,
                p_dis_max_kw=5.0
            )
            session.add(battery)
        
        # Create default trading preferences for P2P trading
        trading_prefs = TradingPreferencesModel(
            house_id=house.id,
            selling_enabled=True,
            buying_enabled=True,
            price_mode="discount",
            fixed_price_lei_kwh=None,
            discount_percent=20.0,
            min_sell_price_lei_kwh=0.0
        )
        session.add(trading_prefs)
        
        # Create wallet for P2P trading credits
        wallet = WalletModel(
            house_id=house.id,
            balance_lei=0.0,
            total_earned_lei=0.0,
            total_spent_lei=0.0,
            transaction_count=0,
            is_flagged=False
        )
        session.add(wallet)
        
        # Create VPP reserve entry
        vpp_reserve = VPPReserveModel(
            house_id=house.id,
            reserved_kwh=0.0,
            base_rate_lei_kwh=0.5,
            pending_bonus_lei=0.0
        )
        session.add(vpp_reserve)
        
        # Only create default devices if explicitly requested
        if create_default_devices:
            for idx, device_template in enumerate(DEFAULT_DEVICES, start=1):
                device = DeviceModel(
                    house_id=house.id,
                    name=device_template["name"],
                    power_w=device_template["power_w"],
                    critical=device_template["critical"],
                    status_on=device_template["status_on"],
                    accumulated_energy_kwh=0.0,
                    last_state_change_ts=None
                )
                session.add(device)
        
        houses.append(house)
        
        # Log progress every 100 houses
        if i % 100 == 0:
            logger.info(f"Created {i}/{num_houses} houses...")
    
    await session.flush()
    logger.info(f"Successfully seeded {num_houses} houses (devices: {'yes' if create_default_devices else 'no'})")
    
    return houses


async def clear_all_data(session: AsyncSession) -> None:
    """Clear all data from the database (for testing/reset)."""
    from sqlalchemy import text
    
    # Delete in order to respect foreign keys
    await session.execute(text("DELETE FROM wallet_transactions"))
    await session.execute(text("DELETE FROM trade_transactions"))
    await session.execute(text("DELETE FROM wallets"))
    await session.execute(text("DELETE FROM trading_preferences"))
    await session.execute(text("DELETE FROM vpp_reserve"))
    await session.execute(text("DELETE FROM energy_logs"))
    await session.execute(text("DELETE FROM devices"))
    await session.execute(text("DELETE FROM batteries"))
    await session.execute(text("DELETE FROM houses"))
    await session.flush()
    logger.info("Cleared all data from database")


async def initialize_database(
    num_houses: int = 10,
    houses_with_battery_ratio: float = 0.8,
    force_reseed: bool = False
) -> None:
    """
    Initialize database and seed with initial data.
    
    Args:
        num_houses: Number of houses to create
        houses_with_battery_ratio: Ratio of houses with batteries
        force_reseed: If True, clear existing data and reseed
    """
    # Create tables
    await init_db()
    
    async with get_session_context() as session:
        if force_reseed:
            await clear_all_data(session)
        
        await seed_houses(
            session,
            num_houses=num_houses,
            houses_with_battery_ratio=houses_with_battery_ratio
        )


def run_init_sync(
    num_houses: int = 10,
    houses_with_battery_ratio: float = 0.8,
    force_reseed: bool = False
) -> None:
    """Synchronous wrapper for database initialization."""
    asyncio.run(initialize_database(
        num_houses=num_houses,
        houses_with_battery_ratio=houses_with_battery_ratio,
        force_reseed=force_reseed
    ))


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Parse command line arguments
    force = "--force" in sys.argv
    num_houses = 10  # Default: 10 houses (8 with batteries)
    
    for arg in sys.argv[1:]:
        if arg.startswith("--houses="):
            num_houses = int(arg.split("=")[1])
    
    print(f"Initializing database with {num_houses} houses...")
    run_init_sync(num_houses=num_houses, force_reseed=force)
    print("Done!")
