import 'package:flutter/material.dart';

enum WeatherCondition {
  sunny,
  partlyCloudy,
  cloudy,
  rainy,
  stormy,
  foggy,
  snow,
  unknown,
}

class Temperature {
  final double _celsius;

  const Temperature({required double celsius}) : _celsius = celsius;

  double get value => _celsius;
  String get celsius => '${_celsius.round()}°C';
  String get fahrenheit => '${(_celsius * 9 / 5 + 32).round()}°F';

  @override
  String toString() => celsius;
}

class WeatherData {
  final WeatherCondition condition;
  final Temperature temperature;
  final int humidity;
  final double windSpeed;
  final String description;
  final double solarFavorability; // 0.0 - 1.0
  final String? locationName;
  final DateTime lastUpdated;

  const WeatherData({
    required this.condition,
    required this.temperature,
    required this.humidity,
    this.windSpeed = 0.0,
    required this.description,
    required this.solarFavorability,
    this.locationName,
    required this.lastUpdated,
  });

  IconData get icon => _getWeatherIcon(condition);

  bool get isSolarFavorable => solarFavorability > 0.5;

  factory WeatherData.fromWeatherApiJson(Map<String, dynamic> json) {
    final current = (json['current'] as Map?) ?? const {};
    final location = (json['location'] as Map?) ?? const {};

    final tempC = (current['temp_c'] as num?)?.toDouble() ?? 0.0;
    final conditionCode = (current['condition']?['code'] as num?)?.toInt() ?? 0;
    final conditionText = current['condition']?['text']?.toString() ?? 'Necunoscut';
    final humidity = (current['humidity'] as num?)?.toInt() ?? 0;
    final windKph = (current['wind_kph'] as num?)?.toDouble() ?? 0.0;
    final cloud = (current['cloud'] as num?)?.toInt() ?? 0;
    final uv = (current['uv'] as num?)?.toDouble() ?? 0.0;
    final isDay = current['is_day'] == 1;

    final condition = _mapConditionCode(conditionCode, isDay);
    final solarImpact = _calculateSolarImpact(cloud, uv, isDay);

    return WeatherData(
      condition: condition,
      temperature: Temperature(celsius: tempC),
      humidity: humidity,
      windSpeed: windKph,
      description: conditionText,
      solarFavorability: solarImpact,
      locationName: '${location['name']}, ${location['country']}',
      lastUpdated: DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'condition': condition.name,
      'temperature': temperature.value,
      'humidity': humidity,
      'wind_speed': windSpeed,
      'description': description,
      'solar_favorability': solarFavorability,
      'location_name': locationName,
      'last_updated': lastUpdated.toIso8601String(),
    };
  }

  WeatherData copyWith({
    WeatherCondition? condition,
    Temperature? temperature,
    int? humidity,
    double? windSpeed,
    String? description,
    double? solarFavorability,
    String? locationName,
    DateTime? lastUpdated,
  }) {
    return WeatherData(
      condition: condition ?? this.condition,
      temperature: temperature ?? this.temperature,
      humidity: humidity ?? this.humidity,
      windSpeed: windSpeed ?? this.windSpeed,
      description: description ?? this.description,
      solarFavorability: solarFavorability ?? this.solarFavorability,
      locationName: locationName ?? this.locationName,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }

  static IconData _getWeatherIcon(WeatherCondition condition) {
    switch (condition) {
      case WeatherCondition.sunny:
        return Icons.wb_sunny;
      case WeatherCondition.partlyCloudy:
        return Icons.wb_cloudy;
      case WeatherCondition.cloudy:
        return Icons.cloud;
      case WeatherCondition.rainy:
        return Icons.water_drop;
      case WeatherCondition.stormy:
        return Icons.thunderstorm;
      case WeatherCondition.foggy:
        return Icons.foggy;
      case WeatherCondition.snow:
        return Icons.ac_unit;
      case WeatherCondition.unknown:
        return Icons.help_outline;
    }
  }

  static WeatherCondition _mapConditionCode(int code, bool isDay) {
    // Sunny / Clear
    if (code == 1000) return WeatherCondition.sunny;

    // Partly cloudy
    if (code == 1003) return WeatherCondition.partlyCloudy;

    // Cloudy / Overcast
    if (code == 1006 || code == 1009) return WeatherCondition.cloudy;

    // Mist / Fog
    if (code == 1030 || code == 1135 || code == 1147) {
      return WeatherCondition.foggy;
    }

    // Rain
    if ([1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246].contains(code)) {
      return WeatherCondition.rainy;
    }

    // Thunderstorm
    if ([1087, 1273, 1276, 1279, 1282].contains(code)) {
      return WeatherCondition.stormy;
    }

    // Snow
    if ([1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258].contains(code)) {
      return WeatherCondition.snow;
    }

    // Sleet / Freezing rain
    if ([1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1237, 1249, 1252, 1261, 1264].contains(code)) {
      return WeatherCondition.rainy;
    }

    return WeatherCondition.unknown;
  }

  /// 0.0 - 1.0
  static double _calculateSolarImpact(int cloudPercent, double uv, bool isDay) {
    if (!isDay) return 0.0;

    double impact = (100 - cloudPercent) / 100.0;
    final uvFactor = (uv / 11.0).clamp(0.0, 1.0);
    impact = (impact * 0.7 + uvFactor * 0.3).clamp(0.0, 1.0);

    return impact;
  }
}
