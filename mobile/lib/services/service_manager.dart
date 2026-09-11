import 'package:flutter_interface/services/api_service.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/core/utils.dart';

/// Centralized service manager for the VPP Simulator app
class ServiceManager {
  static final ServiceManager _instance = ServiceManager._internal();
  factory ServiceManager() => _instance;
  ServiceManager._internal();

  // Service instances
  late final ApiService _apiService;
  
  bool _isInitialized = false;

  /// Initialize all services
  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      AppUtils.debugLog('Initializing services...', tag: 'ServiceManager');
      
      // Initialize API service
      _apiService = ApiService(
        baseUrl: EnvironmentConfig.apiBaseUrl,
        defaultHouseId: AppConstants.defaultHouseId,
      );

      // Test API connection in development
      if (EnvironmentConfig.isDevelopment) {
        final isAvailable = await _apiService.isApiAvailable();
        AppUtils.debugLog('API available: $isAvailable', tag: 'ServiceManager');
      }

      _isInitialized = true;
      AppUtils.debugLog('Services initialized successfully', tag: 'ServiceManager');
    } catch (e, stackTrace) {
      AppUtils.debugLogError('Failed to initialize services', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  /// Get API service instance
  ApiService get apiService {
    _ensureInitialized();
    return _apiService;
  }

  /// Dispose all services
  void dispose() {
    if (!_isInitialized) return;
    
    AppUtils.debugLog('Disposing services...', tag: 'ServiceManager');
    _apiService.dispose();
    _isInitialized = false;
  }

  /// Ensure services are initialized
  void _ensureInitialized() {
    if (!_isInitialized) {
      throw StateError('ServiceManager not initialized. Call initialize() first.');
    }
  }

  /// Reset all services (useful for testing)
  Future<void> reset() async {
    dispose();
    await initialize();
  }
}

/// Global service manager instance
final serviceManager = ServiceManager();