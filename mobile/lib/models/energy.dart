import 'dart:math' as math;

import 'package:flutter_interface/models/json_utils.dart';

/// One point of `/api/me/energy/chart` (kW averaged over the interval).
class EnergyPoint {
  final DateTime time;
  final double solar;
  final double consumption;
  final double battery; // > 0 charging
  final double grid; // > 0 import
  final double p2p; // > 0 buying
  final double solarToBattery;
  final double batteryToLoad;
  final double gridToLoad;
  final double solarToGrid;
  final double socKwh;
  final double priceImport;

  const EnergyPoint({
    required this.time,
    required this.solar,
    required this.consumption,
    required this.battery,
    required this.grid,
    required this.p2p,
    required this.solarToBattery,
    required this.batteryToLoad,
    required this.gridToLoad,
    required this.solarToGrid,
    required this.socKwh,
    required this.priceImport,
  });

  static EnergyPoint? fromJson(Map<String, dynamic> j) {
    final t = asDateTime(j['timestamp']);
    if (t == null) return null;
    return EnergyPoint(
      time: t,
      solar: asDouble(j['solar']),
      consumption: asDouble(j['consumption']),
      battery: asDouble(j['battery']),
      grid: asDouble(j['grid']),
      p2p: asDouble(j['p2p']),
      solarToBattery: asDouble(j['solar_to_battery']),
      batteryToLoad: asDouble(j['battery_to_load']),
      gridToLoad: asDouble(j['grid_to_load']),
      solarToGrid: asDouble(j['solar_to_grid']),
      socKwh: asDouble(j['soc_kwh']),
      priceImport: asDouble(j['price_import']),
    );
  }

  double get p2pBuy => math.max(0.0, p2p);
  double get p2pSell => math.max(0.0, -p2p);

  /// Solar used directly by the load: production minus what was stored,
  /// exported or sold, never above consumption.
  double get solarToLoad {
    final rest = solar - solarToBattery - solarToGrid - p2pSell;
    return rest.clamp(0.0, math.max(0.0, consumption));
  }
}

class EnergyChart {
  final String period;
  final String date;
  final int intervalMinutes;
  final List<EnergyPoint> points;

  const EnergyChart({
    required this.period,
    required this.date,
    required this.intervalMinutes,
    required this.points,
  });

  factory EnergyChart.fromJson(Map<String, dynamic> j) => EnergyChart(
        period: asString(j['period'], 'day'),
        date: asString(j['date']),
        intervalMinutes: asInt(j['interval_minutes'], 15),
        points: asMapList(j['data_points']).map(EnergyPoint.fromJson).whereType<EnergyPoint>().toList(),
      );

  double get hoursPerPoint => intervalMinutes / 60.0;
}

/// Energy split by source for a time-of-use bucket, kWh.
class SourceSplit {
  final double solar;
  final double battery;
  final double grid;
  final double p2p;

  const SourceSplit({required this.solar, required this.battery, required this.grid, required this.p2p});

  factory SourceSplit.fromJson(Map<String, dynamic> j) => SourceSplit(
        solar: asDouble(j['solar']),
        battery: asDouble(j['battery']),
        grid: asDouble(j['grid']),
        p2p: asDouble(j['p2p']),
      );

  double get max => [solar, battery, grid, p2p].reduce(math.max);
}

class MonthlySaving {
  final String month;
  final int year;
  final double savings;
  final bool hasData;
  final bool current;

  const MonthlySaving({
    required this.month,
    required this.year,
    required this.savings,
    required this.hasData,
    required this.current,
  });

  factory MonthlySaving.fromJson(Map<String, dynamic> j) => MonthlySaving(
        month: asString(j['month']),
        year: asInt(j['year']),
        savings: asDouble(j['savings']),
        hasData: asBool(j['has_data']),
        current: asBool(j['current']),
      );
}

class EnergyImpact {
  final String date;
  final double solarPercent;
  final double batteryPercent;
  final double p2pPercent;
  final double gridPercent;
  final double solarKwh;
  final double batteryKwh;
  final double p2pKwh;
  final double gridKwh;
  final SourceSplit peak;
  final SourceSplit offPeak;
  final List<MonthlySaving> monthlySavings;

  const EnergyImpact({
    required this.date,
    required this.solarPercent,
    required this.batteryPercent,
    required this.p2pPercent,
    required this.gridPercent,
    required this.solarKwh,
    required this.batteryKwh,
    required this.p2pKwh,
    required this.gridKwh,
    required this.peak,
    required this.offPeak,
    required this.monthlySavings,
  });

  factory EnergyImpact.fromJson(Map<String, dynamic> j) => EnergyImpact(
        date: asString(j['date']),
        solarPercent: asDouble(j['solar_percent']),
        batteryPercent: asDouble(j['battery_percent']),
        p2pPercent: asDouble(j['p2p_percent']),
        gridPercent: asDouble(j['grid_percent']),
        solarKwh: asDouble(j['solar_kwh']),
        batteryKwh: asDouble(j['battery_kwh']),
        p2pKwh: asDouble(j['p2p_kwh']),
        gridKwh: asDouble(j['grid_kwh']),
        peak: SourceSplit.fromJson(asMap(j['peak'])),
        offPeak: SourceSplit.fromJson(asMap(j['off_peak'])),
        monthlySavings: asMapList(j['monthly_savings']).map(MonthlySaving.fromJson).toList(),
      );

  double get totalKwh => solarKwh + batteryKwh + p2pKwh + gridKwh;
  bool get hasData => totalKwh > 0;
}
