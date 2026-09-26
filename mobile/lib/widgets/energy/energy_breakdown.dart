import 'package:flutter_interface/models/energy.dart';

/// Energy totals (kWh) of a chart period, integrated from the kW points:
/// each point is an average over `hoursPerPoint` hours, so
/// `kWh = kW * hoursPerPoint` summed over the points.
class EnergyBreakdown {
  final double totalSolar;
  final double solarToLoad;
  final double solarToGrid;
  final double solarToBattery;
  final double solarToNeighbours;

  final double totalConsumption;
  final double consumptionFromSolar;
  final double consumptionFromGrid;
  final double consumptionFromBattery;
  final double consumptionFromNeighbours;

  const EnergyBreakdown({
    this.totalSolar = 0,
    this.solarToLoad = 0,
    this.solarToGrid = 0,
    this.solarToBattery = 0,
    this.solarToNeighbours = 0,
    this.totalConsumption = 0,
    this.consumptionFromSolar = 0,
    this.consumptionFromGrid = 0,
    this.consumptionFromBattery = 0,
    this.consumptionFromNeighbours = 0,
  });

  factory EnergyBreakdown.fromPoints(List<EnergyPoint> points, double hoursPerPoint) {
    final h = hoursPerPoint;
    double totalSolar = 0, solarToLoad = 0, solarToGrid = 0, solarToBattery = 0, solarToNeighbours = 0;
    double totalConsumption = 0, fromGrid = 0, fromBattery = 0, fromNeighbours = 0;

    for (final p in points) {
      totalSolar += p.solar * h;
      totalConsumption += p.consumption * h;
      solarToLoad += p.solarToLoad * h;
      solarToGrid += p.solarToGrid * h;
      solarToBattery += p.solarToBattery * h;
      solarToNeighbours += p.p2pSell * h;
      fromGrid += p.gridToLoad * h;
      fromBattery += p.batteryToLoad * h;
      fromNeighbours += p.p2pBuy * h;
    }

    return EnergyBreakdown(
      totalSolar: totalSolar,
      solarToLoad: solarToLoad,
      solarToGrid: solarToGrid,
      solarToBattery: solarToBattery,
      solarToNeighbours: solarToNeighbours,
      totalConsumption: totalConsumption,
      consumptionFromSolar: solarToLoad,
      consumptionFromGrid: fromGrid,
      consumptionFromBattery: fromBattery,
      consumptionFromNeighbours: fromNeighbours,
    );
  }

  double productionPercent(double part) => totalSolar > 0 ? part / totalSolar * 100 : 0.0;

  double consumptionPercent(double part) => totalConsumption > 0 ? part / totalConsumption * 100 : 0.0;
}
