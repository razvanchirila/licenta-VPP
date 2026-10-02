import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';

class BackupReserveCard extends StatelessWidget {
  final double value;
  final double max;
  final bool hasBattery;
  final bool enabled;
  final ValueChanged<double> onChanged;
  final ValueChanged<double> onChangeStart;
  final ValueChanged<double> onChangeEnd;

  const BackupReserveCard({
    super.key,
    required this.value,
    required this.max,
    required this.hasBattery,
    required this.enabled,
    required this.onChanged,
    required this.onChangeStart,
    required this.onChangeEnd,
  });

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
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
                    Text('Rezervă Backup', style: AppText.cardTitle),
                    const SizedBox(height: 4),
                    Text(
                      hasBattery
                          ? 'Procentul minim de baterie păstrat ca rezervă'
                          : 'Casa nu are baterie, rezerva nu se aplică',
                      style: AppText.caption,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.green.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.green.withValues(alpha: 0.3), width: 1),
                ),
                child: Semantics(
                  container: true,
                  identifier: 'settings-reserve-value',
                  child: Text(
                    hasBattery ? '${value.round()}%' : '--',
                    style: GoogleFonts.inter(color: AppColors.green, fontSize: 14, fontWeight: FontWeight.w700),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          SliderTheme(
            data: SliderThemeData(
              activeTrackColor: AppColors.green,
              inactiveTrackColor: Colors.white.withValues(alpha: 0.1),
              thumbColor: AppColors.green,
              overlayColor: AppColors.green.withValues(alpha: 0.2),
              trackHeight: 6,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 12, elevation: 4),
              overlayShape: const RoundSliderOverlayShape(overlayRadius: 24),
            ),
            child: Semantics(
              container: true,
              identifier: 'settings-reserve-slider',
              label: 'Rezervă Backup',
              child: Slider(
                value: value.clamp(0, max),
                min: 0,
                max: max,
                divisions: 12,
                onChanged: enabled ? onChanged : null,
                onChangeStart: onChangeStart,
                onChangeEnd: onChangeEnd,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              children: [
                _tick('0%'),
                const Spacer(),
                _tick('${(max / 2).round()}%'),
                const Spacer(),
                _tick('${max.round()}%'),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.blue.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.blue.withValues(alpha: 0.2), width: 1),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline_rounded, color: AppColors.blue.withValues(alpha: 0.8), size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Această rezervă va fi păstrată pentru situații de urgență (pană de curent). '
                    'Simularea nu descarcă bateria sub acest prag.',
                    style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.7), fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _tick(String text) =>
      Text(text, style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.4), fontSize: 11));
}
