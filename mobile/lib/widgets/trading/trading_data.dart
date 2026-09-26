import 'package:flutter_interface/models/trading.dart';

class TradingData {
  final TradingPrefs prefs;
  final Wallet wallet;
  final TradingStats stats;
  final List<Trade> history;
  final List<WalletTx> walletTransactions;

  const TradingData({
    required this.prefs,
    required this.wallet,
    required this.stats,
    required this.history,
    required this.walletTransactions,
  });
}

String walletTxTypeLabel(String type) {
  switch (type) {
    case 'credit':
      return 'Încasare P2P';
    case 'debit':
      return 'Plată P2P';
    case 'vpp_payment':
      return 'Plată rezervă VPP';
    case 'initial':
      return 'Sold inițial';
    default:
      return type;
  }
}

double tradeSavingsLei(Trade trade) => (trade.gridPriceLeiKwh - trade.priceLeiKwh) * trade.energyKwh;
