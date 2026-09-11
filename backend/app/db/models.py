"""SQLAlchemy ORM models for VPP Simulator database."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Index, Enum, Text
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class UserModel(Base):
    """ORM model for users table - authentication and house assignment."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="SET NULL"), unique=True, nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    house = relationship("HouseModel", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_house_id", "house_id"),
    )
    
    def __repr__(self):
        return f"<UserModel(id={self.id}, username={self.username}, house_id={self.house_id})>"


class EventType(PyEnum):
    """Event types for energy logging."""
    TOGGLE_ON = "toggle_on"
    TOGGLE_OFF = "toggle_off"
    CHECKPOINT = "checkpoint"


class HouseModel(Base):
    """ORM model for houses table."""
    __tablename__ = "houses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    mode = Column(String(20), nullable=False, default="Eco")  # "Eco" or "Profit"
    has_pv = Column(Boolean, nullable=False, default=True)
    pv_capacity_kw = Column(Float, nullable=False, default=10.0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    battery = relationship("BatteryModel", back_populates="house", uselist=False, cascade="all, delete-orphan")
    devices = relationship("DeviceModel", back_populates="house", cascade="all, delete-orphan")
    user = relationship("UserModel", back_populates="house", uselist=False)
    trading_preferences = relationship("TradingPreferencesModel", back_populates="house", uselist=False, cascade="all, delete-orphan")
    wallet = relationship("WalletModel", back_populates="house", uselist=False, cascade="all, delete-orphan")
    vpp_reserve = relationship("VPPReserveModel", back_populates="house", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<HouseModel(id={self.id}, mode={self.mode})>"


class BatteryModel(Base):
    """ORM model for batteries table."""
    __tablename__ = "batteries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    capacity_kwh = Column(Float, nullable=False, default=20.0)
    soc_kwh = Column(Float, nullable=False, default=10.0)
    soc_min_kwh = Column(Float, nullable=False, default=4.0)  # 20% of 20kWh
    soc_max_kwh = Column(Float, nullable=False, default=20.0)
    p_ch_max_kw = Column(Float, nullable=False, default=5.0)
    p_dis_max_kw = Column(Float, nullable=False, default=5.0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    house = relationship("HouseModel", back_populates="battery")
    
    # Indexes
    __table_args__ = (
        Index("idx_battery_house_id", "house_id"),
    )
    
    def __repr__(self):
        return f"<BatteryModel(id={self.id}, house_id={self.house_id}, soc={self.soc_kwh}kWh)>"



class DeviceModel(Base):
    """ORM model for devices table with metering fields."""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    power_w = Column(Float, nullable=False)
    critical = Column(Boolean, nullable=False, default=False)
    status_on = Column(Boolean, nullable=False, default=False)
    
    # Metering fields (Requirements 4.1)
    last_state_change_ts = Column(DateTime, nullable=True)  # When device was last toggled
    accumulated_energy_kwh = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    house = relationship("HouseModel", back_populates="devices")
    energy_logs = relationship("EnergyLogModel", back_populates="device", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_device_house_id", "house_id"),
        Index("idx_device_status", "status_on"),
    )
    
    def __repr__(self):
        status = "ON" if self.status_on else "OFF"
        return f"<DeviceModel(id={self.id}, name={self.name}, {status})>"


class EnergyLogModel(Base):
    """ORM model for energy_logs table (audit log for energy calculations)."""
    __tablename__ = "energy_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    energy_kwh = Column(Float, nullable=False)
    event_type = Column(String(20), nullable=False)  # toggle_on, toggle_off, checkpoint
    details = Column(Text, nullable=True)  # JSON string for additional info
    
    # Relationships
    device = relationship("DeviceModel", back_populates="energy_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_energy_log_device_id", "device_id"),
        Index("idx_energy_log_timestamp", "timestamp"),
        Index("idx_energy_log_event_type", "event_type"),
    )
    
    def __repr__(self):
        return f"<EnergyLogModel(id={self.id}, device_id={self.device_id}, event={self.event_type})>"


class SimulationStateModel(Base):
    """ORM model for persisting simulation state across restarts."""
    __tablename__ = "simulation_state"
    
    id = Column(Integer, primary_key=True, default=1)  # Single row
    total_steps = Column(Integer, nullable=False, default=0)
    current_hour = Column(Integer, nullable=False, default=0)
    sim_datetime = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SimulationStateModel(steps={self.total_steps}, hour={self.current_hour})>"


# ============================================================================
# P2P Trading Models
# ============================================================================

class TradingPreferencesModel(Base):
    """ORM model for trading preferences per house."""
    __tablename__ = "trading_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    selling_enabled = Column(Boolean, nullable=False, default=True)
    buying_enabled = Column(Boolean, nullable=False, default=True)
    price_mode = Column(String(20), nullable=False, default="discount")  # "fixed" or "discount"
    fixed_price_lei_kwh = Column(Float, nullable=True)  # Used when price_mode="fixed"
    discount_percent = Column(Float, nullable=False, default=20.0)  # Used when price_mode="discount"
    min_sell_price_lei_kwh = Column(Float, nullable=False, default=0.0)  # Won't sell below this
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    house = relationship("HouseModel", back_populates="trading_preferences")
    
    # Indexes
    __table_args__ = (
        Index("idx_trading_prefs_house_id", "house_id"),
    )
    
    def __repr__(self):
        return f"<TradingPreferencesModel(house_id={self.house_id}, selling={self.selling_enabled}, buying={self.buying_enabled})>"


class WalletModel(Base):
    """ORM model for virtual wallet per house."""
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    balance_lei = Column(Float, nullable=False, default=0.0)
    total_earned_lei = Column(Float, nullable=False, default=0.0)
    total_spent_lei = Column(Float, nullable=False, default=0.0)
    transaction_count = Column(Integer, nullable=False, default=0)
    is_flagged = Column(Boolean, nullable=False, default=False)  # True if balance went negative
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    house = relationship("HouseModel", back_populates="wallet")
    transactions = relationship("WalletTransactionModel", back_populates="wallet", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_wallet_house_id", "house_id"),
    )
    
    def __repr__(self):
        return f"<WalletModel(house_id={self.house_id}, balance={self.balance_lei:.2f} lei)>"


class WalletTransactionModel(Base):
    """ORM model for wallet transaction log."""
    __tablename__ = "wallet_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # "credit", "debit", "vpp_bonus"
    amount_lei = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)
    reference_id = Column(Integer, nullable=True)  # FK to trade_transactions if applicable
    balance_after = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    wallet = relationship("WalletModel", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index("idx_wallet_tx_wallet_id", "wallet_id"),
        Index("idx_wallet_tx_created_at", "created_at"),
        Index("idx_wallet_tx_type", "transaction_type"),
    )
    
    def __repr__(self):
        return f"<WalletTransactionModel(id={self.id}, type={self.transaction_type}, amount={self.amount_lei:.2f})>"


class TradeTransactionModel(Base):
    """ORM model for P2P trade transactions between houses."""
    __tablename__ = "trade_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    buyer_house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False)
    energy_kwh = Column(Float, nullable=False)
    price_lei_kwh = Column(Float, nullable=False)
    total_value_lei = Column(Float, nullable=False)
    grid_price_lei_kwh = Column(Float, nullable=False)  # Reference price at time of trade
    sim_timestamp = Column(DateTime, nullable=False)  # Simulation time
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_trade_tx_seller", "seller_house_id"),
        Index("idx_trade_tx_buyer", "buyer_house_id"),
        Index("idx_trade_tx_sim_timestamp", "sim_timestamp"),
    )
    
    def __repr__(self):
        return f"<TradeTransactionModel(seller={self.seller_house_id}, buyer={self.buyer_house_id}, {self.energy_kwh:.3f}kWh)>"


