import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/energy_flow.dart';

class TopIndicator extends StatelessWidget {
  final double value;
  final String label;
  final Color valueColor;

  const TopIndicator({
    super.key,
    required this.value,
    required this.label,
    required this.valueColor,
  });

  String _getLocalizedLabel(String label) {
    switch (label) {
      case 'SOLAR':
        return 'SOLAR';
      case 'HOME':
        return 'CONSUM';
      default:
        return label;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '${value.toStringAsFixed(1)} kW',
          style: GoogleFonts.inter(
            color: valueColor,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          _getLocalizedLabel(label),
          style: GoogleFonts.inter(
            color: Colors.white.withValues(alpha: 0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

class BottomIndicator extends StatelessWidget {
  final double value;
  final String label;

  const BottomIndicator({
    super.key,
    required this.value,
    required this.label,
  });

  String _getLocalizedLabel(String label) {
    switch (label) {
      case 'GRID':
        return 'REȚEA';
      default:
        return label;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isActive = value.abs() > FlowThresholds.gridKw;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '${value.abs().toStringAsFixed(1)} kW',
          style: GoogleFonts.inter(
            color: isActive ? Colors.white : Colors.white.withValues(alpha: 0.5),
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          _getLocalizedLabel(label),
          style: GoogleFonts.inter(
            color: Colors.white.withValues(alpha: 0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

/// `power` > 0 = charging, < 0 = discharging.
class BatteryIndicator extends StatelessWidget {
  final double power;
  final int percentage;

  const BatteryIndicator({
    super.key,
    required this.power,
    required this.percentage,
  });

  @override
  Widget build(BuildContext context) {
    final displayPower = power.abs();

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${displayPower.toStringAsFixed(1)} kW',
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              ' · ',
              style: GoogleFonts.inter(
                color: Colors.white.withValues(alpha: 0.5),
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '$percentage%',
              style: GoogleFonts.inter(
                color: batteryLevelColor(percentage),
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          'BATERIE',
          style: GoogleFonts.inter(
            color: Colors.white.withValues(alpha: 0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}
