import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/energy/energy_line_chart.dart';

/// [onChanged] fires on each toggle so the chart behind the sheet updates live.
Future<void> showChartFilterSheet(
  BuildContext context, {
  required EnergySeriesVisibility visibility,
  required ValueChanged<EnergySeriesVisibility> onChanged,
}) {
  var current = visibility;
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => StatefulBuilder(
      builder: (context, setSheetState) {
        void update(EnergySeriesVisibility next) {
          setSheetState(() => current = next);
          onChanged(next);
        }

        return Container(
          padding: const EdgeInsets.all(20),
          decoration: AppTheme.sheetDecoration(),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SheetHandle(),
                const SizedBox(height: 20),
                Text('Afișare grafice', style: AppText.sectionTitle),
                const SizedBox(height: 16),
                _FilterToggle(
                  series: EnergySeries.solar,
                  value: current.solar,
                  onChanged: (v) => update(current.copyWith(solar: v)),
                ),
                _FilterToggle(
                  series: EnergySeries.consumption,
                  value: current.consumption,
                  onChanged: (v) => update(current.copyWith(consumption: v)),
                ),
                _FilterToggle(
                  series: EnergySeries.battery,
                  value: current.battery,
                  onChanged: (v) => update(current.copyWith(battery: v)),
                ),
                _FilterToggle(
                  series: EnergySeries.grid,
                  value: current.grid,
                  onChanged: (v) => update(current.copyWith(grid: v)),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        );
      },
    ),
  );
}

class _FilterToggle extends StatelessWidget {
  final EnergySeries series;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _FilterToggle({required this.series, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final color = series.color;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              series.label,
              style: GoogleFonts.inter(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500),
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: color,
            activeTrackColor: color.withValues(alpha: 0.3),
            inactiveThumbColor: Colors.white.withValues(alpha: 0.5),
            inactiveTrackColor: Colors.white.withValues(alpha: 0.1),
          ),
        ],
      ),
    );
  }
}
