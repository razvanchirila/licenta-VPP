import 'package:flutter_interface/models/json_utils.dart';

class DeviceConsumption {
  final int deviceId;
  final String deviceName;
  final double totalKwh;
  final double percentageOfTotal;
  final double estimatedCost;

  const DeviceConsumption({
    required this.deviceId,
    required this.deviceName,
    required this.totalKwh,
    required this.percentageOfTotal,
    required this.estimatedCost,
  });

  factory DeviceConsumption.fromJson(Map<String, dynamic> json) => DeviceConsumption(
        deviceId: asInt(json['device_id']),
        deviceName: asString(json['device_name']),
        totalKwh: asDouble(json['total_kwh']),
        percentageOfTotal: asDouble(json['percentage_of_total']),
        estimatedCost: asDouble(json['estimated_cost']),
      );
}

class ConsumptionSummary {
  final double totalKwh;
  final double averageDailyKwh;
  final double previousPeriodKwh;
  final double? changePercent;
  final String period;
  final double estimatedCost;
  final bool hasData;

  const ConsumptionSummary({
    required this.totalKwh,
    required this.averageDailyKwh,
    required this.previousPeriodKwh,
    this.changePercent,
    required this.period,
    required this.estimatedCost,
    required this.hasData,
  });

  factory ConsumptionSummary.fromJson(Map<String, dynamic> json) => ConsumptionSummary(
        totalKwh: asDouble(json['total_kwh']),
        averageDailyKwh: asDouble(json['average_daily_kwh']),
        previousPeriodKwh: asDouble(json['previous_period_kwh']),
        changePercent: asDoubleOrNull(json['change_percent']),
        period: asString(json['period']),
        estimatedCost: asDouble(json['estimated_cost']),
        hasData: asBool(json['has_data'], true),
      );
}

class ChartDataPoint {
  final DateTime timestamp;
  final double valueKwh;

  const ChartDataPoint({required this.timestamp, required this.valueKwh});

  static ChartDataPoint? fromJson(Map<String, dynamic> json) {
    final t = asDateTime(json['timestamp']);
    if (t == null) return null;
    return ChartDataPoint(timestamp: t, valueKwh: asDouble(json['value_kwh']));
  }
}

class ChartData {
  final String granularity;
  final String startDate;
  final String endDate;
  final List<ChartDataPoint> dataPoints;

  const ChartData({
    required this.granularity,
    required this.startDate,
    required this.endDate,
    required this.dataPoints,
  });

  factory ChartData.fromJson(Map<String, dynamic> json) => ChartData(
        granularity: asString(json['granularity'], 'daily'),
        startDate: asString(json['start_date']),
        endDate: asString(json['end_date']),
        dataPoints: asMapList(json['data_points']).map(ChartDataPoint.fromJson).whereType<ChartDataPoint>().toList(),
      );
}

class MonthlyComparison {
  final String currentMonth;
  final double currentMonthKwh;
  final String previousMonth;
  final double previousMonthKwh;
  final double? changePercent;
  final String trend;
  final double projectedTotalKwh;
  final bool isProjection;
  final int daysRemaining;

  const MonthlyComparison({
    required this.currentMonth,
    required this.currentMonthKwh,
    required this.previousMonth,
    required this.previousMonthKwh,
    this.changePercent,
    required this.trend,
    required this.projectedTotalKwh,
    required this.isProjection,
    required this.daysRemaining,
  });

  factory MonthlyComparison.fromJson(Map<String, dynamic> json) => MonthlyComparison(
        currentMonth: asString(json['current_month']),
        currentMonthKwh: asDouble(json['current_month_kwh']),
        previousMonth: asString(json['previous_month']),
        previousMonthKwh: asDouble(json['previous_month_kwh']),
        changePercent: asDoubleOrNull(json['change_percent']),
        trend: asString(json['trend'], 'stable'),
        projectedTotalKwh: asDouble(json['projected_total_kwh']),
        isProjection: asBool(json['is_projection']),
        daysRemaining: asInt(json['days_remaining']),
      );
}

class TopConsumersResponse {
  final String period;
  final double totalHouseKwh;
  final List<DeviceConsumption> devices;

  const TopConsumersResponse({
    required this.period,
    required this.totalHouseKwh,
    required this.devices,
  });

  factory TopConsumersResponse.fromJson(Map<String, dynamic> json) => TopConsumersResponse(
        period: asString(json['period']),
        totalHouseKwh: asDouble(json['total_house_kwh']),
        devices: asMapList(json['devices']).map(DeviceConsumption.fromJson).toList(),
      );
}
