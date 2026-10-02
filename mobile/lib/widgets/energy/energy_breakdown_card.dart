import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';

class BreakdownItem {
  final String label;
  final String value;
  final double percentage;
  final Color color;

  const BreakdownItem({required this.label, required this.value, required this.percentage, required this.color});
}

class BreakdownCard extends StatelessWidget {
  final String title;
  final String totalValue;
  final List<BreakdownItem> items;
  final String? semanticsId;

  const BreakdownCard({
    super.key,
    required this.title,
    required this.totalValue,
    required this.items,
    this.semanticsId,
  });

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(child: Text(title, style: AppText.cardTitle, maxLines: 1, overflow: TextOverflow.ellipsis)),
              const SizedBox(width: 8),
              Semantics(
                container: true,
                identifier: semanticsId,
                label: title,
                value: totalValue,
                excludeSemantics: true,
                child: Text(totalValue,
                    style: GoogleFonts.inter(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _SegmentedBar(items: items),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: items.map((item) => Expanded(child: _BreakdownColumn(item: item))).toList(),
          ),
        ],
      ),
    );
  }
}

/// Each segment is at least 3% wide so it stays visible.
class _SegmentedBar extends StatelessWidget {
  final List<BreakdownItem> items;

  const _SegmentedBar({required this.items});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(3),
      child: SizedBox(
        height: 6,
        child: Row(
          children: [
            for (var i = 0; i < items.length; i++)
              Expanded(
                flex: math.max(3, items[i].percentage.round()),
                child: Container(
                  margin: EdgeInsets.only(right: i < items.length - 1 ? 2 : 0),
                  color: items[i].color,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _BreakdownColumn extends StatelessWidget {
  final BreakdownItem item;

  const _BreakdownColumn({required this.item});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${item.percentage.toStringAsFixed(item.percentage >= 10 ? 0 : 1)} %',
          style:
              GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.7), fontSize: 13, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Container(width: 8, height: 8, decoration: BoxDecoration(color: item.color, shape: BoxShape.circle)),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                item.value,
                style: GoogleFonts.inter(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(item.label, style: AppText.small, maxLines: 2, overflow: TextOverflow.ellipsis),
      ],
    );
  }
}
