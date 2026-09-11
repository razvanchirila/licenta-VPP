import 'package:flutter/material.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/battery_autonomy_card.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/price_card.dart';
import 'package:flutter_interface/widgets/smart_stack/battery_health_popup.dart';

/// Battery page for SmartStack
/// Contains battery autonomy card and price card (equal width like temperature cards)
class BatteryPage extends StatefulWidget {
  final double batteryPercent;
  final double batteryCapacityKwh;
  final double pricePerKwh;
  final bool isPriceRising;
  final VoidCallback? onPriceTap;

  const BatteryPage({
    super.key,
    required this.batteryPercent,
    required this.batteryCapacityKwh,
    this.pricePerKwh = 0.85,
    this.isPriceRising = true,
    this.onPriceTap,
  });

  @override
  State<BatteryPage> createState() => _BatteryPageState();
}

class _BatteryPageState extends State<BatteryPage> {
  @override
  void initState() {
    super.initState();
    appState.addListener(_onStateChanged);
  }

  @override
  void dispose() {
    appState.removeListener(_onStateChanged);
    super.dispose();
  }

  void _onStateChanged() {
    if (mounted) setState(() {});
  }

  void _showBatteryHealthPopup() {
    BatteryHealthPopup.show(
      context,
      batteryPercent: widget.batteryPercent,
      batteryCapacityKwh: widget.batteryCapacityKwh,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          // Battery autonomy card - LEFT
          Expanded(
            child: BatteryAutonomyCard(
              batteryPercent: widget.batteryPercent,
              batteryCapacityKwh: widget.batteryCapacityKwh,
              currentConsumptionKw: appState.totalDevicePowerKw,
              onTap: _showBatteryHealthPopup,
            ),
          ),
          const SizedBox(width: 12),
          // Price card - RIGHT
          Expanded(
            child: PriceCard(
              pricePerKwh: widget.pricePerKwh,
              isRising: widget.isPriceRising,
              onTap: widget.onPriceTap,
            ),
          ),
        ],
      ),
    );
  }
}
