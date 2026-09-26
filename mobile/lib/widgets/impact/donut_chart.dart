import 'dart:math' as math;

import 'package:flutter/material.dart';

class DonutSegment {
  final double value;
  final Color color;
  const DonutSegment(this.value, this.color);
}

class DonutChartPainter extends CustomPainter {
  final List<DonutSegment> segments;

  DonutChartPainter({required this.segments});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    const strokeWidth = 12.0;
    final rect = Rect.fromCircle(center: center, radius: radius - strokeWidth / 2);
    const startAngle = -math.pi / 2;

    final total = segments.fold<double>(0, (s, seg) => s + math.max(0.0, seg.value));
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.butt;

    if (total <= 0) {
      paint.color = Colors.white.withValues(alpha: 0.08);
      canvas.drawArc(rect, 0, 2 * math.pi, false, paint);
      return;
    }

    final glowPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth + 8
      ..strokeCap = StrokeCap.butt
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);

    double angle = startAngle;
    for (final seg in segments) {
      final sweep = math.max(0.0, seg.value) / total * 2 * math.pi;
      if (sweep <= 0) continue;
      glowPaint.color = seg.color.withValues(alpha: 0.35);
      canvas.drawArc(rect, angle, sweep, false, glowPaint);
      angle += sweep;
    }

    angle = startAngle;
    for (final seg in segments) {
      final sweep = math.max(0.0, seg.value) / total * 2 * math.pi;
      if (sweep <= 0) continue;
      paint.color = seg.color;
      canvas.drawArc(rect, angle, sweep, false, paint);
      angle += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant DonutChartPainter oldDelegate) {
    if (oldDelegate.segments.length != segments.length) return true;
    for (var i = 0; i < segments.length; i++) {
      if (oldDelegate.segments[i].value != segments[i].value) return true;
    }
    return false;
  }
}
