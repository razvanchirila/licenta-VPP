import 'package:flutter/material.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/widgets/smart_stack/page_indicator.dart';
import 'package:flutter_interface/widgets/smart_stack/pages/temperature_page.dart';
import 'package:flutter_interface/widgets/smart_stack/pages/lighting_page.dart';
import 'package:flutter_interface/widgets/smart_stack/pages/battery_page.dart';
import 'package:flutter_interface/core/theme.dart';

class SmartStack extends StatefulWidget {
  static const double height = 100;

  final Battery? battery;
  final double batteryPercent;
  final double currentConsumptionKw;
  final double? pricePerKwh;
  final bool isPriceRising;
  final VoidCallback? onPriceTap;

  const SmartStack({
    super.key,
    required this.battery,
    required this.batteryPercent,
    required this.currentConsumptionKw,
    required this.pricePerKwh,
    this.isPriceRising = false,
    this.onPriceTap,
  });

  @override
  State<SmartStack> createState() => _SmartStackState();
}

class _SmartStackState extends State<SmartStack> {
  late PageController _pageController;
  int _currentPage = 0;

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
    return Semantics(
      container: true,
      identifier: 'home-smart-stack',
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Container(
            width: double.infinity,
            height: SmartStack.height,
            decoration: BoxDecoration(
              color: AppColors.surfaceAlt.withValues(alpha: 0.75),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.1),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: PageView(
                    controller: _pageController,
                    scrollDirection: Axis.vertical,
                    onPageChanged: _onPageChanged,
                    children: [
                      const TemperaturePage(),
                      const LightingPage(),
                      BatteryPage(
                        battery: widget.battery,
                        batteryPercent: widget.batteryPercent,
                        currentConsumptionKw: widget.currentConsumptionKw,
                        pricePerKwh: widget.pricePerKwh,
                        isPriceRising: widget.isPriceRising,
                        onPriceTap: widget.onPriceTap,
                      ),
                    ],
                  ),
                ),
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
