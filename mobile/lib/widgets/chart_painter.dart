import 'package:flutter/material.dart';
import '../models/price_data.dart';

/// CustomPainter for animated OPCOM price chart
class ChartPainter extends CustomPainter {
  final List<PricePoint> prices;
  final double animationProgress;
  final double glowIntensity;
  final int? touchIndex;
  final Color lineColor;
  final double minPrice;
  final double maxPrice;
  final bool showReferenceLines;

  ChartPainter({
    required this.prices,
    this.animationProgress = 1.0,
    this.glowIntensity = 1.0,
    this.touchIndex,
    this.lineColor = const Color(0xFF00d4aa),
    this.minPrice = 0,
    this.maxPrice = 0,
    this.showReferenceLines = true,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (prices.isEmpty) return;

    final double effectiveMinPrice = minPrice > 0 ? minPrice : _calculateMin();
    final double effectiveMaxPrice = maxPrice > 0 ? maxPrice : _calculateMax();
    
    final double priceRange = effectiveMaxPrice - effectiveMinPrice;
    final double padding = priceRange * 0.08;
    final double paddedMin = effectiveMinPrice - padding;
    final double paddedMax = effectiveMaxPrice + padding;

    if (showReferenceLines) {
      _drawReferenceLines(canvas, size, paddedMin, paddedMax, effectiveMinPrice, effectiveMaxPrice);
    }

    final fullPath = _buildPricePath(size, paddedMin, paddedMax);
    final animatedPath = _getAnimatedPath(fullPath, animationProgress);
    
    // If touching, draw dimmed line first, then bright section around touch
    if (touchIndex != null && touchIndex! >= 0 && touchIndex! < prices.length) {
      _drawTouchEffect(canvas, size, paddedMin, paddedMax, animatedPath);
    } else {
      // Normal drawing
      if (glowIntensity > 0) {
        _drawGlow(canvas, animatedPath);
      }
      _drawMainLine(canvas, animatedPath);
    }
  }

  double _calculateMin() {
    return prices.map((p) => p.priceLeiKwh).reduce((a, b) => a < b ? a : b);
  }

  double _calculateMax() {
    return prices.map((p) => p.priceLeiKwh).reduce((a, b) => a > b ? a : b);
  }

  Path _buildPricePath(Size size, double minPrice, double maxPrice) {
    final path = Path();
    final double priceRange = maxPrice - minPrice;
    if (priceRange == 0) return path;
    
    for (int i = 0; i < prices.length; i++) {
      final double x = (i / (prices.length - 1)) * size.width;
      final double normalizedPrice = (prices[i].priceLeiKwh - minPrice) / priceRange;
      final double y = size.height - (normalizedPrice * size.height);
      
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    
    return path;
  }

  Path _getAnimatedPath(Path fullPath, double progress) {
    if (progress >= 1.0) return fullPath;
    if (progress <= 0.0) return Path();
    
    final pathMetrics = fullPath.computeMetrics();
    final Path animatedPath = Path();
    
    for (final metric in pathMetrics) {
      final double length = metric.length * progress;
      final extractedPath = metric.extractPath(0, length);
      animatedPath.addPath(extractedPath, Offset.zero);
    }
    
    return animatedPath;
  }

  void _drawGlow(Canvas canvas, Path path) {
    final outerGlowPaint = Paint()
      ..color = lineColor.withOpacity(0.15 * glowIntensity)
      ..strokeWidth = 12
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
    canvas.drawPath(path, outerGlowPaint);
    
    final innerGlowPaint = Paint()
      ..color = lineColor.withOpacity(0.3 * glowIntensity)
      ..strokeWidth = 6
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    canvas.drawPath(path, innerGlowPaint);
  }

  void _drawMainLine(Canvas canvas, Path path) {
    final Color mainColor = glowIntensity > 0.5 
        ? Color.lerp(lineColor, Colors.white, glowIntensity)!
        : lineColor;
    
    final linePaint = Paint()
      ..color = mainColor
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(path, linePaint);
  }

  void _drawTouchEffect(Canvas canvas, Size size, double minPrice, double maxPrice, Path fullPath) {
    final priceRange = maxPrice - minPrice;
    if (priceRange == 0) return;
    
    final double touchX = (touchIndex! / (prices.length - 1)) * size.width;
    final double normalizedPrice = (prices[touchIndex!].priceLeiKwh - minPrice) / priceRange;
    final double touchY = size.height - (normalizedPrice * size.height);
    
    // 1. Draw dimmed full line (darker)
    final dimmedPaint = Paint()
      ..color = lineColor.withOpacity(0.3)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(fullPath, dimmedPaint);
    
    // 2. Draw bright section around touch point with glow
    // Dynamic highlight radius based on data points:
    // - 24 points (1 day): radius = 1 (3 points total)
    // - 168 points (1 week): radius = 1 (3 points total)  
    // - 720+ points (1 month+): radius = 1 (3 points total)
    final int highlightRadius;
    if (prices.length <= 24) {
      highlightRadius = 1; // 1 day: very small highlight
    } else if (prices.length <= 168) {
      highlightRadius = 1; // 1 week: small highlight
    } else {
      highlightRadius = 1; // 1 month+: minimal highlight
    }
    final int startIdx = (touchIndex! - highlightRadius).clamp(0, prices.length - 1);
    final int endIdx = (touchIndex! + highlightRadius).clamp(0, prices.length - 1);
    
    // Build highlight path
    final highlightPath = Path();
    for (int i = startIdx; i <= endIdx; i++) {
      final double x = (i / (prices.length - 1)) * size.width;
      final double np = (prices[i].priceLeiKwh - minPrice) / priceRange;
      final double y = size.height - (np * size.height);
      
      if (i == startIdx) {
        highlightPath.moveTo(x, y);
      } else {
        highlightPath.lineTo(x, y);
      }
    }
    
    // Outer glow for highlight
    final highlightGlowOuter = Paint()
      ..color = lineColor.withOpacity(0.3)
      ..strokeWidth = 14
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    canvas.drawPath(highlightPath, highlightGlowOuter);
    
    // Inner glow for highlight
    final highlightGlowInner = Paint()
      ..color = lineColor.withOpacity(0.5)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
    canvas.drawPath(highlightPath, highlightGlowInner);
    
    // Bright white line for highlight section
    final highlightLinePaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    canvas.drawPath(highlightPath, highlightLinePaint);
    
    // 3. Draw vertical indicator line
    final verticalLinePaint = Paint()
      ..color = Colors.white.withOpacity(0.6)
      ..strokeWidth = 1;
    canvas.drawLine(Offset(touchX, 0), Offset(touchX, size.height), verticalLinePaint);
    
    // 4. Draw touch point circle with glow
    // Outer glow
    final pointGlowPaint = Paint()
      ..color = lineColor.withOpacity(0.4)
      ..style = PaintingStyle.fill
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    canvas.drawCircle(Offset(touchX, touchY), 12, pointGlowPaint);
    
    // Inner circle
    final pointPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(touchX, touchY), 5, pointPaint);
  }

  void _drawReferenceLines(Canvas canvas, Size size, double paddedMin, double paddedMax, double actualMin, double actualMax) {
    final priceRange = paddedMax - paddedMin;
    if (priceRange == 0) return;
    
    final dashPaint = Paint()
      ..color = Colors.white.withOpacity(0.12)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    
    final maxY = size.height - ((actualMax - paddedMin) / priceRange * size.height);
    _drawDottedLine(canvas, Offset(0, maxY), Offset(size.width, maxY), dashPaint);
    
    final minY = size.height - ((actualMin - paddedMin) / priceRange * size.height);
    _drawDottedLine(canvas, Offset(0, minY), Offset(size.width, minY), dashPaint);
  }

  void _drawDottedLine(Canvas canvas, Offset start, Offset end, Paint paint) {
    const double dashWidth = 4;
    const double dashSpace = 4;
    
    final double distance = (end - start).distance;
    if (distance == 0) return;
    
    final Offset direction = (end - start) / distance;
    
    double currentDistance = 0;
    while (currentDistance < distance) {
      final startPoint = start + direction * currentDistance;
      final endDistance = (currentDistance + dashWidth).clamp(0.0, distance);
      final endPoint = start + direction * endDistance;
      canvas.drawLine(startPoint, endPoint, paint);
      currentDistance += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant ChartPainter oldDelegate) {
    return oldDelegate.animationProgress != animationProgress ||
           oldDelegate.glowIntensity != glowIntensity ||
           oldDelegate.touchIndex != touchIndex ||
           oldDelegate.prices != prices ||
           oldDelegate.lineColor != lineColor;
  }
}
