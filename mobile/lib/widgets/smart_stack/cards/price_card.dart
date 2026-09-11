import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Card for displaying energy price (same style as TemperatureCard)
class PriceCard extends StatelessWidget {
  final double pricePerKwh;
  final bool isRising;
  final VoidCallback? onTap;

  const PriceCard({
    super.key,
    required this.pricePerKwh,
    required this.isRising,
    this.onTap,
  });

  Color get _trendColor =>
      isRising ? const Color(0xFFEF4444) : const Color(0xFF22C55E);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: _trendColor.withOpacity(0.15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: _trendColor.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Trend icon
            Icon(
              isRising
                  ? Icons.trending_up_rounded
                  : Icons.trending_down_rounded,
              color: _trendColor,
              size: 24,
            ),
            const SizedBox(width: 8),
            // Price and label
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
                      pricePerKwh.toStringAsFixed(2),
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(width: 2),
                    Text(
                      'RON',
                      style: GoogleFonts.inter(
                        color: Colors.white.withOpacity(0.7),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                Text(
                  'Preț /kWh',
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
