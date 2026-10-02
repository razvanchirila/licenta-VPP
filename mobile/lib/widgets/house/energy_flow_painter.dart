import 'dart:math' as math;
import 'dart:ui' show PathMetric;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_interface/core/energy_flow.dart';
import 'package:flutter_interface/core/theme.dart';

/// One animated flow: a polyline in pixels of the original 1073x715 image and its colour.
typedef FlowTrack = ({List<List<double>> points, Color color});

// Coordonate în PIXELI din imaginea originală 1073x715
const List<List<double>> _solarToInverterPx = [
  [814, 394],
  [839, 426],
  [824, 459],
  [824, 507],
];

const List<List<double>> _inverterToBatteryPx = [
  [795, 605],
  [758, 610],
  [711, 616],
];

const List<List<double>> _batteryToInverterPx = [
  [711, 616],
  [758, 610],
  [795, 605],
];

const List<List<double>> _inverterToHomePx = [
  [857, 552],
  [887, 549],
  [928, 543],
];

const List<List<double>> _inverterToGridPx = [
  [824, 609],
  [822, 654],
  [824, 664],
  [829, 669],
  [835, 671],
  [866, 677],
  [956, 690],
];

const List<List<double>> _gridToInverterPx = [
  [956, 690],
  [866, 677],
  [835, 671],
  [829, 669],
  [824, 664],
  [822, 654],
  [824, 609],
];

/// The flows drawn for these powers (kW), in paint order; empty when the house is idle.
/// Battery: positive = charging. Grid: positive = import.
List<FlowTrack> energyFlowTracks({
  required double solarPower,
  required double homePower,
  required double batteryPower,
  required double gridPower,
}) {
  return [
    if (solarPower > FlowThresholds.arrowKw) (points: _solarToInverterPx, color: AppColors.amber),
    if (batteryPower > FlowThresholds.arrowKw)
      (points: _inverterToBatteryPx, color: AppColors.emerald)
    else if (batteryPower < -FlowThresholds.arrowKw)
      (points: _batteryToInverterPx, color: AppColors.red),
    if (homePower > FlowThresholds.arrowKw) (points: _inverterToHomePx, color: AppColors.green),
    if (gridPower > FlowThresholds.gridKw)
      (points: _gridToInverterPx, color: AppColors.red)
    else if (gridPower < -FlowThresholds.gridKw)
      (points: _inverterToGridPx, color: AppColors.emerald),
  ];
}

const double _originalWidth = 1073.0;
const double _originalHeight = 715.0;
const double _dashLength = 12.0;
const double _gapLength = 20.0;

/// Paths and their metrics for the current canvas size, built once instead of on every frame.
class _FlowGeometry {
  static Size? _size;
  static final Map<List<List<double>>, (Path, PathMetric)> _paths = {};

  static (Path, PathMetric) of(List<List<double>> pointsPx, Size size) {
    if (size != _size) {
      _paths.clear();
      _size = size;
    }
    return _paths.putIfAbsent(pointsPx, () {
      final points = pointsPx.map((p) => _convertPoint(p[0], p[1], size)).toList();
      final path = Path()..moveTo(points[0].dx, points[0].dy);
      for (final p in points.skip(1)) {
        path.lineTo(p.dx, p.dy);
      }
      return (path, path.computeMetrics().first);
    });
  }

  static Offset _convertPoint(double origX, double origY, Size containerSize) {
    const aspectRatio = _originalWidth / _originalHeight;
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

    return Offset(
      offsetX + origX * imageWidth / _originalWidth,
      offsetY + origY * imageHeight / _originalHeight,
    );
  }
}

Paint _stroke(Color color, double width, {double blur = 0, StrokeCap cap = StrokeCap.round}) {
  final paint = Paint()
    ..color = color
    ..strokeWidth = width
    ..style = PaintingStyle.stroke
    ..strokeCap = cap;
  if (blur > 0) paint.maskFilter = MaskFilter.blur(BlurStyle.normal, blur);
  return paint;
}

/// The still part of each flow (soft glow and thin base line); repaints only when the set of flows changes.
class EnergyFlowLinesPainter extends CustomPainter {
  final List<FlowTrack> tracks;

  EnergyFlowLinesPainter({required this.tracks});

  static final Map<Color, (Paint, Paint)> _paints = {};

  @override
  void paint(Canvas canvas, Size size) {
    for (final track in tracks) {
      final (path, _) = _FlowGeometry.of(track.points, size);
      final (glow, base) = _paints.putIfAbsent(
        track.color,
        () => (
          _stroke(track.color.withValues(alpha: 0.1), 8, blur: 4, cap: StrokeCap.butt),
          _stroke(track.color.withValues(alpha: 0.2), 2),
        ),
      );
      canvas.drawPath(path, glow);
      canvas.drawPath(path, base);
    }
  }

  @override
  bool shouldRepaint(covariant EnergyFlowLinesPainter oldDelegate) => !listEquals(oldDelegate.tracks, tracks);
}

/// The moving dashes. All dashes of a flow go into one path, so the glow is a single blur per flow.
class EnergyFlowPainter extends CustomPainter {
  final Animation<double> animation;
  final List<FlowTrack> tracks;

  EnergyFlowPainter({required this.animation, required this.tracks}) : super(repaint: animation);

  static final Map<Color, (Paint, Paint)> _paints = {};

  @override
  void paint(Canvas canvas, Size size) {
    const patternLength = _dashLength + _gapLength;
    // the dashes run from the end of each path towards its start
    final dashOffset = (1.0 - animation.value) * patternLength;

    for (final track in tracks) {
      final (_, metric) = _FlowGeometry.of(track.points, size);
      final length = metric.length;
      final dashes = Path();
      for (var distance = -(dashOffset % patternLength); distance < length; distance += patternLength) {
        final start = math.max(0.0, distance);
        final end = math.min(length, distance + _dashLength);
        if (end > start) dashes.addPath(metric.extractPath(start, end), Offset.zero);
      }
      final (glow, dash) = _paints.putIfAbsent(
        track.color,
        () => (_stroke(track.color.withValues(alpha: 0.4), 5, blur: 2), _stroke(track.color, 3)),
      );
      canvas.drawPath(dashes, glow);
      canvas.drawPath(dashes, dash);
    }
  }

  @override
  bool shouldRepaint(covariant EnergyFlowPainter oldDelegate) =>
      oldDelegate.animation != animation || !listEquals(oldDelegate.tracks, tracks);
}
