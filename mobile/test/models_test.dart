import 'package:flutter/material.dart';
import 'package:flutter_interface/models/device.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('House', () {
    test('parses /api/me/house with battery and last_step', () {
      final house = House.fromJson({
        'id': 3,
        'name': 'Casa 3',
        'mode': 'Eco',
        'has_pv': true,
        'pv_capacity_kw': 5.0,
        'has_battery': true,
        'battery': {
          'capacity_kwh': 10.0,
          'soc_kwh': 6.5,
          'soc_percent': 65.0,
          'soc_min_kwh': 2.0,
          'soc_max_kwh': 10.0,
          'available_kwh': 4.5,
          'vpp_reserve_kwh': 0.0,
          'p_ch_max_kw': 3.0,
          'p_dis_max_kw': 3.0,
          'eta_ch': 0.95,
          'eta_dis': 0.95,
        },
        'devices': [
          {'id': 1, 'house_id': 3, 'name': 'Frigider', 'power_w': 150, 'critical': true, 'status_on': true},
        ],
        'device_count': 1,
        'L_crit_kw': 0.15,
        'L_noncrit_kw': 0.0,
        'wallet_balance_lei': 100.0,
        'user': 'user3',
        'last_step': {
          'id': 3,
          'pv_kw': 2.5,
          'load_kw': 1.0,
          'ch_kw': 1.2,
          'dis_kw': 0.0,
          'imp_kw': 0.0,
          'exp_kw': 0.3,
          'p2p_in_kw': 0.0,
          'p2p_out_kw': 0.0,
          'soc_kwh': 6.5,
          'soc_percent': 65.0,
          'p2p_enabled': true,
        },
        'house_id': 3,
        'current_consumption_kw': 0.15,
      });

      expect(house.id, 3);
      expect(house.hasBattery, isTrue);
      expect(house.battery!.availableKwh, 4.5);
      expect(house.devices.single.name, 'Frigider');
      expect(house.devices.single.icon, Icons.kitchen_rounded);
      expect(house.lastStep!.batteryKw, closeTo(1.2, 1e-9));
      expect(house.lastStep!.gridKw, closeTo(-0.3, 1e-9));
      expect(house.batteryPercent, 65.0);
    });

    test('tolerates a house without battery and without last_step', () {
      final house = House.fromJson({'id': 4, 'name': 'Casa 4', 'battery': null, 'last_step': null});
      expect(house.hasBattery, isFalse);
      expect(house.lastStep, isNull);
      expect(house.batteryPercent, 0.0);
      expect(house.devices, isEmpty);
    });
  });

  group('Energy', () {
    test('chart points integrate with the backend interval', () {
      final chart = EnergyChart.fromJson({
        'period': 'day',
        'date': '2026-09-11',
        'interval_minutes': 15,
        'data_points': [
          {
            'timestamp': '2026-09-11T12:00:00',
            'solar': 4.0,
            'consumption': 1.0,
            'battery': 2.0,
            'grid': -0.5,
            'p2p': -0.5,
            'solar_to_battery': 2.0,
            'battery_to_load': 0.0,
            'grid_to_load': 0.0,
            'solar_to_grid': 0.5,
            'soc_kwh': 5.0,
            'price_import': 0.9,
          },
          {'timestamp': 'not-a-date'},
        ],
      });

      expect(chart.points.length, 1, reason: 'points without a valid timestamp are dropped');
      expect(chart.hoursPerPoint, 0.25);
      final p = chart.points.single;
      expect(p.p2pSell, 0.5);
      expect(p.solarToLoad, closeTo(1.0, 1e-9));
    });

    test('impact handles empty monthly savings and zero totals', () {
      final impact = EnergyImpact.fromJson({'date': '2026-09-11', 'peak': {}, 'off_peak': {}});
      expect(impact.hasData, isFalse);
      expect(impact.monthlySavings, isEmpty);
      expect(impact.peak.max, 0.0);
    });
  });

  group('SimPrices', () {
    test('current and previous step, change and stats', () {
      final prices = SimPrices.fromJson({
        'date': '2026-09-11',
        'dt_hours': 0.25,
        'current_step': 1,
        'prices': [
          {'sim_timestamp': '2026-09-11T00:00:00', 'price_import': 0.5, 'price_export': 0.2, 'price_p2p': 0.35},
          {'sim_timestamp': '2026-09-11T00:15:00', 'price_import': 0.7, 'price_export': 0.2, 'price_p2p': 0.49},
        ],
      });

      expect(prices.currentValue(PriceSeries.import), 0.7);
      expect(prices.change(PriceSeries.import), closeTo(0.2, 1e-9));
      expect(prices.isRising(PriceSeries.import), isTrue);
      expect(prices.max(PriceSeries.p2p), 0.49);
      expect(prices.avg(PriceSeries.export), closeTo(0.2, 1e-9));
    });

    test('empty curve does not crash', () {
      final prices = SimPrices.fromJson({'prices': []});
      expect(prices.isEmpty, isTrue);
      expect(prices.current, isNull);
      expect(prices.currentValue(PriceSeries.import), 0.0);
    });
  });

  test('Trade perspective fields and rejected status', () {
    final trade = Trade.fromJson({
      'id': 9,
      'seller_house_id': 1,
      'buyer_house_id': 2,
      'energy_kwh': 0.5,
      'price_lei_kwh': 0.6,
      'total_value_lei': 0.3,
      'grid_price_lei_kwh': 0.9,
      'status': 'rejected',
      'reason': 'sold insuficient',
      'sim_timestamp': '2026-09-11T10:00:00',
      'transaction_type': 'buy',
      'counterparty_house_id': 1,
    });
    expect(trade.isSell, isFalse);
    expect(trade.isRejected, isTrue);
    expect(trade.simTimestamp, DateTime(2026, 9, 11, 10));
  });

  group('Device', () {
    test('parses a seeded device with a schedule and current draw', () {
      final device = Device.fromJson({
        'id': 11,
        'house_id': 1,
        'name': 'boiler electric',
        'power_w': 2000.0,
        'critical': false,
        'status_on': true,
        'schedule': {'mode': 'durata', 'text': '7×75 min/săpt. 6-22'},
        'current_power_kw': 0.05,
        'accumulated_energy_kwh': 1.7724,
        'last_state_change_ts': '2026-09-26T21:45:00',
      });
      expect(device.schedule!.mode, 'durata');
      expect(device.scheduleText, '7×75 min/săpt. 6-22');
      expect(device.currentPowerKw, 0.05);
      expect(device.currentDrawText, 'acum 0,05 kW');
      expect(device.lastStateChange, DateTime(2026, 9, 26, 21, 45));
    });

    test('schedule without text falls back to the mode', () {
      expect(DeviceSchedule.fromJson({'mode': 'permanent'}).text, 'permanent');
    });

    test('manual device has no schedule and zero draw when missing', () {
      final device = Device.fromJson({
        'id': 12,
        'house_id': 1,
        'name': 'Televizor dormitor',
        'power_w': 150,
        'critical': false,
        'status_on': false,
        'schedule': null,
      });
      expect(device.schedule, isNull);
      expect(device.scheduleText, 'manual');
      expect(device.currentPowerKw, 0.0);
      expect(device.currentDrawText, 'acum 0,00 kW');
      expect(device.lastStateChange, isNull);
    });
  });

  test('device icon heuristic falls back to a generic icon', () {
    expect(iconForDeviceName('Ceva necunoscut'), Icons.devices_other_rounded);
    expect(iconForDeviceName('Încărcător EV'), Icons.electric_car_rounded);
  });
}
