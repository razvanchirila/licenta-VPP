/// Model for house state - represents a single house in the VPP
/// 
/// This model holds the configuration and current state of a house,
/// including battery settings, operating mode, and energy values.

class HouseState {
  /// House ID in the VPP system (default: 1)
  final int id;
  
  /// Operating mode: "Eco" or "Profit"
  /// - Eco: Self-power mode, prioritizes using own solar/battery
  /// - Profit: Sell mode, can sell stored energy when prices are high
  String mode;
  
  /// Battery State of Charge minimum (backup reserve)
  /// Value between 0.0 and 1.0 (0% to 100%)
  /// This is the minimum battery level to maintain as reserve
  double socMinRatio;
  
  /// Current battery SOC in kWh
  double socKwh;
  
  /// Battery capacity in kWh
  double capacityKwh;
  
  /// PV capacity in kW
  double pvCapacityKw;
  
  /// Whether house has a battery
  bool hasBattery;
  
  /// Whether house has PV system
  bool hasPv;
  
  /// Current solar production in kW
  double solarPowerKw;
  
  /// Current home consumption in kW
  double homePowerKw;
  
  /// Current battery power in kW (positive = charging, negative = discharging)
  double batteryPowerKw;
  
  /// Current grid power in kW (positive = importing, negative = exporting)
  double gridPowerKw;
  
  HouseState({
    this.id = 1,
    this.mode = "Eco",
    this.socMinRatio = 0.2,
    this.socKwh = 10.0,
    this.capacityKwh = 20.0,
    this.pvCapacityKw = 10.0,
    this.hasBattery = true,
    this.hasPv = true,
    this.solarPowerKw = 0.0,
    this.homePowerKw = 0.0,
    this.batteryPowerKw = 0.0,
    this.gridPowerKw = 0.0,
  });
  
  /// Get battery SOC as percentage (0-100)
  double get socPercent => capacityKwh > 0 ? (socKwh / capacityKwh) * 100 : 0;
  
  /// Get SOC min as percentage (0-100)
  double get socMinPercent => socMinRatio * 100;
  
  /// Set SOC min from percentage (0-100)
  set socMinPercent(double percent) {
    socMinRatio = (percent / 100).clamp(0.0, 1.0);
  }
  
  /// Whether battery is charging
  bool get isCharging => batteryPowerKw > 0;
  
  /// Whether battery is discharging
  bool get isDischarging => batteryPowerKw < 0;
  
  /// Create from API JSON response
  factory HouseState.fromJson(Map<String, dynamic> json) {
    final battery = json['battery'] as Map<String, dynamic>?;
    
    return HouseState(
      id: json['id'] ?? 1,
      mode: json['mode'] ?? "Eco",
      socMinRatio: battery != null 
          ? (battery['soc_min_kwh'] ?? 4.0) / (battery['capacity_kwh'] ?? 20.0)
          : 0.2,
      socKwh: battery?['soc_kwh']?.toDouble() ?? 10.0,
      capacityKwh: battery?['capacity_kwh']?.toDouble() ?? 20.0,
      pvCapacityKw: json['pv_capacity_kw']?.toDouble() ?? 10.0,
      hasBattery: json['has_battery'] ?? true,
      hasPv: json['has_pv'] ?? true,
    );
  }
  
  /// Convert to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'mode': mode,
      'soc_min_ratio': socMinRatio,
    };
  }
  
  /// Create a copy with updated values
  HouseState copyWith({
    int? id,
    String? mode,
    double? socMinRatio,
    double? socKwh,
    double? capacityKwh,
    double? pvCapacityKw,
    bool? hasBattery,
    bool? hasPv,
    double? solarPowerKw,
    double? homePowerKw,
    double? batteryPowerKw,
    double? gridPowerKw,
  }) {
    return HouseState(
      id: id ?? this.id,
      mode: mode ?? this.mode,
      socMinRatio: socMinRatio ?? this.socMinRatio,
      socKwh: socKwh ?? this.socKwh,
      capacityKwh: capacityKwh ?? this.capacityKwh,
      pvCapacityKw: pvCapacityKw ?? this.pvCapacityKw,
      hasBattery: hasBattery ?? this.hasBattery,
      hasPv: hasPv ?? this.hasPv,
      solarPowerKw: solarPowerKw ?? this.solarPowerKw,
      homePowerKw: homePowerKw ?? this.homePowerKw,
      batteryPowerKw: batteryPowerKw ?? this.batteryPowerKw,
      gridPowerKw: gridPowerKw ?? this.gridPowerKw,
    );
  }
}
