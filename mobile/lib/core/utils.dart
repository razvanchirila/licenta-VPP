import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Utility functions for the VPP Simulator app
class AppUtils {
  // Private constructor to prevent instantiation
  AppUtils._();
  
  // Number formatting
  static String formatPower(double power, {int decimals = 1}) {
    return '${power.toStringAsFixed(decimals)} kW';
  }
  
  static String formatEnergy(double energy, {int decimals = 1}) {
    return '${energy.toStringAsFixed(decimals)} kWh';
  }
  
  static String formatPercentage(double percentage, {int decimals = 0}) {
    return '${percentage.toStringAsFixed(decimals)}%';
  }
  
  static String formatCurrency(double amount, {String currency = 'RON', int decimals = 2}) {
    return '${amount.toStringAsFixed(decimals)} $currency';
  }
  
  static String formatTemperature(double temperature, {int decimals = 0}) {
    return '${temperature.toStringAsFixed(decimals)}°C';
  }
  
  // Date formatting
  static String formatTime(DateTime dateTime) {
    return DateFormat('HH:mm').format(dateTime);
  }
  
  static String formatDate(DateTime dateTime) {
    return DateFormat('dd.MM.yyyy').format(dateTime);
  }
  
  static String formatDateTime(DateTime dateTime) {
    return DateFormat('dd.MM.yyyy HH:mm').format(dateTime);
  }
  
  static String formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inMinutes < 1) {
      return 'Acum';
    } else if (difference.inMinutes < 60) {
      return 'Acum ${difference.inMinutes} min';
    } else if (difference.inHours < 24) {
      return 'Acum ${difference.inHours}h';
    } else {
      return formatDate(dateTime);
    }
  }
  
  // Validation
  static bool isValidEmail(String email) {
    return RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email);
  }
  
  static bool isValidPhoneNumber(String phone) {
    return RegExp(r'^\+?[0-9]{10,15}$').hasMatch(phone.replaceAll(RegExp(r'[\s\-\(\)]'), ''));
  }
  
  static bool isValidApiKey(String apiKey) {
    return apiKey.isNotEmpty && apiKey.length >= 16;
  }
  
  // Energy calculations
  static double calculateSavings(double energyUsed, double pricePerKwh) {
    return energyUsed * pricePerKwh;
  }
  
  static double calculateEfficiency(double produced, double consumed) {
    if (consumed == 0) return 0;
    return (produced / consumed) * 100;
  }
  
  static double calculateSelfConsumption(double produced, double exported) {
    if (produced == 0) return 0;
    return ((produced - exported) / produced) * 100;
  }
  
  // UI helpers
  static void showSnackBar(BuildContext context, String message, {
    Color? backgroundColor,
    Duration duration = const Duration(seconds: 3),
    SnackBarAction? action,
  }) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: backgroundColor,
        duration: duration,
        action: action,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }
  
  static void showErrorSnackBar(BuildContext context, String message) {
    showSnackBar(
      context,
      message,
      backgroundColor: const Color(0xFFEF4444),
    );
  }
  
  static void showSuccessSnackBar(BuildContext context, String message) {
    showSnackBar(
      context,
      message,
      backgroundColor: const Color(0xFF22C55E),
    );
  }
  
  static Future<bool?> showConfirmDialog(
    BuildContext context,
    String title,
    String message, {
    String confirmText = 'Confirmă',
    String cancelText = 'Anulează',
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(cancelText),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(confirmText),
          ),
        ],
      ),
    );
  }
  
  // Device info
  static bool isTablet(BuildContext context) {
    final shortestSide = MediaQuery.of(context).size.shortestSide;
    return shortestSide >= 600;
  }
  
  static bool isLandscape(BuildContext context) {
    return MediaQuery.of(context).orientation == Orientation.landscape;
  }
  
  static EdgeInsets getResponsivePadding(BuildContext context) {
    final isTabletDevice = isTablet(context);
    return EdgeInsets.symmetric(
      horizontal: isTabletDevice ? 32 : 16,
      vertical: isTabletDevice ? 24 : 16,
    );
  }
  
  // Animation helpers
  static AnimationController createAnimationController(
    TickerProvider vsync, {
    Duration duration = const Duration(milliseconds: 300),
  }) {
    return AnimationController(
      duration: duration,
      vsync: vsync,
    );
  }
  
  static Animation<double> createFadeAnimation(AnimationController controller) {
    return Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: controller,
      curve: Curves.easeInOut,
    ));
  }
  
  static Animation<Offset> createSlideAnimation(
    AnimationController controller, {
    Offset begin = const Offset(0, 1),
    Offset end = Offset.zero,
  }) {
    return Tween<Offset>(
      begin: begin,
      end: end,
    ).animate(CurvedAnimation(
      parent: controller,
      curve: Curves.easeOutCubic,
    ));
  }
  
  // Debug helpers
  static void debugLog(String message, {String? tag}) {
    if (kDebugMode) {
      final timestamp = DateTime.now().toIso8601String();
      final logTag = tag != null ? '[$tag]' : '[DEBUG]';
      print('$timestamp $logTag $message');
    }
  }
  
  static void debugLogError(String message, {Object? error, StackTrace? stackTrace}) {
    if (kDebugMode) {
      final timestamp = DateTime.now().toIso8601String();
      print('$timestamp [ERROR] $message');
      if (error != null) print('Error: $error');
      if (stackTrace != null) print('StackTrace: $stackTrace');
    }
  }
}

/// Extension methods for common operations
extension DoubleExtensions on double {
  String get kW => AppUtils.formatPower(this);
  String get kWh => AppUtils.formatEnergy(this);
  String get percent => AppUtils.formatPercentage(this);
  String get celsius => AppUtils.formatTemperature(this);
  String get ron => AppUtils.formatCurrency(this);
}

extension DateTimeExtensions on DateTime {
  String get timeString => AppUtils.formatTime(this);
  String get dateString => AppUtils.formatDate(this);
  String get dateTimeString => AppUtils.formatDateTime(this);
  String get relativeString => AppUtils.formatRelativeTime(this);
}

extension BuildContextExtensions on BuildContext {
  void showError(String message) => AppUtils.showErrorSnackBar(this, message);
  void showSuccess(String message) => AppUtils.showSuccessSnackBar(this, message);
  void showMessage(String message) => AppUtils.showSnackBar(this, message);
  
  Future<bool?> confirm(String title, String message) =>
      AppUtils.showConfirmDialog(this, title, message);
  
  bool get isTablet => AppUtils.isTablet(this);
  bool get isLandscape => AppUtils.isLandscape(this);
  EdgeInsets get responsivePadding => AppUtils.getResponsivePadding(this);
}