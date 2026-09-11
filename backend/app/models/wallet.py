"""
Wallet domain models for P2P energy trading
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Wallet:
    """
    Virtual wallet for a house in P2P energy trading.
    
    Attributes:
        house_id: House identifier
        balance_lei: Current balance in lei
        total_earned_lei: Lifetime earnings
        total_spent_lei: Lifetime spending
        transaction_count: Number of transactions
        is_flagged: True if balance went negative
    """
    house_id: int
    balance_lei: float = 0.0
    total_earned_lei: float = 0.0
    total_spent_lei: float = 0.0
    transaction_count: int = 0
    is_flagged: bool = False
    
    def credit(self, amount: float) -> float:
        """
        Add to balance (earning from selling energy).
        
        Args:
            amount: Amount to credit in lei
        
        Returns:
            New balance
        """
        self.balance_lei += amount
        self.total_earned_lei += amount
        self.transaction_count += 1
        return self.balance_lei
    
    def debit(self, amount: float) -> float:
        """
        Subtract from balance (spending on buying energy).
        
        Args:
            amount: Amount to debit in lei
        
        Returns:
            New balance
        """
        self.balance_lei -= amount
        self.total_spent_lei += amount
        self.transaction_count += 1
        
        # Flag if balance goes negative
        if self.balance_lei < 0:
            self.is_flagged = True
        
        return self.balance_lei
    
    def is_consistent(self) -> bool:
        """
        Check if wallet is internally consistent.
        
        Returns:
            True if balance equals earned - spent (within tolerance)
        """
        expected_balance = self.total_earned_lei - self.total_spent_lei
        return abs(self.balance_lei - expected_balance) < 0.01
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "house_id": self.house_id,
            "balance_lei": round(self.balance_lei, 2),
            "total_earned_lei": round(self.total_earned_lei, 2),
            "total_spent_lei": round(self.total_spent_lei, 2),
            "net_balance_lei": round(self.total_earned_lei - self.total_spent_lei, 2),
            "transaction_count": self.transaction_count,
            "is_flagged": self.is_flagged,
            "is_consistent": self.is_consistent()
        }
    
    @classmethod
    def from_db_model(cls, model) -> 'Wallet':
        """Create from database model."""
        return cls(
            house_id=model.house_id,
            balance_lei=model.balance_lei,
            total_earned_lei=model.total_earned_lei,
            total_spent_lei=model.total_spent_lei,
            transaction_count=model.transaction_count,
            is_flagged=model.is_flagged
        )


@dataclass
class WalletTransaction:
    """
    A wallet transaction log entry.
    
    Attributes:
        id: Transaction ID
        wallet_id: Wallet ID
        transaction_type: "credit", "debit", or "vpp_bonus"
        amount_lei: Transaction amount
        description: Human-readable description
        reference_id: Reference to trade_transaction if applicable
        balance_after: Balance after this transaction
        created_at: Timestamp
    """
    wallet_id: int
    transaction_type: str  # "credit", "debit", "vpp_bonus"
    amount_lei: float
    balance_after: float
    description: Optional[str] = None
    reference_id: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "transaction_type": self.transaction_type,
            "amount_lei": round(self.amount_lei, 4),
            "description": self.description,
            "reference_id": self.reference_id,
            "balance_after": round(self.balance_after, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_db_model(cls, model) -> 'WalletTransaction':
        """Create from database model."""
        return cls(
            id=model.id,
            wallet_id=model.wallet_id,
            transaction_type=model.transaction_type,
            amount_lei=model.amount_lei,
            description=model.description,
            reference_id=model.reference_id,
            balance_after=model.balance_after,
            created_at=model.created_at
        )


@dataclass
class VPPReserve:
    """
    VPP energy reserve contribution from a house.
    
    Attributes:
        house_id: House identifier
        reserved_kwh: Energy contributed to VPP reserve
        base_rate_lei_kwh: Rate paid immediately for contribution
        pending_bonus_lei: Bonus from high-price sales (not yet distributed)
    """
    house_id: int
    reserved_kwh: float = 0.0
    base_rate_lei_kwh: float = 0.5
    pending_bonus_lei: float = 0.0
    
    def add_reserve(self, kwh: float) -> float:
        """
        Add energy to VPP reserve.
        
        Args:
            kwh: Energy to add in kWh
        
        Returns:
            Immediate payment in lei (kwh * base_rate)
        """
        self.reserved_kwh += kwh
        return kwh * self.base_rate_lei_kwh
    
    def use_reserve(self, kwh: float) -> float:
        """
        Use energy from VPP reserve.
        
        Args:
            kwh: Energy to use in kWh
        
        Returns:
            Actual energy used (may be less if not enough reserve)
        """
        actual = min(kwh, self.reserved_kwh)
        self.reserved_kwh -= actual
        return actual
    
    def add_bonus(self, amount_lei: float):
        """Add bonus from high-price sales."""
        self.pending_bonus_lei += amount_lei
    
    def claim_bonus(self) -> float:
        """Claim pending bonus and reset to zero."""
        bonus = self.pending_bonus_lei
        self.pending_bonus_lei = 0.0
        return bonus
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "house_id": self.house_id,
            "reserved_kwh": round(self.reserved_kwh, 4),
            "base_rate_lei_kwh": round(self.base_rate_lei_kwh, 4),
            "pending_bonus_lei": round(self.pending_bonus_lei, 2),
            "total_value_lei": round(self.reserved_kwh * self.base_rate_lei_kwh + self.pending_bonus_lei, 2)
        }
    
    @classmethod
    def from_db_model(cls, model) -> 'VPPReserve':
        """Create from database model."""
        return cls(
            house_id=model.house_id,
            reserved_kwh=model.reserved_kwh,
            base_rate_lei_kwh=model.base_rate_lei_kwh,
            pending_bonus_lei=model.pending_bonus_lei
        )
