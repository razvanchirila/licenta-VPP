import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Widget pentru afișarea prețului curent al energiei
/// Cu indicator vizual pentru trend (creștere/scădere)
class PriceIndicator extends StatelessWidget {
  final double pricePerKwh; // Preț în RON/kWh
  final bool isRising; // true = preț în creștere, false = în scădere
  final VoidCallback? onTap;

  const PriceIndicator({
    super.key,
    required this.pricePerKwh,
    required this.isRising,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = isRising ? const Color(0xFFEF4444) : const Color(0xFF22C55E);
    
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: color.withOpacity(0.5),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Trend icon (stock up/down)
            Icon(
              isRising ? Icons.trending_up_rounded : Icons.trending_down_rounded,
              color: color,
              size: 18,
            ),
            const SizedBox(width: 6),
            // Price
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${pricePerKwh.toStringAsFixed(2)} RON',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  '/kWh',
                  style: GoogleFonts.inter(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 10,
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
