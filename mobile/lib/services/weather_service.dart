import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/models/weather_data.dart';
import 'package:http/http.dart' as http;

/// Key injected with `--dart-define=WEATHER_API_KEY=...`; without it, or on any error,
/// the result is null and the UI shows "--°" (never fake weather).
class WeatherService {
  static const String _apiKey = String.fromEnvironment('WEATHER_API_KEY');
  static const String _baseUrl = 'https://api.weatherapi.com/v1';
  static const Duration _cacheValidity = Duration(minutes: 10);

  final http.Client _client;
  WeatherData? _cachedWeather;
  DateTime? _lastFetch;

  WeatherService({http.Client? client}) : _client = client ?? http.Client();

  bool get isConfigured => _apiKey.isNotEmpty;

  /// [location] can be a city name or "lat,lon".
  Future<WeatherData?> getCurrentWeather(String location) async {
    if (_cachedWeather != null && _lastFetch != null) {
      if (DateTime.now().difference(_lastFetch!) < _cacheValidity) {
        return _cachedWeather;
      }
    }
    if (!isConfigured) return null;

    try {
      final url = Uri.parse('$_baseUrl/current.json').replace(queryParameters: {
        'key': _apiKey,
        'q': location,
        'aqi': 'no',
        'lang': 'ro',
      });
      final response = await _client.get(url).timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) {
        debugPrint('WeatherAPI: HTTP ${response.statusCode}');
        return _cachedWeather;
      }
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      _cachedWeather = WeatherData.fromWeatherApiJson(json);
      _lastFetch = DateTime.now();
      return _cachedWeather;
    } catch (e) {
      debugPrint('WeatherAPI: $e');
      return _cachedWeather;
    }
  }

  Future<WeatherData?> getSiteWeather() => getCurrentWeather(SiteLocation.query);
}

final weatherService = WeatherService();
