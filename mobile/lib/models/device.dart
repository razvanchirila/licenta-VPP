import 'package:flutter/material.dart';
import 'package:flutter_interface/models/json_utils.dart';

class DeviceSchedule {
  final String mode;
  final String text;

  const DeviceSchedule({required this.mode, required this.text});

  factory DeviceSchedule.fromJson(Map<String, dynamic> j) => DeviceSchedule(
        mode: asString(j['mode'], 'permanent'),
        text: asString(j['text'], asString(j['mode'], 'permanent')),
      );
}

class Device {
  final int id;
  final String name;
  final double powerW;
  final bool critical;
  final bool statusOn;
  final DeviceSchedule? schedule;
  final double currentPowerKw;
  final double accumulatedEnergyKwh;
  final DateTime? lastStateChange;

  const Device({
    required this.id,
    required this.name,
    required this.powerW,
    required this.critical,
    required this.statusOn,
    required this.schedule,
    required this.currentPowerKw,
    required this.accumulatedEnergyKwh,
    required this.lastStateChange,
  });

  factory Device.fromJson(Map<String, dynamic> j) => Device(
        id: asInt(j['id']),
        name: asString(j['name']),
        powerW: asDouble(j['power_w']),
        critical: asBool(j['critical']),
        statusOn: asBool(j['status_on']),
        schedule: j['schedule'] is Map ? DeviceSchedule.fromJson(asMap(j['schedule'])) : null,
        currentPowerKw: asDouble(j['current_power_kw']),
        accumulatedEnergyKwh: asDouble(j['accumulated_energy_kwh']),
        lastStateChange: asDateTime(j['last_state_change_ts']),
      );

  /// Seeded devices follow a schedule; ones added from the app run manually.
  String get scheduleText => schedule?.text ?? 'manual';

  /// Draw at the last simulated step, e.g. `acum 0,05 kW`.
  String get currentDrawText => 'acum ${currentPowerKw.toStringAsFixed(2).replaceAll('.', ',')} kW';

  /// The backend has no icon field; pick one from the name.
  IconData get icon => iconForDeviceName(name);
}

IconData iconForDeviceName(String name) {
  final n = name.toLowerCase();
  bool word(String w) => RegExp('\\b$w\\b').hasMatch(n);
  if (n.contains('frigider') || n.contains('congelator')) return Icons.kitchen_rounded;
  if (n.contains('aer') || n.contains('clima') || word('ac')) return Icons.ac_unit_rounded;
  if (n.contains('spalat') || n.contains('spălat') || n.contains('rufe')) return Icons.local_laundry_service_rounded;
  if (n.contains('vase')) return Icons.countertops_rounded;
  if (word('tv') || n.contains('televizor')) return Icons.tv_rounded;
  if (n.contains('lumin') || word('bec') || n.contains('ilumin')) return Icons.lightbulb_rounded;
  if (word('ev') || n.contains('masina') || n.contains('mașină') || n.contains('auto')) {
    return Icons.electric_car_rounded;
  }
  if (n.contains('boiler') || n.contains('apa') || n.contains('apă')) return Icons.water_drop_rounded;
  if (n.contains('router') || n.contains('wifi')) return Icons.router_rounded;
  if (n.contains('pc') || n.contains('calculator') || n.contains('laptop')) return Icons.computer_rounded;
  if (n.contains('cuptor') || n.contains('plita') || n.contains('plită')) return Icons.microwave_rounded;
  if (n.contains('pomp') || n.contains('caldur') || n.contains('căldur')) return Icons.heat_pump_rounded;
  return Icons.devices_other_rounded;
}
