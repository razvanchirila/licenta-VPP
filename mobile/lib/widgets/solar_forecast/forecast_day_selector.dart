import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_labels.dart';

class ForecastDaySelector extends StatelessWidget {
  final List<String> dates;
  final String? selected;
  final ValueChanged<String> onSelected;

  const ForecastDaySelector({super.key, required this.dates, required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return Container(
      height: 44,
      decoration: BoxDecoration(color: AppColors.surfaceAlt, borderRadius: BorderRadius.circular(12)),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: dates.length,
        padding: const EdgeInsets.symmetric(horizontal: 4),
        itemBuilder: (context, index) {
          final date = dates[index];
          final isSelected = date == selected;
          return GestureDetector(
            onTap: () => onSelected(date),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              padding: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: isSelected ? AppColors.amber : Colors.transparent,
                borderRadius: BorderRadius.circular(8),
              ),
              alignment: Alignment.center,
              child: Text(
                ForecastLabels.dayLabel(date, now),
                style: GoogleFonts.inter(
                  color: isSelected ? Colors.black : Colors.white70,
                  fontSize: 14,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
