import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_interface/models/weather_data.dart';

/// Service pentru obținerea datelor meteo de la WeatherAPI.com
class WeatherService {

  static const String _apiKey = String.fromEnvironment('WEATHER_API_KEY', defaultValue: 'YOUR_API_KEY_HERE'); // TODO: Înlocuiește cu cheia ta
  static const String _baseUrl = 'https://api.weatherapi.com/v1';

  // Cache pentru a nu face prea multe cereri
  WeatherData? _cachedWeather;
  DateTime? _lastFetch;
  static const Duration _cacheValidity = Duration(minutes: 10);

  /// Verifică dacă cheia API este configurată
  bool get isConfigured => _apiKey != 'YOUR_API_KEY_HERE' && _apiKey.isNotEmpty;

  /// Obține vremea curentă pentru o locație
  /// [location] poate fi: oraș, coordonate (lat,lon), cod poștal, IP
  Future<WeatherData?> getCurrentWeather(String location) async {
    // Verifică cache
    if (_cachedWeather != null && _lastFetch != null) {
      if (DateTime.now().difference(_lastFetch!) < _cacheValidity) {
        return _cachedWeather;
      }
    }

    // Dacă API-ul nu e configurat, returnează date mock
    if (!isConfigured) {
      print('WeatherService: API key nu este configurat, folosesc date mock');
      return WeatherData.sunny;
    }

    try {
      final url = Uri.parse(
          '$_baseUrl/current.json?key=$_apiKey&q=$location&aqi=no&lang=ro');

      final response = await http.get(url).timeout(
            const Duration(seconds: 10),
            onTimeout: () => throw Exception('Timeout la cererea meteo'),
          );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body);
        _cachedWeather = WeatherData.fromWeatherApiJson(json);
        _lastFetch = DateTime.now();
        return _cachedWeather;
      } else {
        print('Eroare API meteo: ${response.statusCode} - ${response.body}');
        return _cachedWeather ?? WeatherData.sunny;
      }
    } catch (e) {
      print('Eroare la obținerea vremii: $e');
      return _cachedWeather ?? WeatherData.sunny;
    }
  }

  /// Obține vremea pentru coordonate GPS
  Future<WeatherData?> getWeatherByCoordinates(double lat, double lon) async {
    return getCurrentWeather('$lat,$lon');
  }

  /// Obține vremea pentru București (default)
  Future<WeatherData?> getWeatherBucharest() async {
    return getCurrentWeather('Bucharest');
  }

  /// Invalidează cache-ul
  void clearCache() {
    _cachedWeather = null;
    _lastFetch = null;
  }
}

/// Instanță globală pentru acces ușor
final weatherService = WeatherService();
