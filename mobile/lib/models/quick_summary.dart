import 'package:flutter/material.dart';

/// Quick summary model for system overview
class QuickSummary {
  final double batteryPercentage;
  final double currentSolarProduction;
  final GridStatus gridStatus;
  final double todayProduction;
  final double todayConsumption;
  final double todaySavings;
  final List<SystemAlert> alerts;

  const QuickSummary({
    required this.batteryPercentage,
    required this.currentSolarProduction,
    required this.gridStatus,
    required this.todayProduction,
    required this.todayConsumption,
    required this.todaySavings,
    required this.alerts,
  });

  /// Create from JSON
  factory QuickSummary.fromJson(Map<String, dynamic> json) {
    return QuickSummary(
      batteryPercentage: (json['battery_percentage'] ?? 0.0).toDouble(),
      currentSolarProduction: (json['current_solar_production'] ?? 0.0).toDouble(),
      gridStatus: GridStatus.values.firstWhere(
        (e) => e.name == json['grid_status'],
        orElse: () => GridStatus.offline,
      ),
      todayProduction: (json['today_production'] ?? 0.0).toDouble(),
      todayConsumption: (json['today_consumption'] ?? 0.0).toDouble(),
      todaySavings: (json['today_savings'] ?? 0.0).toDouble(),
      alerts: (json['alerts'] as List<dynamic>? ?? [])
          .map((alert) => SystemAlert.fromJson(alert))
          .toList(),
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'battery_percentage': batteryPercentage,
      'current_solar_production': currentSolarProduction,
      'grid_status': gridStatus.name,
      'today_production': todayProduction,
      'today_consumption': todayConsumption,
      'today_savings': todaySavings,
      'alerts': alerts.map((alert) => alert.toJson()).toList(),
    };
  }

  /// Create a copy with updated values
  QuickSummary copyWith({
    double? batteryPercentage,
    double? currentSolarProduction,
    GridStatus? gridStatus,
    double? todayProduction,
    double? todayConsumption,
    double? todaySavings,
    List<SystemAlert>? alerts,
  }) {
    return QuickSummary(
      batteryPercentage: batteryPercentage ?? this.batteryPercentage,
      currentSolarProduction: currentSolarProduction ?? this.currentSolarProduction,
      gridStatus: gridStatus ?? this.gridStatus,
      todayProduction: todayProduction ?? this.todayProduction,
      todayConsumption: todayConsumption ?? this.todayConsumption,
      todaySavings: todaySavings ?? this.todaySavings,
      alerts: alerts ?? this.alerts,
    );
  }

  /// Get grid status text
  String get gridStatusText {
    switch (gridStatus) {
      case GridStatus.importing:
        return 'Import';
      case GridStatus.exporting:
        return 'Export';
      case GridStatus.balanced:
        return 'Echilibrat';
      case GridStatus.offline:
        return 'Offline';
    }
  }

  /// Get grid status color
  Color get gridStatusColor {
    switch (gridStatus) {
      case GridStatus.importing:
        return const Color(0xFFEF4444); // Red
      case GridStatus.exporting:
        return const Color(0xFF22C55E); // Green
      case GridStatus.balanced:
        return const Color(0xFF3B82F6); // Blue
      case GridStatus.offline:
        return const Color(0xFF6B7280); // Gray
    }
  }

  /// Get unread alerts count
  int get unreadAlertsCount => alerts.where((alert) => !alert.isRead).length;

  /// Get highest severity alert
  AlertSeverity get highestSeverity {
    if (alerts.isEmpty) return AlertSeverity.info;
    
    final severities = alerts.map((alert) => alert.severity).toList();
    if (severities.contains(AlertSeverity.critical)) return AlertSeverity.critical;
    if (severities.contains(AlertSeverity.error)) return AlertSeverity.error;
    if (severities.contains(AlertSeverity.warning)) return AlertSeverity.warning;
    return AlertSeverity.info;
  }

