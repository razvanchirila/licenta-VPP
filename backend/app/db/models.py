"""SQLAlchemy ORM models. All timestamps named sim_* are simulation time, the rest wall-clock."""
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="SET NULL"), unique=True, nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    house = relationship("HouseModel", back_populates="user")


class HouseModel(Base):
    __tablename__ = "houses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    mode = Column(String(20), nullable=False, default="Eco")  # "Eco" | "Profit"
    has_pv = Column(Boolean, nullable=False, default=True)
    pv_capacity_kw = Column(Float, nullable=False, default=10.0)
    description = Column(String(200), nullable=False, default="")
    people = Column(Integer, nullable=False, default=1)
    home_daytime = Column(Boolean, nullable=False, default=False)
    heating = Column(String(50), nullable=False, default="gaz")      # gaz or a heating device of the catalog
    insulation = Column(String(10), nullable=False, default="medie")  # noua | medie | veche
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    battery = relationship("BatteryModel", back_populates="house", uselist=False, cascade="all, delete-orphan")
    devices = relationship("DeviceModel", back_populates="house", cascade="all, delete-orphan",
                           order_by="DeviceModel.id")
    user = relationship("UserModel", back_populates="house", uselist=False)
    trading_preferences = relationship(
        "TradingPreferencesModel", back_populates="house", uselist=False, cascade="all, delete-orphan"
    )
    wallet = relationship("WalletModel", back_populates="house", uselist=False, cascade="all, delete-orphan")
    vpp_reserve = relationship("VPPReserveModel", back_populates="house", uselist=False, cascade="all, delete-orphan")


class BatteryModel(Base):
    __tablename__ = "batteries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    capacity_kwh = Column(Float, nullable=False, default=20.0)
    soc_kwh = Column(Float, nullable=False, default=10.0)
    soc_min_kwh = Column(Float, nullable=False, default=4.0)
    p_ch_max_kw = Column(Float, nullable=False, default=5.0)
    p_dis_max_kw = Column(Float, nullable=False, default=5.0)
    eta_ch = Column(Float, nullable=False, default=0.95)
    eta_dis = Column(Float, nullable=False, default=0.95)

    house = relationship("HouseModel", back_populates="battery")


class DeviceModel(Base):
    """A device with `mode` set is an appliance of the house's composition: its load is the schedule
    vpp_core.load_model draws from `program` (the device's catalog rows as JSON, per-person counts already
    multiplied); `mode` NULL means a device added by hand, power_w while on."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    power_w = Column(Float, nullable=False)
    critical = Column(Boolean, nullable=False, default=False)
    status_on = Column(Boolean, nullable=False, default=False)
    mode = Column(String(10), nullable=True)                     # permanent | interval | durata | termic
    program = Column(Text, nullable=False, default="[]")
    current_power_kw = Column(Float, nullable=False, default=0.0)   # draw at the last simulated step
    last_state_change_ts = Column(DateTime, nullable=True)       # simulation time of the last toggle
    accumulated_energy_kwh = Column(Float, nullable=False, default=0.0)

    house = relationship("HouseModel", back_populates="devices")
    # the database deletes the logs (ON DELETE CASCADE); loading millions to delete one by one runs out of memory
    energy_logs = relationship("EnergyLogModel", back_populates="device", cascade="all, delete-orphan",
                               passive_deletes=True)


class EnergyLogModel(Base):
    """Per-step energy of a switched-on device (event_type 'step') and toggle events (0 kWh)."""
    __tablename__ = "energy_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False)                 # simulation time
    energy_kwh = Column(Float, nullable=False)
    event_type = Column(String(20), nullable=False)              # step | toggle_on | toggle_off
    details = Column(Text, nullable=True)

    device = relationship("DeviceModel", back_populates="energy_logs")

    __table_args__ = (
        Index("idx_energy_log_device_ts", "device_id", "timestamp"),
    )


class HouseStepModel(Base):
    __tablename__ = "house_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    sim_timestamp = Column(DateTime, nullable=False)
    dt_h = Column(Float, nullable=False)
    controller = Column(String(20), nullable=False)
    pv_kw = Column(Float, nullable=False)
    load_kw = Column(Float, nullable=False)          # sum of the switched-on devices
    device_kw = Column(Float, nullable=False)        # same as load_kw (kept for the clients)
    shed_kw = Column(Float, nullable=False)
    curtail_kw = Column(Float, nullable=False)
    ch_kw = Column(Float, nullable=False)
    dis_kw = Column(Float, nullable=False)
    imp_kw = Column(Float, nullable=False)
    exp_kw = Column(Float, nullable=False)
    p2p_in_kw = Column(Float, nullable=False)
    p2p_out_kw = Column(Float, nullable=False)
    soc_kwh = Column(Float, nullable=False)          # after the step
    price_import = Column(Float, nullable=False)
    price_export = Column(Float, nullable=False)
    price_p2p = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_house_step_house_ts", "house_id", "sim_timestamp"),
    )


class SimulationStateModel(Base):
    """Single row (id=1) so the simulation clock and config survive restarts."""
    __tablename__ = "simulation_state"

    id = Column(Integer, primary_key=True, default=1)
    total_steps = Column(Integer, nullable=False, default=0)
    sim_datetime = Column(DateTime, nullable=True)
    config_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TradingPreferencesModel(Base):
    __tablename__ = "trading_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    selling_enabled = Column(Boolean, nullable=False, default=True)
    buying_enabled = Column(Boolean, nullable=False, default=True)
    price_mode = Column(String(20), nullable=False, default="discount")   # kept for the mobile UI
    fixed_price_lei_kwh = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=False, default=30.0)
    min_sell_price_lei_kwh = Column(Float, nullable=False, default=0.0)

    house = relationship("HouseModel", back_populates="trading_preferences")


class WalletModel(Base):
    """One wallet per house; the row with house_id NULL is the VPP operator's wallet."""
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=True, unique=True)
    balance_lei = Column(Float, nullable=False, default=0.0)
    total_earned_lei = Column(Float, nullable=False, default=0.0)
    total_spent_lei = Column(Float, nullable=False, default=0.0)
    transaction_count = Column(Integer, nullable=False, default=0)

    house = relationship("HouseModel", back_populates="wallet")
    transactions = relationship("WalletTransactionModel", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransactionModel(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)   # credit | debit | vpp_payment | initial
    amount_lei = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)
    reference_id = Column(Integer, nullable=True)           # trade_transactions.id when applicable
    balance_after = Column(Float, nullable=False)
    sim_timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    wallet = relationship("WalletModel", back_populates="transactions")


class TradeTransactionModel(Base):
    __tablename__ = "trade_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, index=True)
    energy_kwh = Column(Float, nullable=False)
    price_lei_kwh = Column(Float, nullable=False)
    total_value_lei = Column(Float, nullable=False)
    grid_price_lei_kwh = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="settled")   # settled | rejected
    reason = Column(String(255), nullable=True)
    sim_timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class VPPReserveModel(Base):
    __tablename__ = "vpp_reserve"

    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    reserved_kwh = Column(Float, nullable=False, default=0.0)
    base_rate_lei_kwh = Column(Float, nullable=False, default=0.5)

    house = relationship("HouseModel", back_populates="vpp_reserve")
