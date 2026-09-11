import 'package:flutter/material.dart';
import 'package:flutter_interface/models/climate_settings.dart';
import 'package:flutter_interface/models/temperature_data.dart';
import 'package:flutter_interface/models/price_data.dart';
import 'package:flutter_interface/core/house_image_selector.dart';

/// Global application state for persisting settings between screens
/// 
/// This is a simple singleton that holds the current settings.
/// When backend is connected, this will sync with the API.

class AppState extends ChangeNotifier {
  // Singleton instance
  static final AppState _instance = AppState._internal();
  factory AppState() => _instance;
  AppState._internal() {
    _initDevices();
  }
  
  // ============================================================
  // CLIMATE & TEMPERATURE STATE
  // ============================================================
  
  // Indoor temperature (mock, in Celsius)
  double _indoorTemperature = 22.0;
  double get indoorTemperature => _indoorTemperature;
  set indoorTemperature(double value) {
    _indoorTemperature = value;
    notifyListeners();
  }
  
  // Outdoor temperature (mock, in Celsius)
  double _outdoorTemperature = 18.0;
  double get outdoorTemperature => _outdoorTemperature;
  set outdoorTemperature(double value) {
    _outdoorTemperature = value;
    notifyListeners();
  }
  
  // Weather description (e.g., "Însorit", "Înnorat", "Ploios")
  String _weatherDescription = 'Însorit';
  String get weatherDescription => _weatherDescription;
  set weatherDescription(String value) {
    _weatherDescription = value;
    notifyListeners();
  }
  
  // Weather icon
  IconData _weatherIcon = Icons.wb_sunny_rounded;
  IconData get weatherIcon => _weatherIcon;
  set weatherIcon(IconData value) {
    _weatherIcon = value;
    notifyListeners();
  }
  
  // Use Celsius or Fahrenheit
  bool _useCelsius = true;
  bool get useCelsius => _useCelsius;
  set useCelsius(bool value) {
    _useCelsius = value;
    notifyListeners();
  }
  
  // Climate control settings
  ClimateSettings _climateSettings = const ClimateSettings();
  ClimateSettings get climateSettings => _climateSettings;
  
  void updateClimateSettings(ClimateSettings settings) {
    _climateSettings = settings;
    notifyListeners();
  }
  
  void setClimateTemperature(double temp) {
    _climateSettings = _climateSettings.copyWith(targetTemperature: temp);
    notifyListeners();
  }
  
  void setClimateMode(ClimateMode mode) {
    _climateSettings = _climateSettings.copyWith(mode: mode);
    notifyListeners();
  }
  
  void toggleClimatePower() {
    _climateSettings = _climateSettings.copyWith(isOn: !_climateSettings.isOn);
    notifyListeners();
  }
  
  // ============================================================
  // LIGHTING STATE
  // ============================================================
  
  bool _allLightsOn = true;
  bool get allLightsOn => _allLightsOn;
  
  void toggleAllLights() {
    _allLightsOn = !_allLightsOn;
    notifyListeners();
  }
  
  void setAllLights(bool on) {
    _allLightsOn = on;
    notifyListeners();
  }

  // ============================================================
  // WEATHER MODE STATE (Day/Night for house image)
  // ============================================================
  
  // Weather mode: true = day/sunny, false = night/rainy
  bool _isDayMode = true;
  bool get isDayMode => _isDayMode;
  
  void setDayMode(bool isDay) {
    _isDayMode = isDay;
    notifyListeners();
  }
  
  void toggleDayMode() {
    _isDayMode = !_isDayMode;
    notifyListeners();
  }

  /// Returns the appropriate house image path based on current state.
  /// Uses HouseImageSelector to determine correct image based on
  /// isDayMode and allLightsOn state.
  /// _Requirements: 4.1_
  String getHouseImagePath() {
    return HouseImageSelector.getImagePath(
      isDayMode: _isDayMode,
      lightsOn: _allLightsOn,
    );
  }

  // House ID (default: 1)
  int houseId = 1;

  // Battery backup reserve (0-100%)
  double _backupReserve = 20.0;
  double get backupReserve => _backupReserve;
  set backupReserve(double value) {
    _backupReserve = value;
    notifyListeners();
  }