class VPPReserveModel(Base):
    """ORM model for VPP energy reserve contributions per house."""
    __tablename__ = "vpp_reserve"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, unique=True)
    reserved_kwh = Column(Float, nullable=False, default=0.0)  # Energy contributed to VPP
    base_rate_lei_kwh = Column(Float, nullable=False, default=0.5)  # Rate paid immediately
    pending_bonus_lei = Column(Float, nullable=False, default=0.0)  # Bonus from high-price sales
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    house = relationship("HouseModel", back_populates="vpp_reserve")
    
    # Indexes
    __table_args__ = (
        Index("idx_vpp_reserve_house_id", "house_id"),
    )
    
    def __repr__(self):
        return f"<VPPReserveModel(house_id={self.house_id}, reserved={self.reserved_kwh:.2f}kWh)>"


# ============================================================================
# OPCOM Price Cache Models
# ============================================================================

class OpcomPriceModel(Base):
    """ORM model for caching OPCOM electricity prices."""
    __tablename__ = "opcom_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)  # Date of the price (date part only)
    hour = Column(Integer, nullable=False)  # Hour 0-23
    price_lei_mwh = Column(Float, nullable=False)  # Original price in lei/MWh
    price_lei_kwh = Column(Float, nullable=False)  # Converted price in lei/kWh
    fetched_at = Column(DateTime, nullable=False, server_default=func.now())  # When data was fetched from OPCOM
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Indexes - unique constraint on date+hour
    __table_args__ = (
        Index("idx_opcom_date_hour", "date", "hour", unique=True),
        Index("idx_opcom_fetched_at", "fetched_at"),
        Index("idx_opcom_date", "date"),
    )
    
    def __repr__(self):
        return f"<OpcomPriceModel(date={self.date.date()}, hour={self.hour}, price={self.price_lei_mwh:.2f} lei/MWh)>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "date": self.date.strftime("%Y-%m-%d"),
            "hour": self.hour,
            "price_lei_mwh": round(self.price_lei_mwh, 2),
            "price_lei_kwh": round(self.price_lei_kwh, 4),
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "timestamp": self.date.replace(hour=self.hour).isoformat()
        }
