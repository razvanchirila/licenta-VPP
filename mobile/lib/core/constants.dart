/// Core constants for the VPP Simulator Flutter app
class AppConstants {
  // API Configuration
  static const String defaultApiBaseUrl = 'http://localhost:8000';
  static const Duration apiTimeout = Duration(seconds: 10);
  static const int defaultHouseId = 1;
  
  // UI Constants
  static const double borderRadius = 16.0;
  static const double smallBorderRadius = 8.0;
  static const double largeBorderRadius = 24.0;
  
  // Animation Durations
  static const Duration shortAnimation = Duration(milliseconds: 200);
  static const Duration mediumAnimation = Duration(milliseconds: 400);
  static const Duration longAnimation = Duration(milliseconds: 800);
  
  // Colors
  static const int primaryColorValue = 0xFF3B82F6;
  static const int successColorValue = 0xFF22C55E;
  static const int warningColorValue = 0xFFFBBF24;
  static const int errorColorValue = 0xFFEF4444;
  static const int backgroundColorValue = 0xFF000000;
  static const int surfaceColorValue = 0xFF1C1C1E;
  
  // Spacing
  static const double spacingXS = 4.0;
  static const double spacingS = 8.0;
  static const double spacingM = 16.0;
  static const double spacingL = 24.0;
  static const double spacingXL = 32.0;
  
  // Typography
  static const double fontSizeXS = 10.0;
  static const double fontSizeS = 12.0;
  static const double fontSizeM = 14.0;
  static const double fontSizeL = 16.0;
  static const double fontSizeXL = 18.0;
  static const double fontSizeXXL = 24.0;
  
  // Cache Configuration
  static const Duration defaultCacheDuration = Duration(minutes: 15);
  static const Duration weatherCacheDuration = Duration(minutes: 30);
  static const int maxCacheSize = 500;
  
  // Weather Configuration
  static const double defaultLatitude = 44.4268; // Bucharest
  static const double defaultLongitude = 26.1025; // Bucharest
  
  // Energy Thresholds
  static const double minPowerThreshold = 0.05; // kW
  static const double lowBatteryThreshold = 20.0; // %
  static const double highBatteryThreshold = 80.0; // %
  
  // Energy Flow Animation Thresholds
  static const double minSolarPower = 0.1;   // kW - threshold pentru afișare flux solar
  static const double minHomePower = 0.1;    // kW - threshold pentru afișare flux consum
  static const double minBatteryPower = 0.1; // kW - threshold pentru afișare flux baterie
  static const double minGridPower = 0.05;   // kW - threshold pentru afișare flux grid
  
  // Update Intervals
  static const Duration realTimeUpdateInterval = Duration(seconds: 30);
  static const Duration weatherUpdateInterval = Duration(minutes: 10);
  static const Duration savingsUpdateInterval = Duration(minutes: 5);
  
  // Asset Paths
  static const String assetsPath = 'assets/';
  static const String imagesPath = '${assetsPath}images/';
  static const String iconsPath = '${assetsPath}icons/';
}

/// Environment-specific configuration
enum Environment { development, staging, production }

class EnvironmentConfig {
  static Environment get current {
    const env = String.fromEnvironment('ENV', defaultValue: 'development');
    switch (env) {
      case 'production':
        return Environment.production;
      case 'staging':
        return Environment.staging;
      default:
        return Environment.development;
    }
  }
  
  static bool get isDevelopment => current == Environment.development;
  static bool get isProduction => current == Environment.production;
  static bool get isStaging => current == Environment.staging;
  
  static String get apiBaseUrl {
    switch (current) {
      case Environment.production:
        return 'https://api.vpp-simulator.com';
      case Environment.staging:
        return 'https://staging-api.vpp-simulator.com';
      default:
        return AppConstants.defaultApiBaseUrl;
    }
  }
  
  static bool get enableLogging => !isProduction;
  static bool get enableMockData => isDevelopment;
}