  // Operating mode: "Eco" or "Profit"
  String _mode = "Eco";
  String get mode => _mode;
  set mode(String value) {
    _mode = value;
    notifyListeners();
  }

  // Time of use selection: "Peak" or "Off-Peak"
  String _timeOfUse = "Off-Peak";
  String get timeOfUse => _timeOfUse;
  set timeOfUse(String value) {
    _timeOfUse = value;
    notifyListeners();
  }

  // Devices list
  List<DeviceState> _devices = [];
  List<DeviceState> get devices => _devices;

  void _initDevices() {
    _devices = [
      DeviceState(id: 1, name: 'Frigider', icon: Icons.kitchen_rounded, powerWatts: 150, isOn: true, isCritical: true),
      DeviceState(id: 2, name: 'Aer condiționat', icon: Icons.ac_unit_rounded, powerWatts: 1200, isOn: true, isCritical: false),
      DeviceState(id: 3, name: 'Mașină de spălat', icon: Icons.local_laundry_service_rounded, powerWatts: 500, isOn: false, isCritical: false),
      DeviceState(id: 4, name: 'TV Living', icon: Icons.tv_rounded, powerWatts: 120, isOn: true, isCritical: false),
      DeviceState(id: 5, name: 'Iluminat', icon: Icons.lightbulb_rounded, powerWatts: 60, isOn: true, isCritical: true),
      DeviceState(id: 6, name: 'Încărcător EV', icon: Icons.electric_car_rounded, powerWatts: 7400, isOn: false, isCritical: false),
      DeviceState(id: 7, name: 'Boiler electric', icon: Icons.water_drop_rounded, powerWatts: 2000, isOn: false, isCritical: false),
      DeviceState(id: 8, name: 'Router WiFi', icon: Icons.router_rounded, powerWatts: 15, isOn: true, isCritical: true),
    ];
  }

  /// Toggle device on/off
  void toggleDevice(int id) {
    final index = _devices.indexWhere((d) => d.id == id);
    if (index != -1 && !_devices[index].isCritical) {
      _devices[index] = _devices[index].copyWith(isOn: !_devices[index].isOn);
      notifyListeners();
    }
  }

  /// Add a new device
  void addDevice({
    required String name,
    required IconData icon,
    required int powerWatts,
    bool isCritical = false,
  }) {
    final newId = _devices.isEmpty ? 1 : _devices.map((d) => d.id).reduce((a, b) => a > b ? a : b) + 1;
    _devices.add(DeviceState(
      id: newId,
      name: name,
      icon: icon,
      powerWatts: powerWatts,
      isOn: false,
      isCritical: isCritical,
    ));
    notifyListeners();
  }

  /// Remove a device
  void removeDevice(int id) {
    _devices.removeWhere((d) => d.id == id);
    notifyListeners();
  }

  /// Get total power consumption from active devices (in kW)
  double get totalDevicePowerKw {
    final totalWatts = _devices
        .where((d) => d.isOn)
        .fold(0, (sum, d) => sum + d.powerWatts);
    return totalWatts / 1000.0;
  }

  /// Get count of active devices
  int get activeDeviceCount => _devices.where((d) => d.isOn).length;

  // ============================================================
  // OPCOM PRICE STATE
  // ============================================================
  
  PriceData? _priceData;
  PriceData? get priceData => _priceData;
  
  /// Current price in lei/kWh
  double get currentPriceLeiKwh => _priceData?.currentPriceLeiKwh ?? 0.0;
  
  /// Is price rising compared to previous hour
  bool get isPriceRising => _priceData?.change.isUp ?? false;
  
  /// Update price data from API
  void updatePriceData(PriceData? data) {
    _priceData = data;
    notifyListeners();
  }
  
  // ============================================================
  // ENERGY FLOW CALCULATION
  // ============================================================
  
  // Solar production (kW) - can be set externally based on weather
  double _solarPower = 3.1;
  double get solarPower => _solarPower;
  set solarPower(double value) {
    _solarPower = value;
    notifyListeners();
  }
  
