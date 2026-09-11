import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';

/// Reusable card widget with consistent styling
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final bool isGlass;
  final bool showShadow;
  final Color? backgroundColor;
  final BorderRadius? borderRadius;

  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.onTap,
    this.isGlass = false,
    this.showShadow = true,
    this.backgroundColor,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    final decoration = isGlass 
        ? AppTheme.glassDecoration 
        : AppTheme.cardDecoration;

    return Container(
      margin: margin ?? EdgeInsets.symmetric(
        horizontal: AppConstants.spacingM,
        vertical: AppConstants.spacingS,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: borderRadius ?? BorderRadius.circular(AppConstants.borderRadius),
          child: Container(
            padding: padding ?? EdgeInsets.all(AppConstants.spacingM),
            decoration: decoration.copyWith(
              color: backgroundColor ?? decoration.color,
              borderRadius: borderRadius ?? decoration.borderRadius,
              boxShadow: showShadow ? [AppTheme.cardShadow] : null,
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}

/// Loading card with shimmer effect
class LoadingCard extends StatefulWidget {
  final double? height;
  final EdgeInsetsGeometry? margin;

  const LoadingCard({
    super.key,
    this.height,
    this.margin,
  });

  @override
  State<LoadingCard> createState() => _LoadingCardState();
}

class _LoadingCardState extends State<LoadingCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AppConstants.longAnimation,
      vsync: this,
    )..repeat(reverse: true);
    
    _animation = Tween<double>(begin: 0.3, end: 0.7).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppCard(
      margin: widget.margin,
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          return Container(
            height: widget.height ?? 80,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(_animation.value * 0.1),
              borderRadius: BorderRadius.circular(AppConstants.smallBorderRadius),
            ),
          );
        },
      ),
    );
  }
}

/// Error card with retry functionality
class ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final EdgeInsetsGeometry? margin;

  const ErrorCard({
    super.key,
    required this.message,
    this.onRetry,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      margin: margin,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(
                Icons.error_outline_rounded,
                color: AppTheme.theme.colorScheme.error,
                size: 20,
              ),
              SizedBox(width: AppConstants.spacingS),
              Expanded(
                child: Text(
                  'Eroare',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.white,
                  ),
                ),
              ),
              if (onRetry != null)
                IconButton(
                  onPressed: onRetry,
                  icon: Icon(
                    Icons.refresh_rounded,
                    color: Colors.white.withOpacity(0.7),
                    size: 20,
                  ),
                  tooltip: 'Încearcă din nou',
                ),
            ],
          ),
          SizedBox(height: AppConstants.spacingS),
          Text(
            message,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.white.withOpacity(0.7),
            ),
          ),
        ],
      ),
    );
  }
}

/// Empty state card
class EmptyCard extends StatelessWidget {
  final String message;
  final IconData? icon;
  final EdgeInsetsGeometry? margin;

  const EmptyCard({
    super.key,
    required this.message,
    this.icon,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      margin: margin,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(
              icon,
              color: Colors.white.withOpacity(0.5),
              size: 32,
            ),
            SizedBox(height: AppConstants.spacingS),
          ],
          Text(
            message,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.white.withOpacity(0.7),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}