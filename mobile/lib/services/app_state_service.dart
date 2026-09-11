import '../core/utils.dart';

/// Service for managing global application state
/// 
/// This service handles app-wide settings and preferences.
/// In production, this should sync with backend APIs.
class AppStateService {
  static final AppStateService _instance = AppStateService._internal();
  factory AppStateService() => _instance;
  AppStateService._internal();

  // House ID (default: 1)
  int _houseId = 1;
  
  // Battery backup reserve (0-100%)
  double _backupReserve = 20.0;
  
  // Operating mode: 'Eco' or 'Profit'
  String _mode = 'Eco';
  
  // Time of use selection: 'Peak' or 'Off-Peak'
  String _timeOfUse = 'Off-Peak';

  // Getters
  int get houseId => _houseId;
  double get backupReserve => _backupReserve;
  String get mode => _mode;
  String get timeOfUse => _timeOfUse;

  // Setters with validation
  set houseId(int value) {
    if (value > 0) {
      _houseId = value;
      AppUtils.debugLog('House ID updated to: $value', tag: 'AppStateService');
    }
  }

  set backupReserve(double value) {
    if (value >= 0 && value <= 100) {
      _backupReserve = value;
      AppUtils.debugLog('Backup reserve updated to: $value%', tag: 'AppStateService');
    }
  }

  set mode(String value) {
    if (value == 'Eco' || value == 'Profit') {
      _mode = value;
      AppUtils.debugLog('Mode updated to: $value', tag: 'AppStateService');
    }
  }

  set timeOfUse(String value) {
    if (value == 'Peak' || value == 'Off-Peak') {
      _timeOfUse = value;
      AppUtils.debugLog('Time of use updated to: $value', tag: 'AppStateService');
    }
  }

  /// Reset to default values
  void reset() {
    _backupReserve = 20.0;
    _mode = 'Eco';
    _timeOfUse = 'Off-Peak';
    AppUtils.debugLog('App state reset to defaults', tag: 'AppStateService');
  }

  /// Load state from storage (future implementation)
  Future<void> loadFromStorage() async {
    // TODO: Implement loading from SharedPreferences or secure storage
    AppUtils.debugLog('Loading app state from storage...', tag: 'AppStateService');
  }

  /// Save state to storage (future implementation)
  Future<void> saveToStorage() async {
    // TODO: Implement saving to SharedPreferences or secure storage
    AppUtils.debugLog('Saving app state to storage...', tag: 'AppStateService');
  }
}

/// Global service instance
final appStateService = AppStateService();