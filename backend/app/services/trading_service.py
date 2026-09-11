"""
Trading Service for P2P energy trading.

Provides high-level operations for trading preferences and history.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.trading_repository import TradingPreferencesRepository
from app.db.repositories.trade_transaction_repository import TradeTransactionRepository
from app.models.trading import TradingPreferences, TradeTransaction, TradingStats


class TradingService:
    """Service for managing P2P trading operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.prefs_repo = TradingPreferencesRepository(session)
        self.trade_repo = TradeTransactionRepository(session)
    
    async def get_preferences(self, house_id: int) -> Optional[TradingPreferences]:
        """
        Get trading preferences for a house.
        
        Args:
            house_id: House ID
        
        Returns:
            TradingPreferences or None if not found
        """
        return await self.prefs_repo.get_by_house_id(house_id)
    
    async def update_preferences(
        self,
        house_id: int,
        updates: dict
    ) -> Optional[TradingPreferences]:
        """
        Update trading preferences for a house.
        
        Args:
            house_id: House ID
            updates: Dictionary of fields to update
        
        Returns:
            Updated TradingPreferences or None if not found
        """
        return await self.prefs_repo.update(house_id, updates)
    
    async def get_all_preferences(self) -> List[TradingPreferences]:
        """Get trading preferences for all houses."""
        return await self.prefs_repo.get_all()
    
    async def get_enabled_sellers(self) -> List[TradingPreferences]:
        """Get all houses with selling enabled."""
        return await self.prefs_repo.get_sellers_enabled()
    
    async def get_enabled_buyers(self) -> List[TradingPreferences]:
        """Get all houses with buying enabled."""
        return await self.prefs_repo.get_buyers_enabled()
    
    async def get_trading_history(
        self,
        house_id: int,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[str] = None
    ) -> List[TradeTransaction]:
        """
        Get trading history for a house.
        
        Args:
            house_id: House ID
            limit: Maximum number of transactions
            start_date: Optional start date filter
            end_date: Optional end date filter
            transaction_type: Optional "sell" or "buy" filter
        
        Returns:
            List of TradeTransaction
        """
        return await self.trade_repo.get_by_house(
            house_id=house_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type
        )
    
    async def get_trading_stats(self, house_id: int) -> TradingStats:
        """
        Get aggregated trading statistics for a house.
        
        Args:
            house_id: House ID
        
        Returns:
            TradingStats with aggregated data
        """
        return await self.trade_repo.get_stats(house_id)
    
    async def record_trade(self, trade: TradeTransaction) -> TradeTransaction:
        """
        Record a completed trade transaction.
        
        Args:
            trade: TradeTransaction to record
        
        Returns:
            Saved TradeTransaction with ID
        """
        return await self.trade_repo.create(trade)
    
    async def record_trades_batch(
        self,
        trades: List[TradeTransaction]
    ) -> List[TradeTransaction]:
        """
        Record multiple trade transactions in batch.
        
        Args:
            trades: List of TradeTransaction to record
        
        Returns:
            List of saved TradeTransaction with IDs
        """
        if not trades:
            return []
        return await self.trade_repo.create_batch(trades)
    
    async def get_recent_trades(self, limit: int = 50) -> List[TradeTransaction]:
        """Get most recent trades across all houses."""
        return await self.trade_repo.get_recent_trades(limit)
