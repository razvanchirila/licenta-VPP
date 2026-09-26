import 'package:flutter/material.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/widgets/smart_stack/battery_details_popup.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/battery_autonomy_card.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/price_card.dart';

class BatteryPage extends StatelessWidget {
  final Battery? battery;
  final double batteryPercent;
  final double currentConsumptionKw;
  final double? pricePerKwh;
  final bool isPriceRising;
  final VoidCallback? onPriceTap;

  const BatteryPage({
    super.key,
    required this.battery,
    required this.batteryPercent,
    required this.currentConsumptionKw,
    required this.pricePerKwh,
    this.isPriceRising = false,
    this.onPriceTap,
  });

  @override
  Widget build(BuildContext context) {
    final b = battery;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: BatteryAutonomyCard(
              hasBattery: b != null,
              batteryPercent: batteryPercent,
              availableKwh: b?.availableKwh ?? 0.0,
              currentConsumptionKw: currentConsumptionKw,
              onTap: b == null ? null : () => BatteryDetailsPopup.show(context, battery: b),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: PriceCard(
              pricePerKwh: pricePerKwh,
              isRising: isPriceRising,
              onTap: onPriceTap,
            ),
          ),
        ],
      ),
    );
  }
}
