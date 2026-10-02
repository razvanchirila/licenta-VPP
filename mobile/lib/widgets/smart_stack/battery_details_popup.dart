import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/core/theme.dart';

class BatteryDetailsPopup extends StatelessWidget {
  final Battery battery;

  const BatteryDetailsPopup({super.key, required this.battery});

  static void show(BuildContext context, {required Battery battery}) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => BatteryDetailsPopup(battery: battery),
    );
  }

  Color _socColor(double percent) {
    if (percent >= 60) return AppColors.green;
    if (percent >= 30) return AppColors.amber;
    return AppColors.red;
  }

  @override
  Widget build(BuildContext context) {
    final b = battery;
    final color = _socColor(b.socPercent);
    final reservePercent = b.capacityKwh > 0 ? 100 * b.socMinKwh / b.capacityKwh : 0.0;

    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      child: Container(
        padding: AppTheme.sheetPadding(context, 24),
        decoration: BoxDecoration(
          color: AppColors.surfaceAlt.withValues(alpha: 0.9),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.1),
            width: 1,
          ),
        ),
        child: SingleChildScrollView(
            child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Icon(Icons.battery_charging_full_rounded, color: color, size: 28),
                const SizedBox(width: 12),
                Text(
                  'Bateria casei',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            _buildSocCircle(color),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    icon: Icons.bolt_rounded,
                    label: 'Capacitate',
                    value: '${b.capacityKwh.toStringAsFixed(1)} kWh',
                    color: AppColors.amber,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildStatCard(
                    icon: Icons.energy_savings_leaf_rounded,
                    label: 'Disponibil peste rezervă',
                    value: '${b.availableKwh.toStringAsFixed(1)} kWh',
                    color: AppColors.emerald,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    icon: Icons.shield_rounded,
                    label: 'Rezervă backup',
                    value: '${reservePercent.toStringAsFixed(0)}% (${b.socMinKwh.toStringAsFixed(1)} kWh)',
                    color: AppColors.blue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildStatCard(
                    icon: Icons.hub_rounded,
                    label: 'Rezervă VPP',
                    value: '${b.vppReserveKwh.toStringAsFixed(2)} kWh',
                    color: const Color(0xFF8B5CF6),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    icon: Icons.swap_vert_rounded,
                    label: 'Putere max. înc./desc.',
                    value: '${b.pChMaxKw.toStringAsFixed(1)} / ${b.pDisMaxKw.toStringAsFixed(1)} kW',
                    color: AppColors.green,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildStatCard(
                    icon: Icons.percent_rounded,
                    label: 'Randament înc./desc.',
                    value: '${(b.etaCh * 100).toStringAsFixed(0)}% / ${(b.etaDis * 100).toStringAsFixed(0)}%',
                    color: AppColors.slate,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: () => Navigator.pop(context),
                style: TextButton.styleFrom(
                  backgroundColor: Colors.white.withValues(alpha: 0.1),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(
                  'Închide',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
          ],
        )),
      ),
    );
  }

  Widget _buildSocCircle(Color color) {
    return Container(
      width: 140,
      height: 140,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color.withValues(alpha: 0.15),
        border: Border.all(
          color: color.withValues(alpha: 0.5),
          width: 3,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${battery.socPercent.toStringAsFixed(0)}%',
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            '${battery.socKwh.toStringAsFixed(1)} kWh',
            style: GoogleFonts.inter(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 8),
          Text(
            value,
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: GoogleFonts.inter(
              color: Colors.white.withValues(alpha: 0.5),
              fontSize: 11,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
