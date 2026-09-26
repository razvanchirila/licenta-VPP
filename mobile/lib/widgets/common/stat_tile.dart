import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

class StatTile extends StatelessWidget {
  final String label;
  final String value;
  final IconData? icon;
  final Color? iconColor;
  final TextStyle? labelStyle;
  final TextStyle? valueStyle;

  const StatTile({
    super.key,
    required this.label,
    required this.value,
    this.icon,
    this.iconColor,
    this.labelStyle,
    this.valueStyle,
  });

  @override
  Widget build(BuildContext context) {
    final labelText = Text(label, style: labelStyle ?? AppText.muted, maxLines: 1, overflow: TextOverflow.ellipsis);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (icon == null)
          labelText
        else
          Row(
            children: [
              Icon(icon, size: 16, color: iconColor),
              const SizedBox(width: 4),
              Flexible(child: labelText),
            ],
          ),
        const SizedBox(height: 4),
        Text(
          value,
          style: valueStyle ?? GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}

class StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color iconColor;

  const StatCard({super.key, required this.label, required this.value, required this.icon, required this.iconColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: AppTheme.surfaceDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, color: iconColor, size: 16),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                style: GoogleFonts.inter(color: Colors.white54, fontSize: 11),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ]),
          const SizedBox(height: 6),
          Text(
            value,
            style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
