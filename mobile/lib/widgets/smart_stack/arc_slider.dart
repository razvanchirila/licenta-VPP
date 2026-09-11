import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Arc slider widget for temperature selection
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
  
  // Arc configuration: starts at bottom-left, goes clockwise to bottom-right
  // Using degrees for clarity, converted to radians when needed
  static const double _startDeg = 140.0;  // Start angle in degrees
  static const double _endDeg = 40.0;     // End angle in degrees  
  static const double _sweepDeg = 260.0;  // Total sweep (360 - gap)

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

  /// Normalize angle to 0-360 range
  double _normalizeAngle(double degrees) {
    degrees = degrees % 360;
    if (degrees < 0) degrees += 360;
    return degrees;
  }

  /// Convert touch position to slider value
  void _updateValueFromPosition(Offset localPosition, Offset center) {
    // Get angle from center to touch point (in degrees)
    final dx = localPosition.dx - center.dx;
    final dy = localPosition.dy - center.dy;
    var angleDeg = math.atan2(dy, dx) * 180 / math.pi;
    angleDeg = _normalizeAngle(angleDeg);
    
    // Calculate position along the arc (0.0 to 1.0)
    // Arc goes from _startDeg (140°) clockwise through 0° to _endDeg (40°)
    
    double position;
    
    if (angleDeg >= _startDeg) {
      // We're in the first part: from start (140°) to 360°
      position = (angleDeg - _startDeg) / _sweepDeg;
    } else if (angleDeg <= _endDeg) {
      // We're in the second part: from 0° to end (40°)
      position = (360 - _startDeg + angleDeg) / _sweepDeg;
    } else {
      // We're in the dead zone (40° to 140°)
      // Determine which end is closer
      final distToEnd = angleDeg - _endDeg;
      final distToStart = _startDeg - angleDeg;
      
      if (distToEnd < distToStart) {
        position = 1.0; // Closer to max
      } else {
        position = 0.0; // Closer to min
      }
    }
    
    position = position.clamp(0.0, 1.0);
    
    // Convert to value
    final newValue = widget.minValue + position * (widget.maxValue - widget.minValue);
    
    // Anti-jump protection: ignore large jumps
    final diff = (newValue - _currentValue).abs();
    final range = widget.maxValue - widget.minValue;
    if (diff > range * 0.3 && _currentValue != widget.currentValue) {
      return; // Ignore this update
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
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Temperatură',
                  style: GoogleFonts.inter(
                    color: Colors.white.withOpacity(0.4),
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

  // Arc config (same as in state)
  static const double _startDeg = 140.0;
  static const double _sweepDeg = 260.0;
  
  // Convert to radians for drawing
  static final double _startRad = _startDeg * math.pi / 180;
  static final double _sweepRad = _sweepDeg * math.pi / 180;

  // App color palette
  static const Color _primaryColor = Color(0xFF3B82F6);
  static const Color _successColor = Color(0xFF22C55E);
  static const Color _warningColor = Color(0xFFFBBF24);
  static const Color _errorColor = Color(0xFFEF4444);
  static const Color _surfaceColor = Color(0xFF1C1C1E);

  _ArcSliderPainter({
    required this.minValue,
    required this.maxValue,
    required this.currentValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 20;

    // Background arc (track)
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

    // Progress arc
    final progress = ((currentValue - minValue) / (maxValue - minValue)).clamp(0.0, 1.0);
    final progressSweep = progress * _sweepRad;

    // Color based on temperature
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

    // Thumb position
    final thumbAngle = _startRad + progressSweep;
    final thumbX = center.dx + radius * math.cos(thumbAngle);
    final thumbY = center.dy + radius * math.sin(thumbAngle);

    // Thumb glow
    canvas.drawCircle(
      Offset(thumbX, thumbY),
      14,
      Paint()
        ..color = progressColor.withOpacity(0.3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );

    // Thumb outer
    canvas.drawCircle(
      Offset(thumbX, thumbY),
      12,
      Paint()..color = progressColor,
    );

    // Thumb inner
    canvas.drawCircle(
      Offset(thumbX, thumbY),
      6,
      Paint()..color = Colors.white,
    );

    // Labels
    final textStyle = TextStyle(
      color: Colors.white.withOpacity(0.4),
      fontSize: 11,
      fontWeight: FontWeight.w500,
    );

    // Min label
    final minX = center.dx + (radius + 22) * math.cos(_startRad);
    final minY = center.dy + (radius + 22) * math.sin(_startRad);
    _drawText(canvas, '${minValue.round()}°', Offset(minX, minY), textStyle);

    // Max label
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
