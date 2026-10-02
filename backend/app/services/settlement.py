"""
Money. Everything runs inside the caller's session and only flushes, so a simulation step
(house rows + trades + wallet movements) is committed or rolled back as one unit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TradeTransactionModel, WalletModel, WalletTransactionModel
from app.services.wallet import find_reserve

ROUND = 4          # lei are stored with 4 decimals
EPS = 1e-9


class SettlementError(Exception):
    """A trade or payment that cannot be recorded at all (bad input, missing wallet)."""


class InsufficientFunds(SettlementError):
    """Safety net: _move refuses to push a balance below zero."""


@dataclass
class Trade:
    seller_house_id: int
    buyer_house_id: int
    energy_kwh: float
    price_lei_kwh: float
    grid_price_lei_kwh: float      # import price at the same step, kept for the history screen

    @property
    def value_lei(self) -> float:
        return round(self.energy_kwh * self.price_lei_kwh, ROUND)

    def check(self) -> None:
        if self.energy_kwh <= 0 or self.price_lei_kwh < 0:
            raise SettlementError("energia trebuie sa fie > 0 si pretul >= 0")
        if self.seller_house_id == self.buyer_house_id:
            raise SettlementError("vanzatorul si cumparatorul trebuie sa fie case diferite")


class SettlementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._wallets: dict[int | None, WalletModel] = {}     # loaded once per batch, see settle_trades

    async def _lock(self, house_ids: set[int | None]) -> None:
        """SELECT ... FOR UPDATE, fresh from the database and always in wallet id order: a simulation step,
        an admin trade and a VPP transfer running at the same time wait for each other instead of
        overwriting each other's balances, and cannot deadlock."""
        missing = {h for h in house_ids if h not in self._wallets}
        if not missing:
            return
        ids = [h for h in missing if h is not None]
        conds = [WalletModel.house_id.in_(ids)] if ids else []
        if None in missing:
            conds.append(WalletModel.house_id.is_(None))
        query = (select(WalletModel).where(or_(*conds)).order_by(WalletModel.id).with_for_update()
                 .execution_options(populate_existing=True))
        for wallet in (await self.session.execute(query)).scalars():
            self._wallets[wallet.house_id] = wallet

    def _wallet(self, house_id: int | None) -> WalletModel:
        wallet = self._wallets.get(house_id)
        if wallet is None:
            raise SettlementError(f"casa {house_id} nu are portofel")
        return wallet

    def _move(self, wallet: WalletModel, amount: float, tx_type: str, description: str,
              sim_ts: datetime, reference_id: int | None = None) -> None:
        """amount > 0 credits, amount < 0 debits; records the movement and the balance after it."""
        amount = round(amount, ROUND)
        new_balance = round(wallet.balance_lei + amount, ROUND)
        if new_balance < -EPS:
            raise InsufficientFunds(
                f"portofel {wallet.house_id}: sold {wallet.balance_lei:.2f} lei, necesar {-amount:.2f} lei")
        wallet.balance_lei = max(new_balance, 0.0)
        if amount >= 0:
            wallet.total_earned_lei = round(wallet.total_earned_lei + amount, ROUND)
        else:
            wallet.total_spent_lei = round(wallet.total_spent_lei - amount, ROUND)
        wallet.transaction_count += 1
        self.session.add(WalletTransactionModel(
            wallet_id=wallet.id, transaction_type=tx_type, amount_lei=abs(amount), description=description,
            reference_id=reference_id, balance_after=wallet.balance_lei, sim_timestamp=sim_ts,
        ))

    async def settle_trade(self, trade: Trade, sim_ts: datetime) -> TradeTransactionModel:
        """Record one P2P trade and, if the buyer can pay, move the money. Invariants:
        buyer debit == seller credit == round(energy_kwh x price_lei_kwh, 4); no negative balance
        (a buyer short of funds gets status 'rejected' and nothing moves); one payout per trade
        (both wallet movements carry reference_id = trade record id)."""
        trade.check()
        await self._lock({trade.buyer_house_id, trade.seller_house_id})
        buyer = self._wallet(trade.buyer_house_id)
        seller = self._wallet(trade.seller_house_id)
        value = trade.value_lei
        record = TradeTransactionModel(
            seller_house_id=trade.seller_house_id, buyer_house_id=trade.buyer_house_id,
            energy_kwh=round(trade.energy_kwh, 6), price_lei_kwh=round(trade.price_lei_kwh, ROUND),
            total_value_lei=value, grid_price_lei_kwh=round(trade.grid_price_lei_kwh, ROUND),
            sim_timestamp=sim_ts, status="settled",
        )
        if buyer.balance_lei + EPS < value:
            record.status = "rejected"
            record.reason = f"fonduri insuficiente: sold {buyer.balance_lei:.2f} lei, necesar {value:.2f} lei"
        self.session.add(record)
        await self.session.flush()          # assigns record.id, referenced by the wallet movements
        if record.status == "settled":
            text = f"{trade.energy_kwh:.3f} kWh @ {trade.price_lei_kwh:.3f} lei/kWh"
            self._move(buyer, -value, "debit", f"Cumparare P2P de la casa {trade.seller_house_id}: {text}",
                       sim_ts, record.id)
            self._move(seller, value, "credit", f"Vanzare P2P catre casa {trade.buyer_house_id}: {text}",
                       sim_ts, record.id)
            await self.session.flush()
        return record

    async def settle_trades(self, trades: list[Trade], sim_ts: datetime) -> list[TradeTransactionModel]:
        """Settled in order: earlier trades reduce the funds left for later ones."""
        await self._lock({t.seller_house_id for t in trades} | {t.buyer_house_id for t in trades})
        return [await self.settle_trade(t, sim_ts) for t in trades]

    async def pay_reserve_contribution(self, house_id: int, energy_kwh: float,
                                       sim_ts: datetime) -> tuple[float, WalletModel]:
        """Returns (payment_lei, house wallet)."""
        if energy_kwh <= 0:
            raise SettlementError("energia trebuie sa fie > 0")
        reserve = await find_reserve(self.session, house_id)
        if reserve is None:
            raise SettlementError(f"casa {house_id} nu are rezerva VPP")
        payment = round(energy_kwh * reserve.base_rate_lei_kwh, ROUND)
        await self._lock({None, house_id})
        operator = self._wallet(None)
        house_wallet = self._wallet(house_id)
        text = f"Rezerva VPP: {energy_kwh:.2f} kWh @ {reserve.base_rate_lei_kwh:.2f} lei/kWh (casa {house_id})"
        self._move(operator, -payment, "vpp_payment", text, sim_ts)
        self._move(house_wallet, payment, "vpp_payment", text, sim_ts)
        reserve.reserved_kwh = round(reserve.reserved_kwh + energy_kwh, 6)
        await self.session.flush()
        return payment, house_wallet
