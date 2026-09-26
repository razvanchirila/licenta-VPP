import 'package:flutter/material.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/widgets/common/stat_tile.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';

class ConsumptionSummaryCard extends StatelessWidget {
  final ConsumptionSummary summary;

  const ConsumptionSummaryCard({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    if (!summary.hasData) {
      return const StatsEmptyCard(message: 'Nu există date de consum pentru această perioadă');
    }

    return SurfaceCard(
      bordered: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Sumar consum dispozitive', style: statsCardTitle),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _stat('Total', formatKwh(summary.totalKwh, decimals: 2), Icons.bolt, AppColors.blue),
              ),
              Expanded(
                child: _stat(
                  'Cost estimat',
                  '${summary.estimatedCost.toStringAsFixed(2)} ${summary.currency}',
                  Icons.attach_money,
                  Colors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _stat(
                  'Medie zilnică',
                  formatKwh(summary.averageDailyKwh, decimals: 2),
                  Icons.calendar_today,
                  Colors.blue,
                ),
              ),
              Expanded(
                child: _stat(
                  'Perioada anterioară',
                  formatKwh(summary.previousPeriodKwh, decimals: 2),
                  Icons.history,
                  Colors.grey,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _stat(String label, String value, IconData icon, Color color) => StatTile(
        label: label,
        value: value,
        icon: icon,
        iconColor: color,
        labelStyle: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
        valueStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
      );
}

class StatsEmptyCard extends StatelessWidget {
  final String message;

  const StatsEmptyCard({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      bordered: false,
      child: Center(
        child: Text(message, style: const TextStyle(color: AppColors.textSecondary), textAlign: TextAlign.center),
      ),
    );
  }
}
