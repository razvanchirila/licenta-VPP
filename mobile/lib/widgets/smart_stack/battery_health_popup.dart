import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Modal popup for displaying battery health information
/// Shows battery health percentage, charge cycles, current percentage and capacity
class BatteryHealthPopup extends StatelessWidget {
  final double batteryPercent;
  final double batteryCapacityKwh;

  const BatteryHealthPopup({
    super.key,
    required this.batteryPercent,
    required this.batteryCapacityKwh,
  });

  /// Generate fictive battery health (85-100%)
  double get batteryHealthPercent {
    // Simulate health based on cycles - newer battery = higher health
    return 100 - (chargeCycles * 0.015);
  }

  /// Generate fictive charge cycles (150-400)
  int get chargeCycles {
    // Use a seed based on capacity to get consistent "random" value
    return 150 + ((batteryCapacityKwh * 17).toInt() % 250);
  }

  Color _getHealthColor(double health) {
    if (health >= 90) return const Color(0xFF22C55E);
    if (health >= 80) return const Color(0xFFFBBF24);
    return const Color(0xFFEF4444);
  }

  /// Show the popup as a modal bottom sheet
  static void show(BuildContext context, {
    required double batteryPercent,
    required double batteryCapacityKwh,
  }) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => BatteryHealthPopup(
        batteryPercent: batteryPercent,
        batteryCapacityKwh: batteryCapacityKwh,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final healthColor = _getHealthColor(batteryHealthPercent);
    final availableEnergy = batteryCapacityKwh * (batteryPercent / 100);

    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFF1A1A1A).withOpacity(0.9),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Handle bar
              Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 24),
              
              // Title
              Row(
                children: [
                  Icon(
                    Icons.battery_charging_full_rounded,
                    color: healthColor,
                    size: 28,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'Sănătatea Bateriei',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              
              // Health percentage - main display
              _buildHealthCircle(healthColor),
              const SizedBox(height: 24),
              
              // Stats grid
              Row(
                children: [
                  Expanded(
                    child: _buildStatCard(
                      icon: Icons.loop_rounded,
                      label: 'Cicluri încărcare',
                      value: '$chargeCycles',
                      color: const Color(0xFF3B82F6),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildStatCard(
                      icon: Icons.battery_std_rounded,
                      label: 'Nivel actual',
                      value: '${batteryPercent.round()}%',
                      color: const Color(0xFF22C55E),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _buildStatCard(
                      icon: Icons.bolt_rounded,
                      label: 'Capacitate totală',
                      value: '${batteryCapacityKwh.toStringAsFixed(1)} kWh',
                      color: const Color(0xFFFBBF24),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildStatCard(
                      icon: Icons.energy_savings_leaf_rounded,
                      label: 'Energie disponibilă',
                      value: '${availableEnergy.toStringAsFixed(1)} kWh',
                      color: const Color(0xFF10B981),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              
              // Close button
              SizedBox(
                width: double.infinity,
                child: TextButton(
                  onPressed: () => Navigator.pop(context),
                  style: TextButton.styleFrom(
                    backgroundColor: Colors.white.withOpacity(0.1),
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
          ),
        ),
      ),
    );
  }

  Widget _buildHealthCircle(Color healthColor) {
    return Container(
      width: 140,
      height: 140,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: healthColor.withOpacity(0.15),
        border: Border.all(
          color: healthColor.withOpacity(0.5),
          width: 3,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${batteryHealthPercent.toStringAsFixed(1)}%',
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            'Sănătate',
            style: GoogleFonts.inter(
              color: Colors.white.withOpacity(0.6),
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
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: color.withOpacity(0.3),
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
              fontSize: 18,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: GoogleFonts.inter(
              color: Colors.white.withOpacity(0.5),
              fontSize: 11,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
