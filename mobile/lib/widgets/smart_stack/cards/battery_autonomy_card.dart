import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Card for displaying battery autonomy (same style as TemperatureCard)
class BatteryAutonomyCard extends StatelessWidget {
  final double batteryPercent;
  final double batteryCapacityKwh;
  final double currentConsumptionKw;
  final VoidCallback? onTap;

  const BatteryAutonomyCard({
    super.key,
    required this.batteryPercent,
    required this.batteryCapacityKwh,
    required this.currentConsumptionKw,
    this.onTap,
  });

  /// Calculate estimated runtime
  String _calculateRuntime() {
    if (currentConsumptionKw <= 0) return '∞';

    final availableEnergy = batteryCapacityKwh * (batteryPercent / 100);
    final hours = availableEnergy / currentConsumptionKw;

    if (hours >= 24) {
      return '${(hours / 24).toStringAsFixed(1)}d';
    } else if (hours >= 1) {
      return '${hours.toStringAsFixed(1)}h';
    } else {
      return '${(hours * 60).toStringAsFixed(0)}m';
    }
  }

  Color _getBatteryColor() {
    if (batteryPercent >= 60) {
      return const Color(0xFF22C55E); // Green
    } else if (batteryPercent >= 30) {
      return const Color(0xFFFBBF24); // Yellow
    } else {
      return const Color(0xFFEF4444); // Red
    }
  }

  @override
  Widget build(BuildContext context) {
    final runtime = _calculateRuntime();
    final batteryColor = _getBatteryColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: batteryColor.withOpacity(0.15),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: batteryColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Battery icon
          Stack(
            alignment: Alignment.center,
            children: [
              Icon(
                Icons.battery_full_rounded,
                color: batteryColor,
                size: 24,
              ),
            ],
          ),
          const SizedBox(width: 8),
          // Runtime and label
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    runtime,
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${batteryPercent.round()}%',
                    style: GoogleFonts.inter(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              Text(
                'Autonomie',
                style: GoogleFonts.inter(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
      ),
    );
  }
}
