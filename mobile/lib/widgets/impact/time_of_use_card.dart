import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/impact/impact_palette.dart';

class TimeOfUseCard extends StatefulWidget {
  final EnergyImpact impact;

  const TimeOfUseCard({super.key, required this.impact});

  @override
  State<TimeOfUseCard> createState() => _TimeOfUseCardState();
}

class _TimeOfUseCardState extends State<TimeOfUseCard> {
  bool _peakSelected = true;

  @override
  Widget build(BuildContext context) {
    final split = _peakSelected ? widget.impact.peak : widget.impact.offPeak;
    final maxValue = math.max(split.max, 0.1);

    return SurfaceCard(
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _TimeOfUseButton(
                  label: 'Vârf',
                  subtitle: '17:00 - 22:00',
                  isSelected: _peakSelected,
                  onTap: () => setState(() => _peakSelected = true),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _TimeOfUseButton(
                  label: 'În afara vârfului',
                  subtitle: '22:00 - 17:00',
                  isSelected: !_peakSelected,
                  onTap: () => setState(() => _peakSelected = false),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 150,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                _VerticalBar(color: ImpactPalette.solar, value: split.solar, maxValue: maxValue, label: 'Solar'),
                _VerticalBar(color: ImpactPalette.battery, value: split.battery, maxValue: maxValue, label: 'Baterie'),
                _VerticalBar(color: ImpactPalette.p2p, value: split.p2p, maxValue: maxValue, label: 'Vecini'),
                _VerticalBar(color: ImpactPalette.grid, value: split.grid, maxValue: maxValue, label: 'Rețea'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TimeOfUseButton extends StatelessWidget {
  final String label;
  final String subtitle;
  final bool isSelected;
  final VoidCallback onTap;

  const _TimeOfUseButton({required this.label, required this.subtitle, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white.withValues(alpha: 0.10) : Colors.white.withValues(alpha: 0.03),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? Colors.white.withValues(alpha: 0.25) : Colors.white.withValues(alpha: 0.06),
            width: 1,
          ),
        ),
        child: Column(
          children: [
            Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: GoogleFonts.inter(
                color: isSelected ? Colors.white : Colors.white.withValues(alpha: 0.4),
                fontSize: 14,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: GoogleFonts.inter(
                color: isSelected ? Colors.white.withValues(alpha: 0.6) : Colors.white.withValues(alpha: 0.25),
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _VerticalBar extends StatelessWidget {
  final Color color;
  final double value;
  final double maxValue;
  final String label;

  const _VerticalBar({required this.color, required this.value, required this.maxValue, required this.label});

  @override
  Widget build(BuildContext context) {
    const maxBarHeight = 70.0;
    final barHeight = maxValue > 0 ? (value / maxValue * maxBarHeight).clamp(2.0, maxBarHeight) : 2.0;

    return SizedBox(
      width: 60,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value.toStringAsFixed(1),
              style: GoogleFonts.inter(color: color, fontSize: 14, fontWeight: FontWeight.w700)),
          Text('kWh', style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.4), fontSize: 10)),
          const SizedBox(height: 6),
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            width: 44,
            height: barHeight,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(6),
              boxShadow: [BoxShadow(color: color.withValues(alpha: 0.4), blurRadius: 8, offset: const Offset(0, 4))],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: GoogleFonts.inter(
                color: Colors.white.withValues(alpha: 0.7), fontSize: 12, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }
}
