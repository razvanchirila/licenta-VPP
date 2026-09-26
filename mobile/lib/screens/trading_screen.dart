import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/async_body.dart';
import 'package:flutter_interface/widgets/price_chart_widget.dart';
import 'package:flutter_interface/widgets/trading/history_tab.dart';
import 'package:flutter_interface/widgets/trading/trading_data.dart';
import 'package:flutter_interface/widgets/trading/trading_settings_tab.dart';
import 'package:flutter_interface/widgets/trading/vpp_transfer_dialog.dart';
import 'package:flutter_interface/widgets/trading/wallet_tab.dart';

class TradingScreen extends StatefulWidget {
  const TradingScreen({super.key});

  @override
  State<TradingScreen> createState() => _TradingScreenState();
}

class _TradingScreenState extends State<TradingScreen>
    with SingleTickerProviderStateMixin, AsyncLoader<TradingData, TradingScreen> {
  static const Color _accent = AppColors.tradingAccent;

  late TabController _tabController;

  /// The price curve is loaded separately: it is optional for the other tabs.
  SimPrices? _prices;
  PriceSeries _series = PriceSeries.import;
  bool _isPriceLoading = false;
  String? _priceError;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadTradingData();
    _loadPrices();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadTradingData() => load(() async {
        final results = await Future.wait<Object>([
          userApiService.getTradingPreferences(),
          userApiService.getWallet(),
          userApiService.getTradingStats(),
          userApiService.getTradingHistory(limit: 30),
          userApiService.getWalletTransactions(limit: 30),
        ]);
        return TradingData(
          prefs: results[0] as TradingPrefs,
          wallet: results[1] as Wallet,
          stats: results[2] as TradingStats,
          history: results[3] as List<Trade>,
          walletTransactions: results[4] as List<WalletTx>,
        );
      });

  Future<void> _loadPrices() async {
    setState(() {
      _isPriceLoading = true;
      _priceError = null;
    });
    try {
      final prices = await userApiService.getSimPrices();
      if (!mounted) return;
      setState(() {
        _prices = prices;
        _isPriceLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _priceError = e.message;
        _isPriceLoading = false;
      });
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: isError ? Colors.red : Colors.green),
    );
  }

  Future<void> _transferToVpp(Wallet wallet) async {
    final value = await showVppTransferDialog(context, rateLeiKwh: wallet.vppBaseRateLeiKwh);
    if (value == null || !mounted) return;
    if (value <= 0 || value > 1000) {
      _showSnackBar('Introdu o cantitate între 0 și 1000 kWh', isError: true);
      return;
    }
    try {
      final result = await userApiService.transferToVpp(value);
      if (!mounted) return;
      _showSnackBar(
        'Transferat ${result.energyTransferredKwh.toStringAsFixed(2)} kWh, '
        'încasat ${result.paymentLei.toStringAsFixed(2)} lei',
      );
      _loadTradingData();
    } on ApiException catch (e) {
      _showSnackBar(e.message, isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: Text('Trading P2P', style: GoogleFonts.inter(color: Colors.white)),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white38,
          isScrollable: false,
          indicatorWeight: 3,
          indicatorSize: TabBarIndicatorSize.tab,
          labelStyle: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 12),
          unselectedLabelStyle: GoogleFonts.inter(fontWeight: FontWeight.w400, fontSize: 12),
          tabs: const [
            Tab(text: 'Preț', icon: Icon(Icons.show_chart)),
            Tab(text: 'Portofel', icon: Icon(Icons.account_balance_wallet)),
            Tab(text: 'Istoric', icon: Icon(Icons.history)),
            Tab(text: 'Setări', icon: Icon(Icons.settings)),
          ],
        ),
      ),
      body: AsyncBody<TradingData>(
        value: state,
        onRetry: _loadTradingData,
        accent: _accent,
        builder: (data) => TabBarView(
          controller: _tabController,
          children: [
            _buildPriceChartTab(),
            WalletTab(
              wallet: data.wallet,
              stats: data.stats,
              transactions: data.walletTransactions,
              onRefresh: _loadTradingData,
              onTransfer: () => _transferToVpp(data.wallet),
            ),
            HistoryTab(trades: data.history, onRefresh: _loadTradingData),
            TradingSettingsTab(prefs: data.prefs, onMessage: _showSnackBar),
          ],
        ),
      ),
    );
  }

  Widget _buildPriceChartTab() {
    return SingleChildScrollView(
      physics: const ClampingScrollPhysics(),
      child: PriceChartWidget(
        prices: _prices,
        isLoading: _isPriceLoading,
        error: _priceError,
        series: _series,
        onSeriesChanged: (s) => setState(() => _series = s),
        onRefresh: _loadPrices,
      ),
    );
  }
}
