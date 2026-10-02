import 'package:flutter/material.dart';
import 'package:flutter_interface/widgets/house/battery_bar_painter.dart';
import 'package:flutter_interface/widgets/house/energy_flow_painter.dart';
import 'package:flutter_interface/widgets/house/flow_indicators.dart';
import 'package:flutter_interface/widgets/house/static_lines_painter.dart';
import 'package:flutter_interface/core/theme.dart';

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

class _HouseSectionState extends State<HouseSection> with SingleTickerProviderStateMixin {
  late final AnimationController _flowController;
  late final AppLifecycleListener _lifecycle;
  late List<FlowTrack> _tracks;
  bool _appVisible = true;

  static const double originalWidth = 1073.0;
  static const double originalHeight = 715.0;

  // Coordonate pe imaginea originală 1073x715
  static const Offset solarTargetPx = Offset(498, 144);
  static const Offset homeTargetPx = Offset(940, 542);
  static const Offset gridTargetPx = Offset(960, 687);
  static const Offset batteryTopPx = Offset(624, 564);
  static const Offset batteryBottomPx = Offset(628, 705);
  static const Offset batteryLinePx = Offset(682, 699);

  @override
  void initState() {
    super.initState();
    _flowController = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    );
    _lifecycle = AppLifecycleListener(onStateChange: (state) {
      _appVisible = state == AppLifecycleState.resumed || state == AppLifecycleState.inactive;
      _syncTicker();
    });
    _tracks = _flowTracks();
    _syncTicker();
  }

  @override
  void didUpdateWidget(HouseSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    _tracks = _flowTracks();
    _syncTicker();
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    _flowController.dispose();
    super.dispose();
  }

  List<FlowTrack> _flowTracks() => energyFlowTracks(
        solarPower: widget.solarPower,
        homePower: widget.homePower,
        batteryPower: widget.batteryPower,
        gridPower: widget.gridPower,
      );

  /// The dashes only move while something flows and the app is on screen.
  void _syncTicker() {
    final run = _appVisible && _tracks.isNotEmpty;
    if (run && !_flowController.isAnimating) {
      _flowController.repeat();
    } else if (!run && _flowController.isAnimating) {
      _flowController.stop();
    }
  }

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

        const aspectRatio = originalWidth / originalHeight;
        double imageWidth, imageHeight;

        final maxImageHeight = availableHeight * 0.72;
        final maxImageWidth = availableWidth * 0.95;

        if (maxImageWidth / maxImageHeight > aspectRatio) {
          imageHeight = maxImageHeight;
          imageWidth = imageHeight * aspectRatio;
        } else {
          imageWidth = maxImageWidth;
          imageHeight = imageWidth / aspectRatio;
        }

        final imageOffsetX = (availableWidth - imageWidth) / 2;
        final imageOffsetY = (availableHeight - imageHeight) / 2 - 20;
        final imageOffset = Offset(imageOffsetX, imageOffsetY);
        final imageSize = Size(imageWidth, imageHeight);

        final solarTarget = _convertPoint(solarTargetPx, imageSize, imageOffset);
        final homeTarget = _convertPoint(homeTargetPx, imageSize, imageOffset);
        final gridTarget = _convertPoint(gridTargetPx, imageSize, imageOffset);
        final batteryTop = _convertPoint(batteryTopPx, imageSize, imageOffset);
        final batteryBottom = _convertPoint(batteryBottomPx, imageSize, imageOffset);
        final batteryLineStart = _convertPoint(batteryLinePx, imageSize, imageOffset);

        final topLabelsY = availableHeight * 0.12;

        final batteryLabelY = batteryLineStart.dy + 20 + availableHeight * 0.10;

        final gridLabelY = gridTarget.dy + 20 + availableHeight * 0.10;

        return RepaintBoundary(
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              CustomPaint(
                size: Size(availableWidth, availableHeight),
                painter: StaticLinesPainter(
                  solarStart: Offset(solarTarget.dx, topLabelsY + 40),
                  solarEnd: solarTarget,
                  homeStart: Offset(homeTarget.dx, topLabelsY + 40),
                  homeEnd: homeTarget,
                  gridStart: gridTarget,
                  gridEnd: Offset(gridTarget.dx, gridLabelY - 5),
                  batteryStart: batteryLineStart,
                  batteryEnd: Offset(batteryLineStart.dx, batteryLabelY - 5),
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
                        const Color(0xFF2A2A2A).withValues(alpha: 0.25),
                        const Color(0xFF1F1F1F).withValues(alpha: 0.15),
                        const Color(0xFF151515).withValues(alpha: 0.08),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.3, 0.6, 1.0],
                    ),
                  ),
                ),
              ),
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
                        gaplessPlayback: true,
                      ),
                      Positioned.fill(
                        child: CustomPaint(painter: EnergyFlowLinesPainter(tracks: _tracks)),
                      ),
                      Positioned.fill(
                        child: RepaintBoundary(
                          child: CustomPaint(
                            painter: EnergyFlowPainter(animation: _flowController, tracks: _tracks),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              CustomPaint(
                size: Size(availableWidth, availableHeight),
                painter: BatteryBarPainter(
                  batteryTop: batteryTop,
                  batteryBottom: batteryBottom,
                  batteryPercentage: widget.powerwallPercentage,
                ),
              ),
              Positioned(
                left: solarTarget.dx - 35,
                top: topLabelsY,
                child: TopIndicator(
                  value: widget.solarPower,
                  label: 'SOLAR',
                  valueColor: AppColors.amber,
                  semanticsId: 'home-solar',
                ),
              ),
              Positioned(
                left: homeTarget.dx - 35,
                top: topLabelsY,
                child: TopIndicator(
                  value: widget.homePower,
                  label: 'HOME',
                  valueColor: Colors.white,
                  semanticsId: 'home-load',
                ),
              ),
              Positioned(
                left: batteryLineStart.dx - 50,
                top: batteryLabelY,
                child: BatteryIndicator(
                  power: widget.batteryPower,
                  percentage: widget.powerwallPercentage,
                ),
              ),
              Positioned(
                left: gridTarget.dx - 30,
                top: gridLabelY,
                child: BottomIndicator(
                  value: widget.gridPower,
                  label: 'GRID',
                  semanticsId: 'home-grid',
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
