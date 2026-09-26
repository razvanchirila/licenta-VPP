import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/widgets/energy/energy_period.dart';

class EnergySeriesVisibility {
  final bool solar;
  final bool consumption;
  final bool battery;
  final bool grid;

  const EnergySeriesVisibility({
    this.solar = true,
    this.consumption = true,
    this.battery = false,
    this.grid = false,
  });

  EnergySeriesVisibility copyWith({bool? solar, bool? consumption, bool? battery, bool? grid}) =>
      EnergySeriesVisibility(
        solar: solar ?? this.solar,
        consumption: consumption ?? this.consumption,
        battery: battery ?? this.battery,
        grid: grid ?? this.grid,
      );

  /// Series in drawing order, so `fl_chart`'s bar index maps back to one.
  List<EnergySeries> get visible => [
        if (solar) EnergySeries.solar,
        if (consumption) EnergySeries.consumption,
        if (battery) EnergySeries.battery,
        if (grid) EnergySeries.grid,
      ];
}

enum EnergySeries {
  solar('Solar', AppColors.blue, 0.2),
  consumption('Consum', AppColors.red, 0.15),
  battery('Baterie', AppColors.green, 0.1),
  grid('Rețea', AppColors.amber, 0.1);

  final String label;
  final Color color;
  final double fillAlpha;

  const EnergySeries(this.label, this.color, this.fillAlpha);

  /// Value plotted for this series (battery and grid use the magnitude).
  double valueOf(EnergyPoint p) {
    switch (this) {
      case EnergySeries.solar:
        return p.solar;
      case EnergySeries.consumption:
        return p.consumption;
      case EnergySeries.battery:
        return p.battery.abs();
      case EnergySeries.grid:
        return p.grid.abs();
    }
  }

  String tooltipSuffix(EnergyPoint p) {
    switch (this) {
      case EnergySeries.battery:
        return p.battery >= 0 ? ' (încărcare)' : ' (descărcare)';
      case EnergySeries.grid:
        return p.grid >= 0 ? ' (import)' : ' (export)';
      default:
        return '';
    }
  }
}

class EnergyChartScale {
  EnergyChartScale._();

  /// Top of the y-axis: 20% headroom above the largest visible value,
  /// rounded up, never below 1 kW.
  static double maxY(List<EnergyPoint> points, EnergySeriesVisibility visibility) {
    double maxVal = 0;
    for (final point in points) {
      for (final series in visibility.visible) {
        maxVal = math.max(maxVal, series.valueOf(point));
      }
    }
    return math.max(1.0, (maxVal * 1.2).ceilToDouble());
  }

  static double horizontalInterval(double maxY) {
    if (maxY <= 2) return 0.5;
    if (maxY <= 5) return 1;
    if (maxY <= 12) return 2;
    return (maxY / 5).ceilToDouble();
  }

  static double verticalInterval(int pointCount, String period) {
    switch (period) {
      case EnergyPeriod.day:
        return math.max(1, (pointCount / 6).ceilToDouble());
      case EnergyPeriod.week:
        return math.max(1, (pointCount / 7).ceilToDouble());
      default:
        return math.max(1, (pointCount / 10).ceilToDouble());
    }
  }

  static double bottomInterval(int pointCount) => math.max(1, (pointCount / 6).ceilToDouble());
}

class EnergyLineChart extends StatelessWidget {
  final List<EnergyPoint> points;
  final String period;
  final EnergySeriesVisibility visibility;

  const EnergyLineChart({super.key, required this.points, required this.period, required this.visibility});

  @override
  Widget build(BuildContext context) {
    final maxY = EnergyChartScale.maxY(points, visibility);
    final horizontal = EnergyChartScale.horizontalInterval(maxY);

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: true,
          horizontalInterval: horizontal,
          verticalInterval: EnergyChartScale.verticalInterval(points.length, period),
          getDrawingHorizontalLine: (value) => FlLine(color: Colors.white.withValues(alpha: 0.1), strokeWidth: 1),
          getDrawingVerticalLine: (value) => FlLine(color: Colors.white.withValues(alpha: 0.05), strokeWidth: 1),
        ),
        titlesData: FlTitlesData(
          show: true,
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              interval: EnergyChartScale.bottomInterval(points.length),
              getTitlesWidget: _bottomTitle,
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: horizontal,
              reservedSize: 40,
              getTitlesWidget: _leftTitle,
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: math.max(1, points.length - 1).toDouble(),
        minY: 0,
        maxY: maxY,
        lineTouchData: LineTouchData(
          enabled: true,
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (touchedSpot) => AppColors.tooltip,
            tooltipRoundedRadius: 12,
            tooltipPadding: const EdgeInsets.all(12),
            getTooltipItems: (touchedSpots) => touchedSpots.map(_tooltipItem).toList(),
          ),
          handleBuiltInTouches: true,
        ),
        lineBarsData: visibility.visible.map(_line).toList(),
      ),
    );
  }

  LineTooltipItem _tooltipItem(LineBarSpot spot) {
    final visible = visibility.visible;
    final series = spot.barIndex < visible.length ? visible[spot.barIndex] : null;
    final index = spot.x.toInt();
    final point = index >= 0 && index < points.length ? points[index] : null;
    final suffix = series != null && point != null ? series.tooltipSuffix(point) : '';

    return LineTooltipItem(
      '${series?.label ?? ''}: ${spot.y.toStringAsFixed(2)} kW$suffix',
      GoogleFonts.inter(color: series?.color ?? Colors.white, fontSize: 12, fontWeight: FontWeight.w500),
    );
  }

  LineChartBarData _line(EnergySeries series) {
    return LineChartBarData(
      spots: [for (var i = 0; i < points.length; i++) FlSpot(i.toDouble(), series.valueOf(points[i]))],
      isCurved: true,
      curveSmoothness: 0.3,
      color: series.color,
      barWidth: 2,
      isStrokeCapRound: true,
      dotData: const FlDotData(show: false),
      belowBarData: BarAreaData(show: true, color: series.color.withValues(alpha: series.fillAlpha)),
    );
  }

  Widget _bottomTitle(double value, TitleMeta meta) {
    final index = value.toInt();
    if (index < 0 || index >= points.length) return const SizedBox.shrink();
    return SideTitleWidget(
      axisSide: meta.axisSide,
      child: Text(EnergyPeriod.axisLabel(points[index].time, period), style: _axisStyle),
    );
  }

  Widget _leftTitle(double value, TitleMeta meta) {
    return SideTitleWidget(axisSide: meta.axisSide, child: Text(value.toStringAsFixed(1), style: _axisStyle));
  }

  TextStyle get _axisStyle => GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 10);
}
