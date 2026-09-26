import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/impact/donut_chart.dart';
import 'package:flutter_interface/widgets/impact/impact_palette.dart';

class EnergySourcesCard extends StatelessWidget {
  final EnergyImpact impact;

  const EnergySourcesCard({super.key, required this.impact});

  @override
  Widget build(BuildContext context) {
    final selfConsumption = impact.hasData ? (100 - impact.gridPercent).clamp(0.0, 100.0) : 0.0;

    return SurfaceCard(
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _LegendItem(
                    color: ImpactPalette.solar, label: 'Solar', percent: impact.solarPercent, kwh: impact.solarKwh),
                const SizedBox(height: 12),
                _LegendItem(
                    color: ImpactPalette.battery,
                    label: 'Baterie',
                    percent: impact.batteryPercent,
                    kwh: impact.batteryKwh),
                const SizedBox(height: 12),
                _LegendItem(
                    color: ImpactPalette.p2p, label: 'Vecini (P2P)', percent: impact.p2pPercent, kwh: impact.p2pKwh),
                const SizedBox(height: 12),
                _LegendItem(
                    color: ImpactPalette.grid, label: 'Rețea', percent: impact.gridPercent, kwh: impact.gridKwh),
              ],
            ),
          ),
          SizedBox(
            width: 130,
            height: 140,
            child: CustomPaint(
              painter: DonutChartPainter(
                segments: [
                  DonutSegment(impact.solarPercent, ImpactPalette.solar),
                  DonutSegment(impact.batteryPercent, ImpactPalette.battery),
                  DonutSegment(impact.p2pPercent, ImpactPalette.p2p),
                  DonutSegment(impact.gridPercent, ImpactPalette.grid),
                ],
              ),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      impact.hasData ? '${selfConsumption.round()}%' : '--',
                      style: GoogleFonts.inter(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w700),
                    ),
                    Text(
                      impact.hasData ? 'Fără rețea' : 'Fără date',
                      style: AppText.small,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  final double percent;
  final double kwh;

  const _LegendItem({required this.color, required this.label, required this.percent, required this.kwh});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
            width: 12, height: 12, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 12)),
              Row(
                children: [
                  Text(
                    '${percent.round()}%',
                    style: AppText.cardTitle,
                  ),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      formatKwh(kwh),
                      style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}
