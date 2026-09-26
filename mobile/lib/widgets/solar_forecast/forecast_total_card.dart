import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

class ForecastTotalCard extends StatelessWidget {
  final double totalKwh;
  final String dayLabel;

  const ForecastTotalCard({super.key, required this.totalKwh, required this.dayLabel});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.amber.withValues(alpha: 0.2), AppColors.amberDark.withValues(alpha: 0.1)],
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.amber.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(color: AppColors.amber.withValues(alpha: 0.2), shape: BoxShape.circle),
                child: const Icon(Icons.wb_sunny_rounded, color: AppColors.amber, size: 32),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Producție estimată $dayLabel',
                      style: GoogleFonts.inter(color: Colors.white70, fontSize: 14),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          totalKwh.toStringAsFixed(1),
                          style: GoogleFonts.inter(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'kWh',
                          style: GoogleFonts.inter(color: Colors.white70, fontSize: 18, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
