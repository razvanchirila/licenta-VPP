"""
VPP Simulator - FastAPI Backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import routes_houses, routes_vpp, routes_sim, routes_config, routes_admin, routes_trading, routes_wallet
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_simulation_state():
    """Load simulation state from database."""
    from app.db.database import get_session_context
    from app.db.models import SimulationStateModel
    from sqlalchemy import select
    
    try:
        async with get_session_context() as session:
            result = await session.execute(select(SimulationStateModel).where(SimulationStateModel.id == 1))
            state = result.scalar_one_or_none()
            if state:
                return {
                    "total_steps": state.total_steps,
                    "current_hour": state.current_hour,
                    "sim_datetime": state.sim_datetime
                }
    except Exception as e:
        logger.warning(f"Could not load simulation state: {e}")
    return None


async def save_simulation_state():
    """Save current simulation state to database."""
    from app.db.database import get_session_context
    from app.db.models import SimulationStateModel
    from app.services.simulation_loop import simulation_loop
    from sqlalchemy import select
    
    try:
        async with get_session_context() as session:
            result = await session.execute(select(SimulationStateModel).where(SimulationStateModel.id == 1))
            state = result.scalar_one_or_none()
            
            if state:
                state.total_steps = simulation_loop.total_steps
                state.current_hour = simulation_loop.clock.hour
                state.sim_datetime = simulation_loop.clock.sim_datetime
            else:
                state = SimulationStateModel(
                    id=1,
                    total_steps=simulation_loop.total_steps,
                    current_hour=simulation_loop.clock.hour,
                    sim_datetime=simulation_loop.clock.sim_datetime
                )
                session.add(state)
            
            await session.flush()
            logger.info(f"Saved simulation state: step {state.total_steps}, hour {state.current_hour}")
    except Exception as e:
        logger.warning(f"Could not save simulation state: {e}")


async def load_vpp_from_db():
    """Load VPP state from database into memory, preserving simulation progress."""
    from app.api.state import vpp_state
    from app.models.vpp import VPP
    from app.models.house import House
    from app.models.battery import Battery
    from app.models.device import Device
    from app.db.database import get_session_context
    from app.db.repositories import HouseRepository
    from app.sim.generator import generate_vpp_profiles_24h
    from app.services.simulation_loop import simulation_loop
    
    # Load saved simulation state first
    saved_state = await load_simulation_state()
    
    async with get_session_context() as session:
        house_repo = HouseRepository(session)
        db_houses = await house_repo.get_all_with_relations()
        
        if not db_houses:
            logger.warning("No houses in database")
            return False
        
        # Create VPP from DB data
        vpp = VPP()
        
        for db_house in db_houses:
            # Create Battery if exists - USE ACTUAL SOC FROM DB
            battery = None
            if db_house.battery:
                battery = Battery(
                    capacity_kwh=db_house.battery.capacity_kwh,
                    soc_min_ratio=db_house.battery.soc_min_kwh / db_house.battery.capacity_kwh,
                    p_ch_max_kw=db_house.battery.p_ch_max_kw,
                    p_dis_max_kw=db_house.battery.p_dis_max_kw,
                    initial_soc_ratio=1.0  # Will be overwritten below
                )
                # Set actual SOC from DB (not initial ratio)
                battery.soc_kwh = db_house.battery.soc_kwh
                logger.info(f"House {db_house.id}: Loaded battery SOC {battery.soc_kwh:.2f} kWh ({battery.get_soc_percent():.1f}%)")
            
            # Load trading preferences if available
            selling_enabled = True
            buying_enabled = True
            trading_price_mode = "discount"
            trading_fixed_price = None
            trading_discount_percent = 20.0
            
            if db_house.trading_preferences:
                tp = db_house.trading_preferences
                selling_enabled = tp.selling_enabled
                buying_enabled = tp.buying_enabled
                trading_price_mode = tp.price_mode
                trading_fixed_price = tp.fixed_price_lei_kwh
                trading_discount_percent = tp.discount_percent
            
            # Create House with trading settings
            house = House(
                id=db_house.id,
                battery=battery,
                mode=db_house.mode,
                has_pv=db_house.has_pv,
                pv_capacity_kw=db_house.pv_capacity_kw,
                selling_enabled=selling_enabled,
                buying_enabled=buying_enabled,
                trading_price_mode=trading_price_mode,
                trading_fixed_price=trading_fixed_price,
                trading_discount_percent=trading_discount_percent
            )
            
            # Add devices with their current state from DB
            active_count = 0
            for db_device in db_house.devices:
                device = Device(
                    id=db_device.id,
                    name=db_device.name,
                    power_w=db_device.power_w,
                    critical=db_device.critical,
                    status_on=db_device.status_on,
                    last_state_change_ts=db_device.last_state_change_ts,
                    accumulated_energy_kwh=db_device.accumulated_energy_kwh
                )
                house.add_device(device)
                if device.status_on:
                    active_count += 1
            
            logger.info(f"House {db_house.id}: {active_count}/{len(db_house.devices)} devices ON, consumption {house.compute_L_crit_kw() + house.compute_L_noncrit_kw():.3f} kW")
            vpp.add_house(house)
        
        # Generate profiles (these are regenerated each startup - could be cached)
        profiles = generate_vpp_profiles_24h(num_houses=len(db_houses), use_opcom=False)
        
        # Update state
        vpp_state.vpp = vpp
        vpp_state.profiles = profiles
        
        # Restore simulation state from DB if available
        if saved_state:
            simulation_loop.set_total_steps(saved_state["total_steps"])
            vpp_state.current_hour = saved_state["current_hour"]
            logger.info(f"Restored simulation state: step {saved_state['total_steps']}, hour {saved_state['current_hour']}")
        else:
            vpp_state.current_hour = 0
            vpp_state.simulation_history = []
        
        logger.info(f"Loaded {len(db_houses)} houses from database into VPP")
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI - handles startup and shutdown."""
    # Startup: Initialize database
    logger.info("Starting VPP Simulator...")
    try:
        from app.db import init_db
        await init_db()
        logger.info("Database tables created/verified")
        
        # Seed data if database is empty
        from app.db.database import get_session_context
        from app.db.repositories import HouseRepository
        async with get_session_context() as session:
            house_repo = HouseRepository(session)
            houses = await house_repo.get_all()
            if not houses:
                logger.info("No houses found, seeding initial data...")
                from app.db.init_data import seed_houses
                await seed_houses(session)
                logger.info("Initial data seeded successfully")
            else:
                logger.info(f"Database has {len(houses)} houses")
        
        # Load VPP from database
        await load_vpp_from_db()
        
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Start simulation loop
    try:
        from app.services import simulation_loop
        await simulation_loop.start()
        logger.info("Simulation loop started (5s interval)")
    except Exception as e:
        logger.warning(f"Failed to start simulation loop: {e}")
    
    yield  # Application runs here
    
    # Shutdown: Save state, stop simulation loop and close database
    logger.info("Shutting down VPP Simulator...")
    
    # Save simulation state before stopping
    try:
        await save_simulation_state()
    except Exception as e:
        logger.warning(f"Error saving simulation state: {e}")
    
    try:
        from app.services import simulation_loop
        await simulation_loop.stop()
        logger.info("Simulation loop stopped")
    except Exception as e:
        logger.warning(f"Error stopping simulation loop: {e}")
    
    try:
        from app.db import close_db
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")


