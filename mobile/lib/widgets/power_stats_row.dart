import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class PowerStatsRow extends StatelessWidget {
  final String? evPower;
  final String evLabel;
  final String solarPower;
  final String solarLabel;
  final String homePower;
  final String homeLabel;

  const PowerStatsRow({
    super.key,
    this.evPower,
    this.evLabel = 'MODEL 3',
    this.solarPower = '3.1 kW',
    this.solarLabel = 'SOLAR',
    this.homePower = '3.0 kW',
    this.homeLabel = 'HOME',
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // EV / Model 3 (optional)
          if (evPower != null)
            _PowerStatItem(
              value: evPower!,
              label: evLabel,
            )
          else
            const SizedBox(width: 80),
          
          // Solar
          _PowerStatItem(
            value: solarPower,
            label: solarLabel,
          ),
          
          // Home
          _PowerStatItem(
            value: homePower,
            label: homeLabel,
          ),
        ],
      ),
    );
  }
}

// Versiune animată a PowerStatsRow
class AnimatedPowerStatsRow extends StatelessWidget {
  final double solarPower;
  final String solarLabel;
  final double homePower;
  final String homeLabel;

  const AnimatedPowerStatsRow({
    super.key,
    this.solarPower = 3.1,
    this.solarLabel = 'SOLAR',
    this.homePower = 3.0,
    this.homeLabel = 'HOME',
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // Solar
          _AnimatedPowerStatItem(
            value: solarPower,
            label: solarLabel,
            valueColor: const Color(0xFFFBBF24), // Galben pentru solar
          ),
          
          // Home
          _AnimatedPowerStatItem(
            value: homePower,
            label: homeLabel,
          ),
        ],
      ),
    );
  }
}

class _PowerStatItem extends StatelessWidget {
  final String value;
  final String label;

  const _PowerStatItem({
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          value,
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.5,
          ),
        ),
      ],
    );
  }
}

class _AnimatedPowerStatItem extends StatelessWidget {
  final double value;
  final String label;
  final Color? valueColor;

  const _AnimatedPowerStatItem({
    required this.value,
    required this.label,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: value),
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeOutCubic,
          builder: (context, animatedValue, child) {
            return Text(
              '${animatedValue.toStringAsFixed(1)} kW',
              style: GoogleFonts.inter(
                color: valueColor ?? Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            );
          },
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.5,
          ),
        ),
      ],
    );
  }
}
