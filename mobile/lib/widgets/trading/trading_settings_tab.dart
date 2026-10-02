import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';

/// Keeps its edits while the user swaps tabs.
class TradingSettingsTab extends StatefulWidget {
  final TradingPrefs prefs;
  final void Function(String message, {bool isError}) onMessage;

  const TradingSettingsTab({super.key, required this.prefs, required this.onMessage});

  @override
  State<TradingSettingsTab> createState() => _TradingSettingsTabState();
}

class _TradingSettingsTabState extends State<TradingSettingsTab> with AutomaticKeepAliveClientMixin {
  static const Color _accent = AppColors.tradingAccent;

  late TextEditingController _fixedPriceController;
  bool _sellingEnabled = true;
  bool _buyingEnabled = true;
  String _priceMode = 'discount';
  double _discountPercent = 20.0;
  double _fixedPrice = 0.8;
  bool _isSaving = false;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _fixedPriceController = TextEditingController();
    _applyPrefs(widget.prefs);
  }

  @override
  void didUpdateWidget(TradingSettingsTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.prefs != widget.prefs) _applyPrefs(widget.prefs);
  }

  @override
  void dispose() {
    _fixedPriceController.dispose();
    super.dispose();
  }

  void _applyPrefs(TradingPrefs prefs) {
    _sellingEnabled = prefs.sellingEnabled;
    _buyingEnabled = prefs.buyingEnabled;
    _priceMode = prefs.priceMode;
    _discountPercent = prefs.discountPercent.clamp(0, 50).toDouble();
    _fixedPrice = prefs.fixedPriceLeiKwh;
    _fixedPriceController.text = _fixedPrice.toStringAsFixed(2);
  }

  Future<void> _savePreferences() async {
    setState(() => _isSaving = true);
    try {
      final prefs = await userApiService.updateTradingPreferences(
        sellingEnabled: _sellingEnabled,
        buyingEnabled: _buyingEnabled,
        priceMode: _priceMode,
        discountPercent: _discountPercent,
        fixedPriceLeiKwh: _fixedPrice,
      );
      if (!mounted) return;
      setState(() {
        _sellingEnabled = prefs.sellingEnabled;
        _buyingEnabled = prefs.buyingEnabled;
      });
      widget.onMessage('Preferințe salvate');
    } on ApiException catch (e) {
      widget.onMessage('Eroare la salvare: ${e.message}', isError: true);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Participare la trading', style: AppText.sectionTitle),
          const SizedBox(height: 12),
          _ToggleCard(
            id: 'trading-selling',
            title: 'Vânzare către vecini',
            subtitle: 'Permite vânzarea surplusului de energie către alte case',
            icon: Icons.sell,
            value: _sellingEnabled,
            onChanged: (value) => setState(() => _sellingEnabled = value),
          ),
          const SizedBox(height: 12),
          _ToggleCard(
            id: 'trading-buying',
            title: 'Cumpărare de la vecini',
            subtitle: 'Permite cumpărarea energiei de la alte case înainte de import din rețea',
            icon: Icons.shopping_cart,
            value: _buyingEnabled,
            onChanged: (value) => setState(() => _buyingEnabled = value),
          ),
          const SizedBox(height: 8),
          Text(
            'Casa participă la P2P doar dacă ambele opțiuni sunt active și soldul este de cel puțin 5 lei.',
            style: AppText.hint,
          ),
          const SizedBox(height: 24),
          Text('Preț de vânzare (preferință)', style: AppText.sectionTitle),
          const SizedBox(height: 4),
          Text(
            'În simulare prețul P2P este unic pe comunitate (70% din prețul de import); preferința este doar memorată.',
            style: AppText.hint,
          ),
          const SizedBox(height: 12),
          _PriceModeSelector(mode: _priceMode, onChanged: (m) => setState(() => _priceMode = m)),
          const SizedBox(height: 16),
          if (_priceMode == 'discount')
            _DiscountSlider(value: _discountPercent, onChanged: (v) => setState(() => _discountPercent = v)),
          if (_priceMode == 'fixed')
            _FixedPriceInput(
              controller: _fixedPriceController,
              onChanged: (value) {
                final parsed = double.tryParse(value.replaceAll(',', '.'));
                if (parsed != null && parsed >= 0 && parsed <= 10) _fixedPrice = parsed;
              },
            ),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            child: Semantics(
              container: true,
              identifier: 'trading-save',
              label: 'Salvează preferințele',
              child: ElevatedButton(
                onPressed: _isSaving ? null : _savePreferences,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _accent,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: _isSaving
                    ? const SizedBox(
                        height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : Text('Salvează preferințele',
                        style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.black)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ToggleCard extends StatelessWidget {
  final String id;
  final String title;
  final String subtitle;
  final IconData icon;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _ToggleCard({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    const accent = AppColors.tradingAccent;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: value ? accent : Colors.white12),
        boxShadow: value ? [BoxShadow(color: accent.withValues(alpha: 0.15), blurRadius: 8, spreadRadius: 0)] : null,
      ),
      child: Row(
        children: [
          Icon(icon, color: value ? accent : Colors.white54, size: 28),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w500)),
                const SizedBox(height: 4),
                Text(subtitle, style: AppText.muted),
              ],
            ),
          ),
          Semantics(
            container: true,
            identifier: id,
            label: title,
            child: Switch(value: value, onChanged: onChanged, activeThumbColor: accent),
          ),
        ],
      ),
    );
  }
}

