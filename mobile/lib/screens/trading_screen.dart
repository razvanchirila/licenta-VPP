import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/user_api_service.dart';
import '../models/price_data.dart';
import '../widgets/price_chart_widget.dart';

class TradingScreen extends StatefulWidget {
  const TradingScreen({super.key});

  @override
  State<TradingScreen> createState() => _TradingScreenState();
}

class _TradingScreenState extends State<TradingScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  late TextEditingController _fixedPriceController;
  
  // Trading preferences
  bool _sellingEnabled = true;
  bool _buyingEnabled = true;
  String _priceMode = 'discount';
  double _discountPercent = 20.0;
  double _fixedPrice = 0.8;
  
  // Wallet data
  Map<String, dynamic>? _wallet;
  Map<String, dynamic>? _tradingStats;
  List<dynamic> _tradingHistory = [];
  List<dynamic> _walletTransactions = [];
  
  // OPCOM price data
  PriceData? _priceData;
  String _selectedPeriod = '1Z';
  bool _isPriceLoading = false;
  
  bool _isLoading = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this); // 4 tabs now
    _fixedPriceController = TextEditingController(text: _fixedPrice.toStringAsFixed(2));
    _loadData();
    _loadOpcomPrices();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _fixedPriceController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    // Load trading preferences
    final prefs = await userApiService.getTradingPreferences();
    if (prefs != null && prefs['error'] == null) {
      setState(() {
        _sellingEnabled = prefs['selling_enabled'] ?? true;
        _buyingEnabled = prefs['buying_enabled'] ?? true;
        _priceMode = prefs['price_mode'] ?? 'discount';
        _discountPercent = (prefs['discount_percent'] ?? 20.0).toDouble();
        _fixedPrice = (prefs['fixed_price_lei_kwh'] ?? 0.8).toDouble();
        _fixedPriceController.text = _fixedPrice.toStringAsFixed(2);
      });
    }
    
    // Load wallet
    final wallet = await userApiService.getWallet();
    if (wallet != null) {
      setState(() => _wallet = wallet);
    }
    
    // Load trading stats
    final stats = await userApiService.getTradingStats();
    if (stats != null) {
      setState(() => _tradingStats = stats);
    }
    
    // Load trading history
    final history = await userApiService.getTradingHistory(limit: 20);
    if (history != null && history['transactions'] != null) {
      setState(() => _tradingHistory = history['transactions']);
    }
    
    // Load wallet transactions
    final transactions = await userApiService.getWalletTransactions(limit: 20);
    if (transactions != null && transactions['transactions'] != null) {
      setState(() => _walletTransactions = transactions['transactions']);
    }
    
    setState(() => _isLoading = false);
  }

  Future<void> _loadOpcomPrices() async {
    setState(() => _isPriceLoading = true);
    
    final result = await userApiService.getOpcomPrices(period: _selectedPeriod);
    
    if (result != null && result['success'] == true && result['data'] != null) {
      setState(() {
        _priceData = PriceData.fromJson(result['data']);
      });
    } else {
      // Generate fallback data for demo
      setState(() {
        _priceData = _generateFallbackPriceData();
      });
    }
    
    setState(() => _isPriceLoading = false);
  }
  
  PriceData _generateFallbackPriceData() {
    // Generate demo price data when API is unavailable
    final now = DateTime.now();
    final prices = <PricePoint>[];
    
    // Generate 24 hourly prices with realistic pattern
    for (int hour = 0; hour < 24; hour++) {
      // Price pattern: lower at night, higher during day
      final basePrice = 450.0;
      final hourFactor = 1 + 0.3 * _sin((hour - 6) * 3.14159 / 12);
      final noise = (hour * 7 % 60) - 30; // Deterministic "noise"
      final priceMwh = basePrice * hourFactor + noise;
      
      prices.add(PricePoint(
        timestamp: DateTime(now.year, now.month, now.day, hour),
        priceLeiMwh: priceMwh,
        priceLeiKwh: priceMwh / 1000,
        hour: hour,
      ));
    }
    
    final priceValues = prices.map((p) => p.priceLeiMwh).toList();
    final minPrice = priceValues.reduce((a, b) => a < b ? a : b);
    final maxPrice = priceValues.reduce((a, b) => a > b ? a : b);
    final avgPrice = priceValues.reduce((a, b) => a + b) / priceValues.length;
    final currentPrice = prices[now.hour].priceLeiMwh;
    final prevPrice = prices[(now.hour - 1) % 24].priceLeiMwh;
    final change = currentPrice - prevPrice;
    final changePercent = (change / prevPrice) * 100;
    
    return PriceData(
      date: '${now.day.toString().padLeft(2, '0')}/${now.month.toString().padLeft(2, '0')}/${now.year}',
      period: _selectedPeriod,
      prices: prices,
      statistics: PriceStats(
        minLeiMwh: minPrice,
        maxLeiMwh: maxPrice,
        avgLeiMwh: avgPrice,
        minLeiKwh: minPrice / 1000,
        maxLeiKwh: maxPrice / 1000,
        avgLeiKwh: avgPrice / 1000,
      ),
      change: PriceChange(
        absoluteLeiMwh: change,
        absoluteLeiKwh: change / 1000,
        percent: changePercent,
        direction: change > 0 ? 'up' : (change < 0 ? 'down' : 'unchanged'),
      ),
      currentPriceLeiMwh: currentPrice,
      currentPriceLeiKwh: currentPrice / 1000,
      currentHour: now.hour,
      source: 'Demo',
      dataPoints: 24,
    );
  }
  
  double _sin(double x) {
    // Simple sine approximation
    x = x % (2 * 3.14159);
    if (x > 3.14159) x -= 2 * 3.14159;
    return x - (x * x * x) / 6 + (x * x * x * x * x) / 120;
  }

  void _onPeriodChanged(String period) {
    setState(() => _selectedPeriod = period);
    _loadOpcomPrices();
  }

  Future<void> _savePreferences() async {
    setState(() => _isSaving = true);
    
    final result = await userApiService.updateTradingPreferences(
      sellingEnabled: _sellingEnabled,
      buyingEnabled: _buyingEnabled,
      priceMode: _priceMode,
      discountPercent: _discountPercent,
      fixedPriceLeiKwh: _fixedPrice,
    );
    
    setState(() => _isSaving = false);
    
    if (result != null && result['error'] == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Preferințe salvate cu succes!'), backgroundColor: Colors.green),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result?['error'] ?? 'Eroare la salvare'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1C1C1E),
        title: Text('P2P Trading', style: GoogleFonts.inter(color: Colors.white)),
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
            Tab(text: 'Wallet', icon: Icon(Icons.account_balance_wallet)),
            Tab(text: 'Istoric', icon: Icon(Icons.history)),
            Tab(text: 'Setări', icon: Icon(Icons.settings)),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFFB3B3B3)))
          : TabBarView(
              controller: _tabController,
              children: [
                _buildPriceChartTab(),
                _buildWalletTab(),
                _buildHistoryTab(),
                _buildSettingsTab(),
              ],
            ),
    );
  }

  Widget _buildPriceChartTab() {
    return SingleChildScrollView(
      physics: const ClampingScrollPhysics(),
      child: PriceChartWidget(
        priceData: _priceData,
        isLoading: _isPriceLoading,
        selectedPeriod: _selectedPeriod,
        onPeriodChanged: _onPeriodChanged,
        onRefresh: _loadOpcomPrices,
      ),
    );
  }

  Widget _buildSettingsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle('Participare la Trading'),
          const SizedBox(height: 12),
          _buildToggleCard(
            'Vânzare către vecini',
            'Permite vânzarea surplusului de energie către alte case',
            Icons.sell,
            _sellingEnabled,
            (value) => setState(() => _sellingEnabled = value),
          ),
          const SizedBox(height: 12),
          _buildToggleCard(
            'Cumpărare de la vecini',
            'Permite cumpărarea energiei de la alte case înainte de import din rețea',
            Icons.shopping_cart,
            _buyingEnabled,
            (value) => setState(() => _buyingEnabled = value),
          ),
          const SizedBox(height: 24),
          _buildSectionTitle('Preț de Vânzare'),
          const SizedBox(height: 12),
          _buildPriceModeSelector(),
          const SizedBox(height: 16),
          if (_priceMode == 'discount') _buildDiscountSlider(),
          if (_priceMode == 'fixed') _buildFixedPriceInput(),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _isSaving ? null : _savePreferences,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFB3B3B3),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: _isSaving
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text('Salvează Preferințele', style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.black)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWalletTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildWalletCard(),
          const SizedBox(height: 24),
          _buildTradingStatsCard(),
          const SizedBox(height: 24),
          _buildSectionTitle('Tranzacții Recente'),
          const SizedBox(height: 12),
          ..._walletTransactions.take(10).map((tx) => _buildWalletTransactionItem(tx)),
          if (_walletTransactions.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text('Nicio tranzacție încă', style: GoogleFonts.inter(color: Colors.white54)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHistoryTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle('Istoric Trading P2P'),
          const SizedBox(height: 12),
          ..._tradingHistory.map((trade) => _buildTradeItem(trade)),
          if (_tradingHistory.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text('Nicio tranzacție P2P încă', style: GoogleFonts.inter(color: Colors.white54)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.white),
    );
  }

  Widget _buildToggleCard(String title, String subtitle, IconData icon, bool value, Function(bool) onChanged) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: value ? const Color(0xFFB3B3B3) : Colors.white12),
        boxShadow: value ? [
          BoxShadow(
            color: const Color(0xFFB3B3B3).withOpacity(0.15),
            blurRadius: 8,
            spreadRadius: 0,
          ),
        ] : null,
      ),
      child: Row(
        children: [
          Icon(icon, color: value ? const Color(0xFFB3B3B3) : Colors.white54, size: 28),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w500)),
                const SizedBox(height: 4),
                Text(subtitle, style: GoogleFonts.inter(color: Colors.white54, fontSize: 12)),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: const Color(0xFFB3B3B3),
          ),
        ],
      ),
    );
  }

  Widget _buildPriceModeSelector() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _priceMode = 'discount'),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: _priceMode == 'discount' ? const Color(0xFFB3B3B3) : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    '% Discount',
                    style: GoogleFonts.inter(
                      color: _priceMode == 'discount' ? Colors.black : Colors.white54,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ),
          ),
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _priceMode = 'fixed'),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: _priceMode == 'fixed' ? const Color(0xFFB3B3B3) : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    'Preț Fix',
                    style: GoogleFonts.inter(
                      color: _priceMode == 'fixed' ? Colors.black : Colors.white54,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiscountSlider() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Discount față de prețul rețelei', style: GoogleFonts.inter(color: Colors.white)),
              Text('${_discountPercent.toInt()}%', style: GoogleFonts.inter(color: const Color(0xFFB3B3B3), fontWeight: FontWeight.w600, fontSize: 18)),
            ],
          ),
          Slider(
            value: _discountPercent,
            min: 0,
            max: 50,
            divisions: 50,
            activeColor: const Color(0xFFB3B3B3),
            inactiveColor: Colors.white24,
            onChanged: (value) => setState(() => _discountPercent = value),
          ),
          Text(
            'Vecinii vor plăti ${100 - _discountPercent.toInt()}% din prețul rețelei',
            style: GoogleFonts.inter(color: Colors.white54, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildFixedPriceInput() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Preț fix per kWh', style: GoogleFonts.inter(color: Colors.white)),
          const SizedBox(height: 12),
          TextField(
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: GoogleFonts.inter(color: Colors.white),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]')),
              _DecimalTextInputFormatter(),
            ],
            decoration: InputDecoration(
              hintText: 'Ex: 0.80',
              hintStyle: GoogleFonts.inter(color: Colors.white38),
              suffixText: 'lei/kWh',
              suffixStyle: GoogleFonts.inter(color: Colors.white54),
              filled: true,
              fillColor: Colors.white.withOpacity(0.05),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
            ),
            controller: _fixedPriceController,
            onChanged: (value) {
              // Replace comma with dot for parsing
              final normalized = value.replaceAll(',', '.');
              final parsed = double.tryParse(normalized);
              if (parsed != null && parsed >= 0) {
                _fixedPrice = parsed;
              }
            },
          ),
          const SizedBox(height: 8),
          Text(
            'Folosește punct (.) sau virgulă (,) pentru zecimale',
            style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
          ),
        ],
      ),
    );
  }

  Widget _buildWalletCard() {
    final balance = _wallet?['balance_lei'] ?? 0.0;
    final earned = _wallet?['total_earned_lei'] ?? 0.0;
    final spent = _wallet?['total_spent_lei'] ?? 0.0;
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1C1C1E), Color(0xFF2d2d44)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFB3B3B3).withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_balance_wallet, color: Color(0xFFB3B3B3), size: 28),
              const SizedBox(width: 12),
              Text('Wallet Virtual', style: GoogleFonts.inter(color: Colors.white, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 20),
          Text(
            '${balance.toStringAsFixed(2)} lei',
            style: GoogleFonts.inter(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Câștigat', style: GoogleFonts.inter(color: Colors.white54, fontSize: 12)),
                    Text('+${earned.toStringAsFixed(2)} lei', style: GoogleFonts.inter(color: Colors.green, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Cheltuit', style: GoogleFonts.inter(color: Colors.white54, fontSize: 12)),
                    Text('-${spent.toStringAsFixed(2)} lei', style: GoogleFonts.inter(color: Colors.red, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTradingStatsCard() {
    if (_tradingStats == null) return const SizedBox.shrink();
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Statistici Trading', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: _buildStatItem('Vândut', '${(_tradingStats!['total_energy_sold_kwh'] ?? 0).toStringAsFixed(2)} kWh', Colors.green)),
              Expanded(child: _buildStatItem('Cumpărat', '${(_tradingStats!['total_energy_bought_kwh'] ?? 0).toStringAsFixed(2)} kWh', Colors.orange)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _buildStatItem('Tranzacții vânzare', '${_tradingStats!['sell_count'] ?? 0}', Colors.green)),
              Expanded(child: _buildStatItem('Tranzacții cumpărare', '${_tradingStats!['buy_count'] ?? 0}', Colors.orange)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.inter(color: Colors.white54, fontSize: 12)),
        const SizedBox(height: 4),
        Text(value, style: GoogleFonts.inter(color: color, fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _buildWalletTransactionItem(Map<String, dynamic> tx) {
    final type = tx['transaction_type'] ?? '';
    final amount = tx['amount_lei'] ?? 0.0;
    final isCredit = type == 'credit' || type == 'vpp_bonus';
    
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            isCredit ? Icons.arrow_downward : Icons.arrow_upward,
            color: isCredit ? Colors.green : Colors.red,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(tx['description'] ?? type, style: GoogleFonts.inter(color: Colors.white, fontSize: 13)),
                Text(tx['created_at']?.toString().substring(0, 16) ?? '', style: GoogleFonts.inter(color: Colors.white38, fontSize: 11)),
              ],
            ),
          ),
          Text(
            '${isCredit ? '+' : '-'}${amount.toStringAsFixed(2)} lei',
            style: GoogleFonts.inter(color: isCredit ? Colors.green : Colors.red, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildTradeItem(Map<String, dynamic> trade) {
    final type = trade['transaction_type'] ?? '';
    final isSell = type == 'sell';
    final energy = trade['energy_kwh'] ?? 0.0;
    final price = trade['price_lei_kwh'] ?? 0.0;
    final total = trade['total_value_lei'] ?? 0.0;
    final counterparty = trade['counterparty_house_id'] ?? '?';
    
    return GestureDetector(
      onTap: () => _showTradeDetails(trade),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF1C1C1E),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSell ? Colors.green.withOpacity(0.3) : Colors.orange.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: (isSell ? Colors.green : Colors.orange).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                isSell ? Icons.sell : Icons.shopping_cart,
                color: isSell ? Colors.green : Colors.orange,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isSell ? 'Vândut către Casa $counterparty' : 'Cumpărat de la Casa $counterparty',
                    style: GoogleFonts.inter(color: Colors.white, fontSize: 13),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${energy.toStringAsFixed(3)} kWh @ ${price.toStringAsFixed(2)} lei/kWh',
                    style: GoogleFonts.inter(color: Colors.white54, fontSize: 11),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${isSell ? '+' : '-'}${total.toStringAsFixed(2)} lei',
                  style: GoogleFonts.inter(color: isSell ? Colors.green : Colors.orange, fontWeight: FontWeight.w600),
                ),
                const Icon(Icons.chevron_right, color: Colors.white24, size: 16),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showTradeDetails(Map<String, dynamic> trade) {
    final type = trade['transaction_type'] ?? '';
    final isSell = type == 'sell';
    final energy = trade['energy_kwh'] ?? 0.0;
    final price = trade['price_lei_kwh'] ?? 0.0;
    final total = trade['total_value_lei'] ?? 0.0;
    final gridPrice = trade['grid_price_lei_kwh'] ?? 0.0;
    final counterparty = trade['counterparty_house_id'] ?? '?';
    final sellerHouse = trade['seller_house_id'] ?? '?';
    final buyerHouse = trade['buyer_house_id'] ?? '?';
    
    // Parse timestamps
    String simTime = '-';
    final simTimestamp = trade['sim_timestamp'];
    if (simTimestamp != null) {
      try {
        final dt = DateTime.parse(simTimestamp);
        simTime = '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
      } catch (_) {}
    }
    
    // Calculate savings
    final savings = (gridPrice - price) * energy;
    
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: const BoxDecoration(
          color: Color(0xFF1C1C1E),
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: (isSell ? Colors.green : Colors.orange).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    isSell ? Icons.sell : Icons.shopping_cart,
                    color: isSell ? Colors.green : Colors.orange,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isSell ? 'Energie Vândută' : 'Energie Cumpărată',
                        style: GoogleFonts.inter(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600),
                      ),
                      Text(
                        isSell ? 'Către Casa $counterparty' : 'De la Casa $counterparty',
                        style: GoogleFonts.inter(color: Colors.white54, fontSize: 14),
                      ),
                    ],
                  ),
                ),
                Text(
                  '${isSell ? '+' : '-'}${total.toStringAsFixed(2)} lei',
                  style: GoogleFonts.inter(
                    color: isSell ? Colors.green : Colors.orange,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            _buildDetailRow('Energie', '${energy.toStringAsFixed(3)} kWh'),
            _buildDetailRow('Preț P2P', '${price.toStringAsFixed(2)} lei/kWh'),
            _buildDetailRow('Preț Rețea', '${gridPrice.toStringAsFixed(2)} lei/kWh'),
            if (!isSell && savings > 0)
              _buildDetailRow('Economie', '${savings.toStringAsFixed(2)} lei', valueColor: Colors.green),
            const Divider(color: Colors.white12, height: 24),
            _buildDetailRow('Vânzător', 'Casa $sellerHouse'),
            _buildDetailRow('Cumpărător', 'Casa $buyerHouse'),
            _buildDetailRow('Ora Simulării', simTime),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                style: TextButton.styleFrom(
                  backgroundColor: Colors.white.withOpacity(0.1),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: Text('Închide', style: GoogleFonts.inter(color: Colors.white70)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: GoogleFonts.inter(color: Colors.white54, fontSize: 14)),
          Text(value, style: GoogleFonts.inter(color: valueColor ?? Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}


/// Custom TextInputFormatter that allows only one decimal separator (. or ,)
/// and converts comma to dot for consistent parsing
class _DecimalTextInputFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final text = newValue.text;
    
    // Count decimal separators (both . and ,)
    int separatorCount = 0;
    for (int i = 0; i < text.length; i++) {
      if (text[i] == '.' || text[i] == ',') {
        separatorCount++;
      }
    }
    
    // If more than one separator, reject the change
    if (separatorCount > 1) {
      return oldValue;
    }
    
    return newValue;
  }
}
