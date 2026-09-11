"""Repository for trade transaction operations."""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TradeTransactionModel
from app.models.trading import TradeTransaction, TradingStats


class TradeTransactionRepository:
    """Repository for trade transaction CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, trade: TradeTransaction) -> TradeTransaction:
        """Create a new trade transaction."""
        model = TradeTransactionModel(
            seller_house_id=trade.seller_house_id,
            buyer_house_id=trade.buyer_house_id,
            energy_kwh=trade.energy_kwh,
            price_lei_kwh=trade.price_lei_kwh,
            total_value_lei=trade.total_value_lei,
            grid_price_lei_kwh=trade.grid_price_lei_kwh,
            sim_timestamp=trade.sim_timestamp
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return TradeTransaction.from_db_model(model)
    
    async def create_batch(self, trades: List[TradeTransaction]) -> List[TradeTransaction]:
        """Create multiple trade transactions in batch."""
        models = []
        for trade in trades:
            model = TradeTransactionModel(
                seller_house_id=trade.seller_house_id,
                buyer_house_id=trade.buyer_house_id,
                energy_kwh=trade.energy_kwh,
                price_lei_kwh=trade.price_lei_kwh,
                total_value_lei=trade.total_value_lei,
                grid_price_lei_kwh=trade.grid_price_lei_kwh,
                sim_timestamp=trade.sim_timestamp
            )
            self.session.add(model)
            models.append(model)
        
        await self.session.commit()
        
        # Refresh all models to get IDs
        for model in models:
            await self.session.refresh(model)
        
        return [TradeTransaction.from_db_model(m) for m in models]
    
    async def get_by_house(
        self,
        house_id: int,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        transaction_type: Optional[str] = None  # "sell" or "buy"
    ) -> List[TradeTransaction]:
        """
        Get trade transactions for a house.
        
        Args:
            house_id: House ID
            limit: Maximum number of transactions
            start_date: Optional start date filter
            end_date: Optional end date filter
            transaction_type: Optional "sell" or "buy" filter
        
        Returns:
            List of TradeTransaction
        """
        # Build conditions based on transaction type
        if transaction_type == "sell":
            house_condition = TradeTransactionModel.seller_house_id == house_id
        elif transaction_type == "buy":
            house_condition = TradeTransactionModel.buyer_house_id == house_id
        else:
            # Both sell and buy
            house_condition = (
                (TradeTransactionModel.seller_house_id == house_id) |
                (TradeTransactionModel.buyer_house_id == house_id)
            )
        
        query = select(TradeTransactionModel).where(house_condition)
        
        if start_date:
            query = query.where(TradeTransactionModel.sim_timestamp >= start_date)
        if end_date:
            query = query.where(TradeTransactionModel.sim_timestamp <= end_date)
        
        query = query.order_by(desc(TradeTransactionModel.sim_timestamp)).limit(limit)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [TradeTransaction.from_db_model(m) for m in models]
    
    async def get_stats(self, house_id: int) -> TradingStats:
        """
        Get aggregated trading statistics for a house.
        
        Args:
            house_id: House ID
        
        Returns:
            TradingStats with aggregated data
        """
        stats = TradingStats(house_id=house_id)
        
        # Get sell stats
        sell_result = await self.session.execute(
            select(
                func.count(TradeTransactionModel.id).label('count'),
                func.sum(TradeTransactionModel.energy_kwh).label('total_energy'),
                func.sum(TradeTransactionModel.total_value_lei).label('total_value'),
                func.avg(TradeTransactionModel.price_lei_kwh).label('avg_price')
            ).where(TradeTransactionModel.seller_house_id == house_id)
        )
        sell_row = sell_result.one()
        
        if sell_row.count and sell_row.count > 0:
            stats.sell_count = sell_row.count
            stats.total_energy_sold_kwh = sell_row.total_energy or 0
            stats.total_earned_lei = sell_row.total_value or 0
            stats.avg_sell_price_lei_kwh = sell_row.avg_price or 0
        
        # Get buy stats
        buy_result = await self.session.execute(
            select(
                func.count(TradeTransactionModel.id).label('count'),
                func.sum(TradeTransactionModel.energy_kwh).label('total_energy'),
                func.sum(TradeTransactionModel.total_value_lei).label('total_value'),
                func.avg(TradeTransactionModel.price_lei_kwh).label('avg_price')
            ).where(TradeTransactionModel.buyer_house_id == house_id)
        )
        buy_row = buy_result.one()
        
        if buy_row.count and buy_row.count > 0:
            stats.buy_count = buy_row.count
            stats.total_energy_bought_kwh = buy_row.total_energy or 0
            stats.total_spent_lei = buy_row.total_value or 0
            stats.avg_buy_price_lei_kwh = buy_row.avg_price or 0
        
        # Calculate net earnings
        stats.net_earnings_lei = stats.total_earned_lei - stats.total_spent_lei
        
        return stats
    
    async def get_recent_trades(
        self,
        limit: int = 50
    ) -> List[TradeTransaction]:
        """Get most recent trades across all houses."""
        result = await self.session.execute(
            select(TradeTransactionModel)
            .order_by(desc(TradeTransactionModel.sim_timestamp))
            .limit(limit)
        )
        models = result.scalars().all()
        return [TradeTransaction.from_db_model(m) for m in models]
