import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';

class ScreenHeader extends StatelessWidget {
  final String title;
  final List<Widget> actions;

  const ScreenHeader({super.key, required this.title, this.actions = const []});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          const BackNavButton(icon: Icons.arrow_back_ios_rounded, size: 22),
          const SizedBox(width: 8),
          Expanded(
            child: Text(title, style: AppText.screenTitle, maxLines: 1, overflow: TextOverflow.ellipsis),
          ),
          ...actions,
        ],
      ),
    );
  }
}

/// The Material back button with a Romanian tooltip (the app has no localizations delegate).
class BackNavButton extends StatelessWidget {
  final IconData icon;
  final double size;

  const BackNavButton({super.key, this.icon = Icons.arrow_back, this.size = 24});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      identifier: 'back',
      child: IconButton(
        onPressed: () => Navigator.maybePop(context),
        tooltip: 'Înapoi',
        icon: Icon(icon, color: Colors.white, size: size),
      ),
    );
  }
}
