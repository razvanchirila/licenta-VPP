import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/energy_flow.dart';

class TopIndicator extends StatelessWidget {
  final double value;
  final String label;
  final Color valueColor;
  final String? semanticsId;

  const TopIndicator({
    super.key,
    required this.value,
    required this.label,
    required this.valueColor,
    this.semanticsId,
  });

  @override
  Widget build(BuildContext context) {
    return _PowerSemantics(
      id: semanticsId,
      label: label,
      value: '${value.toStringAsFixed(1)} kW',
      child: Column(
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
          Text(label, style: _flowLabelStyle),
        ],
      ),
    );
  }
}

class BottomIndicator extends StatelessWidget {
  /// Positive = import from the grid, negative = export.
  final double value;
  final String label;
  final String? semanticsId;

  const BottomIndicator({
    super.key,
    required this.value,
    required this.label,
    this.semanticsId,
  });

  @override
  Widget build(BuildContext context) {
    final isActive = value.abs() > FlowThresholds.gridKw;
    final direction = !isActive
        ? ''
        : value > 0
            ? ' import'
            : ' export';
    return _PowerSemantics(
      id: semanticsId,
      label: label,
      value: '${value.abs().toStringAsFixed(1)} kW$direction',
      child: Column(
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
          Text(label, style: _flowLabelStyle),
        ],
      ),
    );
  }
}

/// Energy traded with the other houses: `value` > 0 = bought, < 0 = sold. It has no line in the
/// picture (it travels over the grid connection), so the label carries the direction.
class NeighbourIndicator extends StatelessWidget {
  final double value;

  const NeighbourIndicator({super.key, required this.value});

  @override
  Widget build(BuildContext context) {
    final isActive = value.abs() > FlowThresholds.gridKw;
    final buying = value > 0;
    return _PowerSemantics(
      id: 'home-p2p',
      label: 'Vecini',
      value: '${value.abs().toStringAsFixed(1)} kW${!isActive ? '' : buying ? ' cumpărare' : ' vânzare'}',
      child: Column(
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
          Text(!isActive ? 'VECINI' : (buying ? 'DE LA VECINI' : 'CĂTRE VECINI'), style: _flowLabelStyle),
        ],
      ),
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
    final direction = power > FlowThresholds.idleKw
        ? ' încărcare'
        : power < -FlowThresholds.idleKw
            ? ' descărcare'
            : '';

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _PowerSemantics(
              id: 'home-battery',
              label: 'Baterie',
              value: '${displayPower.toStringAsFixed(1)} kW$direction',
              child: Text(
                '${displayPower.toStringAsFixed(1)} kW',
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            ExcludeSemantics(
              child: Text(
                ' · ',
                style: GoogleFonts.inter(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            _PowerSemantics(
              id: 'home-soc',
              label: 'Nivel baterie',
              value: '$percentage%',
              child: Text(
                '$percentage%',
                style: GoogleFonts.inter(
                  color: batteryLevelColor(percentage),
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        ExcludeSemantics(child: Text('BATERIE', style: _flowLabelStyle)),
      ],
    );
  }
}

TextStyle get _flowLabelStyle => GoogleFonts.inter(
      color: Colors.white.withValues(alpha: 0.5),
      fontSize: 10,
      fontWeight: FontWeight.w600,
      letterSpacing: 1.2,
    );

/// One readable node per value ("Solar 3.1 kW") instead of two loose text fragments.
class _PowerSemantics extends StatelessWidget {
  final String? id;
  final String label;
  final String value;
  final Widget child;

  const _PowerSemantics({required this.id, required this.label, required this.value, required this.child});

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        identifier: id,
        label: label,
        value: value,
        excludeSemantics: true,
        child: child,
      );
}
