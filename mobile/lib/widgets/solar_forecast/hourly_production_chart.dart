import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

class HourlyProductionChart extends StatefulWidget {
  final String selectedDate;
  final Map<int, double> hourlyKw;
  final double maxKw;
  final Set<int> peakHours;
  final bool isToday;

  const HourlyProductionChart({
    super.key,
    required this.selectedDate,
    required this.hourlyKw,
    required this.maxKw,
    required this.peakHours,
    required this.isToday,
  });

  @override
  State<HourlyProductionChart> createState() => _HourlyProductionChartState();
}

class _HourlyProductionChartState extends State<HourlyProductionChart> {
  static const double _barsHeight = 160;
  int? _touchedHour;

  @override
  void didUpdateWidget(HourlyProductionChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedDate != widget.selectedDate) _touchedHour = null;
  }

  void _touch(double localX, double chartWidth) {
    final hour = ((localX / chartWidth) * 24).clamp(0, 23).toInt();
    if (hour != _touchedHour) setState(() => _touchedHour = hour);
  }

  void _release() => setState(() => _touchedHour = null);

  @override
  Widget build(BuildContext context) {
    final currentHour = DateTime.now().hour;
    final touched = _touchedHour;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceAlt,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Producție orară', style: AppText.cardTitle),
              if (touched != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.amber.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${touched.toString().padLeft(2, '0')}:00 - ${(widget.hourlyKw[touched] ?? 0).toStringAsFixed(2)} kW',
                    style: GoogleFonts.inter(color: AppColors.amber, fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 20),
          LayoutBuilder(
            builder: (context, constraints) {
              final chartWidth = constraints.maxWidth;
              return GestureDetector(
                onHorizontalDragUpdate: (d) => _touch(d.localPosition.dx, chartWidth),
                onTapDown: (d) => _touch(d.localPosition.dx, chartWidth),
                onTapUp: (_) => _release(),
                onHorizontalDragEnd: (_) => _release(),
                child: SizedBox(
                  height: 200,
                  child: Column(
                    children: [
                      Expanded(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: List.generate(24, (hour) => Expanded(child: _bar(hour, currentHour))),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(children: List.generate(24, (hour) => Expanded(child: _hourLabel(hour, currentHour)))),
                    ],
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  if (widget.isToday) ...[const _LegendItem(AppColors.blue, 'Acum'), const SizedBox(width: 12)],
                  const _LegendItem(AppColors.amber, 'Vârf'),
                ],
              ),
              Flexible(
                child: Text(
                  'Atinge graficul pentru detalii',
                  style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _bar(int hour, int currentHour) {
    final kw = widget.hourlyKw[hour] ?? 0;
    final heightPercent = widget.maxKw > 0 ? (kw / widget.maxKw) : 0.0;
    final isCurrentHour = widget.isToday && hour == currentHour;
    final isPeakHour = widget.peakHours.contains(hour);
    final isTouched = hour == _touchedHour;

    final color = isTouched
        ? AppColors.amber
        : isCurrentHour
            ? AppColors.blue
            : isPeakHour
                ? AppColors.amber
                : AppColors.amber.withValues(alpha: 0.4);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 1),
      alignment: Alignment.bottomCenter,
      child: Container(
        height: (_barsHeight * heightPercent).clamp(3.0, _barsHeight),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(2),
          boxShadow: isTouched
              ? [BoxShadow(color: AppColors.amber.withValues(alpha: 0.5), blurRadius: 8, spreadRadius: 1)]
              : null,
        ),
      ),
    );
  }

  Widget _hourLabel(int hour, int currentHour) {
    if (hour % 4 != 0) return const SizedBox.shrink();
    final isCurrentHour = widget.isToday && hour == currentHour;
    final isTouched = hour == _touchedHour;
    return Text(
      '$hour',
      textAlign: TextAlign.center,
      style: GoogleFonts.inter(
        color: isTouched
            ? AppColors.amber
            : isCurrentHour
                ? AppColors.blue
                : Colors.white38,
        fontSize: 10,
        fontWeight: isTouched ? FontWeight.w600 : FontWeight.w400,
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem(this.color, this.label);

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
            width: 10, height: 10, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 4),
        Text(label, style: GoogleFonts.inter(color: Colors.white54, fontSize: 11)),
      ],
    );
  }
}
