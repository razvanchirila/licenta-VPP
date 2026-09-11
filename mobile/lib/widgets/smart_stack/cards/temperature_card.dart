import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Card for displaying temperature (indoor or outdoor)
class TemperatureCard extends StatelessWidget {
  final double temperature;
  final String label;
  final IconData icon;
  final Color iconColor;
  final bool isInteractive;
  final VoidCallback? onTap;
  final bool useCelsius;
  final VoidCallback? onUnitToggle;
  final bool showUnitToggle;

  const TemperatureCard({
    super.key,
    required this.temperature,
    required this.label,
    this.icon = Icons.thermostat_rounded,
    this.iconColor = const Color(0xFFFBBF24),
    this.isInteractive = false,
    this.onTap,
    this.useCelsius = true,
    this.onUnitToggle,
    this.showUnitToggle = false,
  });

  String get _displayTemperature {
    final temp = useCelsius ? temperature : (temperature * 9 / 5 + 32);
    return '${temp.round()}°';
  }

  String get _unitLabel => useCelsius ? 'C' : 'F';

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: isInteractive ? onTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isInteractive
              ? const Color(0xFF3B82F6).withOpacity(0.15)
              : Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isInteractive
                ? const Color(0xFF3B82F6).withOpacity(0.3)
                : Colors.white.withOpacity(0.1),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icon
            Icon(
              icon,
              color: iconColor,
              size: 24,
            ),
            const SizedBox(width: 8),
            // Temperature and label
            Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _displayTemperature,
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (showUnitToggle) ...[
                      const SizedBox(width: 2),
                      GestureDetector(
                        onTap: onUnitToggle,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            _unitLabel,
                            style: GoogleFonts.inter(
                              color: Colors.white.withOpacity(0.7),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                Text(
                  label,
                  style: GoogleFonts.inter(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
            if (isInteractive) ...[
              const SizedBox(width: 8),
              Icon(
                Icons.chevron_right_rounded,
                color: Colors.white.withOpacity(0.3),
                size: 18,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
