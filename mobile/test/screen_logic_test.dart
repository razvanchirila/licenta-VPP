import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_interface/widgets/impact/monthly_savings_card.dart';
import 'package:flutter_interface/widgets/solar_forecast/forecast_labels.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';
import 'package:flutter_interface/widgets/trading/trading_data.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('savingsChangePercent', () {
    MonthlySaving month(String name, double savings, {bool current = false, bool hasData = true}) =>
        MonthlySaving.fromJson({'month': name, 'savings': savings, 'current': current, 'has_data': hasData});

    test('compares the current month with the last month that has data', () {
      final months = [
        month('Iun', 100),
        month('Iul', 80),
        month('Aug', 0, hasData: false),
        month('Sep', 120, current: true)
      ];
      expect(savingsChangePercent(months), closeTo(50, 1e-9));
    });

    test('is null without a current month, a previous month or a usable base', () {
      expect(savingsChangePercent([month('Sep', 120, current: true)]), isNull);
      expect(savingsChangePercent([month('Aug', 50)]), isNull);
      expect(savingsChangePercent([month('Aug', 0.001), month('Sep', 5, current: true)]), isNull);
    });
  });

  group('StatisticsRules', () {
    final now = DateTime(2026, 9, 11, 10);

    test('chart range per period', () {
      expect(StatisticsRules.chartRange('day', now).$1, DateTime(2026, 9, 10, 10));
      expect(StatisticsRules.chartRange('week', now).$1, DateTime(2026, 9, 4, 10));
      expect(StatisticsRules.chartRange('month', now).$1, DateTime(2026, 8, 12, 10));
      expect(StatisticsRules.chartRange('year', now).$1, DateTime(2025, 9, 1));
      expect(StatisticsRules.chartRange('year', now).$2, now);
    });

    test('intervals and rank colours', () {
      final points = [
        ChartDataPoint(timestamp: DateTime(2026, 9, 1), valueKwh: 2),
        ChartDataPoint(timestamp: DateTime(2026, 9, 2), valueKwh: 8),
      ];
      expect(StatisticsRules.chartInterval(points), 2);
      expect(StatisticsRules.chartInterval(const []), 1);
      expect(StatisticsRules.bottomTitleInterval(7), 1);
      expect(StatisticsRules.bottomTitleInterval(20), 5);
      expect(StatisticsRules.bottomTitleInterval(60), 7);
      expect(StatisticsRules.rankColor(1), Colors.amber);
      expect(StatisticsRules.rankColor(4), AppColors.blue);
    });
  });

  group('ForecastLabels', () {
    final now = DateTime(2026, 9, 11);

    test('day labels: Azi, Mâine, weekday + day', () {
      expect(ForecastLabels.ymd(now), '2026-09-11');
      expect(ForecastLabels.dayLabel('2026-09-11', now), 'Azi');
      expect(ForecastLabels.dayLabel('2026-09-12', now), 'Mâine');
      expect(ForecastLabels.dayLabel('2026-09-14', now), 'Lun 14');
      expect(ForecastLabels.dayLabel('not-a-date', now), 'not-a-date');
    });

    test('time since update and peak hours text', () {
      expect(ForecastLabels.timeSinceUpdate(null, now), '');
      expect(ForecastLabels.timeSinceUpdate(now.subtract(const Duration(seconds: 30)), now), 'Actualizat acum');
      expect(ForecastLabels.timeSinceUpdate(now.subtract(const Duration(minutes: 5)), now), 'Actualizat acum 5 min');
      expect(ForecastLabels.timeSinceUpdate(now.subtract(const Duration(hours: 3)), now), 'Actualizat acum 3 ore');
      expect(ForecastLabels.timeSinceUpdate(now.subtract(const Duration(days: 2)), now), 'Actualizat acum 2 zile');
      expect(ForecastLabels.peakHoursText([9, 12]), '09:00, 12:00');
    });
  });

  group('trading helpers', () {
    test('wallet transaction labels', () {
      expect(walletTxTypeLabel('credit'), 'Încasare P2P');
      expect(walletTxTypeLabel('vpp_payment'), 'Plată rezervă VPP');
      expect(walletTxTypeLabel('other'), 'other');
    });

    test('trade savings versus grid price', () {
      final trade = Trade.fromJson({
        'id': 1,
        'seller_house_id': 2,
        'buyer_house_id': 3,
        'energy_kwh': 2,
        'price_lei_kwh': 0.7,
        'total_value_lei': 1.4,
        'grid_price_lei_kwh': 1.0,
        'status': 'settled',
        'transaction_type': 'buy',
      });
      expect(tradeSavingsLei(trade), closeTo(0.6, 1e-9));
    });
  });
}
