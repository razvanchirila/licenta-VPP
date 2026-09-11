import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math' as math;

class HouseSection extends StatefulWidget {
  final String houseImage;
  /// Puterea bateriei (kW): pozitiv = încărcare, negativ = descărcare
  final double batteryPower;
  final int powerwallPercentage;
  /// Puterea grid (kW): pozitiv = import, negativ = export
  final double gridPower;
  final double solarPower;
  final double homePower;

  const HouseSection({
    super.key,
    this.houseImage = 'assets/casa_noapte_lumini.png',
    this.batteryPower = 4.1,
    this.powerwallPercentage = 98,
    this.gridPower = 0.0,
    this.solarPower = 3.1,
    this.homePower = 3.0,
  });

  @override
  State<HouseSection> createState() => _HouseSectionState();
}

class _HouseSectionState extends State<HouseSection>
    with TickerProviderStateMixin {
  late AnimationController _flowController;

  // Dimensiuni imagine originală
  static const double originalWidth = 1073.0;
  static const double originalHeight = 715.0;

  // Coordonate pe imaginea originală 1073x715
  static const Offset solarTargetPx = Offset(498, 144);   // panouri solare
  static const Offset homeTargetPx = Offset(940, 542);    // punct home
  static const Offset gridTargetPx = Offset(960, 687);    // punct grid
  static const Offset batteryTopPx = Offset(624, 564);    // început baterie (sus)
  static const Offset batteryBottomPx = Offset(628, 705); // final baterie (jos)
  static const Offset batteryLinePx = Offset(682, 699);   // punct pentru linia spre label

  @override
  void initState() {
    super.initState();
    _flowController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat();
  }

  @override
  void dispose() {
    _flowController.dispose();
    super.dispose();
  }

  // Convertește coordonate din imagine originală în coordonate pentru container
  Offset _convertPoint(Offset origPoint, Size imageSize, Offset imageOffset) {
    final scaleX = imageSize.width / originalWidth;
    final scaleY = imageSize.height / originalHeight;
    return Offset(
      imageOffset.dx + origPoint.dx * scaleX,
      imageOffset.dy + origPoint.dy * scaleY,
    );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final availableWidth = constraints.maxWidth;
        final availableHeight = constraints.maxHeight;
        
        // Calculăm dimensiunea imaginii (păstrând aspect ratio)
        const aspectRatio = originalWidth / originalHeight;
        double imageWidth, imageHeight;
        
        // Calculăm să încapă imaginea în ~75% din înălțime
        final maxImageHeight = availableHeight * 0.72;
        final maxImageWidth = availableWidth * 0.95;
        
        if (maxImageWidth / maxImageHeight > aspectRatio) {
          imageHeight = maxImageHeight;
          imageWidth = imageHeight * aspectRatio;
        } else {
          imageWidth = maxImageWidth;
          imageHeight = imageWidth / aspectRatio;
        }
        
        // Centrăm imaginea
        final imageOffsetX = (availableWidth - imageWidth) / 2;
        final imageOffsetY = (availableHeight - imageHeight) / 2 - 20;
        final imageOffset = Offset(imageOffsetX, imageOffsetY);
        final imageSize = Size(imageWidth, imageHeight);
        
        // Convertim punctele țintă
        final solarTarget = _convertPoint(solarTargetPx, imageSize, imageOffset);
        final homeTarget = _convertPoint(homeTargetPx, imageSize, imageOffset);
        final gridTarget = _convertPoint(gridTargetPx, imageSize, imageOffset);
        final batteryTop = _convertPoint(batteryTopPx, imageSize, imageOffset);
        final batteryBottom = _convertPoint(batteryBottomPx, imageSize, imageOffset);
        final batteryLineStart = _convertPoint(batteryLinePx, imageSize, imageOffset);
        
        // Poziții pentru label-uri
        // SOLAR și HOME - la același nivel (12% din înălțime)
        final topLabelsY = availableHeight * 0.12; // 12% de sus pentru text
        
        // BATTERY - sub bara de baterie (+ 10% mai jos)
        final batteryLabelY = batteryLineStart.dy + 20 + availableHeight * 0.10;
        
        // GRID - sub punctul grid (+ 10% mai jos)
        final gridLabelY = gridTarget.dy + 20 + availableHeight * 0.10;

        return Stack(
          clipBehavior: Clip.none,
          children: [
            // === Liniile statice albe (fără bara de baterie) ===
            CustomPaint(
              size: Size(availableWidth, availableHeight),
              painter: _StaticLinesPainter(
                // Solar: de la label în jos spre panouri
                solarStart: Offset(solarTarget.dx, topLabelsY + 40),
                solarEnd: solarTarget,
                // Home: de la label în jos spre casă
                homeStart: Offset(homeTarget.dx, topLabelsY + 40),
                homeEnd: homeTarget,
                // Grid: de la punct grid în jos spre label (lung)
                gridStart: gridTarget,
                gridEnd: Offset(gridTarget.dx, gridLabelY - 5),
                // Baterie: de la punctul 682,699 în jos spre label
                batteryStart: batteryLineStart,
                batteryEnd: Offset(batteryLineStart.dx, batteryLabelY - 5),
                // alte date
                batteryTop: batteryTop,
                batteryBottom: batteryBottom,
                batteryPercentage: widget.powerwallPercentage,
                solarPower: widget.solarPower,
                homePower: widget.homePower,
                gridPower: widget.gridPower,
                batteryPower: widget.batteryPower,
                drawBattery: false,
              ),
            ),
            
            // === GLOW/UMBRA SUB CASĂ - efect premium cu tonuri de gri ===
            Positioned(
              left: imageOffsetX - imageWidth * 0.2,
              top: imageOffsetY + imageHeight * 0.85,
              child: Container(
                width: imageWidth * 1.4,
                height: imageHeight * 0.35,
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment.topCenter,
                    radius: 0.8,
                    colors: [
                      const Color(0xFF2A2A2A).withOpacity(0.25), // Gri deschis în centru
                      const Color(0xFF1F1F1F).withOpacity(0.15), // Gri mediu
                      const Color(0xFF151515).withOpacity(0.08), // Gri închis
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.3, 0.6, 1.0],
                  ),
                ),
              ),
            ),
            
            // === CASA (imaginea) ===
            Positioned(
              left: imageOffsetX,
              top: imageOffsetY,
              child: SizedBox(
                width: imageWidth,
                height: imageHeight,
                child: Stack(
                  children: [
                    Image.asset(
                      widget.houseImage,
                      width: imageWidth,
                      height: imageHeight,
                      fit: BoxFit.contain,
                    ),
                    // Animația fluxului energie
                    Positioned.fill(
                      child: CustomPaint(
                        painter: _EnergyFlowPainter(
                          animation: _flowController,
                          solarPower: widget.solarPower,
                          homePower: widget.homePower,
                          batteryPower: widget.batteryPower,
                          gridPower: widget.gridPower,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            
            // === BARA DE BATERIE (DEASUPRA CASEI) ===
            CustomPaint(
              size: Size(availableWidth, availableHeight),
              painter: _BatteryBarPainter(
                batteryTop: batteryTop,
                batteryBottom: batteryBottom,
                batteryPercentage: widget.powerwallPercentage,
              ),
            ),
            
            // === LABEL SOLAR (sus, la același nivel cu HOME) ===
            Positioned(
              left: solarTarget.dx - 35,
              top: topLabelsY,
              child: _TopIndicator(
                value: widget.solarPower,
                label: 'SOLAR',
                valueColor: const Color(0xFFFBBF24),
              ),
            ),
            
            // === LABEL HOME (sus, la același nivel cu SOLAR) ===
            Positioned(
              left: homeTarget.dx - 35,
              top: topLabelsY,
              child: _TopIndicator(
                value: widget.homePower,
                label: 'HOME',
                valueColor: Colors.white,
              ),
            ),
            
            // === LABEL BATERIE (sub punctul 682,699) ===
            Positioned(
              left: batteryLineStart.dx - 50,
              top: batteryLabelY,
              child: _BatteryIndicator(
                power: widget.batteryPower,
                percentage: widget.powerwallPercentage,
              ),
            ),
            
            // === LABEL GRID (sub linia grid) ===
            Positioned(
              left: gridTarget.dx - 30,
              top: gridLabelY,
              child: _BottomIndicator(
                value: widget.gridPower,
                label: 'GRID',
              ),
            ),
          ],
        );
      },
    );
  }
}

// Painter pentru liniile statice albe (fără bara de baterie)
class _StaticLinesPainter extends CustomPainter {
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

  _StaticLinesPainter({
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
      ..color = Colors.white.withOpacity(0.7)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    
    final inactivePaint = Paint()
      ..color = Colors.white.withOpacity(0.35)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Linie SOLAR (de la label în jos spre panouri) - mereu vizibilă
    final solarActive = solarPower > 0.1;
    canvas.drawLine(solarStart, solarEnd, solarActive ? activePaint : inactivePaint);

    // Linie HOME (de la label în jos spre casă) - mereu vizibilă
    final homeActive = homePower > 0.1;
    canvas.drawLine(homeStart, homeEnd, homeActive ? activePaint : inactivePaint);

    // Linie GRID (de la punct în jos spre label) - mereu vizibilă
    final gridActive = gridPower.abs() > 0.01;
    canvas.drawLine(gridStart, gridEnd, gridActive ? activePaint : inactivePaint);

    // Linie BATERIE (de la bara verde în jos spre label) - mereu vizibilă
    final batteryActive = batteryPower.abs() > 0.1;
    canvas.drawLine(batteryStart, batteryEnd, batteryActive ? activePaint : inactivePaint);
  }

  @override
  bool shouldRepaint(covariant _StaticLinesPainter oldDelegate) {
    return oldDelegate.solarPower != solarPower ||
           oldDelegate.homePower != homePower ||
           oldDelegate.gridPower != gridPower ||
           oldDelegate.batteryPower != batteryPower;
  }
}

// Painter separat pentru bara de baterie (desenată DEASUPRA casei)
class _BatteryBarPainter extends CustomPainter {
  final Offset batteryTop;
  final Offset batteryBottom;
  final int batteryPercentage;

  _BatteryBarPainter({
    required this.batteryTop,
    required this.batteryBottom,
    required this.batteryPercentage,
  });

  Color _getBatteryColor(int percentage) {
    if (percentage > 60) return const Color(0xFF22C55E); // Verde
    if (percentage > 30) return const Color(0xFFFBBF24); // Galben
    return const Color(0xFFEF4444); // Roșu
  }

  @override
  void paint(Canvas canvas, Size size) {
    // Background-ul (gri/transparent) - toată bara
    final batteryBgPaint = Paint()
      ..color = Colors.white.withOpacity(0.15)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    
    canvas.drawLine(batteryTop, batteryBottom, batteryBgPaint);

    // Bara colorată în funcție de procentaj (de jos în sus)
    if (batteryPercentage > 0) {
      final batteryHeight = batteryBottom.dy - batteryTop.dy;
      final filledHeight = batteryHeight * (batteryPercentage / 100);
      
      // Punctul de sus al părții pline
      final filledTopY = batteryBottom.dy - filledHeight;
      // Interpolăm X-ul pentru linia ușor înclinată
      final tFactor = filledHeight / batteryHeight;
      final filledTopX = batteryBottom.dx + (batteryTop.dx - batteryBottom.dx) * tFactor;
      final filledTop = Offset(filledTopX, filledTopY);
      
      // Glow effect
      final glowPaint = Paint()
        ..color = _getBatteryColor(batteryPercentage).withOpacity(0.5)
        ..strokeWidth = 14
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
      
      final batteryFillPaint = Paint()
        ..color = _getBatteryColor(batteryPercentage)
        ..strokeWidth = 8
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;
      
      canvas.drawLine(filledTop, batteryBottom, glowPaint);
      canvas.drawLine(filledTop, batteryBottom, batteryFillPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _BatteryBarPainter oldDelegate) {
    return oldDelegate.batteryPercentage != batteryPercentage;
  }
}

// Indicator simplu pentru SOLAR și HOME (sus)
class _TopIndicator extends StatelessWidget {
  final double value;
  final String label;
  final Color valueColor;

  const _TopIndicator({
    required this.value,
    required this.label,
    required this.valueColor,
  });

  String _getLocalizedLabel(String label) {
    switch (label) {
      case 'SOLAR': return 'SOLAR';
      case 'HOME': return 'CONSUM';
      default: return label;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '${value.toStringAsFixed(1)} kW',
          style: GoogleFonts.inter(
            color: valueColor,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          _getLocalizedLabel(label),
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

// Indicator pentru GRID (jos)
class _BottomIndicator extends StatelessWidget {
  final double value;
  final String label;

  const _BottomIndicator({
    required this.value,
    required this.label,
  });

  String _getLocalizedLabel(String label) {
    switch (label) {
      case 'GRID': return 'REȚEA';
      default: return label;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isActive = value.abs() > 0.05;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '${value.abs().toStringAsFixed(1)} kW',
          style: GoogleFonts.inter(
            color: isActive ? Colors.white : Colors.white.withOpacity(0.5),
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          _getLocalizedLabel(label),
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

// Indicator pentru baterie cu procentaj și label BATERIE
// power: pozitiv = încărcare, negativ = descărcare
class _BatteryIndicator extends StatelessWidget {
  final double power;
  final int percentage;

  const _BatteryIndicator({
    required this.power,
    required this.percentage,
  });

  Color _getBatteryColor(int percentage) {
    if (percentage > 60) return const Color(0xFF22C55E);
    if (percentage > 30) return const Color(0xFFFBBF24);
    return const Color(0xFFEF4444);
  }

  @override
  Widget build(BuildContext context) {
    // Afișăm valoarea absolută a puterii
    final displayPower = power.abs();
    
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '${displayPower.toStringAsFixed(1)} kW',
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              ' · ',
              style: GoogleFonts.inter(
                color: Colors.white.withOpacity(0.5),
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '$percentage%',
              style: GoogleFonts.inter(
                color: _getBatteryColor(percentage),
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          'BATERIE',
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.5),
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

// Painter pentru liniile de flux energie animate - STIL TESLA
// Logica bazată pe semn și culori:
// - Solar → Invertor: galben (producție)
// - Invertor → Casă: verde (consum)
// - batteryPower > 0.1 → încărcare (Invertor → Baterie, verde - energie care vine)
// - batteryPower < -0.1 → descărcare (Baterie → Invertor, roșu - energie care pleacă)
// - gridPower > 0.05 → import (Grid → Invertor, roșu - cumpărăm)
// - gridPower < -0.05 → export (Invertor → Grid, verde - vindem)
class _EnergyFlowPainter extends CustomPainter {
  final Animation<double> animation;
  final double solarPower;
  final double homePower;
  /// Puterea bateriei: pozitiv = încărcare, negativ = descărcare
  final double batteryPower;
  /// Puterea grid: pozitiv = import, negativ = export
  final double gridPower;

  // Thresholds pentru afișare flux
  static const double _minSolarPower = 0.1;
  static const double _minHomePower = 0.1;
  static const double _minBatteryPower = 0.1;
  static const double _minGridPower = 0.05;

  _EnergyFlowPainter({
    required this.animation,
    required this.solarPower,
    required this.homePower,
    required this.batteryPower,
    required this.gridPower,
  }) : super(repaint: animation);

  // Dimensiuni imagine originală
  static const double originalWidth = 1073.0;
  static const double originalHeight = 715.0;
  static const double aspectRatio = originalWidth / originalHeight; // ~1.5

  // Coordonate în PIXELI din imaginea originală 1073x715
  // Traseu Panouri Solare -> Invertor (galben)
  // Path definit de la panouri (sus) spre invertor (jos)
  static const List<List<double>> solarToInverterPathPx = [
    [814, 394], // Start - la panouri solare (sus)
    [839, 426],
    [824, 459],
    [824, 507], // End - la invertor (jos)
  ];

  // Traseu Invertor -> Baterie (albastru - charging)
  static const List<List<double>> inverterToBatteryPathPx = [
    [795, 605], // Start de la invertor
    [758, 610],
    [711, 616], // End la baterie
  ];

  // Traseu Baterie -> Invertor (verde - discharging)
  static const List<List<double>> batteryToInverterPathPx = [
    [711, 616], // Start de la baterie
    [758, 610],
    [795, 605], // End la invertor
  ];

  // Traseu Invertor -> Casa (consum)
  static const List<List<double>> inverterToHomePathPx = [
    [857, 552], // Start de la invertor
    [887, 549],
    [928, 543], // End la casa
  ];

  // Traseu Invertor -> Grid (export - vând surplus)
  static const List<List<double>> inverterToGridPathPx = [
    [824, 609], // Start de la invertor
    [822, 654],
    [824, 664],
    [829, 669],
    [835, 671],
    [866, 677],
    [956, 690], // End la grid
  ];

  // Traseu Grid -> Invertor (import - cumpăr)
  static const List<List<double>> gridToInverterPathPx = [
    [956, 690], // Start de la grid
    [866, 677],
    [835, 671],
    [829, 669],
    [824, 664],
    [822, 654],
    [824, 609], // End la invertor
  ];

  // Convertește coordonate din imagine originală în coordonate pentru container
  Offset _convertPoint(double origX, double origY, Size containerSize) {
    // Calculează dimensiunea reală a imaginii în container (BoxFit.contain)
    double imageWidth, imageHeight;
    double offsetX = 0, offsetY = 0;

    if (containerSize.width / containerSize.height > aspectRatio) {
      // Container mai lat - imaginea e limitată de înălțime
      imageHeight = containerSize.height;
      imageWidth = imageHeight * aspectRatio;
      offsetX = (containerSize.width - imageWidth) / 2;
    } else {
      // Container mai înalt - imaginea e limitată de lățime
      imageWidth = containerSize.width;
      imageHeight = imageWidth / aspectRatio;
      offsetY = (containerSize.height - imageHeight) / 2;
    }

    // Scalează coordonatele
    final scaleX = imageWidth / originalWidth;
    final scaleY = imageHeight / originalHeight;

    return Offset(
      offsetX + origX * scaleX,
      offsetY + origY * scaleY,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    // Solar -> Invertor (dacă produce)
    // Energia curge de la panouri (sus) spre invertor (jos)
    if (solarPower > _minSolarPower) {
      _drawFlowPathPx(
        canvas,
        size,
        solarToInverterPathPx,
        const Color(0xFFFBBF24), // Galben solar
        animation.value,
        solarPower,
        reverseAnimation: true, // Energia curge în direcția path-ului
      );
    }

    // Baterie - logica bazată pe semn:
    // batteryPower > 0.1 → încărcare (Invertor → Baterie, verde - energie care vine)
    // batteryPower < -0.1 → descărcare (Baterie → Invertor, roșu - energie care pleacă)
    if (batteryPower > _minBatteryPower) {
      // Încărcare - flux de la invertor spre baterie (verde - ca la export)
      _drawFlowPathPx(
        canvas,
        size,
        inverterToBatteryPathPx,
        const Color(0xFF10B981), // Verde - încărcare (energie care vine în baterie)
        animation.value,
        batteryPower,
        reverseAnimation: true,
      );
    } else if (batteryPower < -_minBatteryPower) {
      // Descărcare - flux de la baterie spre invertor (roșu - ca la import)
      _drawFlowPathPx(
        canvas,
        size,
        batteryToInverterPathPx,
        const Color(0xFFEF4444), // Roșu - descărcare (energie care pleacă din baterie)
        animation.value,
        batteryPower.abs(),
        reverseAnimation: true,
      );
    }

    // Invertor -> Casa (consum)
    // Energia curge de la invertor spre casă
    if (homePower > _minHomePower) {
      _drawFlowPathPx(
        canvas,
        size,
        inverterToHomePathPx,
        const Color(0xFF22C55E), // Verde consum
        animation.value,
        homePower,
        reverseAnimation: true, // Energia curge în direcția path-ului
      );
    }

    // Grid - logica bazată pe semn:
    // gridPower > 0.05 → import (Grid → Invertor, roșu)
    // gridPower < -0.05 → export (Invertor → Grid, verde)
    if (gridPower > _minGridPower) {
      // Import din grid - flux de la grid spre invertor (roșu)
      _drawFlowPathPx(
        canvas,
        size,
        gridToInverterPathPx,
        const Color(0xFFEF4444), // Roșu - import din rețea
        animation.value,
        gridPower,
        reverseAnimation: true, // Energia curge în direcția path-ului
      );
    } else if (gridPower < -_minGridPower) {
      // Export în grid - flux de la invertor spre grid (verde)
      _drawFlowPathPx(
        canvas,
        size,
        inverterToGridPathPx,
        const Color(0xFF10B981), // Verde - export în rețea
        animation.value,
        gridPower.abs(),
        reverseAnimation: true, // Energia curge în direcția path-ului
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

    // Convertește pixelii originali în coordonate pentru container
    final points = pathPointsPx.map((p) => _convertPoint(p[0], p[1], size)).toList();

    // Creează path-ul
    final path = Path();
    path.moveTo(points[0].dx, points[0].dy);
    for (int i = 1; i < points.length; i++) {
      path.lineTo(points[i].dx, points[i].dy);
    }

    // Calculează lungimea totală
    final pathMetrics = path.computeMetrics().first;
    final pathLength = pathMetrics.length;

    // === 1. LINIE DE BAZĂ (glow subtil) ===
    final glowPaint = Paint()
      ..color = color.withOpacity(0.1)
      ..strokeWidth = 8
      ..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
    canvas.drawPath(path, glowPaint);

    // === 2. LINIE STATICĂ SUBTILĂ ===
    final basePaint = Paint()
      ..color = color.withOpacity(0.2)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, basePaint);

    // === 3. DASHED LINE CU OFFSET ANIMAT ===
    // Folosim pattern length ca bază pentru animație smooth (fără salt la reset)
    const dashLength = 12.0;
    const gapLength = 20.0;
    final patternLength = dashLength + gapLength;
    
    // Offset-ul se mișcă exact cu lungimea unui pattern pe durata animației
    // Inversăm direcția dacă reverseAnimation e true
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

    // Normalizează offset-ul
    double currentOffset = dashOffset % patternLength;
    double distance = -currentOffset;

    while (distance < pathLength) {
      // Start of dash
      final double dashStart = math.max(0.0, distance);
      // End of dash
      final double dashEnd = math.min(pathLength, distance + dashLength);

      if (dashStart < pathLength && dashEnd > 0 && dashEnd > dashStart) {
        final extractedPath = pathMetrics.extractPath(dashStart, dashEnd);
        
        // Adaugă glow pe fiecare dash
        final glowPaint = Paint()
          ..color = paint.color.withOpacity(0.4)
          ..strokeWidth = paint.strokeWidth + 2
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
        canvas.drawPath(extractedPath, glowPaint);
        
        // Dash-ul principal
        canvas.drawPath(extractedPath, paint);
      }

      distance += patternLength;
    }
  }

  @override
  bool shouldRepaint(covariant _EnergyFlowPainter oldDelegate) => true;
}