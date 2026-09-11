/// Model pentru datele de flux energetic primite de la backend.
/// 
/// Convenții de semn:
/// - [batteryPower]: pozitiv = încărcare, negativ = descărcare
/// - [gridPower]: pozitiv = import din rețea, negativ = export în rețea
/// - [solarPower]: întotdeauna >= 0
/// - [homePower]: întotdeauna >= 0
class EnergyFlowData {
  /// Puterea generată de panourile solare (kW), >= 0
  final double solarPower;
  
  /// Puterea consumată de casă (kW), >= 0
  final double homePower;
  
  /// Puterea bateriei (kW): + = încărcare, - = descărcare
  final double batteryPower;
  
  /// Procentajul bateriei (0-100)
  final int batteryPercentage;
  
  /// Puterea schimbată cu rețeaua (kW): + = import, - = export
  final double gridPower;

  const EnergyFlowData({
    this.solarPower = 0.0,
    this.homePower = 0.0,
    this.batteryPower = 0.0,
    this.batteryPercentage = 0,
    this.gridPower = 0.0,
  });

  /// Creează o instanță din JSON primit de la backend
  factory EnergyFlowData.fromJson(Map<String, dynamic> json) {
    return EnergyFlowData(
      solarPower: _parseDouble(json['solarPower']),
      homePower: _parseDouble(json['homePower']),
      batteryPower: _parseDouble(json['batteryPower']),
      batteryPercentage: _parseInt(json['batteryPercentage']),
      gridPower: _parseDouble(json['gridPower']),
    );
  }

  /// Convertește în JSON pentru serializare
  Map<String, dynamic> toJson() {
    return {
      'solarPower': solarPower,
      'homePower': homePower,
      'batteryPower': batteryPower,
      'batteryPercentage': batteryPercentage,
      'gridPower': gridPower,
    };
  }

  /// Helper pentru parsare double cu valoare default
  static double _parseDouble(dynamic value) {
    if (value == null) return 0.0;
    if (value is double) return value.isFinite ? value : 0.0;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }

  /// Helper pentru parsare int cu clamp la 0-100
  static int _parseInt(dynamic value) {
    if (value == null) return 0;
    int result;
    if (value is int) {
      result = value;
    } else if (value is double) {
      result = value.toInt();
    } else if (value is String) {
      result = int.tryParse(value) ?? 0;
    } else {
      result = 0;
    }
    return result.clamp(0, 100);
  }

  /// Verifică dacă bateria se încarcă
  bool get isCharging => batteryPower > 0.1;

  /// Verifică dacă bateria se descarcă
  bool get isDischarging => batteryPower < -0.1;

  /// Verifică dacă importăm din rețea
  bool get isImportingFromGrid => gridPower > 0.05;

  /// Verifică dacă exportăm în rețea
  bool get isExportingToGrid => gridPower < -0.05;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is EnergyFlowData &&
        other.solarPower == solarPower &&
        other.homePower == homePower &&
        other.batteryPower == batteryPower &&
        other.batteryPercentage == batteryPercentage &&
        other.gridPower == gridPower;
  }

  @override
  int get hashCode {
    return Object.hash(
      solarPower,
      homePower,
      batteryPower,
      batteryPercentage,
      gridPower,
    );
  }

  @override
  String toString() {
    return 'EnergyFlowData(solar: $solarPower kW, home: $homePower kW, '
        'battery: $batteryPower kW @ $batteryPercentage%, grid: $gridPower kW)';
  }
}
