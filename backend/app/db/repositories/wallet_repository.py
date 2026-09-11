"""Repository for wallet operations."""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WalletModel, WalletTransactionModel
from app.models.wallet import Wallet, WalletTransaction


class WalletRepository:
    """Repository for wallet CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_house_id(self, house_id: int) -> Optional[Wallet]:
        """Get wallet for a house."""
        result = await self.session.execute(
            select(WalletModel).where(WalletModel.house_id == house_id)
        )
        model = result.scalar_one_or_none()
        if model:
            return Wallet.from_db_model(model)
        return None
    
    async def get_model_by_house_id(self, house_id: int) -> Optional[WalletModel]:
        """Get wallet model for a house (for internal use)."""
        result = await self.session.execute(
            select(WalletModel).where(WalletModel.house_id == house_id)
        )
        return result.scalar_one_or_none()
    
    async def credit(
        self,
        house_id: int,
        amount: float,
        description: str,
        reference_id: Optional[int] = None
    ) -> Optional[Wallet]:
        """
        Credit wallet and log transaction.
        
        Args:
            house_id: House ID
            amount: Amount to credit
            description: Transaction description
            reference_id: Optional reference to trade transaction
        
        Returns:
            Updated Wallet or None if not found
        """
        wallet_model = await self.get_model_by_house_id(house_id)
        if not wallet_model:
            return None
        
        # Update wallet
        new_balance = wallet_model.balance_lei + amount
        wallet_model.balance_lei = new_balance
        wallet_model.total_earned_lei += amount
        wallet_model.transaction_count += 1
        
        # Create transaction log
        tx = WalletTransactionModel(
            wallet_id=wallet_model.id,
            transaction_type="credit",
            amount_lei=amount,
            description=description,
            reference_id=reference_id,
            balance_after=new_balance
        )
        self.session.add(tx)
        
        await self.session.commit()
        await self.session.refresh(wallet_model)
        
        return Wallet.from_db_model(wallet_model)
    
    async def debit(
        self,
        house_id: int,
        amount: float,
        description: str,
        reference_id: Optional[int] = None
    ) -> Optional[Wallet]:
        """
        Debit wallet and log transaction.
        
        Args:
            house_id: House ID
            amount: Amount to debit
            description: Transaction description
            reference_id: Optional reference to trade transaction
        
        Returns:
            Updated Wallet or None if not found
        """
        wallet_model = await self.get_model_by_house_id(house_id)
        if not wallet_model:
            return None
        
        # Update wallet
        new_balance = wallet_model.balance_lei - amount
        wallet_model.balance_lei = new_balance
        wallet_model.total_spent_lei += amount
        wallet_model.transaction_count += 1
        
        # Flag if negative
        if new_balance < 0:
            wallet_model.is_flagged = True
        
        # Create transaction log
        tx = WalletTransactionModel(
            wallet_id=wallet_model.id,
            transaction_type="debit",
            amount_lei=amount,
            description=description,
            reference_id=reference_id,
            balance_after=new_balance
        )
        self.session.add(tx)
        
        await self.session.commit()
        await self.session.refresh(wallet_model)
        
        return Wallet.from_db_model(wallet_model)
    
    async def add_vpp_bonus(
        self,
        house_id: int,
        amount: float,
        description: str = "VPP bonus from high-price sales"
    ) -> Optional[Wallet]:
        """Add VPP bonus to wallet."""
        wallet_model = await self.get_model_by_house_id(house_id)
        if not wallet_model:
            return None
        
        # Update wallet
        new_balance = wallet_model.balance_lei + amount
        wallet_model.balance_lei = new_balance
        wallet_model.total_earned_lei += amount
        wallet_model.transaction_count += 1
        
        # Create transaction log
        tx = WalletTransactionModel(
            wallet_id=wallet_model.id,
            transaction_type="vpp_bonus",
            amount_lei=amount,
            description=description,
            balance_after=new_balance
        )
        self.session.add(tx)
        
        await self.session.commit()
        await self.session.refresh(wallet_model)
        
        return Wallet.from_db_model(wallet_model)
    
    async def get_transactions(
        self,
        house_id: int,
        limit: int = 50,
        transaction_type: Optional[str] = None
    ) -> List[WalletTransaction]:
        """
        Get wallet transactions for a house.
        
        Args:
            house_id: House ID
            limit: Maximum number of transactions to return
            transaction_type: Optional filter by type
        
        Returns:
            List of WalletTransaction
        """
        wallet_model = await self.get_model_by_house_id(house_id)
        if not wallet_model:
            return []
        
        query = select(WalletTransactionModel).where(
            WalletTransactionModel.wallet_id == wallet_model.id
        )
        
        if transaction_type:
            query = query.where(
                WalletTransactionModel.transaction_type == transaction_type
            )
        
        query = query.order_by(desc(WalletTransactionModel.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [WalletTransaction.from_db_model(m) for m in models]
    
    async def create(self, wallet: Wallet) -> Wallet:
        """Create new wallet."""
        model = WalletModel(
            house_id=wallet.house_id,
            balance_lei=wallet.balance_lei,
            total_earned_lei=wallet.total_earned_lei,
            total_spent_lei=wallet.total_spent_lei,
            transaction_count=wallet.transaction_count,
            is_flagged=wallet.is_flagged
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return Wallet.from_db_model(model)
