/// Price data models for OPCOM energy prices

class PricePoint {
  final DateTime timestamp;
  final double priceLeiMwh;
  final double priceLeiKwh;
  final int hour;

  PricePoint({
    required this.timestamp,
    required this.priceLeiMwh,
    required this.priceLeiKwh,
    this.hour = 0,
  });

  factory PricePoint.fromJson(Map<String, dynamic> json) {
    return PricePoint(
      timestamp: DateTime.parse(json['timestamp']),
      priceLeiMwh: (json['price_lei_mwh'] ?? 0).toDouble(),
      priceLeiKwh: (json['price_lei_kwh'] ?? 0).toDouble(),
      hour: json['hour'] ?? 0,
    );
  }
}

class PriceStats {
  final double minLeiMwh;
  final double maxLeiMwh;
  final double avgLeiMwh;
  final double minLeiKwh;
  final double maxLeiKwh;
  final double avgLeiKwh;

  PriceStats({
    this.minLeiMwh = 0,
    this.maxLeiMwh = 0,
    this.avgLeiMwh = 0,
    this.minLeiKwh = 0,
    this.maxLeiKwh = 0,
    this.avgLeiKwh = 0,
  });

  factory PriceStats.fromJson(Map<String, dynamic> json) {
    return PriceStats(
      minLeiMwh: (json['min_lei_mwh'] ?? 0).toDouble(),
      maxLeiMwh: (json['max_lei_mwh'] ?? 0).toDouble(),
      avgLeiMwh: (json['avg_lei_mwh'] ?? 0).toDouble(),
      minLeiKwh: (json['min_lei_kwh'] ?? 0).toDouble(),
      maxLeiKwh: (json['max_lei_kwh'] ?? 0).toDouble(),
      avgLeiKwh: (json['avg_lei_kwh'] ?? 0).toDouble(),
    );
  }
}

class PriceChange {
  final double absoluteLeiMwh;
  final double absoluteLeiKwh;
  final double percent;
  final String direction; // "up", "down", "unchanged"

  PriceChange({
    this.absoluteLeiMwh = 0,
    this.absoluteLeiKwh = 0,
    this.percent = 0,
    this.direction = 'unchanged',
  });

  factory PriceChange.fromJson(Map<String, dynamic> json) {
    return PriceChange(
      absoluteLeiMwh: (json['absolute_lei_mwh'] ?? 0).toDouble(),
      absoluteLeiKwh: (json['absolute_lei_kwh'] ?? 0).toDouble(),
      percent: (json['percent'] ?? 0).toDouble(),
      direction: json['direction'] ?? 'unchanged',
    );
  }

  bool get isUp => direction == 'up';
  bool get isDown => direction == 'down';
}

class PriceData {
  final String date;
  final String period;
  final List<PricePoint> prices;
  final PriceStats statistics;
  final PriceChange change;
  final double currentPriceLeiMwh;
  final double currentPriceLeiKwh;
  final int currentHour;
  final String source;
  final int dataPoints;

  PriceData({
    required this.date,
    required this.period,
    required this.prices,
    required this.statistics,
    required this.change,
    this.currentPriceLeiMwh = 0,
    this.currentPriceLeiKwh = 0,
    this.currentHour = 0,
    this.source = 'Generated',
    this.dataPoints = 0,
  });

  factory PriceData.fromJson(Map<String, dynamic> json) {
    final pricesList = (json['prices'] as List<dynamic>?)
        ?.map((p) => PricePoint.fromJson(p))
        .toList() ?? [];

    return PriceData(
      date: json['date'] ?? '',
      period: json['period'] ?? '1Z',
      prices: pricesList,
      statistics: PriceStats.fromJson(json['statistics'] ?? {}),
      change: PriceChange.fromJson(json['change'] ?? {}),
      currentPriceLeiMwh: (json['current_price_lei_mwh'] ?? 0).toDouble(),
      currentPriceLeiKwh: (json['current_price_lei_kwh'] ?? 0).toDouble(),
      currentHour: json['current_hour'] ?? 0,
      source: json['source'] ?? 'Generated',
      dataPoints: json['data_points'] ?? pricesList.length,
    );
  }

  /// Get min and max prices for chart scaling
  double get minPrice => prices.isEmpty ? 0 : prices.map((p) => p.priceLeiMwh).reduce((a, b) => a < b ? a : b);
  double get maxPrice => prices.isEmpty ? 0 : prices.map((p) => p.priceLeiMwh).reduce((a, b) => a > b ? a : b);
}
