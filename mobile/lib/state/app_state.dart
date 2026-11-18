import 'package:flutter/material.dart';
import 'package:flutter_interface/core/house_image_selector.dart';
import 'package:flutter_interface/models/climate_settings.dart';

class AppState extends ChangeNotifier {
  static final AppState _instance = AppState._internal();
  factory AppState() => _instance;
  AppState._internal();

  // Indoor temperature of the last simulated step; null until the house is loaded or without a thermal model.
  double? _indoorTemperature;
  double? get indoorTemperature => _indoorTemperature;

  void setIndoorTemperature(double? value) {
    if (_indoorTemperature == value) return;
    _indoorTemperature = value;
    notifyListeners();
  }

  // Outdoor weather from WeatherAPI; null until loaded, then "--°" with the plain label "Vreme" on error.
  double? _outdoorTemperature;
  double? get outdoorTemperature => _outdoorTemperature;

  String _weatherDescription = 'Vreme';
  String get weatherDescription => _weatherDescription;

  IconData _weatherIcon = Icons.cloud_outlined;
  IconData get weatherIcon => _weatherIcon;

  void setWeather({required double? temperature, required String description, required IconData icon}) {
    _outdoorTemperature = temperature;
    _weatherDescription = description;
    _weatherIcon = icon;
    notifyListeners();
  }

  bool _useCelsius = true;
  bool get useCelsius => _useCelsius;
  set useCelsius(bool value) {
    _useCelsius = value;
    notifyListeners();
  }

  ClimateSettings _climateSettings = const ClimateSettings();
  ClimateSettings get climateSettings => _climateSettings;

  void updateClimateSettings(ClimateSettings settings) {
    _climateSettings = settings;
    notifyListeners();
  }

  bool _allLightsOn = true;
  bool get allLightsOn => _allLightsOn;

  void toggleAllLights() {
    _allLightsOn = !_allLightsOn;
    notifyListeners();
  }

  bool _isDayMode = true;
  bool get isDayMode => _isDayMode;

  void setDayMode(bool isDay) {
    if (_isDayMode == isDay) return;
    _isDayMode = isDay;
    notifyListeners();
  }

  String getHouseImagePath() {
    return HouseImageSelector.getImagePath(
      isDayMode: _isDayMode,
      lightsOn: _allLightsOn,
    );
  }
}

final appState = AppState();
