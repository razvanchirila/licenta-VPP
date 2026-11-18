import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/models/solar_forecast_data.dart';

/// Cached to respect the 12 requests/hour rate limit of forecast.solar.
class SolarForecastService {
  static const double defaultLatitude = SiteLocation.latitude;
  static const double defaultLongitude = SiteLocation.longitude;
  static const double defaultDeclination = 35.0; // tilt angle
  static const double defaultAzimuth = 180.0; // south facing
  static const double defaultKwp = 10.0;

  static const String _cacheKey = 'solar_forecast_cache';
  static const String _cacheTimestampKey = 'solar_forecast_timestamp';
  static const Duration _cacheDuration = Duration(hours: 6);

  static final SolarForecastService _instance = SolarForecastService._internal();
  factory SolarForecastService() => _instance;
  SolarForecastService._internal();

  String _buildApiUrl({
    double? lat,
    double? lon,
    double? dec,
    double? az,
    double? kwp,
  }) {
    final latitude = lat ?? defaultLatitude;
    final longitude = lon ?? defaultLongitude;
    final declination = dec ?? defaultDeclination;
    final azimuth = az ?? defaultAzimuth;
    final power = kwp ?? defaultKwp;

    return 'https://api.forecast.solar/estimate/$latitude/$longitude/$declination/$azimuth/$power';
  }

  Future<bool> _isCacheValid() async {
    final prefs = await SharedPreferences.getInstance();
    final timestampStr = prefs.getString(_cacheTimestampKey);
    if (timestampStr == null) return false;

    final timestamp = DateTime.tryParse(timestampStr);
    if (timestamp == null) return false;

    return DateTime.now().difference(timestamp) < _cacheDuration;
  }

  Future<SolarForecastData?> _getCachedData() async {
    final prefs = await SharedPreferences.getInstance();
    final cachedJson = prefs.getString(_cacheKey);
    if (cachedJson == null) return null;

    try {
      final data = jsonDecode(cachedJson);
      return SolarForecastData.fromJson(data);
    } catch (e) {
      return null;
    }
  }

  Future<void> _saveToCache(Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey, jsonEncode(data));
    await prefs.setString(_cacheTimestampKey, DateTime.now().toIso8601String());
  }

  Future<DateTime?> getCacheTimestamp() async {
    final prefs = await SharedPreferences.getInstance();
    final timestampStr = prefs.getString(_cacheTimestampKey);
    if (timestampStr == null) return null;
    return DateTime.tryParse(timestampStr);
  }

  Future<SolarForecastResult> getForecast({
    double? lat,
    double? lon,
    double? dec,
    double? az,
    double? kwp,
    bool forceRefresh = false,
  }) async {
    if (!forceRefresh && await _isCacheValid()) {
      final cachedData = await _getCachedData();
      if (cachedData != null) {
        final timestamp = await getCacheTimestamp();
        return SolarForecastResult(
          data: cachedData,
          fromCache: true,
          timestamp: timestamp,
        );
      }
    }

    try {
      final url = _buildApiUrl(lat: lat, lon: lon, dec: dec, az: az, kwp: kwp);
      final response = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final jsonData = jsonDecode(response.body);
        await _saveToCache(jsonData);
        return SolarForecastResult(
          data: SolarForecastData.fromJson(jsonData),
          fromCache: false,
          timestamp: DateTime.now(),
        );
      } else if (response.statusCode == 429) {
        // Rate limit exceeded - try to use cache
        final cachedData = await _getCachedData();
        if (cachedData != null) {
          final timestamp = await getCacheTimestamp();
          return SolarForecastResult(
            data: cachedData,
            fromCache: true,
            timestamp: timestamp,
            rateLimited: true,
          );
        }
        return SolarForecastResult(
          error: 'Limită depășită. Încearcă din nou peste o oră.',
          rateLimited: true,
        );
      } else {
        return SolarForecastResult(
          error: 'Eroare API: ${response.statusCode}',
        );
      }
    } catch (e) {
      final cachedData = await _getCachedData();
      if (cachedData != null) {
        final timestamp = await getCacheTimestamp();
        return SolarForecastResult(
          data: cachedData,
          fromCache: true,
          timestamp: timestamp,
          networkError: true,
        );
      }
      return SolarForecastResult(
        error: 'Nu s-au putut încărca predicțiile. Verifică conexiunea.',
        networkError: true,
      );
    }
  }
}

class SolarForecastResult {
  final SolarForecastData? data;
  final String? error;
  final bool fromCache;
  final DateTime? timestamp;
  final bool rateLimited;
  final bool networkError;

  SolarForecastResult({
    this.data,
    this.error,
    this.fromCache = false,
    this.timestamp,
    this.rateLimited = false,
    this.networkError = false,
  });

  bool get hasData => data != null;
  bool get hasError => error != null;
}

final solarForecastService = SolarForecastService();
