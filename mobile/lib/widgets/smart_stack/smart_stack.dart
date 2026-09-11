import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_interface/widgets/smart_stack/page_indicator.dart';
import 'package:flutter_interface/widgets/smart_stack/pages/temperature_page.dart';
import 'package:flutter_interface/widgets/smart_stack/pages/lighting_page.dart';
import 'package:flutter_interface/widgets/smart_stack/pages/battery_page.dart';

/// Smart Stack widget - replaces DevicesDock
/// Vertical swipeable container with multiple card pages
class SmartStack extends StatefulWidget {
  final double batteryPercent;
  final double batteryCapacityKwh;
  final double pricePerKwh;
  final bool isPriceRising;
  final VoidCallback? onPriceTap;

  const SmartStack({
    super.key,
    this.batteryPercent = 74,
    this.batteryCapacityKwh = 13.5,
    this.pricePerKwh = 0.85,
    this.isPriceRising = true,
    this.onPriceTap,
  });

  @override
  State<SmartStack> createState() => _SmartStackState();
}

class _SmartStackState extends State<SmartStack> {
  late PageController _pageController;
  int _currentPage = 0;
  
  // Number of pages in the stack
  static const int _pageCount = 3;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(initialPage: 0);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onPageChanged(int page) {
    setState(() {
      _currentPage = page;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
          child: Container(
            width: double.infinity,
            height: 100,
          decoration: BoxDecoration(
            color: const Color(0xFF1A1A1A).withOpacity(0.75),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              // Main content - PageView
              Expanded(
                child: PageView(
                  controller: _pageController,
                  scrollDirection: Axis.vertical,
                  onPageChanged: _onPageChanged,
                  children: [
                    // Page 1: Temperature cards
                    const TemperaturePage(),
                    // Page 2: Lighting control
                    const LightingPage(),
                    // Page 3: Battery autonomy + Price indicator
                    BatteryPage(
                      batteryPercent: widget.batteryPercent,
                      batteryCapacityKwh: widget.batteryCapacityKwh,
                      pricePerKwh: widget.pricePerKwh,
                      isPriceRising: widget.isPriceRising,
                      onPriceTap: widget.onPriceTap,
                    ),
                  ],
                ),
              ),
              
              // Page indicator (dots) on the right
              Padding(
                padding: const EdgeInsets.only(right: 12),
                child: PageIndicator(
                  pageCount: _pageCount,
                  currentPage: _currentPage,
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
