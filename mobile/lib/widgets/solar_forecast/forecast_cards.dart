import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/solar_forecast_data.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_labels.dart';

class PeakHoursCard extends StatelessWidget {
  final List<int> peakHours;

  const PeakHoursCard({super.key, required this.peakHours});

  @override
  Widget build(BuildContext context) {
    if (peakHours.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.green.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.green.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.green.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.tips_and_updates_rounded, color: AppColors.green, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Recomandare',
                  style: GoogleFonts.inter(color: AppColors.green, fontSize: 14, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  'Folosește aparatele cu consum mare între orele ${ForecastLabels.peakHoursText(peakHours)} '
                  'pentru a maximiza autoconsumul.',
                  style: GoogleFonts.inter(color: Colors.white70, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class DailyForecastList extends StatelessWidget {
  final List<DailyForecast> forecasts;
  final String? selectedDate;
  final ValueChanged<String> onSelected;

  const DailyForecastList({super.key, required this.forecasts, required this.selectedDate, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    if (forecasts.isEmpty) return const SizedBox.shrink();
    final maxKwh = forecasts.map((f) => f.kWh).reduce((a, b) => a > b ? a : b);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Toate zilele', style: AppText.cardTitle),
        const SizedBox(height: 16),
        ...forecasts.map(
          (f) => _DayCard(
            forecast: f,
            share: maxKwh > 0 ? f.kWh / maxKwh : 0.0,
            isSelected: f.date == selectedDate,
            onTap: () => onSelected(f.date),
          ),
        ),
      ],
    );
  }
}

class _DayCard extends StatelessWidget {
  final DailyForecast forecast;
  final double share;
  final bool isSelected;
  final VoidCallback onTap;

  const _DayCard({required this.forecast, required this.share, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.amber.withValues(alpha: 0.15) : AppColors.surfaceAlt,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? AppColors.amber.withValues(alpha: 0.5) : Colors.white.withValues(alpha: 0.1),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Flexible(
                  child: Row(
                    children: [
                      if (forecast.isToday)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          margin: const EdgeInsets.only(right: 8),
                          decoration: BoxDecoration(color: AppColors.amber, borderRadius: BorderRadius.circular(4)),
                          child: Text(
                            'AZI',
                            style: GoogleFonts.inter(color: Colors.black, fontSize: 10, fontWeight: FontWeight.w700),
                          ),
                        ),
                      Flexible(
                        child: Text(
                          forecast.formattedDate,
                          style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  formatKwh(forecast.kWh),
                  style: GoogleFonts.inter(
                    color: isSelected ? AppColors.amber : Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: share,
                backgroundColor: Colors.white.withValues(alpha: 0.1),
                valueColor: AlwaysStoppedAnimation(
                  isSelected ? AppColors.amber : AppColors.amber.withValues(alpha: 0.5),
                ),
                minHeight: 6,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ForecastBanner extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String text;

  const ForecastBanner({super.key, required this.icon, required this.color, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: GoogleFonts.inter(color: Colors.white70, fontSize: 13))),
        ],
      ),
    );
  }
}

class ForecastMessage extends StatelessWidget {
  final IconData icon;
  final String message;
  final VoidCallback? onRetry;

  const ForecastMessage({super.key, required this.icon, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white38, size: 64),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center, style: GoogleFonts.inter(color: Colors.white70, fontSize: 16)),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Reîncearcă'),
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.amber, foregroundColor: Colors.black),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
