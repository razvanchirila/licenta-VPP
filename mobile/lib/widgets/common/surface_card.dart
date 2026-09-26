import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';

class SurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final double radius;
  final bool bordered;
  final EdgeInsetsGeometry? margin;

  const SurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.radius = 16,
    this.bordered = true,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      padding: padding,
      decoration: bordered
          ? BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(radius),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08), width: 1),
            )
          : AppTheme.surfaceDecoration(radius: radius),
      child: child,
    );
  }
}

class SheetHandle extends StatelessWidget {
  final Color? color;
  final EdgeInsetsGeometry margin;

  const SheetHandle({super.key, this.color, this.margin = EdgeInsets.zero});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        margin: margin,
        width: 40,
        height: 4,
        decoration: BoxDecoration(
          color: color ?? Colors.white.withValues(alpha: 0.3),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }
}
