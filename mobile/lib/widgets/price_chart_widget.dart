import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/widgets/chart_painter.dart';
import 'package:flutter_interface/widgets/error_state.dart';
import 'package:flutter_interface/widgets/trading/price_header.dart';
import 'package:flutter_interface/widgets/trading/price_stats_section.dart';

class PriceChartWidget extends StatefulWidget {
  final SimPrices? prices;
  final bool isLoading;
  final String? error;
  final PriceSeries series;
  final ValueChanged<PriceSeries> onSeriesChanged;
  final VoidCallback? onRefresh;

  const PriceChartWidget({
    super.key,
    required this.prices,
    this.isLoading = false,
    this.error,
    required this.series,
    required this.onSeriesChanged,
    this.onRefresh,
  });

  @override
  State<PriceChartWidget> createState() => _PriceChartWidgetState();
}

class _PriceChartWidgetState extends State<PriceChartWidget> with TickerProviderStateMixin {
  late final AnimationController _lineController;
  late final AnimationController _glowController;
  late final Animation<double> _lineAnimation;
  late final Animation<double> _glowAnimation;
  int? _touchIndex;
  bool _isTouching = false;

  List<double> get _values => widget.prices?.prices.map((p) => p.value(widget.series)).toList() ?? const [];

  @override
  void initState() {
    super.initState();
    _lineController = AnimationController(duration: const Duration(milliseconds: 1200), vsync: this);
    _lineAnimation = CurvedAnimation(parent: _lineController, curve: Curves.easeOutCubic);
    _glowController = AnimationController(duration: const Duration(milliseconds: 500), vsync: this);
    _glowAnimation = CurvedAnimation(parent: _glowController, curve: Curves.easeOut);
    _lineController.addStatusListener((status) {
      if (status == AnimationStatus.completed) _glowController.forward();
    });
    if (_values.isNotEmpty) _lineController.forward();
  }

  @override
  void didUpdateWidget(PriceChartWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.series != widget.series || oldWidget.prices != widget.prices) {
      _lineController.reset();
      _glowController.reset();
      if (_values.isNotEmpty) _lineController.forward();
    }
  }

  @override
  void dispose() {
    _lineController.dispose();
    _glowController.dispose();
    super.dispose();
  }

  void _updateTouchIndex(double touchX, double chartWidth) {
    final n = _values.length;
    if (n == 0 || chartWidth <= 0) return;
    final normalizedX = (touchX / chartWidth).clamp(0.0, 1.0);
    setState(() {
      _isTouching = true;
      _touchIndex = (normalizedX * (n - 1)).round().clamp(0, n - 1);
    });
  }

  void _endTouch() {
    setState(() {
      _isTouching = false;
      _touchIndex = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final prices = widget.prices;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(height: 16),
        PriceHeader(
          prices: prices,
          series: widget.series,
          touchIndex: _isTouching ? _touchIndex : null,
          isLoading: widget.isLoading,
          onRefresh: widget.onRefresh,
        ),
        const SizedBox(height: 16),
        _buildChartSection(),
        const SizedBox(height: 16),
        _buildSeriesSelector(),
        const SizedBox(height: 24),
        if (prices != null && !prices.isEmpty) PriceStatsSection(prices: prices, series: widget.series),
      ],
    );
  }

  Widget _buildChartSection() {
    if (widget.isLoading) {
      return Container(
        height: 200,
        alignment: Alignment.center,
        child: const CircularProgressIndicator(color: AppColors.teal),
      );
    }
    if (widget.error != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: InlineError(message: widget.error!, onRetry: widget.onRefresh ?? () {}),
      );
    }

    final values = _values;
    if (values.isEmpty) {
      return Container(
        height: 200,
        alignment: Alignment.center,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.show_chart, color: Colors.white24, size: 48),
            const SizedBox(height: 8),
            Text('Simularea nu a generat încă prețuri', style: GoogleFonts.inter(color: Colors.white38)),
          ],
        ),
      );
    }

    final prices = widget.prices!;
    final minPrice = prices.min(widget.series);
    final maxPrice = prices.max(widget.series);
    final lineColor = (prices.change(widget.series) < 0) ? AppColors.priceDown : AppColors.priceUp;
    final axisStyle = GoogleFonts.inter(color: Colors.white38, fontSize: 11);

    return Container(
      height: 200,
      margin: const EdgeInsets.symmetric(horizontal: 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final chartSize = Size(constraints.maxWidth - 50, constraints.maxHeight);
          return Stack(
            children: [
              Positioned(right: 0, top: 8, child: Text(maxPrice.toStringAsFixed(4), style: axisStyle)),
              Positioned(right: 0, bottom: 8, child: Text(minPrice.toStringAsFixed(4), style: axisStyle)),
              Padding(
                padding: const EdgeInsets.only(right: 50),
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTapDown: (d) => _updateTouchIndex(d.localPosition.dx, chartSize.width),
                  onTapUp: (_) => _endTouch(),
                  onHorizontalDragStart: (d) => _updateTouchIndex(d.localPosition.dx, chartSize.width),
                  onHorizontalDragUpdate: (d) => _updateTouchIndex(d.localPosition.dx, chartSize.width),
                  onHorizontalDragEnd: (_) => _endTouch(),
                  child: AnimatedBuilder(
                    animation: Listenable.merge([_lineAnimation, _glowAnimation]),
                    builder: (context, child) => CustomPaint(
                      size: chartSize,
                      painter: ChartPainter(
                        prices: values,
                        animationProgress: _lineAnimation.value,
                        glowIntensity: 1.0 - _glowAnimation.value,
                        touchIndex: _touchIndex,
                        lineColor: lineColor,
                        minPrice: minPrice,
                        maxPrice: maxPrice,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSeriesSelector() {
    return Container(
      height: 44,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: PriceSeries.values.map((s) {
          final isSelected = widget.series == s;
          return Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => widget.onSeriesChanged(s),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.surface : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                alignment: Alignment.center,
                child: Text(
                  s.label,
                  style: GoogleFonts.inter(
                    color: isSelected ? Colors.white : Colors.white54,
                    fontSize: 13,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
