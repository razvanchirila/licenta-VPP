import 'package:flutter_interface/models/device.dart';
import 'package:flutter_interface/models/json_utils.dart';

class Battery {
  final double capacityKwh;
  final double socKwh;
  final double socPercent;
  final double socMinKwh;
  final double availableKwh;
  final double vppReserveKwh;
  final double pChMaxKw;
  final double pDisMaxKw;
  final double etaCh;
  final double etaDis;

  const Battery({
    required this.capacityKwh,
    required this.socKwh,
    required this.socPercent,
    required this.socMinKwh,
    required this.availableKwh,
    required this.vppReserveKwh,
    required this.pChMaxKw,
    required this.pDisMaxKw,
    required this.etaCh,
    required this.etaDis,
  });

  factory Battery.fromJson(Map<String, dynamic> j) => Battery(
        capacityKwh: asDouble(j['capacity_kwh']),
        socKwh: asDouble(j['soc_kwh']),
        socPercent: asDouble(j['soc_percent']),
        socMinKwh: asDouble(j['soc_min_kwh']),
        availableKwh: asDouble(j['available_kwh']),
        vppReserveKwh: asDouble(j['vpp_reserve_kwh']),
        pChMaxKw: asDouble(j['p_ch_max_kw']),
        pDisMaxKw: asDouble(j['p_dis_max_kw']),
        etaCh: asDouble(j['eta_ch'], 1.0),
        etaDis: asDouble(j['eta_dis'], 1.0),
      );
}

/// Result of the last simulation step for a house (`HouseStep`), in kW.
class HouseStep {
  final double pvKw;
  final double loadKw;
  final double deviceKw;
  final double shedKw;
  final double curtailKw;
  final double chKw;
  final double disKw;
  final double impKw;
  final double expKw;
  final double p2pInKw;
  final double p2pOutKw;
  final double socKwh;
  final double? socPercent;
  final bool p2pEnabled;

  const HouseStep({
    required this.pvKw,
    required this.loadKw,
    required this.deviceKw,
    required this.shedKw,
    required this.curtailKw,
    required this.chKw,
    required this.disKw,
    required this.impKw,
    required this.expKw,
    required this.p2pInKw,
    required this.p2pOutKw,
    required this.socKwh,
    required this.socPercent,
    required this.p2pEnabled,
  });

  factory HouseStep.fromJson(Map<String, dynamic> j) => HouseStep(
        pvKw: asDouble(j['pv_kw']),
        loadKw: asDouble(j['load_kw']),
        deviceKw: asDouble(j['device_kw']),
        shedKw: asDouble(j['shed_kw']),
        curtailKw: asDouble(j['curtail_kw']),
        chKw: asDouble(j['ch_kw']),
        disKw: asDouble(j['dis_kw']),
        impKw: asDouble(j['imp_kw']),
        expKw: asDouble(j['exp_kw']),
        p2pInKw: asDouble(j['p2p_in_kw']),
        p2pOutKw: asDouble(j['p2p_out_kw']),
        socKwh: asDouble(j['soc_kwh']),
        socPercent: asDoubleOrNull(j['soc_percent']),
        p2pEnabled: asBool(j['p2p_enabled']),
      );

  /// > 0 charging, < 0 discharging.
  double get batteryKw => chKw - disKw;

  /// > 0 import, < 0 export.
  double get gridKw => impKw - expKw;

  /// > 0 buying from neighbours, < 0 selling.
  double get p2pKw => p2pInKw - p2pOutKw;
}

class House {
  final int id;
  final String name;
  final String mode;
  final bool hasPv;
  final double pvCapacityKw;
  final Battery? battery;
  final List<Device> devices;
  final double lCritKw;
  final double lNoncritKw;
  final double? walletBalanceLei;
  final String? user;
  final HouseStep? lastStep;
  final double currentConsumptionKw;

  const House({
    required this.id,
    required this.name,
    required this.mode,
    required this.hasPv,
    required this.pvCapacityKw,
    required this.battery,
    required this.devices,
    required this.lCritKw,
    required this.lNoncritKw,
    required this.walletBalanceLei,
    required this.user,
    required this.lastStep,
    required this.currentConsumptionKw,
  });

  bool get hasBattery => battery != null;

  double get batteryPercent => lastStep?.socPercent ?? battery?.socPercent ?? 0.0;

  factory House.fromJson(Map<String, dynamic> j) {
    final battery = j['battery'];
    final step = j['last_step'];
    return House(
      id: asInt(j['id'] ?? j['house_id']),
      name: asString(j['name']),
      mode: asString(j['mode'], 'Eco'),
      hasPv: asBool(j['has_pv']),
      pvCapacityKw: asDouble(j['pv_capacity_kw']),
      battery: battery is Map ? Battery.fromJson(asMap(battery)) : null,
      devices: asMapList(j['devices']).map(Device.fromJson).toList(),
      lCritKw: asDouble(j['L_crit_kw']),
      lNoncritKw: asDouble(j['L_noncrit_kw']),
      walletBalanceLei: asDoubleOrNull(j['wallet_balance_lei']),
      user: j['user']?.toString(),
      lastStep: step is Map ? HouseStep.fromJson(asMap(step)) : null,
      currentConsumptionKw: asDouble(j['current_consumption_kw']),
    );
  }
}

class HouseSettings {
  final String mode;
  final double? backupReservePercent;
  final Battery? battery;

  const HouseSettings({required this.mode, required this.backupReservePercent, required this.battery});

  factory HouseSettings.fromJson(Map<String, dynamic> j) => HouseSettings(
        mode: asString(j['mode'], 'Eco'),
        backupReservePercent: asDoubleOrNull(j['backup_reserve_percent']),
        battery: j['battery'] is Map ? Battery.fromJson(asMap(j['battery'])) : null,
      );
}
