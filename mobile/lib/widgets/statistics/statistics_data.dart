import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/models/sim_prices.dart';

const TextStyle statsCardTitle = TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white);

class StatisticsData {
  final ConsumptionSummary summary;
  final TopConsumersResponse topConsumers;
  final MonthlyComparison comparison;
  final ChartData chart;

  const StatisticsData({
    required this.summary,
    required this.topConsumers,
    required this.comparison,
    required this.chart,
  });
}

class StatisticsRules {
  StatisticsRules._();

  /// The simulated day usually differs from the wall clock, so the chart is anchored to it.
  static DateTime simulatedNow(SimPrices? prices, DateTime fallback) =>
      prices?.current?.timestamp ?? DateTime.tryParse(prices?.date ?? '') ?? fallback;

  /// The backend clamps the window to the simulated data.
  static (DateTime, DateTime) chartRange(String period, DateTime now) {
    switch (period) {
      case 'day':
        return (now.subtract(const Duration(days: 1)), now);
      case 'week':
        return (now.subtract(const Duration(days: 7)), now);
      case 'year':
        return (DateTime(now.year - 1, now.month, 1), now);
      default:
        return (now.subtract(const Duration(days: 30)), now);
    }
  }

  static double chartInterval(List<ChartDataPoint> points) {
    if (points.isEmpty) return 1;
    final maxValue = points.map((e) => e.valueKwh).reduce((a, b) => a > b ? a : b);
    return maxValue > 0 ? maxValue / 4 : 1;
  }

  static double bottomTitleInterval(int count) {
    if (count <= 7) return 1;
    if (count <= 14) return 2;
    if (count <= 30) return 5;
    return 7;
  }

  static Color rankColor(int rank) {
    switch (rank) {
      case 1:
        return Colors.amber;
      case 2:
        return Colors.grey;
      case 3:
        return Colors.brown;
      default:
        return AppColors.blue;
    }
  }
}
