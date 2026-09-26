import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/energy/energy_period.dart';

class DateNavigation extends StatelessWidget {
  final String label;
  final String period;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final ValueChanged<String> onPeriodChanged;

  const DateNavigation({
    super.key,
    required this.label,
    required this.period,
    required this.onPrevious,
    required this.onNext,
    required this.onPeriodChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _NavButton(icon: Icons.chevron_left_rounded, onTap: onPrevious),
        const SizedBox(width: 8),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppText.sectionTitle,
            ),
          ),
        ),
        const SizedBox(width: 8),
        _NavButton(icon: Icons.chevron_right_rounded, onTap: onNext),
        const SizedBox(width: 16),
        _PeriodDropdown(period: period, onChanged: onPeriodChanged),
      ],
    );
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _NavButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08), width: 1),
        ),
        child: Icon(icon, color: Colors.white, size: 24),
      ),
    );
  }
}

class _PeriodDropdown extends StatelessWidget {
  final String period;
  final ValueChanged<String> onChanged;

  const _PeriodDropdown({required this.period, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08), width: 1),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: period,
          dropdownColor: AppColors.surface,
          icon: Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white.withValues(alpha: 0.6)),
          style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500),
          items: const [
            DropdownMenuItem(value: EnergyPeriod.day, child: Text('Zi')),
            DropdownMenuItem(value: EnergyPeriod.week, child: Text('Săpt.')),
            DropdownMenuItem(value: EnergyPeriod.month, child: Text('Lună')),
          ],
          onChanged: (value) {
            if (value != null) onChanged(value);
          },
        ),
      ),
    );
  }
}
