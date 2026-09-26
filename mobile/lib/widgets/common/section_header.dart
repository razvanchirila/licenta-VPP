import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

class SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color? color;

  const SectionHeader({super.key, required this.icon, required this.title, required this.subtitle, this.color});

  @override
  Widget build(BuildContext context) {
    final tinted = color != null;
    return Row(
      children: [
        Container(
          width: tinted ? 36 : 40,
          height: tinted ? 36 : 40,
          decoration: BoxDecoration(
            color: tinted ? color!.withValues(alpha: 0.15) : AppColors.surface,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(
            icon,
            color: tinted ? color : Colors.white.withValues(alpha: 0.8),
            size: tinted ? 20 : 22,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: tinted ? AppText.cardTitle : AppText.sectionTitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              Text(
                subtitle,
                style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: tinted ? 12 : 13),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
