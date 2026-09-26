import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/sim_prices.dart';

class PriceHeader extends StatelessWidget {
  final SimPrices? prices;
  final PriceSeries series;
  final int? touchIndex;
  final bool isLoading;
  final VoidCallback? onRefresh;

  const PriceHeader({
    super.key,
    required this.prices,
    required this.series,
    required this.touchIndex,
    required this.isLoading,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    final p = prices;
    final values = p?.prices.map((e) => e.value(series)).toList() ?? const <double>[];
    final idx = touchIndex;
    final touched = idx != null && idx < values.length;

    final displayPrice = touched ? values[idx] : (p?.currentValue(series) ?? 0);
    final displayTime = touched && p != null ? _formatTimestamp(p.prices[idx].timestamp) : '';

    final change = p?.change(series) ?? 0.0;
    final isUp = change > 0;
    final isDown = change < 0;
    final changeColor = isUp ? AppColors.priceUp : (isDown ? AppColors.priceDown : Colors.white54);
    final prev = p?.previous?.value(series) ?? 0;
    final percent = prev.abs() > 1e-9 ? change / prev.abs() * 100 : 0.0;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Preț ${series.label.toLowerCase()} · simulare', style: AppText.cardTitle),
                    Text(p == null ? 'Curba zilei simulate' : 'Ziua simulată ${p.date}', style: AppText.muted),
                  ],
                ),
              ),
              if (onRefresh != null)
                IconButton(
                  onPressed: isLoading ? null : onRefresh,
                  icon: isLoading
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
                values.isEmpty ? '--' : displayPrice.toStringAsFixed(4),
                style: GoogleFonts.inter(
                    color: Colors.white, fontSize: 42, fontWeight: FontWeight.w700, letterSpacing: -1),
              ),
              const SizedBox(width: 6),
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text('lei/kWh', style: GoogleFonts.inter(color: Colors.white54, fontSize: 14)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          if (touched && displayTime.isNotEmpty)
            Text(displayTime, style: GoogleFonts.inter(color: Colors.white54, fontSize: 13))
          else if (values.isNotEmpty)
            Row(
              children: [
                Text(
                  '${isUp ? '+' : ''}${change.toStringAsFixed(4)} lei',
                  style: GoogleFonts.inter(color: changeColor, fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(width: 4),
                Icon(isUp ? Icons.arrow_drop_up : (isDown ? Icons.arrow_drop_down : Icons.remove),
                    color: changeColor, size: 20),
                Text(
                  '${percent.abs().toStringAsFixed(2)}%',
                  style: GoogleFonts.inter(color: changeColor, fontSize: 14, fontWeight: FontWeight.w500),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    '· față de pasul anterior',
                    style: GoogleFonts.inter(color: Colors.white38, fontSize: 13),
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

  static String _formatTimestamp(DateTime t) => '${formatClock(t)} · ${formatDayMonth(t)}';
}
