import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';

class StatsPeriodSelector extends StatelessWidget {
  final String selected;
  final ValueChanged<String> onChanged;

  const StatsPeriodSelector({super.key, required this.selected, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: AppTheme.surfaceDecoration(),
      child: Row(
        children: [
          _button('day', 'Zi'),
          _button('week', 'Săptămână'),
          _button('month', 'Lună'),
          _button('year', 'An'),
        ],
      ),
    );
  }

  Widget _button(String period, String label) {
    final isSelected = selected == period;
    return Expanded(
      child: Semantics(
        container: true,
        identifier: 'stats-period-$period',
        button: true,
        selected: isSelected,
        child: GestureDetector(
          onTap: () {
            if (!isSelected) onChanged(period);
          },
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: isSelected ? AppColors.blue : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isSelected ? Colors.white : AppColors.textSecondary,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
