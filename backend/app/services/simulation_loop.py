"""Simulation Loop Service - runs VPP simulation with internal simulation clock."""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Callable

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SimulationClock:
    """
    Internal simulation clock.
    
    Maps real time to simulation time:
    - 5 seconds real = 10 minutes simulation (configurable)
    - Tracks simulation datetime independently
    """
    
    def __init__(
        self,
        start_datetime: Optional[datetime] = None,
        sim_minutes_per_step: int = 10
    ):
        # Start at midnight today if not specified
        if start_datetime is None:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_datetime = today
        
        self.sim_datetime = start_datetime
        self.sim_minutes_per_step = sim_minutes_per_step  # 10 min sim per 5 sec real
        self.total_sim_minutes = 0
    
    def advance(self) -> datetime:
        """Advance simulation clock by one step (10 minutes)."""
        self.sim_datetime += timedelta(minutes=self.sim_minutes_per_step)
        self.total_sim_minutes += self.sim_minutes_per_step
        return self.sim_datetime
    
    @property
    def hour(self) -> int:
        """Current simulation hour (0-23)."""
        return self.sim_datetime.hour
    
    @property
    def minute(self) -> int:
        """Current simulation minute (0-59)."""
        return self.sim_datetime.minute
    
    @property
    def time_str(self) -> str:
        """Current simulation time as HH:MM string."""
        return self.sim_datetime.strftime("%H:%M")
    
    @property
    def datetime_str(self) -> str:
        """Current simulation datetime as ISO string."""
        return self.sim_datetime.isoformat()
    
    @property
    def dt_hours(self) -> float:
        """Time delta in hours for energy calculations."""
        return self.sim_minutes_per_step / 60.0  # 10 min = 0.1667 hours
    
    def to_dict(self) -> dict:
        """Get clock state as dictionary."""
        return {
            "sim_datetime": self.datetime_str,
            "sim_time": self.time_str,
            "sim_hour": self.hour,
            "sim_minute": self.minute,
            "total_sim_minutes": self.total_sim_minutes,
            "sim_minutes_per_step": self.sim_minutes_per_step,
            "dt_hours": round(self.dt_hours, 4)
        }



