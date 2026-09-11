import 'package:flutter/material.dart';

/// Page indicator with dots for SmartStack
/// Shows current page position with highlighted dot
class PageIndicator extends StatelessWidget {
  final int pageCount;
  final int currentPage;
  final Color activeColor;
  final Color inactiveColor;
  final double dotSize;
  final double activeDotSize;
  final double spacing;

  const PageIndicator({
    super.key,
    required this.pageCount,
    required this.currentPage,
    this.activeColor = const Color(0xFF3B82F6),
    this.inactiveColor = const Color(0xFF4B5563),
    this.dotSize = 6,
    this.activeDotSize = 8,
    this.spacing = 6,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(pageCount, (index) {
        final isActive = index == currentPage;
        return Padding(
          padding: EdgeInsets.symmetric(vertical: spacing / 2),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: isActive ? activeDotSize : dotSize,
            height: isActive ? activeDotSize : dotSize,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isActive ? activeColor : inactiveColor,
              boxShadow: isActive
                  ? [
                      BoxShadow(
                        color: activeColor.withOpacity(0.4),
                        blurRadius: 4,
                        spreadRadius: 1,
                      ),
                    ]
                  : null,
            ),
          ),
        );
      }),
    );
  }
}
