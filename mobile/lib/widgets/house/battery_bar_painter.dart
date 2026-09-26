import 'package:flutter/material.dart';
import 'package:flutter_interface/core/energy_flow.dart';

class BatteryBarPainter extends CustomPainter {
  final Offset batteryTop;
  final Offset batteryBottom;
  final int batteryPercentage;

  BatteryBarPainter({
    required this.batteryTop,
    required this.batteryBottom,
    required this.batteryPercentage,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final batteryBgPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.15)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(batteryTop, batteryBottom, batteryBgPaint);

    if (batteryPercentage > 0) {
      final batteryHeight = batteryBottom.dy - batteryTop.dy;
      final filledHeight = batteryHeight * (batteryPercentage / 100);

      final filledTopY = batteryBottom.dy - filledHeight;
      // Interpolăm X-ul pentru linia ușor înclinată
      final tFactor = filledHeight / batteryHeight;
      final filledTopX = batteryBottom.dx + (batteryTop.dx - batteryBottom.dx) * tFactor;
      final filledTop = Offset(filledTopX, filledTopY);

      final glowPaint = Paint()
        ..color = batteryLevelColor(batteryPercentage).withValues(alpha: 0.5)
        ..strokeWidth = 14
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);

      final batteryFillPaint = Paint()
        ..color = batteryLevelColor(batteryPercentage)
        ..strokeWidth = 8
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      canvas.drawLine(filledTop, batteryBottom, glowPaint);
      canvas.drawLine(filledTop, batteryBottom, batteryFillPaint);
    }
  }

  @override
  bool shouldRepaint(covariant BatteryBarPainter oldDelegate) {
    return oldDelegate.batteryPercentage != batteryPercentage;
  }
}
