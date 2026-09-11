import 'package:flutter/material.dart';

/// Smart tip model for contextual recommendations
class SmartTip {
  final String id;
  final String title;
  final String description;
  final TipType type;
  final TipPriority priority;
  final IconData icon;
  final Color color;
  final String? actionText;
  final VoidCallback? onAction;
  final DateTime timestamp;
  final bool isRead;

  const SmartTip({
    required this.id,
    required this.title,
    required this.description,
    required this.type,
    required this.priority,
    required this.icon,
    required this.color,
    this.actionText,
    this.onAction,
    required this.timestamp,
    this.isRead = false,
  });

  /// Create from JSON
  factory SmartTip.fromJson(Map<String, dynamic> json) {
    return SmartTip(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      type: TipType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => TipType.efficiency,
      ),
      priority: TipPriority.values.firstWhere(
        (e) => e.name == json['priority'],
        orElse: () => TipPriority.medium,
      ),
      icon: _getIconFromString(json['icon']),
      color: Color(json['color'] ?? 0xFF3B82F6),
      actionText: json['action_text'],
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
      isRead: json['is_read'] ?? false,
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'type': type.name,
      'priority': priority.name,
      'icon': icon.codePoint,
      'color': color.value,
      'action_text': actionText,
      'timestamp': timestamp.toIso8601String(),
      'is_read': isRead,
    };
  }

  /// Create a copy with updated values
  SmartTip copyWith({
    String? id,
    String? title,
    String? description,
    TipType? type,
    TipPriority? priority,
    IconData? icon,
    Color? color,
    String? actionText,
    VoidCallback? onAction,
    DateTime? timestamp,
    bool? isRead,
  }) {
    return SmartTip(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      type: type ?? this.type,
      priority: priority ?? this.priority,
      icon: icon ?? this.icon,
      color: color ?? this.color,
      actionText: actionText ?? this.actionText,
      onAction: onAction ?? this.onAction,
      timestamp: timestamp ?? this.timestamp,
      isRead: isRead ?? this.isRead,
    );
  }

  /// Mark as read
  SmartTip markAsRead() => copyWith(isRead: true);

  /// Get priority label
  String get priorityLabel {
    switch (priority) {
      case TipPriority.critical:
        return 'URGENT';
      case TipPriority.high:
        return 'IMPORTANT';
      case TipPriority.medium:
        return 'MEDIU';
      case TipPriority.low:
        return 'SCĂZUT';
    }
  }

  /// Get type label
  String get typeLabel {
    switch (type) {
      case TipType.weather:
        return 'VREMEA';
      case TipType.battery:
        return 'BATERIE';
      case TipType.grid:
        return 'REȚEA';
      case TipType.efficiency:
        return 'EFICIENȚĂ';
      case TipType.maintenance:
        return 'MENTENANȚĂ';
    }
  }

  /// Check if tip is urgent
  bool get isUrgent => priority == TipPriority.critical || priority == TipPriority.high;

  /// Check if tip is recent (within last hour)
  bool get isRecent {
    final now = DateTime.now();
    return now.difference(timestamp).inHours < 1;
  }

  static IconData _getIconFromString(dynamic iconData) {
    if (iconData is int) {
      return IconData(iconData, fontFamily: 'MaterialIcons');
    }
    return Icons.lightbulb_outline_rounded;
  }
}

/// Types of tips
enum TipType {
  weather,
  battery,
  grid,
  efficiency,
  maintenance,
}

/// Priority levels for tips
enum TipPriority {
  low,
  medium,
  high,
  critical,
}

/// Battery state for tip generation
class BatteryState {
  final double percentage;
  final bool isCharging;
  final double power;
  final DateTime timestamp;

  const BatteryState({
    required this.percentage,
    required this.isCharging,
    required this.power,
    required this.timestamp,
  });

  /// Battery status
  BatteryStatus get status {
    if (percentage < 20) return BatteryStatus.low;
    if (percentage > 80) return BatteryStatus.high;
    return BatteryStatus.normal;
  }

  /// Is battery discharging
  bool get isDischarging => !isCharging && power < 0;

  /// Is battery idle
  bool get isIdle => power.abs() < 0.1;
}

/// Battery status enumeration
enum BatteryStatus {
  low,
  normal,
  high,
}

/// Grid state for tip generation
class GridState {
  final double power;
  final double price;
  final bool isHighDemand;
  final DateTime timestamp;

  const GridState({
    required this.power,
    required this.price,
    required this.isHighDemand,
    required this.timestamp,
  });

  /// Is importing from grid
  bool get isImporting => power > 0;

  /// Is exporting to grid
  bool get isExporting => power < 0;

  /// Is balanced (minimal grid interaction)
  bool get isBalanced => power.abs() < 0.1;
}