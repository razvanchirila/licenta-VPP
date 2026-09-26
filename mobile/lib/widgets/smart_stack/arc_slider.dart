import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

class ArcSlider extends StatefulWidget {
  final double minValue;
  final double maxValue;
  final double currentValue;
  final ValueChanged<double> onChanged;
  final double size;

  const ArcSlider({
    super.key,
    this.minValue = 16,
    this.maxValue = 32,
    required this.currentValue,
    required this.onChanged,
    this.size = 200,
  });

  @override
  State<ArcSlider> createState() => _ArcSliderState();
}

class _ArcSliderState extends State<ArcSlider> {
  double _currentValue = 0;

  static const double _startDeg = 140.0;
  static const double _endDeg = 40.0;
  static const double _sweepDeg = 260.0;

  @override
  void initState() {
    super.initState();
    _currentValue = widget.currentValue.clamp(widget.minValue, widget.maxValue);
  }

  @override
  void didUpdateWidget(ArcSlider oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentValue != widget.currentValue) {
      _currentValue = widget.currentValue.clamp(widget.minValue, widget.maxValue);
    }
  }

  double _normalizeAngle(double degrees) {
    degrees = degrees % 360;
    if (degrees < 0) degrees += 360;
    return degrees;
  }

  void _updateValueFromPosition(Offset localPosition, Offset center) {
    final dx = localPosition.dx - center.dx;
    final dy = localPosition.dy - center.dy;
    var angleDeg = math.atan2(dy, dx) * 180 / math.pi;
    angleDeg = _normalizeAngle(angleDeg);

    // Arc goes from _startDeg (140°) clockwise through 0° to _endDeg (40°)

    double position;

    if (angleDeg >= _startDeg) {
      position = (angleDeg - _startDeg) / _sweepDeg;
    } else if (angleDeg <= _endDeg) {
      position = (360 - _startDeg + angleDeg) / _sweepDeg;
    } else {
      // We're in the dead zone (40° to 140°)
      final distToEnd = angleDeg - _endDeg;
      final distToStart = _startDeg - angleDeg;

      if (distToEnd < distToStart) {
        position = 1.0;
      } else {
        position = 0.0;
      }
    }

    position = position.clamp(0.0, 1.0);

    final newValue = widget.minValue + position * (widget.maxValue - widget.minValue);

    // Anti-jump protection: ignore large jumps
    final diff = (newValue - _currentValue).abs();
    final range = widget.maxValue - widget.minValue;
    if (diff > range * 0.3 && _currentValue != widget.currentValue) {
      return;
    }

    setState(() {
      _currentValue = newValue;
    });
    widget.onChanged(newValue.roundToDouble());
  }

  @override
  Widget build(BuildContext context) {
    final center = Offset(widget.size / 2, widget.size / 2);

    return GestureDetector(
      onPanStart: (details) => _updateValueFromPosition(details.localPosition, center),
      onPanUpdate: (details) => _updateValueFromPosition(details.localPosition, center),
      onTapDown: (details) => _updateValueFromPosition(details.localPosition, center),
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: CustomPaint(
          painter: _ArcSliderPainter(
            minValue: widget.minValue,
            maxValue: widget.maxValue,
            currentValue: _currentValue,
          ),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${_currentValue.round()}',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 44,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -1,
                  ),
                ),
                Text(
                  '°C',
                  style: GoogleFonts.inter(
                    color: Colors.white.withValues(alpha: 0.6),
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Temperatură',
                  style: GoogleFonts.inter(
                    color: Colors.white.withValues(alpha: 0.4),
                    fontSize: 11,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ArcSliderPainter extends CustomPainter {
  final double minValue;
  final double maxValue;
  final double currentValue;

  static const double _startDeg = 140.0;
  static const double _sweepDeg = 260.0;

  static final double _startRad = _startDeg * math.pi / 180;
  static final double _sweepRad = _sweepDeg * math.pi / 180;

  static const Color _primaryColor = AppColors.blue;
  static const Color _successColor = AppColors.green;
  static const Color _warningColor = AppColors.amber;
  static const Color _errorColor = AppColors.red;
  static const Color _surfaceColor = AppColors.surface;

  _ArcSliderPainter({
    required this.minValue,
    required this.maxValue,
    required this.currentValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 20;

    final trackPaint = Paint()
      ..color = _surfaceColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 10
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      _startRad,
      _sweepRad,
      false,
      trackPaint,
    );

    final progress = ((currentValue - minValue) / (maxValue - minValue)).clamp(0.0, 1.0);
    final progressSweep = progress * _sweepRad;

    Color progressColor;
    if (currentValue <= 20) {
      progressColor = _primaryColor;
    } else if (currentValue <= 24) {
      progressColor = _successColor;
    } else if (currentValue <= 28) {
      progressColor = _warningColor;
    } else {
      progressColor = _errorColor;
    }

    if (progressSweep > 0) {
      final progressPaint = Paint()
        ..color = progressColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = 10
        ..strokeCap = StrokeCap.round;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        _startRad,
        progressSweep,
        false,
        progressPaint,
      );
    }

    final thumbAngle = _startRad + progressSweep;
    final thumbX = center.dx + radius * math.cos(thumbAngle);
    final thumbY = center.dy + radius * math.sin(thumbAngle);

    canvas.drawCircle(
      Offset(thumbX, thumbY),
      14,
      Paint()
        ..color = progressColor.withValues(alpha: 0.3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );

    canvas.drawCircle(
      Offset(thumbX, thumbY),
      12,
      Paint()..color = progressColor,
    );

    canvas.drawCircle(
      Offset(thumbX, thumbY),
      6,
      Paint()..color = Colors.white,
    );

    final textStyle = TextStyle(
      color: Colors.white.withValues(alpha: 0.4),
      fontSize: 11,
      fontWeight: FontWeight.w500,
    );

    final minX = center.dx + (radius + 22) * math.cos(_startRad);
    final minY = center.dy + (radius + 22) * math.sin(_startRad);
    _drawText(canvas, '${minValue.round()}°', Offset(minX, minY), textStyle);

    final maxAngle = _startRad + _sweepRad;
    final maxX = center.dx + (radius + 22) * math.cos(maxAngle);
    final maxY = center.dy + (radius + 22) * math.sin(maxAngle);
    _drawText(canvas, '${maxValue.round()}°', Offset(maxX, maxY), textStyle);
  }

  void _drawText(Canvas canvas, String text, Offset position, TextStyle style) {
    final textPainter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
    )..layout();

    textPainter.paint(
      canvas,
      Offset(position.dx - textPainter.width / 2, position.dy - textPainter.height / 2),
    );
  }

  @override
  bool shouldRepaint(covariant _ArcSliderPainter oldDelegate) {
    return oldDelegate.currentValue != currentValue;
  }
}
