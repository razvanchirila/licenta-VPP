import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/device.dart';

class DeviceCard extends StatelessWidget {
  final Device device;
  final bool busy;
  final VoidCallback? onToggle;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const DeviceCard({
    super.key,
    required this.device,
    this.busy = false,
    this.onToggle,
    this.onTap,
    this.onLongPress,
  });

  @override
  Widget build(BuildContext context) {
    final isOn = device.statusOn;
    return GestureDetector(
      onTap: onTap,
      onLongPress: onLongPress,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isOn ? AppColors.green.withValues(alpha: 0.3) : Colors.white.withValues(alpha: 0.06),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: isOn ? AppColors.green.withValues(alpha: 0.15) : Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(device.icon, color: isOn ? AppColors.green : Colors.white.withValues(alpha: 0.4), size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          device.name,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600),
                        ),
                      ),
                      if (device.critical) ...[const SizedBox(width: 8), const _CriticalBadge()],
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    device.scheduleText,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 12),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isOn ? device.currentDrawText : 'Oprit · ${formatPowerW(device.powerW)}',
                    style: GoogleFonts.inter(
                      color: isOn ? AppColors.amber : Colors.white.withValues(alpha: 0.4),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    'Consumat: ${formatKwh(device.accumulatedEnergyKwh, decimals: 2)}',
                    style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.35), fontSize: 11),
                  ),
                ],
              ),
            ),
            Tooltip(
              message: device.critical ? 'Dispozitiv critic, nu poate fi oprit' : '',
              child: _ToggleSwitch(isOn: isOn, busy: busy, onTap: (device.critical || busy) ? null : onToggle),
            ),
          ],
        ),
      ),
    );
  }
}

class _CriticalBadge extends StatelessWidget {
  const _CriticalBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(color: AppColors.red.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
      child: Text(
        'CRITIC',
        style: GoogleFonts.inter(color: AppColors.red, fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 0.5),
      ),
    );
  }
}

class _ToggleSwitch extends StatelessWidget {
  final bool isOn;
  final bool busy;
  final VoidCallback? onTap;

  const _ToggleSwitch({required this.isOn, required this.busy, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 52,
          height: 30,
          decoration: BoxDecoration(
            color: isOn ? AppColors.green : Colors.white.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(15),
          ),
          child: Stack(
            children: [
              AnimatedPositioned(
                duration: const Duration(milliseconds: 200),
                curve: Curves.easeOutCubic,
                left: isOn ? 24 : 2,
                top: 2,
                child: Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    color: busy ? Colors.white54 : Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 4, offset: const Offset(0, 2)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
