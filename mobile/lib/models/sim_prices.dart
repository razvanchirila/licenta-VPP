import 'dart:math' as math;

import 'package:flutter_interface/models/json_utils.dart';

enum PriceSeries { import, export, p2p }

extension PriceSeriesLabel on PriceSeries {
  String get label {
    switch (this) {
      case PriceSeries.import:
        return 'Import';
      case PriceSeries.export:
        return 'Export';
      case PriceSeries.p2p:
        return 'P2P';
    }
  }
}

class PricePoint {
  final DateTime timestamp;
  final double priceImport;
  final double priceExport;
  final double priceP2p;

  const PricePoint({
    required this.timestamp,
    required this.priceImport,
    required this.priceExport,
    required this.priceP2p,
  });

  static PricePoint? fromJson(Map<String, dynamic> j) {
    final t = asDateTime(j['sim_timestamp']);
    if (t == null) return null;
    return PricePoint(
      timestamp: t,
      priceImport: asDouble(j['price_import']),
      priceExport: asDouble(j['price_export']),
      priceP2p: asDouble(j['price_p2p']),
    );
  }

  double value(PriceSeries s) {
    switch (s) {
      case PriceSeries.import:
        return priceImport;
      case PriceSeries.export:
        return priceExport;
      case PriceSeries.p2p:
        return priceP2p;
    }
  }
}

/// `/api/sim/prices`: the price curve of the simulated day (lei/kWh).
class SimPrices {
  final String date;
  final double dtHours;
  final int currentStep;
  final List<PricePoint> prices;

  const SimPrices({
    required this.date,
    required this.dtHours,
    required this.currentStep,
    required this.prices,
  });

  factory SimPrices.fromJson(Map<String, dynamic> j) => SimPrices(
        date: asString(j['date']),
        dtHours: asDouble(j['dt_hours'], 0.25),
        currentStep: asInt(j['current_step']),
        prices: asMapList(j['prices']).map(PricePoint.fromJson).whereType<PricePoint>().toList(),
      );

  bool get isEmpty => prices.isEmpty;

  PricePoint? get current => prices.isEmpty ? null : prices[currentStep.clamp(0, prices.length - 1)];

  PricePoint? get previous => prices.isEmpty ? null : prices[(currentStep - 1).clamp(0, prices.length - 1)];

  double currentValue(PriceSeries s) => current?.value(s) ?? 0.0;

  double change(PriceSeries s) => currentValue(s) - (previous?.value(s) ?? currentValue(s));

  bool isRising(PriceSeries s) => change(s) > 0;

  double min(PriceSeries s) => prices.isEmpty ? 0 : prices.map((p) => p.value(s)).reduce(math.min);
  double max(PriceSeries s) => prices.isEmpty ? 0 : prices.map((p) => p.value(s)).reduce(math.max);
  double avg(PriceSeries s) =>
      prices.isEmpty ? 0 : prices.map((p) => p.value(s)).reduce((a, b) => a + b) / prices.length;
}
