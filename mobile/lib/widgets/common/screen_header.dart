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
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back_ios_rounded, color: Colors.white, size: 22),
          ),
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
