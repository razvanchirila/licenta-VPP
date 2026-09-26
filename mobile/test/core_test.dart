import 'package:flutter/material.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/energy_flow.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('formatters', () {
    test('power switches to kW at 1000 W', () {
      expect(formatPowerW(150), '150 W');
      expect(formatPowerW(999.6), '1000 W');
      expect(formatPowerW(1000), '1.0 kW');
      expect(formatPowerW(2350), '2.4 kW');
    });

    test('energy switches to Wh below 1 kWh', () {
      expect(formatEnergyKwh(0.35), '350 Wh');
      expect(formatEnergyKwh(1), '1.0 kWh');
      expect(formatEnergyKwh(12.34), '12.3 kWh');
      expect(formatKwh(12.345, decimals: 2), '12.35 kWh');
    });

    test('lei with optional sign', () {
      expect(formatLei(12.5), '12.50 lei');
      expect(formatLei(12.5, signed: true), '+12.50 lei');
      expect(formatLei(-3, signed: true), '-3.00 lei');
    });

    test('dates and clocks are zero padded', () {
      final t = DateTime(2026, 9, 7, 8, 5);
      expect(formatClock(t), '08:05');
      expect(formatDayMonth(t), '07/09');
      expect(formatSimTime(t), '07/09 08:05');
      expect(formatSimTime(null), '-');
      expect(formatApiDate(t), '2026-09-07');
    });
  });

  group('battery colour', () {
    test('green above 60, amber above 30, red below', () {
      expect(batteryLevelColor(100), AppColors.green);
      expect(batteryLevelColor(60), AppColors.green);
      expect(batteryLevelColor(59.9), AppColors.amber);
      expect(batteryLevelColor(30), AppColors.amber);
      expect(batteryLevelColor(29), AppColors.red);
      expect(batteryLevelColor(0), AppColors.red);
    });

    test('AppTheme.getBatteryColor delegates to the same thresholds', () {
      expect(AppTheme.getBatteryColor(45), batteryLevelColor(45));
    });
  });

  group('battery status', () {
    House house({bool battery = true, Map<String, dynamic>? step}) => House.fromJson({
          'id': 1,
          'name': 'Casa 1',
          'mode': 'Eco',
          'has_pv': true,
          'pv_capacity_kw': 5,
          'has_battery': battery,
          if (battery)
            'battery': {
              'capacity_kwh': 10,
              'soc_kwh': 5,
              'soc_percent': 50,
              'soc_min_kwh': 1,
              'soc_max_kwh': 10,
              'available_kwh': 4,
              'vpp_reserve_kwh': 0,
              'p_ch_max_kw': 3,
              'p_dis_max_kw': 3,
              'eta_ch': 0.95,
              'eta_dis': 0.95,
            },
          'devices': [],
          'device_count': 0,
          'L_crit_kw': 0,
          'L_noncrit_kw': 0,
          'user': 'u',
          if (step != null) 'last_step': step,
        });

    Map<String, dynamic> step({double ch = 0, double dis = 0}) => {
          'pv_kw': 1,
          'load_kw': 1,
          'device_kw': 0,
          'shed_kw': 0,
          'curtail_kw': 0,
          'ch_kw': ch,
          'dis_kw': dis,
          'imp_kw': 0,
          'exp_kw': 0,
          'p2p_in_kw': 0,
          'p2p_out_kw': 0,
          'soc_kwh': 5,
          'p2p_enabled': true,
        };

    test('describes charging, discharging, idle, no battery and no step', () {
      expect(batteryStatusLabel(house(battery: false)), 'Fără baterie');
      expect(batteryStatusLabel(house()), 'Simularea nu a rulat încă');
      expect(batteryStatusLabel(house(step: step(ch: 1.5))), 'Bateria se încarcă');
      expect(batteryStatusLabel(house(step: step(dis: 0.5))), 'Bateria se descarcă');
      expect(batteryStatusLabel(house(step: step(ch: 0.01))), 'Baterie inactivă');
    });

    test('discharging threshold uses the idle epsilon', () {
      expect(isBatteryDischarging(-0.5), isTrue);
      expect(isBatteryDischarging(-0.01), isFalse);
      expect(isBatteryDischarging(0.5), isFalse);
    });
  });

  group('AsyncValue', () {
    test('when() picks loading, error or data', () {
      String render(AsyncValue<int> v) => v.when(loading: () => 'L', error: (m) => 'E:$m', data: (d) => 'D:$d');

      expect(render(const AsyncValue.loading()), 'L');
      expect(render(const AsyncValue.error('boom')), 'E:boom');
      expect(render(const AsyncValue.data(3)), 'D:3');
    });

    test('keeps previous data while reloading, error wins over stale data', () {
      const reloading = AsyncValue<int>.loading(previous: 7);
      expect(reloading.isLoading, isTrue);
      expect(reloading.data, 7);

      const failed = AsyncValue<int>.error('x', previous: 7);
      expect(failed.hasError, isTrue);
      expect(failed.data, 7);
      expect(failed.when(loading: () => 'L', error: (m) => 'E', data: (d) => 'D'), 'E');
    });
  });

  test('AppColors.textSecondary equals white at 60%', () {
    expect(AppColors.textSecondary, Colors.white.withValues(alpha: 0.6));
  });
}
