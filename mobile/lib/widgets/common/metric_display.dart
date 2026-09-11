import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/core/utils.dart';

/// Reusable metric display widget
class MetricDisplay extends StatelessWidget {
  final String label;
  final String value;
  final IconData? icon;
  final Color? valueColor;
  final Color? iconColor;
  final VoidCallback? onTap;
  final bool isCompact;

  const MetricDisplay({
    super.key,
    required this.label,
    required this.value,
    this.icon,
    this.valueColor,
    this.iconColor,
    this.onTap,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactDisplay(context);
    }
    return _buildFullDisplay(context);
  }

  Widget _buildFullDisplay(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Row(
              children: [
                Icon(
                  icon,
                  color: iconColor ?? AppTheme.theme.colorScheme.primary,
                  size: 16,
                ),
                SizedBox(width: AppConstants.spacingXS),
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.white.withOpacity(0.6),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ] else ...[
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.white.withOpacity(0.6),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          SizedBox(height: AppConstants.spacingXS),
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: valueColor ?? Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactDisplay(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(
              icon,
              color: iconColor ?? AppTheme.theme.colorScheme.primary,
              size: 14,
            ),
            SizedBox(width: AppConstants.spacingXS),
          ],
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: valueColor ?? Colors.white,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

/// Animated metric display with value transitions
class AnimatedMetricDisplay extends StatelessWidget {
  final String label;
  final double value;
  final String Function(double) formatter;
  final IconData? icon;
  final Color? valueColor;
  final Color? iconColor;
  final VoidCallback? onTap;
  final Duration animationDuration;

  const AnimatedMetricDisplay({
    super.key,
    required this.label,
    required this.value,
    required this.formatter,
    this.icon,
    this.valueColor,
    this.iconColor,
    this.onTap,
    this.animationDuration = const Duration(milliseconds: 800),
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Row(
              children: [
                Icon(
                  icon,
                  color: iconColor ?? AppTheme.theme.colorScheme.primary,
                  size: 16,
                ),
                SizedBox(width: AppConstants.spacingXS),
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.white.withOpacity(0.6),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ] else ...[
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.white.withOpacity(0.6),
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          SizedBox(height: AppConstants.spacingXS),
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: value),
            duration: animationDuration,
            curve: Curves.easeOutCubic,
            builder: (context, animatedValue, child) {
              return Text(
                formatter(animatedValue),
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: valueColor ?? Colors.white,
                  fontWeight: FontWeight.w600,
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

/// Power metric display with specific formatting
class PowerMetricDisplay extends StatelessWidget {
  final String label;
  final double powerKw;
  final IconData? icon;
  final Color? color;
  final VoidCallback? onTap;
  final bool showAnimation;

  const PowerMetricDisplay({
    super.key,
    required this.label,
    required this.powerKw,
    this.icon,
    this.color,
    this.onTap,
    this.showAnimation = false,
  });

  @override
  Widget build(BuildContext context) {
    if (showAnimation) {
      return AnimatedMetricDisplay(
        label: label,
        value: powerKw,
        formatter: (value) => value.kW,
        icon: icon,
        valueColor: color,
        iconColor: color,
        onTap: onTap,
      );
    }

    return MetricDisplay(
      label: label,
      value: powerKw.kW,
      icon: icon,
      valueColor: color,
      iconColor: color,
      onTap: onTap,
    );
  }
}

/// Battery metric display with percentage and power
class BatteryMetricDisplay extends StatelessWidget {
  final double percentage;
  final double powerKw;
  final VoidCallback? onTap;
  final bool showAnimation;

  const BatteryMetricDisplay({
    super.key,
    required this.percentage,
    required this.powerKw,
    this.onTap,
    this.showAnimation = false,
  });

  @override
  Widget build(BuildContext context) {
    final batteryColor = AppTheme.getBatteryColor(percentage);
    
    return GestureDetector(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(
                Icons.battery_charging_full_rounded,
                color: batteryColor,
                size: 16,
              ),
              SizedBox(width: AppConstants.spacingXS),
              Text(
                'BATERIE',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.white.withOpacity(0.6),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          SizedBox(height: AppConstants.spacingXS),
          Row(
            children: [
              if (showAnimation) ...[
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: powerKw),
                  duration: AppConstants.longAnimation,
                  curve: Curves.easeOutCubic,
                  builder: (context, animatedValue, child) {
                    return Text(
                      animatedValue.kW,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    );
                  },
                ),
              ] else ...[
                Text(
                  powerKw.kW,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              Text(
                ' · ',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.white.withOpacity(0.5),
                ),
              ),
              if (showAnimation) ...[
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: percentage),
                  duration: AppConstants.longAnimation,
                  curve: Curves.easeOutCubic,
                  builder: (context, animatedValue, child) {
                    return Text(
                      animatedValue.percent,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: AppTheme.getBatteryColor(animatedValue),
                        fontWeight: FontWeight.w600,
                      ),
                    );
                  },
                ),
              ] else ...[
                Text(
                  percentage.percent,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: batteryColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}