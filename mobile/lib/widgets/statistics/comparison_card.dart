import 'package:flutter/material.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';

class MonthlyComparisonCard extends StatelessWidget {
  final MonthlyComparison comparison;

  const MonthlyComparisonCard({super.key, required this.comparison});

  @override
  Widget build(BuildContext context) {
    final isIncrease = comparison.trend == 'increased';
    final isDecrease = comparison.trend == 'decreased';
    final trendColor = isIncrease
        ? Colors.red
        : isDecrease
            ? Colors.green
            : Colors.grey;

    return SurfaceCard(
      bordered: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Flexible(
                  child: const Text('Comparație lunară', style: statsCardTitle, overflow: TextOverflow.ellipsis)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: trendColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      isIncrease
                          ? Icons.arrow_upward
                          : isDecrease
                              ? Icons.arrow_downward
                              : Icons.remove,
                      size: 16,
                      color: trendColor,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${comparison.changePercent?.abs().toStringAsFixed(1) ?? '0'}%',
                      style: TextStyle(fontWeight: FontWeight.bold, color: trendColor),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _MonthColumn(
                  title: comparison.currentMonth,
                  kwh: comparison.currentMonthKwh,
                  note: comparison.isProjection
                      ? 'Proiecție: ${formatKwh(comparison.projectedTotalKwh, decimals: 2)}'
                      : null,
                ),
              ),
              Expanded(
                child: _MonthColumn(title: comparison.previousMonth, kwh: comparison.previousMonthKwh),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MonthColumn extends StatelessWidget {
  final String title;
  final double kwh;
  final String? note;

  const _MonthColumn({required this.title, required this.kwh, this.note});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        Text(
          formatKwh(kwh, decimals: 2),
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
        ),
        if (note != null)
          Text(
            note!,
            style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontStyle: FontStyle.italic),
          ),
      ],
    );
  }
}
