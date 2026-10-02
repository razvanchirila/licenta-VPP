import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

/// Autonomy = energy above the backup reserve / current load.
class BatteryAutonomyCard extends StatelessWidget {
  final bool hasBattery;
  final double batteryPercent;
  final double availableKwh;
  final double currentConsumptionKw;
  final VoidCallback? onTap;

  const BatteryAutonomyCard({
    super.key,
    required this.hasBattery,
    required this.batteryPercent,
    required this.availableKwh,
    required this.currentConsumptionKw,
    this.onTap,
  });

  String _calculateRuntime() {
    if (availableKwh <= 0) return '0m';
    if (currentConsumptionKw <= 0.001) return '∞';

    final hours = availableKwh / currentConsumptionKw;
    if (hours >= 24) {
      return '${(hours / 24).toStringAsFixed(1)}d';
    } else if (hours >= 1) {
      return '${hours.toStringAsFixed(1)}h';
    }
    return '${(hours * 60).toStringAsFixed(0)}m';
  }

  Color _getBatteryColor() {
    if (!hasBattery) return AppColors.slate;
    if (batteryPercent >= 60) return AppColors.green;
    if (batteryPercent >= 30) return AppColors.amber;
    return AppColors.red;
  }

  @override
  Widget build(BuildContext context) {
    final batteryColor = _getBatteryColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: batteryColor.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: batteryColor.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              hasBattery ? Icons.battery_full_rounded : Icons.battery_unknown_rounded,
              color: batteryColor,
              size: 24,
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          hasBattery ? _calculateRuntime() : '--',
                          style: GoogleFonts.inter(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          hasBattery ? '${batteryPercent.round()}%' : '',
                          style: GoogleFonts.inter(
                            color: Colors.white.withValues(alpha: 0.7),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    hasBattery ? 'Autonomie' : 'Fără baterie',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
