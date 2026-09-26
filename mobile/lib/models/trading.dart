import 'package:flutter_interface/models/json_utils.dart';

class TradingPrefs {
  final int houseId;
  final bool sellingEnabled;
  final bool buyingEnabled;
  final String priceMode;
  final double fixedPriceLeiKwh;
  final double discountPercent;
  final double minSellPriceLeiKwh;

  const TradingPrefs({
    required this.houseId,
    required this.sellingEnabled,
    required this.buyingEnabled,
    required this.priceMode,
    required this.fixedPriceLeiKwh,
    required this.discountPercent,
    required this.minSellPriceLeiKwh,
  });

  factory TradingPrefs.fromJson(Map<String, dynamic> j) => TradingPrefs(
        houseId: asInt(j['house_id']),
        sellingEnabled: asBool(j['selling_enabled'], true),
        buyingEnabled: asBool(j['buying_enabled'], true),
        priceMode: asString(j['price_mode'], 'discount'),
        fixedPriceLeiKwh: asDouble(j['fixed_price_lei_kwh'], 0.8),
        discountPercent: asDouble(j['discount_percent'], 20),
        minSellPriceLeiKwh: asDouble(j['min_sell_price_lei_kwh']),
      );
}

class Trade {
  final int id;
  final int sellerHouseId;
  final int buyerHouseId;
  final double energyKwh;
  final double priceLeiKwh;
  final double totalValueLei;
  final double gridPriceLeiKwh;
  final String status;
  final String? reason;
  final DateTime? simTimestamp;
  final String transactionType;
  final int? counterpartyHouseId;

  const Trade({
    required this.id,
    required this.sellerHouseId,
    required this.buyerHouseId,
    required this.energyKwh,
    required this.priceLeiKwh,
    required this.totalValueLei,
    required this.gridPriceLeiKwh,
    required this.status,
    required this.reason,
    required this.simTimestamp,
    required this.transactionType,
    required this.counterpartyHouseId,
  });

  bool get isSell => transactionType == 'sell';
  bool get isRejected => status == 'rejected';

  factory Trade.fromJson(Map<String, dynamic> j) => Trade(
        id: asInt(j['id']),
        sellerHouseId: asInt(j['seller_house_id']),
        buyerHouseId: asInt(j['buyer_house_id']),
        energyKwh: asDouble(j['energy_kwh']),
        priceLeiKwh: asDouble(j['price_lei_kwh']),
        totalValueLei: asDouble(j['total_value_lei']),
        gridPriceLeiKwh: asDouble(j['grid_price_lei_kwh']),
        status: asString(j['status'], 'settled'),
        reason: j['reason']?.toString(),
        simTimestamp: asDateTime(j['sim_timestamp']),
        transactionType: asString(j['transaction_type']),
        counterpartyHouseId: asIntOrNull(j['counterparty_house_id']),
      );
}

class TradingStats {
  final double totalEnergySoldKwh;
  final double totalEnergyBoughtKwh;
  final double totalEarnedLei;
  final double totalSpentLei;
  final double netEarningsLei;
  final int sellCount;
  final int buyCount;

  const TradingStats({
    required this.totalEnergySoldKwh,
    required this.totalEnergyBoughtKwh,
    required this.totalEarnedLei,
    required this.totalSpentLei,
    required this.netEarningsLei,
    required this.sellCount,
    required this.buyCount,
  });

  factory TradingStats.fromJson(Map<String, dynamic> j) => TradingStats(
        totalEnergySoldKwh: asDouble(j['total_energy_sold_kwh']),
        totalEnergyBoughtKwh: asDouble(j['total_energy_bought_kwh']),
        totalEarnedLei: asDouble(j['total_earned_lei']),
        totalSpentLei: asDouble(j['total_spent_lei']),
        netEarningsLei: asDouble(j['net_earnings_lei']),
        sellCount: asInt(j['sell_count']),
        buyCount: asInt(j['buy_count']),
      );
}

class Wallet {
  final int? houseId;
  final double balanceLei;
  final double totalEarnedLei;
  final double totalSpentLei;
  final int transactionCount;
  final double vppReservedKwh;
  final double vppBaseRateLeiKwh;

  const Wallet({
    required this.houseId,
    required this.balanceLei,
    required this.totalEarnedLei,
    required this.totalSpentLei,
    required this.transactionCount,
    required this.vppReservedKwh,
    required this.vppBaseRateLeiKwh,
  });

  factory Wallet.fromJson(Map<String, dynamic> j) {
    final reserve = asMap(j['vpp_reserve']);
    return Wallet(
      houseId: asIntOrNull(j['house_id']),
      balanceLei: asDouble(j['balance_lei']),
      totalEarnedLei: asDouble(j['total_earned_lei']),
      totalSpentLei: asDouble(j['total_spent_lei']),
      transactionCount: asInt(j['transaction_count']),
      vppReservedKwh: asDouble(reserve['reserved_kwh']),
      vppBaseRateLeiKwh: asDouble(reserve['base_rate_lei_kwh']),
    );
  }
}

class WalletTx {
  final int id;
  final String transactionType; // credit | debit | vpp_payment | initial
  final double amountLei;
  final String description;
  final double balanceAfter;
  final DateTime? simTimestamp;
  final DateTime? createdAt;

  const WalletTx({
    required this.id,
    required this.transactionType,
    required this.amountLei,
    required this.description,
    required this.balanceAfter,
    required this.simTimestamp,
    required this.createdAt,
  });

  bool get isCredit => transactionType != 'debit';

  factory WalletTx.fromJson(Map<String, dynamic> j) => WalletTx(
        id: asInt(j['id']),
        transactionType: asString(j['transaction_type']),
        amountLei: asDouble(j['amount_lei']),
        description: asString(j['description']),
        balanceAfter: asDouble(j['balance_after']),
        simTimestamp: asDateTime(j['sim_timestamp']),
        createdAt: asDateTime(j['created_at']),
      );
}

class VppTransferResult {
  final double energyTransferredKwh;
  final double paymentLei;
  final double newBatterySocKwh;
  final double walletBalanceLei;

  const VppTransferResult({
    required this.energyTransferredKwh,
    required this.paymentLei,
    required this.newBatterySocKwh,
    required this.walletBalanceLei,
  });

  factory VppTransferResult.fromJson(Map<String, dynamic> j) => VppTransferResult(
        energyTransferredKwh: asDouble(j['energy_transferred_kwh']),
        paymentLei: asDouble(j['payment_lei']),
        newBatterySocKwh: asDouble(j['new_battery_soc_kwh']),
        walletBalanceLei: asDouble(j['wallet_balance_lei']),
      );
}