  // Battery state
  double _batteryCapacityKwh = 13.5; // Tesla Powerwall capacity
  double _batteryChargeKwh = 10.0; // Current charge in kWh
  double get batteryPercentage => (_batteryChargeKwh / _batteryCapacityKwh * 100).clamp(0, 100);
  
  // Max charge/discharge rates
  final double _maxBatteryChargeKw = 5.0;
  final double _maxBatteryDischargeKw = 5.0;
  
  /// Calculate energy flows based on solar production and home consumption
  /// Returns: (batteryPower, gridPower) where:
  /// - batteryPower > 0 means charging, < 0 means discharging
  /// - gridPower > 0 means importing, < 0 means exporting
  EnergyFlows calculateEnergyFlows() {
    final homeConsumption = totalDevicePowerKw;
    final solar = _solarPower;
    
    double batteryPower = 0.0;
    double gridPower = 0.0;
    
    final energyBalance = solar - homeConsumption;
    
    if (energyBalance >= 0) {
      // Solar covers consumption, excess available
      final excess = energyBalance;
      
      // Try to charge battery first (if not full)
      if (batteryPercentage < 100) {
        final availableCapacity = _batteryCapacityKwh - _batteryChargeKwh;
        final maxChargeNow = _maxBatteryChargeKw.clamp(0.0, availableCapacity);
        batteryPower = excess.clamp(0.0, maxChargeNow);
      }
      
      // Export remaining to grid
      final remaining = excess - batteryPower;
      if (remaining > 0) {
        gridPower = -remaining; // Negative = export
      }
    } else {
      // Solar doesn't cover consumption, need additional power
      final deficit = -energyBalance;
      
      // Try to use battery first (if above backup reserve)
      final usableCharge = _batteryChargeKwh - (_batteryCapacityKwh * backupReserve / 100);
      if (usableCharge > 0) {
        final maxDischargeNow = _maxBatteryDischargeKw.clamp(0.0, usableCharge);
        batteryPower = -deficit.clamp(0.0, maxDischargeNow); // Negative = discharge
      }
      
      // Import remaining from grid
      final remaining = deficit + batteryPower; // batteryPower is negative
      if (remaining > 0) {
        gridPower = remaining; // Positive = import
      }
    }
    
    return EnergyFlows(
      solarPower: solar,
      homePower: homeConsumption,
      batteryPower: batteryPower,
      gridPower: gridPower,
      batteryPercentage: batteryPercentage.round(),
    );
  }
  
  /// Set battery percentage directly (for testing)
  void setBatteryPercentage(double percent) {
    _batteryChargeKwh = _batteryCapacityKwh * percent.clamp(0, 100) / 100;
    notifyListeners();
  }

  // Reset to defaults
  void reset() {
    _backupReserve = 20.0;
    _mode = "Eco";
    _timeOfUse = "Off-Peak";
    _initDevices();
    notifyListeners();
  }
}

/// Device state model
class DeviceState {
  final int id;
  final String name;
  final IconData icon;
  final int powerWatts;
  final bool isOn;
  final bool isCritical;

  DeviceState({
    required this.id,
    required this.name,
    required this.icon,
    required this.powerWatts,
    required this.isOn,
    required this.isCritical,
  });

  DeviceState copyWith({
    int? id,
    String? name,
    IconData? icon,
    int? powerWatts,
    bool? isOn,
    bool? isCritical,
  }) {
    return DeviceState(
      id: id ?? this.id,
      name: name ?? this.name,
      icon: icon ?? this.icon,
      powerWatts: powerWatts ?? this.powerWatts,
      isOn: isOn ?? this.isOn,
      isCritical: isCritical ?? this.isCritical,
    );
  }
}

/// Energy flows data class
class EnergyFlows {
  final double solarPower;
  final double homePower;
  final double batteryPower;
  final double gridPower;
  final int batteryPercentage;

  EnergyFlows({
    required this.solarPower,
    required this.homePower,
    required this.batteryPower,
    required this.gridPower,
    required this.batteryPercentage,
  });
}

/// Global instance for easy access
final appState = AppState();
