import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const String simDate = '2026-07-15';
const int houseId = 3;

String _ts(int step) => DateTime.parse('${simDate}T00:00:00').add(Duration(minutes: 15 * step)).toIso8601String();

double _pv(int step) {
  final h = step / 4;
  if (h < 6 || h > 20) return 0;
  final x = (h - 13) / 7;
  return 8.4 * (1 - x * x);
}

Map<String, dynamic> _battery() => {
      'capacity_kwh': 32.0,
      'soc_kwh': 21.7,
      'soc_percent': 67.8,
      'soc_min_kwh': 3.2,
      'available_kwh': 18.5,
      'vpp_reserve_kwh': 4.0,
      'p_ch_max_kw': 10.0,
      'p_dis_max_kw': 10.0,
      'eta_ch': 0.95,
      'eta_dis': 0.95,
    };

final List<Map<String, dynamic>> devices = [
  {
    'id': 1,
    'name': 'Frigider cu congelator',
    'power_w': 150,
    'critical': true,
    'status_on': true,
    'schedule': {'mode': 'permanent', 'text': 'permanent'},
    'current_power_kw': 0.15,
    'accumulated_energy_kwh': 12.34,
    'last_state_change_ts': '${simDate}T08:00:00',
  },
  {
    'id': 2,
    'name': 'Pompă de căldură aer-apă (încălzire și ACM)',
    'power_w': 3500,
    'critical': false,
    'status_on': true,
    'schedule': {'mode': 'termic', 'text': 'termic'},
    'current_power_kw': 3.5,
    'accumulated_energy_kwh': 1234.5,
    'last_state_change_ts': '${simDate}T09:15:00',
  },
  {
    'id': 3,
    'name': 'Mașină de spălat vase',
    'power_w': 1800,
    'critical': false,
    'status_on': false,
    'schedule': {'mode': 'durata', 'text': '5×120 min/săpt. 19-23'},
    'current_power_kw': 0,
    'accumulated_energy_kwh': 87.6,
    'last_state_change_ts': '${simDate}T07:30:00',
  },
  {
    'id': 4,
    'name': 'Încărcător mașină electrică',
    'power_w': 11000,
    'critical': false,
    'status_on': true,
    'schedule': {'mode': 'durata', 'text': '3×200 min/săpt. 18-7'},
    'current_power_kw': 11.0,
    'accumulated_energy_kwh': 2310.75,
    'last_state_change_ts': '${simDate}T13:30:00',
  },
];

Map<String, dynamic> house() => {
      'id': houseId,
      'house_id': houseId,
      'name': 'Casa 3 – Str. Mărășești nr. 112, Bacău',
      'mode': 'Eco',
      'has_pv': true,
      'pv_capacity_kw': 10.0,
      'battery': _battery(),
      'devices': devices,
      'L_crit_kw': 0.4,
      'L_noncrit_kw': 2.1,
      'wallet_balance_lei': 1234.56,
      'user': 'user3',
      'current_consumption_kw': 14.65,
      'last_step': {
        'pv_kw': 8.12,
        'load_kw': 14.65,
        'device_kw': 14.65,
        'shed_kw': 0,
        'curtail_kw': 0,
        'ch_kw': 0,
        'dis_kw': 6.53,
        'imp_kw': 0,
        'exp_kw': 0,
        'p2p_in_kw': 0,
        'p2p_out_kw': 0,
        'soc_kwh': 21.7,
        'soc_percent': 67.8,
        'p2p_enabled': true,
        'temp_in_c': 21.4,
      },
    };

Map<String, dynamic> currentUser() => {
      'user_id': 3,
      'username': 'user3',
      'house_id': houseId,
      'house_name': 'Casa 3 – Str. Mărășești nr. 112, Bacău',
      'is_admin': false,
      'created_at': '2026-10-02T12:00:00',
    };

Map<String, dynamic> simConfig() => {
      'controller': 'mpc',
      'tick_seconds': 2.0,
      'import_max_kw': 50.0,
      'export_max_kw': 40.0,
      'internal_line_kw': 30.0,
      'p2p_price_factor': 0.6,
      'min_p2p_balance_lei': 8.0,
      'seed': 42,
      'dt_hours': 0.25,
      'data_source': 'sintetic',
      'data_year': 2025,
      'controllers': ['reguli', 'mpc'],
    };

Map<String, dynamic> simPrices() => {
      'date': simDate,
      'dt_hours': 0.25,
      'current_step': 54,
      'prices': [
        for (var i = 0; i < 96; i++)
          {
            'sim_timestamp': _ts(i),
            'price_import': 0.9 + 0.6 * (i % 24) / 24 + (i > 68 && i < 84 ? 0.8 : 0),
            'price_export': 0.35 + 0.2 * (i % 24) / 24,
            'price_p2p': 0.62 + 0.4 * (i % 24) / 24,
          },
      ],
    };

