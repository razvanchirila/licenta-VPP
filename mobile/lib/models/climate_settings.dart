import 'package:flutter/material.dart';

enum ClimateMode {
  cold,
  fan,
  dry,
  heat,
}

enum ClimateRoom {
  livingRoom,
  bedroom,
  kitchen,
  bathroom,
  office,
}

extension ClimateRoomExtension on ClimateRoom {
  String get displayName {
    switch (this) {
      case ClimateRoom.livingRoom:
        return 'Sufragerie';
      case ClimateRoom.bedroom:
        return 'Dormitor';
      case ClimateRoom.kitchen:
        return 'Bucătărie';
      case ClimateRoom.bathroom:
        return 'Baie';
      case ClimateRoom.office:
        return 'Birou';
    }
  }

  IconData get icon {
    switch (this) {
      case ClimateRoom.livingRoom:
        return Icons.weekend_rounded;
      case ClimateRoom.bedroom:
        return Icons.bed_rounded;
      case ClimateRoom.kitchen:
        return Icons.kitchen_rounded;
      case ClimateRoom.bathroom:
        return Icons.bathtub_rounded;
      case ClimateRoom.office:
        return Icons.computer_rounded;
    }
  }
}

class ClimateSchedule {
  final TimeOfDay onTime;
  final TimeOfDay offTime;
  final bool isEnabled;

  const ClimateSchedule({
    this.onTime = const TimeOfDay(hour: 7, minute: 0),
    this.offTime = const TimeOfDay(hour: 22, minute: 0),
    this.isEnabled = false,
  });

  ClimateSchedule copyWith({
    TimeOfDay? onTime,
    TimeOfDay? offTime,
    bool? isEnabled,
  }) {
    return ClimateSchedule(
      onTime: onTime ?? this.onTime,
      offTime: offTime ?? this.offTime,
      isEnabled: isEnabled ?? this.isEnabled,
    );
  }

  String formatTime(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }
}

/// Mock/local state, not sent to the backend.
class ClimateSettings {
  final double targetTemperature;
  final ClimateMode mode;
  final bool isOn;
  final ClimateRoom room;
  final ClimateSchedule schedule;

  const ClimateSettings({
    this.targetTemperature = 22.0,
    this.mode = ClimateMode.cold,
    this.isOn = false,
    this.room = ClimateRoom.livingRoom,
    this.schedule = const ClimateSchedule(),
  });

  ClimateSettings copyWith({
    double? targetTemperature,
    ClimateMode? mode,
    bool? isOn,
    ClimateRoom? room,
    ClimateSchedule? schedule,
  }) {
    return ClimateSettings(
      targetTemperature: targetTemperature ?? this.targetTemperature,
      mode: mode ?? this.mode,
      isOn: isOn ?? this.isOn,
      room: room ?? this.room,
      schedule: schedule ?? this.schedule,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is ClimateSettings &&
        other.targetTemperature == targetTemperature &&
        other.mode == mode &&
        other.isOn == isOn &&
        other.room == room;
  }

  @override
  int get hashCode => Object.hash(targetTemperature, mode, isOn, room);
}