class SimulationLoop:
    """
    Background service that runs VPP simulation with internal clock.
    
    Configuration:
    - interval_seconds: Real time between steps (default 5s)
    - sim_minutes_per_step: Simulation minutes per step (default 10 min)
    
    This means: every 5 real seconds, 10 simulation minutes pass.
    So 1 real hour = 120 simulation hours (5 simulation days).
    """
    
    def __init__(
        self,
        interval_seconds: float = 5.0,
        sim_minutes_per_step: int = 10
    ):
        self.interval_seconds = interval_seconds
        self.sim_minutes_per_step = sim_minutes_per_step
        
        self.running = False
        self.paused = False
        self.total_steps = 0
        self.last_step_time: Optional[float] = None
        self.last_result: Optional[dict] = None
        
        # Internal simulation clock
        self.clock = SimulationClock(sim_minutes_per_step=sim_minutes_per_step)
        
        self._task: Optional[asyncio.Task] = None
        self._websocket_clients: List[WebSocket] = []
        self._on_step_callbacks: List[Callable] = []
    
    async def start(self):
        """Start the simulation loop."""
        if self.running:
            logger.warning("Simulation loop already running")
            return
        
        self.running = True
        self.paused = False
        logger.info(
            f"Starting simulation loop: {self.interval_seconds}s real = "
            f"{self.sim_minutes_per_step} min simulation"
        )
        
        self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        """Stop the simulation loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Simulation loop stopped")
    
    def pause(self):
        """Pause the simulation loop."""
        self.paused = True
        logger.info("Simulation loop paused")
    
    def resume(self):
        """Resume the simulation loop."""
        self.paused = False
        logger.info("Simulation loop resumed")
    
    def set_speed(self, seconds: float):
        """Change the real-time interval between steps."""
        self.interval_seconds = max(1.0, min(60.0, seconds))
        logger.info(f"Simulation interval set to {self.interval_seconds}s")
    
    def set_sim_speed(self, minutes_per_step: int):
        """Change how many simulation minutes pass per step."""
        self.sim_minutes_per_step = max(1, min(60, minutes_per_step))
        self.clock.sim_minutes_per_step = self.sim_minutes_per_step
        logger.info(f"Simulation speed set to {self.sim_minutes_per_step} min/step")
    
    async def _run_loop(self):
        """Main loop - executes steps at configured interval."""
        while self.running:
            try:
                if not self.paused:
                    result = await self.execute_step()
                    if result:
                        await self._broadcast_to_clients(result)
                
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                await asyncio.sleep(self.interval_seconds)
    
    async def _sync_from_db(self):
        """
        Sync ALL state FROM database to memory before each simulation step.
        
        This ensures any manual DB changes (via MySQL queries) are reflected
        in the simulation. DB is the source of truth for:
        - House mode (Eco/Profit)
        - Device status (on/off)
        - Device properties (name, power, critical)
        - Battery capacity and limits
        - Trading preferences (selling_enabled, buying_enabled, prices)
        
        Battery SOC is managed by simulation and written TO DB.
        """
        try:
            from app.api.state import vpp_state
            from app.db.database import get_session_context
            from app.db.repositories import HouseRepository
            from app.db.repositories.trading_repository import TradingPreferencesRepository
            from app.models.device import Device as MemDevice
            
            if not vpp_state.vpp:
                return
            
            async with get_session_context() as session:
                house_repo = HouseRepository(session)
                trading_repo = TradingPreferencesRepository(session)
                
                for house in vpp_state.vpp.houses:
                    db_house = await house_repo.get_by_id_with_relations(house.id)
                    if not db_house:
                        continue
                    
                    # Sync house properties from DB
                    house.mode = db_house.mode
                    house.has_pv = db_house.has_pv
                    house.pv_capacity_kw = db_house.pv_capacity_kw
                    
                    # Sync trading preferences from DB
                    trading_prefs = await trading_repo.get_by_house_id(house.id)
                    if trading_prefs:
                        house.selling_enabled = trading_prefs.selling_enabled
                        house.buying_enabled = trading_prefs.buying_enabled
                        house.trading_price_mode = trading_prefs.price_mode
                        house.trading_fixed_price = trading_prefs.fixed_price_lei_kwh
                        house.trading_discount_percent = trading_prefs.discount_percent
                    
                    # Sync battery properties (but NOT soc_kwh - that's simulation controlled)
                    if house.battery and db_house.battery:
                        house.battery.capacity_kwh = db_house.battery.capacity_kwh
                        house.battery.soc_max_kwh = db_house.battery.soc_max_kwh
                        house.battery.soc_min_kwh = db_house.battery.soc_min_kwh
                        house.battery.p_ch_max_kw = db_house.battery.p_ch_max_kw
                        house.battery.p_dis_max_kw = db_house.battery.p_dis_max_kw
                    
                    # Create maps for device sync
                    db_devices_map = {d.id: d for d in db_house.devices}
                    mem_devices_map = {d.id: d for d in house.devices}
                    
                    # Update existing devices from DB
                    for db_device in db_house.devices:
                        if db_device.id in mem_devices_map:
                            mem_device = mem_devices_map[db_device.id]
                            # Sync all properties from DB (DB is source of truth)
                            mem_device.status_on = db_device.status_on
                            mem_device.name = db_device.name
                            mem_device.power_w = db_device.power_w
                            mem_device.critical = db_device.critical
                        else:
                            # New device in DB - add to memory
                            new_device = MemDevice(
                                id=db_device.id,
                                name=db_device.name,
                                power_w=db_device.power_w,
                                critical=db_device.critical,
                                status_on=db_device.status_on,
                                last_state_change_ts=db_device.last_state_change_ts,
                                accumulated_energy_kwh=db_device.accumulated_energy_kwh
                            )
                            house.add_device(new_device)
                            logger.debug(f"Added new device {db_device.id} from DB to house {house.id}")
                    
                    # Remove devices that no longer exist in DB
                    for mem_device_id in list(mem_devices_map.keys()):
                        if mem_device_id not in db_devices_map:
                            house.remove_device(mem_device_id)
                            logger.debug(f"Removed device {mem_device_id} from house {house.id} (deleted from DB)")
                            
        except Exception as e:
            logger.warning(f"Failed to sync from DB: {e}")
    
    async def _persist_p2p_trades(self, internal_trades: list, sim_timestamp: datetime):
        """
        Persist P2P trades to database and update wallets.
        
        Args:
            internal_trades: List of trade dictionaries from vpp_step
            sim_timestamp: Simulation timestamp
        """
        if not internal_trades:
            return
        
        try:
            from app.db.database import get_session_context
            from app.db.repositories.trade_transaction_repository import TradeTransactionRepository
            from app.services.wallet_service import WalletService
            from app.models.trading import TradeTransaction
            
            async with get_session_context() as session:
                trade_repo = TradeTransactionRepository(session)
                wallet_service = WalletService(session)
                
                for trade in internal_trades:
                    seller_id = trade["from_house_id"]
                    buyer_id = trade["to_house_id"]
                    energy_kwh = trade["energy_kwh"]
                    price_per_kwh = trade["price_per_kwh"]
                    total_value = trade["total_value_lei"]
                    grid_price = trade["grid_price_per_kwh"]
                    
                    # Create trade transaction record
                    trade_obj = TradeTransaction(
                        seller_house_id=seller_id,
                        buyer_house_id=buyer_id,
                        energy_kwh=energy_kwh,
                        price_lei_kwh=price_per_kwh,
                        total_value_lei=total_value,
                        grid_price_lei_kwh=grid_price,
                        sim_timestamp=sim_timestamp
                    )
                    await trade_repo.create(trade_obj)
                    
                    # Credit seller wallet
                    await wallet_service.credit_wallet(
                        house_id=seller_id,
                        amount=total_value,
                        description=f"P2P sale to House {buyer_id}: {energy_kwh:.3f} kWh @ {price_per_kwh:.2f} lei/kWh"
                    )
                    
                    # Debit buyer wallet
                    await wallet_service.debit_wallet(
                        house_id=buyer_id,
                        amount=total_value,
                        description=f"P2P purchase from House {seller_id}: {energy_kwh:.3f} kWh @ {price_per_kwh:.2f} lei/kWh"
                    )
                
                logger.info(f"Persisted {len(internal_trades)} P2P trades to database")
                
        except Exception as e:
            logger.warning(f"Failed to persist P2P trades: {e}")


    async def execute_step(self) -> Optional[dict]:
        """
        Execute one simulation step.
        
        Uses internal clock for time calculations:
        - dt_h = sim_minutes_per_step / 60 (e.g., 10/60 = 0.1667 hours)
        - Energy = Power * dt_h
        """
        try:
            from app.api.state import vpp_state
            from app.sim.vpp_step import simulate_vpp_step
            from app.db.database import get_session_context
            from app.db.repositories import HouseRepository, DeviceRepository
            
            if not vpp_state.vpp or not vpp_state.profiles:
                logger.debug("VPP not initialized, skipping step")
                return None
            
            # Sync ALL state FROM database before simulation
            # This ensures any manual DB changes (mode, devices, etc.) are reflected
            await self._sync_from_db()
            
            # Get simulation time
            sim_hour = self.clock.hour
            dt_h = self.clock.dt_hours  # 10 min = 0.1667 hours
            
            # Get price for current hour
            price_t = vpp_state.profiles["prices_24h"][sim_hour]
            
            # Get PV production for current hour (interpolated by minute would be better)
            pv_profile_kw = {}
            for house in vpp_state.vpp.houses:
                pv_profile_kw[house.id] = vpp_state.profiles["pv_profiles"][house.id][sim_hour]
            
            # Run simulation step with correct dt_h
            result = simulate_vpp_step(
                vpp=vpp_state.vpp,
                pv_profile_kw=pv_profile_kw,
                price_t=price_t,
                dt_h=dt_h  # Use simulation time delta
            )
            
            # Add metadata with simulation clock
            result["real_timestamp"] = datetime.now().isoformat()
            result["sim_clock"] = self.clock.to_dict()
            result["step_number"] = self.total_steps
            result["dt_hours"] = dt_h
            
            # Accumulate P2P trades and persist hourly to avoid spamming DB
            if result.get("internal_trades"):
                # Add to pending trades buffer
                if not hasattr(self, '_pending_trades'):
                    self._pending_trades = []
                self._pending_trades.extend(result["internal_trades"])
                
                # Persist at the end of each hour (when minute == 50, next step is new hour)
                if self.clock.minute == 50:
                    # Aggregate trades by seller-buyer pair
                    aggregated = {}
                    for trade in self._pending_trades:
                        key = (trade["from_house_id"], trade["to_house_id"])
                        if key not in aggregated:
                            aggregated[key] = {
                                "from_house_id": trade["from_house_id"],
                                "to_house_id": trade["to_house_id"],
                                "energy_kwh": 0,
                                "total_value_lei": 0,
                                "price_per_kwh": trade["price_per_kwh"],
                                "grid_price_per_kwh": trade["grid_price_per_kwh"],
                            }
                        aggregated[key]["energy_kwh"] += trade["energy_kwh"]
                        aggregated[key]["total_value_lei"] += trade["total_value_lei"]
                    
                    # Persist aggregated trades
                    aggregated_list = list(aggregated.values())
                    if aggregated_list:
                        await self._persist_p2p_trades(aggregated_list, self.clock.sim_datetime)
                    
                    # Clear buffer
                    self._pending_trades = []
            
            # Store in history (keep last 1000)
            vpp_state.simulation_history.append(result)
            if len(vpp_state.simulation_history) > 1000:
                vpp_state.simulation_history = vpp_state.simulation_history[-1000:]
            
            # Persist battery SOC and update device accumulated energy
            # NOTE: energy_logs is populated ONLY on device toggle (event-driven)
            # See user_api/routes/me.py toggle_my_device() for logging
            try:
                async with get_session_context() as session:
                    house_repo = HouseRepository(session)
                    device_repo = DeviceRepository(session)
                    current_sim_time = self.clock.sim_datetime
                    
                    for house in vpp_state.vpp.houses:
                        # Update battery SOC
                        if house.battery:
                            db_house = await house_repo.get_by_id_with_relations(house.id)
                            if db_house and db_house.battery:
                                db_house.battery.soc_kwh = house.battery.soc_kwh
                        
                        # Update accumulated_energy for devices that are ON
                        # This updates the running total but does NOT log to energy_logs
                        for device in house.devices:
                            if device.status_on:
                                db_device = await device_repo.get_by_id(device.id)
                                
                                # If last_state_change_ts is NULL, initialize it now
                                if not device.last_state_change_ts:
                                    device.last_state_change_ts = current_sim_time
                                    if db_device:
                                        db_device.last_state_change_ts = current_sim_time
                                    continue
                                
                                # Calculate energy since last update
                                duration = current_sim_time - device.last_state_change_ts
                                duration_hours = duration.total_seconds() / 3600
                                energy_kwh = device.get_power_kw() * duration_hours
                                
                                if energy_kwh > 0:
                                    # Update in memory
                                    device.accumulated_energy_kwh += energy_kwh
                                    device.last_state_change_ts = current_sim_time
                                    
                                    # Update in DB (but don't log to energy_logs)
                                    if db_device:
                                        db_device.accumulated_energy_kwh = device.accumulated_energy_kwh
                                        db_device.last_state_change_ts = current_sim_time
                    
                    # Save simulation state every 10 steps
                    if self.total_steps % 10 == 0:
                        from app.db.models import SimulationStateModel
                        from sqlalchemy import select
                        result_state = await session.execute(
                            select(SimulationStateModel).where(SimulationStateModel.id == 1)
                        )
                        sim_state = result_state.scalar_one_or_none()
                        if sim_state:
                            sim_state.total_steps = self.total_steps
                            sim_state.current_hour = self.clock.hour
                            sim_state.sim_datetime = self.clock.sim_datetime
                        else:
                            sim_state = SimulationStateModel(
                                id=1,
                                total_steps=self.total_steps,
                                current_hour=self.clock.hour,
                                sim_datetime=self.clock.sim_datetime
                            )
                            session.add(sim_state)
            except Exception as e:
                logger.warning(f"Failed to persist to DB: {e}")
            
            # Advance simulation clock
            self.clock.advance()
            self.total_steps += 1
            self.last_step_time = time.time()
            self.last_result = result
            
            # Sync vpp_state hour with simulation clock
            vpp_state.current_hour = self.clock.hour
            
            # Call callbacks
            for callback in self._on_step_callbacks:
                try:
                    await callback(result)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            logger.debug(
                f"Step {self.total_steps}: Sim time {self.clock.time_str}, "
                f"dt={dt_h:.4f}h, hour={sim_hour}"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error executing simulation step: {e}")
            import traceback
            traceback.print_exc()
            return None


    def add_websocket_client(self, websocket: WebSocket):
        """Add a WebSocket client for live updates."""
        self._websocket_clients.append(websocket)
        logger.info(f"WebSocket client added. Total: {len(self._websocket_clients)}")
    
    def remove_websocket_client(self, websocket: WebSocket):
        """Remove a WebSocket client."""
        if websocket in self._websocket_clients:
            self._websocket_clients.remove(websocket)
            logger.info(f"WebSocket client removed. Total: {len(self._websocket_clients)}")
    
    async def _broadcast_to_clients(self, result: dict):
        """Send simulation result to all connected WebSocket clients."""
        if not self._websocket_clients:
            return
        
        # Enrich result with full house data for live updates
        try:
            from app.api.state import vpp_state
            if vpp_state.vpp:
                enriched_houses = []
                for house in vpp_state.vpp.houses:
                    house_data = house.to_dict()
                    # Find matching house result and merge energy data
                    for hr in result.get("houses", []):
                        if hr["house_id"] == house.id:
                            house_data.update({
                                "L_crit_kw": hr["L_crit_kw"],
                                "L_noncrit_kw": hr["L_noncrit_kw"],
                                "L_total_kw": hr["L_total_kw"],
                                "pv_prod_kw": hr["pv_prod_kw"],
                                "price_zone": hr["price_zone"],
                                # P2P trading fields
                                "surplus_after_grid_kw": hr.get("surplus_after_grid_kw", 0),
                                "P_from_grid_load_kw": hr.get("P_from_grid_load_kw", 0),
                                "P_from_batt_kw": hr.get("P_from_batt_kw", 0),
                                "P_to_grid_export_kw": hr.get("P_to_grid_export_kw", 0),
                                "P_internal_export_kw": hr.get("P_internal_export_kw", 0),
                                "P_internal_import_kw": hr.get("P_internal_import_kw", 0),
                                "battery_soc_kwh": hr.get("battery_soc_kwh", 0),
                                "battery_soc_percent": hr.get("battery_soc_percent", 0),
                            })
                            break
                    enriched_houses.append(house_data)
                result["houses"] = enriched_houses
        except Exception as e:
            logger.warning(f"Failed to enrich house data: {e}")
        
        message = {
            "type": "step",
            "data": result
        }
        
        disconnected = []
        for client in self._websocket_clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)
        
        for client in disconnected:
            self.remove_websocket_client(client)
    
    def add_callback(self, callback: Callable):
        """Add a callback to be called after each step."""
        self._on_step_callbacks.append(callback)
    
    def get_status(self) -> dict:
        """Get current simulation status."""
        return {
            "running": self.running,
            "paused": self.paused,
            "total_steps": self.total_steps,
            "interval_seconds": self.interval_seconds,
            "sim_minutes_per_step": self.sim_minutes_per_step,
            "last_step_time": self.last_step_time,
            "websocket_clients": len(self._websocket_clients),
            "clock": self.clock.to_dict()
        }
    
    def set_total_steps(self, steps: int):
        """
        Set total steps and synchronize the simulation clock.
        
        This recalculates the simulation datetime based on the new step count.
        """
        self.total_steps = steps
        
        # Recalculate simulation time based on steps
        total_sim_minutes = steps * self.sim_minutes_per_step
        self.clock.total_sim_minutes = total_sim_minutes
        
        # Reset clock to start datetime and advance to correct position
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.clock.sim_datetime = today + timedelta(minutes=total_sim_minutes)
        
        # Sync vpp_state if available
        try:
            from app.api.state import vpp_state
            vpp_state.current_hour = self.clock.hour
        except Exception:
            pass
        
        logger.info(f"Total steps set to {steps}, sim time: {self.clock.time_str}")


# Global simulation loop instance
# 5 sec real = 10 min simulation
simulation_loop = SimulationLoop(interval_seconds=5.0, sim_minutes_per_step=10)