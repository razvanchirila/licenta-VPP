import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';

class Header extends StatelessWidget {
  final String address;
  final String status;
  final bool isDischarging;
  final int notificationCount;
  final VoidCallback? onProfileTap;
  final Widget? customWidget;
  final bool showCustomWidget;
  final String userName;

  const Header({
    super.key,
    this.address = '',
    this.status = '',
    this.isDischarging = false,
    this.notificationCount = 0,
    this.onProfileTap,
    this.customWidget,
    this.showCustomWidget = false,
    this.userName = '',
  });

  String _getGreeting() {
    final name = userName.isEmpty ? '' : ', $userName';
    final hour = DateTime.now().hour;
    if (hour >= 5 && hour < 12) {
      return 'Bună dimineața$name!';
    } else if (hour >= 12 && hour < 18) {
      return 'Salut$name!';
    } else {
      return 'Bună seara$name!';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppConstants.spacingL,
        vertical: AppConstants.spacingS,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _getGreeting(),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: Colors.white,
                        fontSize: 18,
                      ),
                ),
                const SizedBox(height: AppConstants.spacingXS),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _StatusIndicator(isDischarging: isDischarging),
                    const SizedBox(width: AppConstants.spacingS),
                    Text(
                      status,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: isDischarging ? AppTheme.battery : AppTheme.success,
                            fontWeight: FontWeight.w500,
                          ),
                    ),
                  ],
                ),
                if (showCustomWidget && customWidget != null) ...[
                  const SizedBox(height: AppConstants.spacingS),
                  customWidget!,
                ],
              ],
            ),
          ),
          _ProfileButton(
            notificationCount: notificationCount,
            onTap: onProfileTap,
          ),
        ],
      ),
    );
  }
}

class _ProfileButton extends StatelessWidget {
  final int notificationCount;
  final VoidCallback? onTap;

  const _ProfileButton({
    required this.notificationCount,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Stack(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppTheme.theme.colorScheme.surface,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.1),
                width: 1,
              ),
            ),
            child: const Icon(
              Icons.person_rounded,
              color: Colors.white70,
              size: 24,
            ),
          ),
          if (notificationCount > 0)
            Positioned(
              right: 0,
              top: 0,
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: AppTheme.theme.colorScheme.error,
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: AppTheme.theme.colorScheme.surface,
                    width: 2,
                  ),
                ),
                child: Center(
                  child: Text(
                    notificationCount > 9 ? '9+' : notificationCount.toString(),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _StatusIndicator extends StatefulWidget {
  final bool isDischarging;

  const _StatusIndicator({required this.isDischarging});

  @override
  State<_StatusIndicator> createState() => _StatusIndicatorState();
}

class _StatusIndicatorState extends State<_StatusIndicator> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AppConstants.longAnimation,
      vsync: this,
    )..repeat(reverse: true);

    _animation = Tween<double>(begin: 0.4, end: 1.0).animate(
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
    final color = widget.isDischarging ? AppTheme.battery : AppTheme.success;

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color.withValues(alpha: _animation.value),
            borderRadius: BorderRadius.circular(4),
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: _animation.value * 0.5),
                blurRadius: 6,
                spreadRadius: 1,
              ),
            ],
          ),
        );
      },
    );
  }
}
