import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';

class TotalConsumptionCard extends StatelessWidget {
  final double totalWatts;
  final int activeCount;

  const TotalConsumptionCard({super.key, required this.totalWatts, required this.activeCount});

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: AppColors.red.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.bolt_rounded, color: AppColors.red, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Consum dispozitive pornite',
                  style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 14),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Semantics(
                  container: true,
                  identifier: 'devices-total',
                  child: Text(
                    formatPowerW(totalWatts),
                    style: GoogleFonts.inter(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.green.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '$activeCount active',
              style: GoogleFonts.inter(color: AppColors.green, fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
