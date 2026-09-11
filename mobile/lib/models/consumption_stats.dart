/// Data models for energy analytics and statistics.

/// Energy consumption data for a single device.
class DeviceConsumption {
  final int deviceId;
  final String deviceName;
  final double totalKwh;
  final double percentageOfTotal;
  final double estimatedCost;

  DeviceConsumption({
    required this.deviceId,
    required this.deviceName,
    required this.totalKwh,
    required this.percentageOfTotal,
    required this.estimatedCost,
  });

  factory DeviceConsumption.fromJson(Map<String, dynamic> json) {
    return DeviceConsumption(
      deviceId: json['device_id'] as int,
      deviceName: json['device_name'] as String,
      totalKwh: (json['total_kwh'] as num).toDouble(),
      percentageOfTotal: (json['percentage_of_total'] as num).toDouble(),
      estimatedCost: (json['estimated_cost'] as num).toDouble(),
    );
  }
}

/// Summary of energy consumption for a period.
class ConsumptionSummary {
  final double totalKwh;
  final double averageDailyKwh;
  final double previousPeriodKwh;
  final double? changePercent;
  final String period;
  final double estimatedCost;
  final String currency;
  final bool hasData;

  ConsumptionSummary({
    required this.totalKwh,
    required this.averageDailyKwh,
    required this.previousPeriodKwh,
    this.changePercent,
    required this.period,
    required this.estimatedCost,
    required this.currency,
    required this.hasData,
  });

  factory ConsumptionSummary.fromJson(Map<String, dynamic> json) {
    return ConsumptionSummary(
      totalKwh: (json['total_kwh'] as num).toDouble(),
      averageDailyKwh: (json['average_daily_kwh'] as num).toDouble(),
      previousPeriodKwh: (json['previous_period_kwh'] as num).toDouble(),
      changePercent: json['change_percent'] != null
          ? (json['change_percent'] as num).toDouble()
          : null,
      period: json['period'] as String,
      estimatedCost: (json['estimated_cost'] as num).toDouble(),
      currency: json['currency'] as String,
      hasData: json['has_data'] as bool,
    );
  }
}

/// Single data point for consumption charts.
class ChartDataPoint {
  final DateTime timestamp;
  final double valueKwh;

  ChartDataPoint({
    required this.timestamp,
    required this.valueKwh,
  });

  factory ChartDataPoint.fromJson(Map<String, dynamic> json) {
    return ChartDataPoint(
      timestamp: DateTime.parse(json['timestamp'] as String),
      valueKwh: (json['value_kwh'] as num).toDouble(),
    );
  }
}

/// Chart data response with granularity info.
class ChartData {
  final String granularity;
  final String startDate;
  final String endDate;
  final List<ChartDataPoint> dataPoints;

  ChartData({
    required this.granularity,
    required this.startDate,
    required this.endDate,
    required this.dataPoints,
  });

  factory ChartData.fromJson(Map<String, dynamic> json) {
    return ChartData(
      granularity: json['granularity'] as String,
      startDate: json['start_date'] as String,
      endDate: json['end_date'] as String,
      dataPoints: (json['data_points'] as List)
          .map((e) => ChartDataPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Comparison between current and previous month.
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

  MonthlyComparison({
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

  factory MonthlyComparison.fromJson(Map<String, dynamic> json) {
    return MonthlyComparison(
      currentMonth: json['current_month'] as String,
      currentMonthKwh: (json['current_month_kwh'] as num).toDouble(),
      previousMonth: json['previous_month'] as String,
      previousMonthKwh: (json['previous_month_kwh'] as num).toDouble(),
      changePercent: json['change_percent'] != null
          ? (json['change_percent'] as num).toDouble()
          : null,
      trend: json['trend'] as String,
      projectedTotalKwh: (json['projected_total_kwh'] as num).toDouble(),
      isProjection: json['is_projection'] as bool,
      daysRemaining: json['days_remaining'] as int,
    );
  }
}

/// Top consumers response.
class TopConsumersResponse {
  final String period;
  final double totalHouseKwh;
  final List<DeviceConsumption> devices;

  TopConsumersResponse({
    required this.period,
    required this.totalHouseKwh,
    required this.devices,
  });

  factory TopConsumersResponse.fromJson(Map<String, dynamic> json) {
    return TopConsumersResponse(
      period: json['period'] as String,
      totalHouseKwh: (json['total_house_kwh'] as num).toDouble(),
      devices: (json['devices'] as List)
          .map((e) => DeviceConsumption.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
