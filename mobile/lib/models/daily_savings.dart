/// Daily savings model for tracking energy cost savings
class DailySavings {
  final double totalSavings;
  final double solarSavings;
  final double batterySavings;
  final double exportRevenue;
  final double gridAvoidanceSavings;
  final DateTime date;
  final String currency;

  const DailySavings({
    required this.totalSavings,
    required this.solarSavings,
    required this.batterySavings,
    required this.exportRevenue,
    required this.gridAvoidanceSavings,
    required this.date,
    this.currency = 'RON',
  });

  /// Create from JSON
  factory DailySavings.fromJson(Map<String, dynamic> json) {
    return DailySavings(
      totalSavings: (json['total_savings'] ?? 0.0).toDouble(),
      solarSavings: (json['solar_savings'] ?? 0.0).toDouble(),
      batterySavings: (json['battery_savings'] ?? 0.0).toDouble(),
      exportRevenue: (json['export_revenue'] ?? 0.0).toDouble(),
      gridAvoidanceSavings: (json['grid_avoidance_savings'] ?? 0.0).toDouble(),
      date: DateTime.tryParse(json['date'] ?? '') ?? DateTime.now(),
      currency: json['currency'] ?? 'RON',
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'total_savings': totalSavings,
      'solar_savings': solarSavings,
      'battery_savings': batterySavings,
      'export_revenue': exportRevenue,
      'grid_avoidance_savings': gridAvoidanceSavings,
      'date': date.toIso8601String(),
      'currency': currency,
    };
  }

  /// Create a copy with updated values
  DailySavings copyWith({
    double? totalSavings,
    double? solarSavings,
    double? batterySavings,
    double? exportRevenue,
    double? gridAvoidanceSavings,
    DateTime? date,
    String? currency,
  }) {
    return DailySavings(
      totalSavings: totalSavings ?? this.totalSavings,
      solarSavings: solarSavings ?? this.solarSavings,
      batterySavings: batterySavings ?? this.batterySavings,
      exportRevenue: exportRevenue ?? this.exportRevenue,
      gridAvoidanceSavings: gridAvoidanceSavings ?? this.gridAvoidanceSavings,
      date: date ?? this.date,
      currency: currency ?? this.currency,
    );
  }

  /// Get savings breakdown as a list
  List<SavingsBreakdown> get breakdown => [
    SavingsBreakdown(
      type: SavingsType.solar,
      amount: solarSavings,
      description: 'Economii din energia solară',
    ),
    SavingsBreakdown(
      type: SavingsType.battery,
      amount: batterySavings,
      description: 'Economii din baterie',
    ),
    SavingsBreakdown(
      type: SavingsType.export,
      amount: exportRevenue,
      description: 'Venituri din export',
    ),
    SavingsBreakdown(
      type: SavingsType.gridAvoidance,
      amount: gridAvoidanceSavings,
      description: 'Evitarea tarifelor de rețea',
    ),
  ];

  /// Check if it's today's savings
  bool get isToday {
    final now = DateTime.now();
    return date.year == now.year &&
           date.month == now.month &&
           date.day == now.day;
  }

  /// Mock data for testing
  static DailySavings get mock => DailySavings(
    totalSavings: 12.45,
    solarSavings: 8.30,
    batterySavings: 2.15,
    exportRevenue: 1.50,
    gridAvoidanceSavings: 0.50,
    date: DateTime.now(),
  );

  static DailySavings get empty => DailySavings(
    totalSavings: 0.0,
    solarSavings: 0.0,
    batterySavings: 0.0,
    exportRevenue: 0.0,
    gridAvoidanceSavings: 0.0,
    date: DateTime.now(),
  );
}

/// Savings breakdown item
class SavingsBreakdown {
  final SavingsType type;
  final double amount;
  final String description;

  const SavingsBreakdown({
    required this.type,
    required this.amount,
    required this.description,
  });
}

/// Types of savings
enum SavingsType {
  solar,
  battery,
  export,
  gridAvoidance,
}

/// Energy data for calculations
class EnergyData {
  final double solarProduction;
  final double consumption;
  final double batteryCharge;
  final double batteryDischarge;
  final double gridImport;
  final double gridExport;
  final DateTime timestamp;

  const EnergyData({
    required this.solarProduction,
    required this.consumption,
    required this.batteryCharge,
    required this.batteryDischarge,
    required this.gridImport,
    required this.gridExport,
    required this.timestamp,
  });

  /// Net battery power (positive = charging, negative = discharging)
  double get netBatteryPower => batteryCharge - batteryDischarge;

  /// Net grid power (positive = importing, negative = exporting)
  double get netGridPower => gridImport - gridExport;

  /// Self-consumption ratio
  double get selfConsumptionRatio {
    if (solarProduction == 0) return 0;
    return ((solarProduction - gridExport) / solarProduction).clamp(0.0, 1.0);
  }
}

/// Pricing data for calculations
class PricingData {
  final double gridPrice;
  final double peakPrice;
  final double offPeakPrice;
  final double exportPrice;
  final DateTime timestamp;

  const PricingData({
    required this.gridPrice,
    required this.peakPrice,
    required this.offPeakPrice,
    required this.exportPrice,
    required this.timestamp,
  });

  /// Mock pricing data
  static PricingData get mock => PricingData(
    gridPrice: 0.65, // RON per kWh
    peakPrice: 0.85, // RON per kWh
    offPeakPrice: 0.45, // RON per kWh
    exportPrice: 0.35, // RON per kWh
    timestamp: DateTime.now(),
  );
}