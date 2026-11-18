import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';

class SimTimeChip extends StatelessWidget {
  final DateTime? time;

  const SimTimeChip({super.key, required this.time});

  @override
  Widget build(BuildContext context) {
    final t = time;
    if (t == null) return const SizedBox.shrink();
    return Semantics(
      container: true,
      identifier: 'home-sim-clock',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
        ),
        child: Text(
          'Simulare ${formatDayMonth(t)} ${formatClock(t)}',
          style: GoogleFonts.inter(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.w500),
        ),
      ),
    );
  }
}

/// Shown over stale data. [offline] = the server could not be reached; otherwise it answered with an error.
class ConnectionBanner extends StatelessWidget {
  final String message;
  final bool offline;

  const ConnectionBanner({super.key, required this.message, required this.offline});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.red.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.red.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          Icon(offline ? Icons.wifi_off_rounded : Icons.error_outline_rounded, color: AppColors.red, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${offline ? 'Conexiune pierdută' : 'Actualizare eșuată'}: $message. Date de la ultima actualizare.',
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 11),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class SolarForecastButton extends StatelessWidget {
  final VoidCallback onTap;

  const SolarForecastButton({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      identifier: 'home-solar-forecast',
      button: true,
      label: 'Prognoză solară',
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.amber.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: AppColors.amber.withValues(alpha: 0.4), width: 1),
          ),
          child: const Icon(Icons.wb_sunny_rounded, color: AppColors.amber, size: 22),
        ),
      ),
    );
  }
}

void showProfileMenu(BuildContext context,
    {required String username, required String houseName, required VoidCallback onLogout}) {
  showModalBottomSheet(
    context: context,
    backgroundColor: Colors.transparent,
    builder: (context) => Container(
      decoration: AppTheme.sheetDecoration(color: AppColors.surfaceMenu),
      padding: AppTheme.sheetPadding(context, 20),
      child: Material(
        type: MaterialType.transparency,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SheetHandle(color: Colors.grey.shade600),
            const SizedBox(height: 20),
            Semantics(
              container: true,
              identifier: 'profile-user',
              child: ListTile(
                leading: const Icon(Icons.person_rounded, color: Colors.white70),
                title: Text(username, style: const TextStyle(color: Colors.white)),
                subtitle: Text(houseName, style: const TextStyle(color: Colors.white54)),
              ),
            ),
            Semantics(
              container: true,
              identifier: 'profile-logout',
              child: ListTile(
                leading: const Icon(Icons.logout, color: Colors.red),
                title: const Text('Deconectare', style: TextStyle(color: Colors.white)),
                onTap: () {
                  Navigator.pop(context);
                  onLogout();
                },
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