Map<String, dynamic> settings() => {'mode': 'Eco', 'backup_reserve_percent': 20, 'battery': _battery()};

Map<String, dynamic> energyChart(String period) {
  final count = period == 'day' ? 96 : (period == 'week' ? 56 : 31);
  return {
    'period': period,
    'date': simDate,
    'interval_minutes': period == 'day' ? 15 : (period == 'week' ? 180 : 1440),
    'data_points': [
      for (var i = 0; i < count; i++)
        {
          'timestamp': _ts(i),
          'solar': _pv(i % 96),
          'consumption': 1.2 + (i % 7) * 0.4,
          'shed': 0,
          'battery': i.isEven ? 1.5 : -1.2,
          'grid': i % 3 == 0 ? 0.8 : -0.5,
          'p2p': i % 4 == 0 ? 0.3 : -0.2,
          'solar_to_battery': 1.5,
          'battery_to_load': 1.2,
          'grid_to_load': 0.8,
          'solar_to_grid': 0.5,
          'soc_kwh': 18.0,
          'price_import': 1.21,
        },
    ],
  };
}

const List<String> _months = ['Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul'];

Map<String, dynamic> impact() => {
      'date': simDate,
      'solar_percent': 46.3,
      'battery_percent': 28.1,
      'p2p_percent': 7.4,
      'grid_percent': 18.2,
      'solar_kwh': 1234.5,
      'battery_kwh': 750.25,
      'p2p_kwh': 197.6,
      'grid_kwh': 485.9,
      'peak': {'solar': 38.0, 'battery': 41.0, 'grid': 21.0},
      'off_peak': {'solar': 12.0, 'battery': 30.0, 'grid': 58.0},
      'monthly_savings': [
        for (var m = 0; m < _months.length; m++)
          {
            'month': _months[m],
            'year': 2026,
            'savings': 3703.68 / (m + 1),
            'has_data': true,
            'current': m == _months.length - 1,
          },
      ],
    };

Map<String, dynamic> statsSummary(String period) => {
      'total_kwh': 1234.567,
      'average_daily_kwh': 39.82,
      'previous_period_kwh': 1102.3,
      'change_percent': 12.0,
      'period': period,
      'estimated_cost': 2345.67,
      'currency': 'RON',
      'has_data': true,
    };

Map<String, dynamic> topConsumers(String period) => {
      'period': period,
      'total_house_kwh': 1234.567,
      'devices': [
        for (final d in devices)
          {
            'device_id': d['id'],
            'device_name': d['name'],
            'total_kwh': 345.67,
            'percentage_of_total': 28.0,
            'estimated_cost': 456.78,
          },
      ],
    };

Map<String, dynamic> comparison() => {
      'current_month': 'July 2026',
      'current_month_kwh': 1234.56,
      'previous_month': 'June 2026',
      'previous_month_kwh': 1102.3,
      'change_percent': 12.0,
      'trend': 'increasing',
      'projected_total_kwh': 2551.43,
      'is_projection': true,
      'days_remaining': 16,
    };

Map<String, dynamic> statsChart(String start, String end) {
  final from = DateTime.parse(start);
  final days = DateTime.parse(end).difference(from).inDays + 1;
  final Duration step;
  final int count;
  if (days <= 2) {
    step = const Duration(hours: 1);
    count = 24 * days;
  } else if (days <= 62) {
    step = const Duration(days: 1);
    count = days;
  } else {
    step = const Duration(days: 7);
    count = days ~/ 7;
  }
  return {
    'granularity': days <= 2 ? 'hourly' : (days <= 62 ? 'daily' : 'weekly'),
    'start_date': start,
    'end_date': end,
    'data_points': [
      for (var i = 0; i < count; i++)
        {'timestamp': from.add(step * i).toIso8601String(), 'value_kwh': 30.0 + (i % 5) * 4.5},
    ],
  };
}

Map<String, dynamic> tradingPrefs() => {
      'house_id': houseId,
      'selling_enabled': true,
      'buying_enabled': true,
      'price_mode': 'discount',
      'fixed_price_lei_kwh': 0.8,
      'discount_percent': 20,
      'min_sell_price_lei_kwh': 0.45,
    };

Map<String, dynamic> trade(int i) => {
      'id': i,
      'seller_house_id': i.isEven ? houseId : 7,
      'buyer_house_id': i.isEven ? 10 : houseId,
      'energy_kwh': 12.345,
      'price_lei_kwh': 0.8123,
      'total_value_lei': 1234.56,
      'grid_price_lei_kwh': 1.4567,
      'status': i % 5 == 0 ? 'rejected' : 'settled',
      'reason': i % 5 == 0 ? 'Bateria cumpărătorului este plină' : null,
      'sim_timestamp': _ts(40 + i),
      'transaction_type': i.isEven ? 'sell' : 'buy',
      'counterparty_house_id': i.isEven ? 10 : 7,
    };

