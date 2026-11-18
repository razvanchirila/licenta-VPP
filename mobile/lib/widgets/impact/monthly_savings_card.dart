import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/impact/impact_palette.dart';

double? savingsChangePercent(List<MonthlySaving> months) {
  final current = months.where((m) => m.current).toList();
  final previous = months.where((m) => !m.current && m.hasData).toList();
  if (current.isEmpty || previous.isEmpty) return null;
  final base = previous.last.savings;
  if (base.abs() <= 0.01) return null;
  return (current.first.savings - base) / base.abs() * 100;
}

class MonthlySavingsCard extends StatelessWidget {
  final List<MonthlySaving> months;

  const MonthlySavingsCard({super.key, required this.months});

  @override
  Widget build(BuildContext context) {
    final maxSavings = months.isEmpty ? 0.0 : months.map((m) => m.savings.abs()).reduce(math.max);
    final totalSavings = months.fold<double>(0, (sum, m) => sum + m.savings);
    final changePercent = savingsChangePercent(months);

    return SurfaceCard(
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Total economisit (6 luni)',
                      style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.6), fontSize: 13),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      formatLei(totalSavings, decimals: 0),
                      style: GoogleFonts.inter(
                        color: totalSavings >= 0 ? ImpactPalette.battery : ImpactPalette.peak,
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              if (changePercent != null) _ChangeBadge(changePercent: changePercent),
            ],
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 140,
            child: months.isEmpty
                ? Center(child: Text('Nu există date lunare', style: GoogleFonts.inter(color: Colors.white38)))
                : Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: months.map((m) => _MonthlyBar(month: m, maxSavings: maxSavings)).toList(),
                  ),
          ),
        ],
      ),
    );
  }
}

class _ChangeBadge extends StatelessWidget {
  final double changePercent;

  const _ChangeBadge({required this.changePercent});

  @override
  Widget build(BuildContext context) {
    final up = changePercent >= 0;
    final color = up ? ImpactPalette.battery : ImpactPalette.peak;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(8)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(up ? Icons.trending_up_rounded : Icons.trending_down_rounded, color: color, size: 18),
          const SizedBox(width: 4),
          Text(
            '${up ? '+' : ''}${changePercent.toStringAsFixed(0)}%',
            style: GoogleFonts.inter(color: color, fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _MonthlyBar extends StatelessWidget {
  final MonthlySaving month;
  final double maxSavings;

  const _MonthlyBar({required this.month, required this.maxSavings});

  @override
  Widget build(BuildContext context) {
    final m = month;
    final isCurrent = m.current;
    final color = !m.hasData
        ? Colors.white.withValues(alpha: 0.08)
        : isCurrent
            ? ImpactPalette.battery
            : Colors.white.withValues(alpha: 0.3);
    const maxBarHeight = 80.0;
    final barHeight = maxSavings > 0 ? (m.savings.abs() / maxSavings * maxBarHeight).clamp(2.0, maxBarHeight) : 2.0;

    return SizedBox(
      width: 44,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            m.hasData ? m.savings.toStringAsFixed(0) : '-',
            style: GoogleFonts.inter(
              color: isCurrent ? ImpactPalette.battery : Colors.white.withValues(alpha: 0.5),
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            width: 36,
            height: barHeight,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(6),
              boxShadow: isCurrent && m.hasData
                  ? [
                      BoxShadow(
                        color: ImpactPalette.battery.withValues(alpha: 0.4),
                        blurRadius: 8,
                        offset: const Offset(0, 4),
                      ),
                    ]
                  : null,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            m.month,
            style: GoogleFonts.inter(
              color: isCurrent ? Colors.white : Colors.white.withValues(alpha: 0.5),
              fontSize: 12,
              fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}
