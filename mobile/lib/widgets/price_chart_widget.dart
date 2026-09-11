import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/price_data.dart';
import 'chart_painter.dart';

/// Animated OPCOM price chart widget (Revolut-style)
class PriceChartWidget extends StatefulWidget {
  final PriceData? priceData;
  final bool isLoading;
  final String selectedPeriod;
  final Function(String) onPeriodChanged;
  final VoidCallback? onRefresh;

  const PriceChartWidget({
    super.key,
    this.priceData,
    this.isLoading = false,
    this.selectedPeriod = '1Z',
    required this.onPeriodChanged,
    this.onRefresh,
  });

  @override
  State<PriceChartWidget> createState() => _PriceChartWidgetState();
}

class _PriceChartWidgetState extends State<PriceChartWidget>
    with TickerProviderStateMixin {
  AnimationController? _lineController;
  AnimationController? _glowController;
  Animation<double>? _lineAnimation;
  Animation<double>? _glowAnimation;
  int? _touchIndex;
  bool _isTouching = false;

  @override
  void initState() {
    super.initState();
    _initAnimations();
  }

  void _initAnimations() {
    // Line drawing animation (1.2s)
    _lineController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _lineAnimation = CurvedAnimation(
      parent: _lineController!,
      curve: Curves.easeOutCubic,
    );
    
    // Glow fade out animation (starts after line completes, 500ms)
    _glowController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _glowAnimation = CurvedAnimation(
      parent: _glowController!,
      curve: Curves.easeOut,
    );
    
    // When line animation completes, start glow fade out
    _lineController!.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        _glowController!.forward();
      }
    });
    
    if (widget.priceData != null && widget.priceData!.prices.isNotEmpty) {
      _lineController!.forward();
    }
  }

  @override
  void didUpdateWidget(PriceChartWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    if (oldWidget.selectedPeriod != widget.selectedPeriod ||
        oldWidget.priceData != widget.priceData) {
      _lineController?.reset();
      _glowController?.reset();
      if (widget.priceData != null && widget.priceData!.prices.isNotEmpty) {
        _lineController?.forward();
      }
    }
  }

  @override
  void dispose() {
    _lineController?.dispose();
    _glowController?.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details, Size chartSize) {
    setState(() {
      _isTouching = true;
      _updateTouchIndex(details.localPosition.dx, chartSize.width);
    });
  }

  void _handleTapUp(TapUpDetails details) {
    setState(() {
      _isTouching = false;
      _touchIndex = null;
    });
  }

  void _handlePanStartInternal(DragStartDetails details, Size chartSize) {
    setState(() {
      _isTouching = true;
      _updateTouchIndex(details.localPosition.dx, chartSize.width);
    });
  }

  void _handlePanUpdateInternal(DragUpdateDetails details, Size chartSize) {
    if (_isTouching) {
      _updateTouchIndex(details.localPosition.dx, chartSize.width);
    }
  }

  void _handlePanEndInternal(DragEndDetails details) {
    setState(() {
      _isTouching = false;
      _touchIndex = null;
    });
  }

  void _updateTouchIndex(double touchX, double chartWidth) {
    if (widget.priceData == null || widget.priceData!.prices.isEmpty) return;
    
    final int dataPoints = widget.priceData!.prices.length;
    final double normalizedX = (touchX / chartWidth).clamp(0.0, 1.0);
    final int index = (normalizedX * (dataPoints - 1)).round();
    
    setState(() {
      _touchIndex = index.clamp(0, dataPoints - 1);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(height: 16),
        _buildPriceHeader(),
        const SizedBox(height: 16),
        _buildChartSection(),
        const SizedBox(height: 16),
        _buildPeriodSelector(),
        const SizedBox(height: 24),
        _buildInfoSection(),
      ],
    );
  }

  Widget _buildPriceHeader() {
    final priceData = widget.priceData;
    
    final double displayPrice = _isTouching && _touchIndex != null && priceData != null
        ? priceData.prices[_touchIndex!].priceLeiKwh
        : priceData?.currentPriceLeiKwh ?? 0;
    
    final String displayTime = _isTouching && _touchIndex != null && priceData != null
        ? _formatTimestamp(priceData.prices[_touchIndex!].timestamp)
        : '';
    
    final change = priceData?.change;
    final bool isUp = change?.isUp ?? false;
    final bool isDown = change?.isDown ?? false;
    final Color changeColor = isUp ? const Color(0xFF00C853) : (isDown ? const Color(0xFFFF5252) : Colors.white54);
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'OPCOM · Preț Energie',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    'Piața pentru Ziua Următoare',
                    style: GoogleFonts.inter(
                      color: Colors.white54,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              if (widget.onRefresh != null)
                IconButton(
                  onPressed: widget.isLoading ? null : widget.onRefresh,
                  icon: widget.isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white54),
                        )
                      : const Icon(Icons.refresh, color: Colors.white54, size: 22),
                ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                displayPrice.toStringAsFixed(4),
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 42,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -1,
                ),
              ),
              const SizedBox(width: 6),
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  'lei/kWh',
                  style: GoogleFonts.inter(color: Colors.white54, fontSize: 14),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          if (_isTouching && displayTime.isNotEmpty)
            Text(displayTime, style: GoogleFonts.inter(color: Colors.white54, fontSize: 13))
          else if (change != null)
            Row(
              children: [
                Text(
                  '${isUp ? '+' : ''}${change.absoluteLeiKwh.toStringAsFixed(4)} lei',
                  style: GoogleFonts.inter(color: changeColor, fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(width: 4),
                Icon(
                  isUp ? Icons.arrow_drop_up : (isDown ? Icons.arrow_drop_down : Icons.remove),
                  color: changeColor,
                  size: 20,
                ),
                Text(
                  '${change.percent.abs().toStringAsFixed(2)}%',
                  style: GoogleFonts.inter(color: changeColor, fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(width: 8),
                Text(
                  '· ${_getPeriodLabel(widget.selectedPeriod)}',
                  style: GoogleFonts.inter(color: Colors.white38, fontSize: 13),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildChartSection() {
    if (widget.isLoading) {
      return Container(
        height: 200,
        alignment: Alignment.center,
        child: const CircularProgressIndicator(color: Color(0xFF00d4aa)),
      );
    }
    
    if (widget.priceData == null || widget.priceData!.prices.isEmpty) {
      return Container(
        height: 200,
        alignment: Alignment.center,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.show_chart, color: Colors.white24, size: 48),
            const SizedBox(height: 8),
            Text('Nu sunt date disponibile', style: GoogleFonts.inter(color: Colors.white38)),
          ],
        ),
      );
    }
    
    final priceData = widget.priceData!;
    // Green when price is up, red when down
    final lineColor = priceData.change.isDown 
        ? const Color(0xFFFF5252) 
        : const Color(0xFF00C853);
    
    // If animations not ready, show static chart
    if (_lineAnimation == null || _glowAnimation == null) {
      return Container(
        height: 200,
        margin: const EdgeInsets.symmetric(horizontal: 8),
        child: CustomPaint(
          size: const Size(double.infinity, 200),
          painter: ChartPainter(
            prices: priceData.prices,
            animationProgress: 1.0,
            glowIntensity: 0.0,
            touchIndex: _touchIndex,
            lineColor: lineColor,
            minPrice: priceData.minPrice / 1000,
            maxPrice: priceData.maxPrice / 1000,
          ),
        ),
      );
    }
    
    return Container(
      height: 200,
      margin: const EdgeInsets.symmetric(horizontal: 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Stack(
            children: [
              Positioned(
                right: 0,
                top: 8,
                child: Text(
                  (priceData.maxPrice / 1000).toStringAsFixed(4),
                  style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
                ),
              ),
              Positioned(
                right: 0,
                bottom: 8,
                child: Text(
                  (priceData.minPrice / 1000).toStringAsFixed(4),
                  style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(right: 50),
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTapDown: (d) => _handleTapDown(d, Size(constraints.maxWidth - 50, constraints.maxHeight)),
                  onTapUp: _handleTapUp,
                  onHorizontalDragStart: (d) => _handlePanStartInternal(d, Size(constraints.maxWidth - 50, constraints.maxHeight)),
                  onHorizontalDragUpdate: (d) => _handlePanUpdateInternal(d, Size(constraints.maxWidth - 50, constraints.maxHeight)),
                  onHorizontalDragEnd: _handlePanEndInternal,
                  child: AnimatedBuilder(
                    animation: Listenable.merge([_lineAnimation!, _glowAnimation!]),
                    builder: (context, child) {
                      final double glowIntensity = 1.0 - _glowAnimation!.value;
                      
                      return CustomPaint(
                        size: Size(constraints.maxWidth - 50, constraints.maxHeight),
                        painter: ChartPainter(
                          prices: priceData.prices,
                          animationProgress: _lineAnimation!.value,
                          glowIntensity: glowIntensity,
                          touchIndex: _touchIndex,
                          lineColor: lineColor,
                          minPrice: priceData.minPrice / 1000,
                          maxPrice: priceData.maxPrice / 1000,
                        ),
                      );
                    },
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildPeriodSelector() {
    // Only show periods with real data: 1Z (today), 1S (week), 1L (month)
    final periods = ['1Z', '1S', '1L'];
    
    return Container(
      height: 36,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: periods.map((period) {
          final isSelected = widget.selectedPeriod == period;
          return Expanded(
            child: GestureDetector(
              onTap: () => widget.onPeriodChanged(period),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: isSelected ? const Color(0xFF1C1C1E) : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                alignment: Alignment.center,
                child: Text(
                  period,
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

  Widget _buildInfoSection() {
    final priceData = widget.priceData;
    if (priceData == null) return const SizedBox.shrink();
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Statistici și informații', style: GoogleFonts.inter(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
              const Icon(Icons.info_outline, color: Colors.white38, size: 18),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: _buildStatCard('Preț minim', '${priceData.statistics.minLeiKwh.toStringAsFixed(4)} lei/kWh', Icons.trending_down, const Color(0xFF00C853))),
              const SizedBox(width: 12),
              Expanded(child: _buildStatCard('Preț maxim', '${priceData.statistics.maxLeiKwh.toStringAsFixed(4)} lei/kWh', Icons.trending_up, const Color(0xFFFF5252))),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _buildStatCard('Preț mediu', '${priceData.statistics.avgLeiKwh.toStringAsFixed(4)} lei/kWh', Icons.analytics_outlined, Colors.white54)),
              const SizedBox(width: 12),
              Expanded(child: _buildStatCard('Sursă date', priceData.source, Icons.cloud_outlined, const Color(0xFF00d4aa))),
            ],
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color iconColor) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: const Color(0xFF1C1C1E), borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, color: iconColor, size: 16),
            const SizedBox(width: 6),
            Text(label, style: GoogleFonts.inter(color: Colors.white54, fontSize: 11)),
          ]),
          const SizedBox(height: 6),
          Text(value, style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    return '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')} · ${timestamp.day.toString().padLeft(2, '0')}/${timestamp.month.toString().padLeft(2, '0')}';
  }

  String _getPeriodLabel(String period) {
    switch (period) {
      case '1Z': return 'Astăzi';
      case '1S': return '1 săptămână';
      case '1L': return '1 lună';
      default: return period;
    }
  }
}
