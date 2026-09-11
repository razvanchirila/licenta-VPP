import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';

/// Reusable header widget for the VPP Simulator app
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
    this.address = 'Str. Victoriei 123',
    this.status = 'Se descarcă',
    this.isDischarging = true,
    this.notificationCount = 0,
    this.onProfileTap,
    this.customWidget,
    this.showCustomWidget = false,
    this.userName = 'Tudor',
  });

  /// Returnează salutul bazat pe ora curentă
  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour >= 5 && hour < 12) {
      return 'Bună dimineața, $userName! 🤩';
    } else if (hour >= 12 && hour < 18) {
      return 'Salut, $userName! 😊';
    } else {
      return 'Seara faină, $userName! 🥱';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: AppConstants.spacingL,
        vertical: AppConstants.spacingS,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Coloana stânga: Salut, Status, Widget personalizat (vertical)
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Salut
                Text(
                  _getGreeting(),
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    color: Colors.white,
                    fontSize: 18,
                  ),
                ),
                SizedBox(height: AppConstants.spacingXS),
                // Status cu indicator colorat
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _StatusIndicator(isDischarging: isDischarging),
                    SizedBox(width: AppConstants.spacingS),
                    Text(
                      status,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: isDischarging 
                            ? AppTheme.battery
                            : AppTheme.success,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                // Widget personalizat (buton Test)
                if (showCustomWidget && customWidget != null) ...[
                  SizedBox(height: AppConstants.spacingS),
                  customWidget!,
                ],
              ],
            ),
          ),
          // Buton profil cu badge notificări (dreapta)
          _ProfileButton(
            notificationCount: notificationCount,
            onTap: onProfileTap,
          ),
        ],
      ),
    );
  }
}

/// Profile button with notification badge
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
                color: Colors.white.withOpacity(0.1),
                width: 1,
              ),
            ),
            child: const Icon(
              Icons.person_rounded,
              color: Colors.white70,
              size: 24,
            ),
          ),
          // Badge notificări
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
                    color: AppTheme.theme.colorScheme.background,
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

/// Animated status indicator
class _StatusIndicator extends StatefulWidget {
  final bool isDischarging;

  const _StatusIndicator({required this.isDischarging});

  @override
  State<_StatusIndicator> createState() => _StatusIndicatorState();
}

class _StatusIndicatorState extends State<_StatusIndicator>
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
            color: color.withOpacity(_animation.value),
            borderRadius: BorderRadius.circular(4),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(_animation.value * 0.5),
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
