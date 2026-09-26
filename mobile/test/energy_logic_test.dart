import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/widgets/energy/energy_breakdown.dart';
import 'package:flutter_interface/widgets/energy/energy_line_chart.dart';
import 'package:flutter_interface/widgets/energy/energy_period.dart';
import 'package:flutter_test/flutter_test.dart';

EnergyPoint point({
  double solar = 0,
  double consumption = 0,
  double battery = 0,
  double grid = 0,
  double p2p = 0,
  double solarToGrid = 0,
  double solarToBattery = 0,
  double gridToLoad = 0,
  double batteryToLoad = 0,
}) =>
    EnergyPoint(
      time: DateTime(2026, 9, 7, 12),
      solar: solar,
      consumption: consumption,
      battery: battery,
      grid: grid,
      p2p: p2p,
      solarToBattery: solarToBattery,
      batteryToLoad: batteryToLoad,
      gridToLoad: gridToLoad,
      solarToGrid: solarToGrid,
      socKwh: 5,
      priceImport: 1,
    );

void main() {
  group('EnergyPeriod', () {
    test('shift moves by day, week and clamps the day of month', () {
      final base = DateTime(2026, 1, 31);
      expect(EnergyPeriod.shift(base, EnergyPeriod.day, 1), DateTime(2026, 2, 1));
      expect(EnergyPeriod.shift(base, EnergyPeriod.week, -1), DateTime(2026, 1, 24));
      expect(EnergyPeriod.shift(base, EnergyPeriod.month, 1), DateTime(2026, 2, 28));
      expect(EnergyPeriod.shift(base, EnergyPeriod.month, -1), DateTime(2025, 12, 31));
      expect(EnergyPeriod.shift(base, 'unknown', 1), base);
    });

    test('label formats per period and falls back while no date', () {
      final wednesday = DateTime(2026, 9, 9);
      expect(EnergyPeriod.label(null, EnergyPeriod.day), 'Ziua simulată');
      expect(EnergyPeriod.label(wednesday, EnergyPeriod.day), '09/09/2026');
      expect(EnergyPeriod.label(wednesday, EnergyPeriod.week), '07/09 - 13/09');
      expect(EnergyPeriod.label(wednesday, EnergyPeriod.month), '09/2026');
    });

    test('axis label and adjective', () {
      final t = DateTime(2026, 9, 9, 14, 30);
      expect(EnergyPeriod.axisLabel(t, EnergyPeriod.day), '14:30');
      expect(EnergyPeriod.axisLabel(t, EnergyPeriod.month), '09');
      expect(EnergyPeriod.adjective(EnergyPeriod.week), 'săptămânală');
      expect(EnergyPeriod.adjective('x'), 'zilnică');
    });
  });

  group('EnergyBreakdown', () {
    test('integrates kW points into kWh with hoursPerPoint', () {
      final points = [
        // p2p < 0 = selling 0.5 kW; solarToLoad = 4 - 1 - 0.5 - 0.5 = 2 kW
        point(solar: 4, consumption: 2, solarToBattery: 1, solarToGrid: 0.5, p2p: -0.5),
        // p2p > 0 = buying 0.5 kW
        point(solar: 0, consumption: 2, gridToLoad: 1, batteryToLoad: 0.5, p2p: 0.5),
      ];
      final b = EnergyBreakdown.fromPoints(points, 0.5);

      expect(b.totalSolar, 2.0);
      expect(b.totalConsumption, 2.0);
      expect(b.solarToLoad, 1.0);
      expect(b.solarToBattery, 0.5);
      expect(b.solarToGrid, 0.25);
      expect(b.solarToNeighbours, 0.25);
      expect(b.consumptionFromSolar, 1.0);
      expect(b.consumptionFromGrid, 0.5);
      expect(b.consumptionFromBattery, 0.25);
      expect(b.consumptionFromNeighbours, 0.25);
      expect(b.productionPercent(b.solarToLoad), 50);
      expect(b.consumptionPercent(b.consumptionFromGrid), 25);
    });

    test('percentages are 0 when nothing was produced or consumed', () {
      const b = EnergyBreakdown();
      expect(b.productionPercent(1), 0);
      expect(b.consumptionPercent(1), 0);
    });
  });

  group('EnergyChartScale', () {
    final points = [point(solar: 3, consumption: 1, battery: -6, grid: 2), point(solar: 1, consumption: 4)];

    test('maxY adds 20% headroom over the visible series only', () {
      expect(EnergyChartScale.maxY(points, const EnergySeriesVisibility()), 5); // max(3,4)*1.2 = 4.8 -> 5
      expect(EnergyChartScale.maxY(points, const EnergySeriesVisibility(battery: true)), 8); // |-6|*1.2
      expect(EnergyChartScale.maxY(const [], const EnergySeriesVisibility()), 1);
    });

    test('grid intervals scale with the range and the point count', () {
      expect(EnergyChartScale.horizontalInterval(1.5), 0.5);
      expect(EnergyChartScale.horizontalInterval(4), 1);
      expect(EnergyChartScale.horizontalInterval(10), 2);
      expect(EnergyChartScale.horizontalInterval(30), 6);
      expect(EnergyChartScale.verticalInterval(96, EnergyPeriod.day), 16);
      expect(EnergyChartScale.verticalInterval(7, EnergyPeriod.week), 1);
      expect(EnergyChartScale.bottomInterval(96), 16);
    });

    test('visibility lists series in drawing order', () {
      const v = EnergySeriesVisibility(solar: false, grid: true);
      expect(v.visible, [EnergySeries.consumption, EnergySeries.grid]);
      expect(v.copyWith(solar: true).visible.first, EnergySeries.solar);
    });

    test('battery and grid plot magnitudes with a direction suffix', () {
      final p = point(battery: -1.5, grid: 0.8);
      expect(EnergySeries.battery.valueOf(p), 1.5);
      expect(EnergySeries.battery.tooltipSuffix(p), ' (descărcare)');
      expect(EnergySeries.grid.tooltipSuffix(p), ' (import)');
      expect(EnergySeries.solar.tooltipSuffix(p), '');
    });
  });
}
