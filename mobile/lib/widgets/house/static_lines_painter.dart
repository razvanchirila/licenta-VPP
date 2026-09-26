import 'package:flutter/material.dart';
import 'package:flutter_interface/core/energy_flow.dart';

class StaticLinesPainter extends CustomPainter {
  final Offset solarStart;
  final Offset solarEnd;
  final Offset homeStart;
  final Offset homeEnd;
  final Offset gridStart;
  final Offset gridEnd;
  final Offset batteryStart;
  final Offset batteryEnd;
  final Offset batteryTop;
  final Offset batteryBottom;
  final int batteryPercentage;
  final double solarPower;
  final double homePower;
  final double gridPower;
  final double batteryPower;
  final bool drawBattery;

  StaticLinesPainter({
    required this.solarStart,
    required this.solarEnd,
    required this.homeStart,
    required this.homeEnd,
    required this.gridStart,
    required this.gridEnd,
    required this.batteryStart,
    required this.batteryEnd,
    required this.batteryTop,
    required this.batteryBottom,
    required this.batteryPercentage,
    required this.solarPower,
    required this.homePower,
    required this.gridPower,
    required this.batteryPower,
    this.drawBattery = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final activePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.7)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final inactivePaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.35)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final solarActive = solarPower > FlowThresholds.arrowKw;
    canvas.drawLine(solarStart, solarEnd, solarActive ? activePaint : inactivePaint);

    final homeActive = homePower > FlowThresholds.arrowKw;
    canvas.drawLine(homeStart, homeEnd, homeActive ? activePaint : inactivePaint);

    final gridActive = gridPower.abs() > FlowThresholds.gridLineKw;
    canvas.drawLine(gridStart, gridEnd, gridActive ? activePaint : inactivePaint);

    final batteryActive = batteryPower.abs() > FlowThresholds.arrowKw;
    canvas.drawLine(batteryStart, batteryEnd, batteryActive ? activePaint : inactivePaint);
  }

  @override
  bool shouldRepaint(covariant StaticLinesPainter oldDelegate) {
    return oldDelegate.solarPower != solarPower ||
        oldDelegate.homePower != homePower ||
        oldDelegate.gridPower != gridPower ||
        oldDelegate.batteryPower != batteryPower;
  }
}