Map<String, dynamic> tradingStats() => {
      'total_energy_sold_kwh': 1234.5,
      'total_energy_bought_kwh': 987.6,
      'total_earned_lei': 12345.67,
      'total_spent_lei': 9876.54,
      'net_earnings_lei': 2469.13,
      'sell_count': 123,
      'buy_count': 98,
    };

Map<String, dynamic> wallet() => {
      'house_id': houseId,
      'balance_lei': 12345.67,
      'total_earned_lei': 23456.78,
      'total_spent_lei': 11111.11,
      'transaction_count': 221,
      'vpp_reserve': {'reserved_kwh': 4.0, 'base_rate_lei_kwh': 0.65},
    };

Map<String, dynamic> walletTx(int i) => {
      'id': i,
      'wallet_id': 1,
      'transaction_type': ['credit', 'debit', 'vpp_payment', 'initial'][i % 4],
      'amount_lei': 1234.56,
      'description': 'Vânzare P2P către casa 10 (12,35 kWh la 0,81 lei/kWh)',
      'reference_id': i,
      'balance_after': 12345.67,
      'sim_timestamp': _ts(30 + i),
      'created_at': '2026-10-02T12:00:00',
    };

Map<String, dynamic> solarForecast(DateTime now) {
  String day(int offset) {
    final d = DateTime(now.year, now.month, now.day).add(Duration(days: offset));
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }

  final watts = <String, int>{};
  final daily = <String, int>{};
  for (var offset = 0; offset < 2; offset++) {
    var total = 0;
    for (var h = 6; h <= 20; h++) {
      final x = (h - 13) / 7;
      final w = (8400 * (1 - x * x)).round();
      watts['${day(offset)} ${h.toString().padLeft(2, '0')}:00:00'] = w;
      total += w;
    }
    daily[day(offset)] = total;
  }
  return {
    'result': {'watts': watts, 'watt_hours_day': daily},
    'message': {'code': 0, 'type': 'success'},
  };
}

Object? _route(http.Request request) {
  final path = request.url.path;
  final q = request.url.queryParameters;
  if (request.url.host == 'api.forecast.solar') return solarForecast(DateTime.now());
  if (path.endsWith('/me/house')) return house();
  if (path.endsWith('/auth/me')) return currentUser();
  if (path.endsWith('/config')) return simConfig();
  if (path.endsWith('/sim/prices')) return simPrices();
  if (path.endsWith('/me/settings')) return settings();
  if (path.endsWith('/me/devices')) {
    return request.method == 'POST' ? {'id': 99, ...json.decode(request.body) as Map<String, dynamic>} : devices;
  }
  if (path.contains('/me/devices/') && request.method == 'PUT') {
    final id = int.parse(request.url.pathSegments.last);
    return {...devices.firstWhere((d) => d['id'] == id), ...json.decode(request.body) as Map<String, dynamic>};
  }
  if (path.endsWith('/me/energy/chart')) return energyChart(q['period'] ?? 'day');
  if (path.endsWith('/me/energy/impact')) return impact();
  if (path.endsWith('/stats/summary')) return statsSummary(q['period'] ?? 'month');
  if (path.endsWith('/stats/top-consumers')) return topConsumers(q['period'] ?? 'month');
  if (path.endsWith('/stats/comparison')) return comparison();
  if (path.endsWith('/stats/chart')) return statsChart(q['start_date']!, q['end_date']!);
  if (path.contains('/trading/preferences/')) {
    return request.method == 'PUT'
        ? {...tradingPrefs(), ...json.decode(request.body) as Map<String, dynamic>}
        : tradingPrefs();
  }
  if (path.contains('/trading/history/')) return {'transactions': List.generate(12, (i) => trade(i + 1))};
  if (path.contains('/trading/stats/')) return tradingStats();
  if (path.endsWith('/transactions')) return {'transactions': List.generate(12, (i) => walletTx(i + 1))};
  if (path.contains('/wallet/')) return wallet();
  return null;
}

/// Every request is recorded so tests can check which URLs the screens asked for.
final List<Uri> requestLog = [];

/// POST and PUT requests, for tests that check what a form sent.
final List<http.Request> writeLog = [];

http.Client fixtureClient() => MockClient((request) async {
      requestLog.add(request.url);
      if (request.method != 'GET') writeLog.add(request);
      final body = _route(request);
      if (body == null) return http.Response('{"detail": "Not found"}', 404);
      return http.Response.bytes(
        utf8.encode(json.encode(body)),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
