import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_interface/core/energy_flow.dart';
import 'package:flutter_interface/core/theme.dart';

class EnergyFlowPainter extends CustomPainter {
  final Animation<double> animation;
  final double solarPower;
  final double homePower;

  /// Puterea bateriei: pozitiv = încărcare, negativ = descărcare
  final double batteryPower;

  /// Puterea grid: pozitiv = import, negativ = export
  final double gridPower;

  // Thresholds below which no arrow is drawn
  static const double _minSolarPower = FlowThresholds.arrowKw;
  static const double _minHomePower = FlowThresholds.arrowKw;
  static const double _minBatteryPower = FlowThresholds.arrowKw;
  static const double _minGridPower = FlowThresholds.gridKw;

  EnergyFlowPainter({
    required this.animation,
    required this.solarPower,
    required this.homePower,
    required this.batteryPower,
    required this.gridPower,
  }) : super(repaint: animation);

  static const double originalWidth = 1073.0;
  static const double originalHeight = 715.0;
  static const double aspectRatio = originalWidth / originalHeight;

  // Coordonate în PIXELI din imaginea originală 1073x715
  static const List<List<double>> solarToInverterPathPx = [
    [814, 394],
    [839, 426],
    [824, 459],
    [824, 507],
  ];

  static const List<List<double>> inverterToBatteryPathPx = [
    [795, 605],
    [758, 610],
    [711, 616],
  ];

  static const List<List<double>> batteryToInverterPathPx = [
    [711, 616],
    [758, 610],
    [795, 605],
  ];

  static const List<List<double>> inverterToHomePathPx = [
    [857, 552],
    [887, 549],
    [928, 543],
  ];

  static const List<List<double>> inverterToGridPathPx = [
    [824, 609],
    [822, 654],
    [824, 664],
    [829, 669],
    [835, 671],
    [866, 677],
    [956, 690],
  ];

  static const List<List<double>> gridToInverterPathPx = [
    [956, 690],
    [866, 677],
    [835, 671],
    [829, 669],
    [824, 664],
    [822, 654],
    [824, 609],
  ];

  Offset _convertPoint(double origX, double origY, Size containerSize) {
    double imageWidth, imageHeight;
    double offsetX = 0, offsetY = 0;

    if (containerSize.width / containerSize.height > aspectRatio) {
      imageHeight = containerSize.height;
      imageWidth = imageHeight * aspectRatio;
      offsetX = (containerSize.width - imageWidth) / 2;
    } else {
      imageWidth = containerSize.width;
      imageHeight = imageWidth / aspectRatio;
      offsetY = (containerSize.height - imageHeight) / 2;
    }

    final scaleX = imageWidth / originalWidth;
    final scaleY = imageHeight / originalHeight;

    return Offset(
      offsetX + origX * scaleX,
      offsetY + origY * scaleY,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (solarPower > _minSolarPower) {
      _drawFlowPathPx(
        canvas,
        size,
        solarToInverterPathPx,
        AppColors.amber,
        animation.value,
        solarPower,
        reverseAnimation: true,
      );
    }

    if (batteryPower > _minBatteryPower) {
      _drawFlowPathPx(
        canvas,
        size,
        inverterToBatteryPathPx,
        AppColors.emerald,
        animation.value,
        batteryPower,
        reverseAnimation: true,
      );
    } else if (batteryPower < -_minBatteryPower) {
      _drawFlowPathPx(
        canvas,
        size,
        batteryToInverterPathPx,
        AppColors.red,
        animation.value,
        batteryPower.abs(),
        reverseAnimation: true,
      );
    }

    if (homePower > _minHomePower) {
      _drawFlowPathPx(
        canvas,
        size,
        inverterToHomePathPx,
        AppColors.green,
        animation.value,
        homePower,
        reverseAnimation: true,
      );
    }

    if (gridPower > _minGridPower) {
      _drawFlowPathPx(
        canvas,
        size,
        gridToInverterPathPx,
        AppColors.red,
        animation.value,
        gridPower,
        reverseAnimation: true,
      );
    } else if (gridPower < -_minGridPower) {
      _drawFlowPathPx(
        canvas,
        size,
        inverterToGridPathPx,
        AppColors.emerald,
        animation.value,
        gridPower.abs(),
        reverseAnimation: true,
      );
    }
  }

  void _drawFlowPathPx(
    Canvas canvas,
    Size size,
    List<List<double>> pathPointsPx,
    Color color,
    double animationValue,
    double power, {
    bool reverseAnimation = false,
  }) {
    if (pathPointsPx.length < 2) return;

    final points = pathPointsPx.map((p) => _convertPoint(p[0], p[1], size)).toList();

    final path = Path();
    path.moveTo(points[0].dx, points[0].dy);
    for (int i = 1; i < points.length; i++) {
      path.lineTo(points[i].dx, points[i].dy);
    }

    final pathMetrics = path.computeMetrics().first;
    final pathLength = pathMetrics.length;

    final glowPaint = Paint()
      ..color = color.withValues(alpha: 0.1)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
    canvas.drawPath(path, glowPaint);

    final basePaint = Paint()
      ..color = color.withValues(alpha: 0.2)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, basePaint);

    // Folosim pattern length ca bază pentru animație smooth (fără salt la reset)
    const dashLength = 12.0;
    const gapLength = 20.0;
    final patternLength = dashLength + gapLength;

    final effectiveAnimValue = reverseAnimation ? (1.0 - animationValue) : animationValue;
    final dashOffset = effectiveAnimValue * patternLength;
    final dashPattern = [dashLength, gapLength];

    final dashPaint = Paint()
      ..color = color
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    _drawDashedPathWithOffset(
      canvas,
      path,
      dashPaint,
      dashPattern,
      dashOffset,
      pathLength,
    );
  }

  void _drawDashedPathWithOffset(
    Canvas canvas,
    Path path,
    Paint paint,
    List<double> dashPattern,
    double dashOffset,
    double pathLength,
  ) {
    final pathMetrics = path.computeMetrics().first;
    final dashLength = dashPattern[0];
    final gapLength = dashPattern[1];
    final patternLength = dashLength + gapLength;

    double currentOffset = dashOffset % patternLength;
    double distance = -currentOffset;

    while (distance < pathLength) {
      final double dashStart = math.max(0.0, distance);
      final double dashEnd = math.min(pathLength, distance + dashLength);

      if (dashStart < pathLength && dashEnd > 0 && dashEnd > dashStart) {
        final extractedPath = pathMetrics.extractPath(dashStart, dashEnd);

        final glowPaint = Paint()
          ..color = paint.color.withValues(alpha: 0.4)
          ..strokeWidth = paint.strokeWidth + 2
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
        canvas.drawPath(extractedPath, glowPaint);

        canvas.drawPath(extractedPath, paint);
      }

      distance += patternLength;
    }
  }

  @override
  bool shouldRepaint(covariant EnergyFlowPainter oldDelegate) => true;
}
