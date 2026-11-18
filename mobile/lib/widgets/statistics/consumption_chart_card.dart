import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';

class ConsumptionChartCard extends StatelessWidget {
  final ChartData chart;

  const ConsumptionChartCard({super.key, required this.chart});

  @override
  Widget build(BuildContext context) {
    final points = chart.dataPoints;
    return SurfaceCard(
      bordered: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Evoluție consum', style: statsCardTitle),
          Text('Granularitate: $_granularityLabel',
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          SizedBox(
            height: 200,
            child: points.isEmpty
                ? const Center(
                    child: Text('Nu există date pentru grafic', style: TextStyle(color: AppColors.textSecondary)),
                  )
                : LineChart(_chartData(points)),
          ),
        ],
      ),
    );
  }

  LineChartData _chartData(List<ChartDataPoint> points) {
    const axisStyle = TextStyle(fontSize: 10, color: AppColors.textSecondary);
    return LineChartData(
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: StatisticsRules.chartInterval(points),
        getDrawingHorizontalLine: (value) => FlLine(
          color: AppColors.textSecondary.withValues(alpha: 0.2),
          strokeWidth: 1,
        ),
      ),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            getTitlesWidget: (value, meta) => Text(value.toStringAsFixed(1), style: axisStyle),
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 30,
            interval: StatisticsRules.bottomTitleInterval(points.length),
            getTitlesWidget: (value, meta) {
              final index = value.toInt();
              if (index < 0 || index >= points.length) return const SizedBox.shrink();
              return Text(_axisDate(points[index].timestamp), style: axisStyle);
            },
          ),
        ),
        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      borderData: FlBorderData(show: false),
      minY: 0,
      lineBarsData: [
        LineChartBarData(
          spots: [for (var i = 0; i < points.length; i++) FlSpot(i.toDouble(), points[i].valueKwh)],
          isCurved: true,
          color: AppColors.blue,
          barWidth: 3,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(show: true, color: AppColors.blue.withValues(alpha: 0.1)),
        ),
      ],
    );
  }

  String get _granularityLabel {
    switch (chart.granularity) {
      case 'hourly':
        return 'orară';
      case 'weekly':
        return 'săptămânală';
      default:
        return 'zilnică';
    }
  }

  String _axisDate(DateTime date) => chart.granularity == 'hourly' ? formatClock(date) : formatDayMonth(date);
}
