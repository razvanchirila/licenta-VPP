"""
Wallet Service for P2P energy trading.

Provides high-level operations for wallet management.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.wallet_repository import WalletRepository
from app.models.wallet import Wallet, WalletTransaction


class WalletService:
    """Service for managing virtual wallets."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.wallet_repo = WalletRepository(session)
    
    async def get_wallet(self, house_id: int) -> Optional[Wallet]:
        """
        Get wallet for a house.
        
        Args:
            house_id: House ID
        
        Returns:
            Wallet or None if not found
        """
        return await self.wallet_repo.get_by_house_id(house_id)
    
    async def get_or_create_wallet(self, house_id: int) -> Wallet:
        """
        Get wallet for a house, creating it if it doesn't exist.
        
        Args:
            house_id: House ID
        
        Returns:
            Wallet (existing or newly created)
        """
        wallet = await self.wallet_repo.get_by_house_id(house_id)
        if wallet:
            return wallet
        
        # Create new wallet with zero balance
        new_wallet = Wallet(
            house_id=house_id,
            balance_lei=0.0,
            total_earned_lei=0.0,
            total_spent_lei=0.0,
            transaction_count=0,
            is_flagged=False
        )
        return await self.wallet_repo.create(new_wallet)
    
    async def credit_wallet(
        self,
        house_id: int,
        amount: float,
        description: str,
        reference_id: Optional[int] = None
    ) -> Optional[Wallet]:
        """
        Credit wallet (add money from selling energy).
        
        Args:
            house_id: House ID
            amount: Amount to credit in lei
            description: Transaction description
            reference_id: Optional reference to trade transaction
        
        Returns:
            Updated Wallet or None if not found
        """
        return await self.wallet_repo.credit(
            house_id=house_id,
            amount=amount,
            description=description,
            reference_id=reference_id
        )
    
    async def debit_wallet(
        self,
        house_id: int,
        amount: float,
        description: str,
        reference_id: Optional[int] = None
    ) -> Optional[Wallet]:
        """
        Debit wallet (subtract money for buying energy).
        
        Args:
            house_id: House ID
            amount: Amount to debit in lei
            description: Transaction description
            reference_id: Optional reference to trade transaction
        
        Returns:
            Updated Wallet or None if not found
        """
        return await self.wallet_repo.debit(
            house_id=house_id,
            amount=amount,
            description=description,
            reference_id=reference_id
        )
    
    async def add_vpp_bonus(
        self,
        house_id: int,
        amount: float,
        description: str = "VPP bonus from high-price sales"
    ) -> Optional[Wallet]:
        """
        Add VPP bonus to wallet.
        
        Args:
            house_id: House ID
            amount: Bonus amount in lei
            description: Transaction description
        
        Returns:
            Updated Wallet or None if not found
        """
        return await self.wallet_repo.add_vpp_bonus(
            house_id=house_id,
            amount=amount,
            description=description
        )
    
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
            limit: Maximum number of transactions
            transaction_type: Optional filter by type ("credit", "debit", "vpp_bonus")
        
        Returns:
            List of WalletTransaction
        """
        return await self.wallet_repo.get_transactions(
            house_id=house_id,
            limit=limit,
            transaction_type=transaction_type
        )
    
    async def process_trade_wallets(
        self,
        seller_house_id: int,
        buyer_house_id: int,
        amount_lei: float,
        trade_id: Optional[int] = None
    ) -> tuple[Optional[Wallet], Optional[Wallet]]:
        """
        Process wallet updates for a completed trade.
        
        Credits seller and debits buyer.
        
        Args:
            seller_house_id: Seller's house ID
            buyer_house_id: Buyer's house ID
            amount_lei: Trade value in lei
            trade_id: Optional trade transaction ID for reference
        
        Returns:
            Tuple of (seller_wallet, buyer_wallet)
        """
        seller_wallet = await self.credit_wallet(
            house_id=seller_house_id,
            amount=amount_lei,
            description=f"P2P sale to house {buyer_house_id}",
            reference_id=trade_id
        )
        
        buyer_wallet = await self.debit_wallet(
            house_id=buyer_house_id,
            amount=amount_lei,
            description=f"P2P purchase from house {seller_house_id}",
            reference_id=trade_id
        )
        
        return seller_wallet, buyer_wallet
