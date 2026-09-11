/// Model for temperature data with unit conversion
class TemperatureData {
  final double indoorTemperature; // Always stored in Celsius
  final double outdoorTemperature; // Always stored in Celsius
  final bool useCelsius;

  const TemperatureData({
    this.indoorTemperature = 22.0,
    this.outdoorTemperature = 18.0,
    this.useCelsius = true,
  });

  /// Get indoor temperature in display unit
  double get displayIndoor => useCelsius ? indoorTemperature : _toFahrenheit(indoorTemperature);

  /// Get outdoor temperature in display unit
  double get displayOutdoor => useCelsius ? outdoorTemperature : _toFahrenheit(outdoorTemperature);

  /// Get unit symbol
  String get unitSymbol => useCelsius ? '°C' : '°F';

  /// Convert Celsius to Fahrenheit
  static double _toFahrenheit(double celsius) => celsius * 9 / 5 + 32;

  /// Convert Fahrenheit to Celsius
  static double toFahrenheit(double celsius) => celsius * 9 / 5 + 32;
  
  /// Convert Fahrenheit to Celsius
  static double toCelsius(double fahrenheit) => (fahrenheit - 32) * 5 / 9;

  TemperatureData copyWith({
    double? indoorTemperature,
    double? outdoorTemperature,
    bool? useCelsius,
  }) {
    return TemperatureData(
      indoorTemperature: indoorTemperature ?? this.indoorTemperature,
      outdoorTemperature: outdoorTemperature ?? this.outdoorTemperature,
      useCelsius: useCelsius ?? this.useCelsius,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is TemperatureData &&
        other.indoorTemperature == indoorTemperature &&
        other.outdoorTemperature == outdoorTemperature &&
        other.useCelsius == useCelsius;
  }

  @override
  int get hashCode => Object.hash(indoorTemperature, outdoorTemperature, useCelsius);
}
