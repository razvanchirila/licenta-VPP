import 'package:flutter/material.dart';
import 'package:flutter_interface/models/house.dart';

/// Power thresholds (kW) below which a flow is treated as idle. Shared by
class FlowThresholds {
  FlowThresholds._();

  /// Battery flow that still counts as "inactive" in the status text.
  static const double idleKw = 0.02;

  /// Grid import/export needed to show the grid arrow and highlight its label.
  static const double gridKw = 0.05;

  /// Solar / consumption / battery flow needed to draw an animated arrow.
  static const double arrowKw = 0.1;

  /// Grid flow needed to brighten the static grid line.
  static const double gridLineKw = 0.01;
}

/// Green above 60%, amber above 30%, red below (state of charge).
Color batteryLevelColor(num percent) {
  if (percent >= 60) return const Color(0xFF22C55E);
  if (percent >= 30) return const Color(0xFFFBBF24);
  return const Color(0xFFEF4444);
}

/// Positive `batteryKw` = charging.
String batteryStatusLabel(House house) {
  final step = house.lastStep;
  if (!house.hasBattery) return 'Fără baterie';
  if (step == null) return 'Simularea nu a rulat încă';
  if (step.batteryKw > FlowThresholds.idleKw) return 'Bateria se încarcă';
  if (step.batteryKw < -FlowThresholds.idleKw) return 'Bateria se descarcă';
  return 'Baterie inactivă';
}

bool isBatteryDischarging(double batteryKw) => batteryKw < -FlowThresholds.idleKw;