class _PriceModeSelector extends StatelessWidget {
  final String mode;
  final ValueChanged<String> onChanged;

  const _PriceModeSelector({required this.mode, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: AppTheme.surfaceDecoration(),
      child: Row(
        children: [
          _option('discount', '% Discount'),
          _option('fixed', 'Preț fix'),
        ],
      ),
    );
  }

  Widget _option(String value, String label) {
    final selected = mode == value;
    return Expanded(
      child: Semantics(
        container: true,
        identifier: 'trading-mode-$value',
        button: true,
        selected: selected,
        child: GestureDetector(
          onTap: () => onChanged(value),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: selected ? AppColors.tradingAccent : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                label,
                style: GoogleFonts.inter(color: selected ? Colors.black : Colors.white54, fontWeight: FontWeight.w500),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DiscountSlider extends StatelessWidget {
  final double value;
  final ValueChanged<double> onChanged;

  const _DiscountSlider({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: AppTheme.surfaceDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text('Discount față de prețul rețelei', style: GoogleFonts.inter(color: Colors.white)),
              ),
              Semantics(
                container: true,
                identifier: 'trading-discount-value',
                child: Text('${value.toInt()}%',
                    style:
                        GoogleFonts.inter(color: AppColors.tradingAccent, fontWeight: FontWeight.w600, fontSize: 18)),
              ),
            ],
          ),
          Semantics(
            container: true,
            identifier: 'trading-discount',
            label: 'Discount față de prețul rețelei',
            child: Slider(
              value: value,
              min: 0,
              max: 50,
              divisions: 50,
              activeColor: AppColors.tradingAccent,
              inactiveColor: Colors.white24,
              onChanged: onChanged,
            ),
          ),
          Text('Vecinii ar plăti ${100 - value.toInt()}% din prețul rețelei', style: AppText.muted),
        ],
      ),
    );
  }
}

class _FixedPriceInput extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onChanged;

  const _FixedPriceInput({required this.controller, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: AppTheme.surfaceDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Preț fix per kWh', style: GoogleFonts.inter(color: Colors.white)),
          const SizedBox(height: 12),
          Semantics(
            container: true,
            identifier: 'trading-fixed-price',
            label: 'Preț fix per kWh',
            child: TextField(
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: GoogleFonts.inter(color: Colors.white),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]')),
                DecimalTextInputFormatter(),
              ],
              decoration: InputDecoration(
                hintText: 'Ex: 0.80',
                hintStyle: GoogleFonts.inter(color: Colors.white38),
                suffixText: 'lei/kWh',
                suffixStyle: GoogleFonts.inter(color: Colors.white54),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
              ),
              controller: controller,
              onChanged: onChanged,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Între 0 și 10 lei/kWh, cu punct sau virgulă pentru zecimale',
            style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class DecimalTextInputFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    final separators = newValue.text.split('').where((c) => c == '.' || c == ',').length;
    return separators > 1 ? oldValue : newValue;
  }
}
