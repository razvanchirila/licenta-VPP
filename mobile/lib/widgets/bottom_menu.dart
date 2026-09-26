import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/screens/contact_screen.dart';
import 'package:flutter_interface/screens/devices_screen.dart';
import 'package:flutter_interface/screens/energy_screen.dart';
import 'package:flutter_interface/screens/impact_screen.dart';
import 'package:flutter_interface/screens/settings_screen.dart';
import 'package:flutter_interface/screens/statistics_screen.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/core/theme.dart';

class _MenuEntry {
  final IconData icon;
  final String title;
  final Widget Function() build;

  const _MenuEntry(this.icon, this.title, this.build);
}

final List<_MenuEntry> _entries = [
  _MenuEntry(Icons.trending_up, 'Energie', () => const EnergyScreen()),
  _MenuEntry(Icons.eco, 'Impact', () => const ImpactScreen()),
  _MenuEntry(Icons.settings, 'Setări', () => const SettingsScreen()),
  _MenuEntry(Icons.devices_other_rounded, 'Dispozitive', () => const DevicesScreen()),
  _MenuEntry(Icons.bar_chart_rounded, 'Statistici', () => const StatisticsScreen()),
  _MenuEntry(Icons.swap_horiz_rounded, 'Trading P2P', () => const TradingScreen()),
  _MenuEntry(Icons.contact_support_rounded, 'Contact', () => const ContactScreen()),
];

class OverlayBottomMenu extends StatefulWidget {
  const OverlayBottomMenu({super.key});

  @override
  State<OverlayBottomMenu> createState() => _OverlayBottomMenuState();
}

class _OverlayBottomMenuState extends State<OverlayBottomMenu> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  double _dragExtent = 0;
  final double _minHeight = 60;
  final double _maxHeight = 420;

  bool get _isExpanded => _animation.value > 0.5;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _handleDragStart(DragStartDetails details) {
    _dragExtent = _controller.value * (_maxHeight - _minHeight);
  }

  void _handleDragUpdate(DragUpdateDetails details) {
    _dragExtent -= details.primaryDelta ?? 0;
    _dragExtent = _dragExtent.clamp(0.0, _maxHeight - _minHeight);
    _controller.value = _dragExtent / (_maxHeight - _minHeight);
  }

  void _handleDragEnd(DragEndDetails details) {
    final velocity = details.primaryVelocity ?? 0;
    if (velocity.abs() > 500) {
      _controller.animateTo(velocity < 0 ? 1.0 : 0.0);
    } else {
      _controller.animateTo(_controller.value > 0.5 ? 1.0 : 0.0);
    }
  }

  void _toggleMenu() {
    _controller.animateTo(_isExpanded ? 0.0 : 1.0);
  }

  Future<void> _open(Widget Function() build) async {
    await _controller.animateTo(0.0);
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => build()));
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        final height = _minHeight + (_maxHeight - _minHeight) * _animation.value;

        return GestureDetector(
          onVerticalDragStart: _handleDragStart,
          onVerticalDragUpdate: _handleDragUpdate,
          onVerticalDragEnd: _handleDragEnd,
          child: ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
              child: Container(
                height: height,
                decoration: BoxDecoration(
                  color: AppColors.surfaceAlt.withValues(alpha: 0.85),
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
                  border: Border(
                    top: BorderSide(
                      color: Colors.white.withValues(alpha: 0.1),
                      width: 1,
                    ),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.5),
                      blurRadius: 30,
                      offset: const Offset(0, -10),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: _toggleMenu,
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        child: Center(
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            width: 40,
                            height: 5,
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: _isExpanded ? 0.4 : 0.25),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: IgnorePointer(
                        ignoring: !_isExpanded,
                        child: ClipRect(
                          child: Opacity(
                            opacity: _animation.value.clamp(0.0, 1.0),
                            child: SingleChildScrollView(
                              physics:
                                  _isExpanded ? const BouncingScrollPhysics() : const NeverScrollableScrollPhysics(),
                              child: Column(
                                children: [
                                  for (final e in _entries)
                                    TeslaMenuItem(
                                      icon: e.icon,
                                      title: e.title,
                                      onTap: () => _open(e.build),
                                    ),
                                  const SizedBox(height: 24),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class TeslaMenuItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;

  const TeslaMenuItem({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        splashColor: Colors.white.withValues(alpha: 0.08),
        highlightColor: Colors.white.withValues(alpha: 0.04),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: 24,
            vertical: subtitle != null ? 12 : 16,
          ),
          child: Row(
            children: [
              Icon(
                icon,
                color: Colors.white.withValues(alpha: 0.9),
                size: 24,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w500,
                        letterSpacing: -0.3,
                      ),
                    ),
                    if (subtitle != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        subtitle!,
                        style: GoogleFonts.inter(
                          color: Colors.white.withValues(alpha: 0.5),
                          fontSize: 13,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: Colors.white.withValues(alpha: 0.35),
                size: 24,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