# Create FastAPI app with lifespan
app = FastAPI(
    title="VPP Simulator API",
    description="Virtual Power Plant Simulator - Energy Management System",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_houses.router, prefix="/api")
app.include_router(routes_vpp.router, prefix="/api")
app.include_router(routes_sim.router, prefix="/api")
app.include_router(routes_config.router, prefix="/api")
app.include_router(routes_admin.router, prefix="/api")
app.include_router(routes_trading.router, prefix="/api")
app.include_router(routes_wallet.router, prefix="/api")


# Mount static files (dashboard)
dashboard_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/static", StaticFiles(directory=dashboard_path), name="static")


@app.get("/")
def root():
    """Serve dashboard or API info"""
    dashboard_index = os.path.join(dashboard_path, "index.html")
    if os.path.exists(dashboard_index):
        return FileResponse(dashboard_index)
    
    return {
        "name": "VPP Simulator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "houses": "/api/houses",
            "vpp": "/api/vpp",
            "simulation": "/api/sim",
            "docs": "/docs",
            "dashboard": "/"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.api.state import vpp_state
    from app.services.simulation_loop import simulation_loop
    
    # Check database connection
    db_status = "unknown"
    db_houses = 0
    try:
        from app.db.database import get_session_context
        from app.db.repositories import HouseRepository
        async with get_session_context() as session:
            house_repo = HouseRepository(session)
            houses = await house_repo.get_all()
            db_houses = len(houses)
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get simulation clock info
    clock_info = simulation_loop.clock.to_dict() if simulation_loop.clock else {}
    
    return {
        "status": "healthy",
        "vpp_initialized": vpp_state.vpp is not None,
        "profiles_loaded": vpp_state.profiles is not None,
        "current_hour": vpp_state.current_hour,
        "simulation_steps": simulation_loop.total_steps,
        "sim_clock": clock_info,
        "database": {
            "status": db_status,
            "houses_in_db": db_houses
        }
    }


if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Check if running in development mode
    dev_mode = "--dev" in sys.argv
    
    uvicorn.run(
        "main:app" if dev_mode else app,
        host="0.0.0.0",
        port=8000,
        reload=dev_mode  # Auto-reload on file changes in dev mode
    )