  /// Get energy efficiency ratio
  double get energyEfficiency {
    if (todayConsumption == 0) return 0;
    return (todayProduction / todayConsumption * 100).clamp(0.0, 200.0);
  }

  /// Get self-sufficiency ratio
  double get selfSufficiency {
    if (todayConsumption == 0) return 0;
    final selfConsumed = todayProduction < todayConsumption 
        ? todayProduction 
        : todayConsumption;
    return (selfConsumed / todayConsumption * 100).clamp(0.0, 100.0);
  }

  /// Mock data for testing
  static QuickSummary get mock => QuickSummary(
    batteryPercentage: 75.0,
    currentSolarProduction: 3.2,
    gridStatus: GridStatus.exporting,
    todayProduction: 18.5,
    todayConsumption: 12.3,
    todaySavings: 8.45,
    alerts: [
      SystemAlert.mock,
    ],
  );
}

/// Grid status enumeration
enum GridStatus {
  importing,
  exporting,
  balanced,
  offline,
}

/// System alert model
class SystemAlert {
  final String id;
  final String title;
  final String message;
  final AlertSeverity severity;
  final DateTime timestamp;
  final bool isRead;
  final String? actionUrl;

  const SystemAlert({
    required this.id,
    required this.title,
    required this.message,
    required this.severity,
    required this.timestamp,
    this.isRead = false,
    this.actionUrl,
  });

  /// Create from JSON
  factory SystemAlert.fromJson(Map<String, dynamic> json) {
    return SystemAlert(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      message: json['message'] ?? '',
      severity: AlertSeverity.values.firstWhere(
        (e) => e.name == json['severity'],
        orElse: () => AlertSeverity.info,
      ),
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
      isRead: json['is_read'] ?? false,
      actionUrl: json['action_url'],
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'message': message,
      'severity': severity.name,
      'timestamp': timestamp.toIso8601String(),
      'is_read': isRead,
      'action_url': actionUrl,
    };
  }

  /// Create a copy with updated values
  SystemAlert copyWith({
    String? id,
    String? title,
    String? message,
    AlertSeverity? severity,
    DateTime? timestamp,
    bool? isRead,
    String? actionUrl,
  }) {
    return SystemAlert(
      id: id ?? this.id,
      title: title ?? this.title,
      message: message ?? this.message,
      severity: severity ?? this.severity,
      timestamp: timestamp ?? this.timestamp,
      isRead: isRead ?? this.isRead,
      actionUrl: actionUrl ?? this.actionUrl,
    );
  }

  /// Mark as read
  SystemAlert markAsRead() => copyWith(isRead: true);

  /// Get severity color
  Color get severityColor {
    switch (severity) {
      case AlertSeverity.critical:
        return const Color(0xFFEF4444); // Red
      case AlertSeverity.error:
        return const Color(0xFFEF4444); // Red
      case AlertSeverity.warning:
        return const Color(0xFFF97316); // Orange
      case AlertSeverity.info:
        return const Color(0xFF3B82F6); // Blue
    }
  }

  /// Get severity icon
  IconData get severityIcon {
    switch (severity) {
      case AlertSeverity.critical:
        return Icons.error_rounded;
      case AlertSeverity.error:
        return Icons.warning_rounded;
      case AlertSeverity.warning:
        return Icons.warning_amber_rounded;
      case AlertSeverity.info:
        return Icons.info_rounded;
    }
  }

  /// Check if alert is urgent
  bool get isUrgent => severity == AlertSeverity.critical || severity == AlertSeverity.error;

  /// Check if alert is recent (within last hour)
  bool get isRecent {
    final now = DateTime.now();
    return now.difference(timestamp).inHours < 1;
  }

  /// Mock data for testing
  static SystemAlert get mock => SystemAlert(
    id: 'alert_1',
    title: 'Baterie descărcată',
    message: 'Nivelul bateriei este sub 20%',
    severity: AlertSeverity.warning,
    timestamp: DateTime.now().subtract(const Duration(minutes: 15)),
  );
}

/// Alert severity levels
enum AlertSeverity {
  info,
  warning,
  error,
  critical,
}