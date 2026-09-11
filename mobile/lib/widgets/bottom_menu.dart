import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/screens/settings_screen.dart';
import 'package:flutter_interface/screens/impact_screen.dart';
import 'package:flutter_interface/screens/energy_screen.dart';
import 'package:flutter_interface/screens/devices_screen.dart';
import 'package:flutter_interface/screens/coming_soon_screen.dart';
import 'package:flutter_interface/screens/statistics_screen.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/screens/contact_screen.dart';

class BottomMenu extends StatelessWidget {
  const BottomMenu({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF111111),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.6),
            blurRadius: 24,
            offset: const Offset(0, -8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            margin: const EdgeInsets.only(top: 14, bottom: 10),
            width: 40,
            height: 5,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.25),
              borderRadius: BorderRadius.circular(3),
            ),
          ),
          // Menu items
          TeslaMenuItem(
            icon: Icons.trending_up,
            title: 'Energy',
            onTap: () {},
          ),
          TeslaMenuItem(
            icon: Icons.eco,
            title: 'Impact',
            onTap: () {},
          ),
          TeslaMenuItem(
            icon: Icons.settings,
            title: 'Settings',
            onTap: () {},
          ),
          TeslaMenuItem(
            icon: Icons.contact_support_rounded,
            title: 'Contact',
            onTap: () {},
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

// Versiune draggable a meniului (legacy)
class DraggableBottomMenu extends StatefulWidget {
  const DraggableBottomMenu({super.key});

  @override
  State<DraggableBottomMenu> createState() => _DraggableBottomMenuState();
}

class _DraggableBottomMenuState extends State<DraggableBottomMenu>
    with SingleTickerProviderStateMixin {
  bool _isExpanded = false;
  late AnimationController _controller;
  late Animation<double> _heightAnimation;

  final double _collapsedHeight = 340;
  final double _expandedHeight = 500;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _heightAnimation = Tween<double>(
      begin: _collapsedHeight,
      end: _expandedHeight,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    ));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  void _handleDragUpdate(DragUpdateDetails details) {
    if (details.primaryDelta! < -5 && !_isExpanded) {
      _toggleExpanded();
    } else if (details.primaryDelta! > 5 && _isExpanded) {
      _toggleExpanded();
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onVerticalDragUpdate: _handleDragUpdate,
      onTap: _toggleExpanded,
      child: AnimatedBuilder(
        animation: _heightAnimation,
        builder: (context, child) {
          return Container(
            constraints: BoxConstraints(
              maxHeight: _heightAnimation.value,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFF111111),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.6),
                  blurRadius: 24,
                  offset: const Offset(0, -8),
                ),
              ],
            ),
            child: SingleChildScrollView(
              physics: const NeverScrollableScrollPhysics(),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 14, bottom: 10),
                    width: 40,
                    height: 5,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.25),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                  TeslaMenuItem(
                    icon: Icons.trending_up,
                    title: 'Energy',
                    subtitle: _isExpanded ? 'View energy usage details' : null,
                    onTap: () {},
                  ),
                  TeslaMenuItem(
                    icon: Icons.eco,
                    title: 'Impact',
                    subtitle: _isExpanded ? 'Environmental benefits' : null,
                    onTap: () {},
                  ),
                  TeslaMenuItem(
                    icon: Icons.settings,
                    title: 'Settings',
                    subtitle: _isExpanded ? 'Configure your system' : null,
                    onTap: () {},
                  ),
                  TeslaMenuItem(
                    icon: Icons.contact_support_rounded,
                    title: 'Contact',
                    subtitle: _isExpanded ? 'Contactează-ne' : null,
                    onTap: () {},
                  ),
                  if (_isExpanded) ...[
                    const Divider(color: Colors.white12, height: 1),
                    TeslaMenuItem(
                      icon: Icons.history,
                      title: 'History',
                      subtitle: 'View past data',
                      onTap: () {},
                    ),
                    TeslaMenuItem(
                      icon: Icons.notifications_outlined,
                      title: 'Notifications',
                      subtitle: 'Manage alerts',
                      onTap: () {},
                    ),
                  ],
                  const SizedBox(height: 24),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

// OVERLAY BOTTOM MENU - se suprapune peste conținut cu animație smooth
class OverlayBottomMenu extends StatefulWidget {
  const OverlayBottomMenu({super.key});

  @override
  State<OverlayBottomMenu> createState() => _OverlayBottomMenuState();
}

class _OverlayBottomMenuState extends State<OverlayBottomMenu>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  
  double _dragExtent = 0;
  final double _minHeight = 60; // Doar drag handle vizibil
  final double _maxHeight = 420; // Meniu complet expandat
  
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
    _dragExtent -= details.primaryDelta!;
    _dragExtent = _dragExtent.clamp(0.0, _maxHeight - _minHeight);
    _controller.value = _dragExtent / (_maxHeight - _minHeight);
  }

  void _handleDragEnd(DragEndDetails details) {
    final velocity = details.primaryVelocity ?? 0;
    
    // Dacă viteza e mare, animează în direcția swipe-ului
    if (velocity.abs() > 500) {
      if (velocity < 0) {
        // Swipe în sus - expandează
        _controller.animateTo(1.0);
      } else {
        // Swipe în jos - închide
        _controller.animateTo(0.0);
      }
    } else {
      // Bazat pe poziția curentă
      if (_controller.value > 0.5) {
        _controller.animateTo(1.0);
      } else {
        _controller.animateTo(0.0);
      }
    }
  }

  void _toggleMenu() {
    if (_isExpanded) {
      _controller.animateTo(0.0);
    } else {
      _controller.animateTo(1.0);
    }
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
          // onTap mutat pe drag handle pentru a evita tap-uri accidentale
          child: ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
              child: Container(
                height: height,
                decoration: BoxDecoration(
                  // Glassmorphism: gri închis semi-transparent
                  color: const Color(0xFF1A1A1A).withOpacity(0.85),
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
                  border: Border(
                    top: BorderSide(
                      color: Colors.white.withOpacity(0.1),
                      width: 1,
                    ),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.5),
                      blurRadius: 30,
                      offset: const Offset(0, -10),
                    ),
                  ],
                ),
                child: Column(
              children: [
                // Drag handle - mereu vizibil, tap pentru toggle
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
                          color: Colors.white.withOpacity(_isExpanded ? 0.4 : 0.25),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                    ),
                  ),
                ),
                
                // Conținutul meniului (cu fade și clip)
                // IgnorePointer când meniul e collapsed pentru a preveni tap-uri accidentale
                Expanded(
                  child: IgnorePointer(
                    ignoring: !_isExpanded,
                    child: ClipRect(
                      child: Opacity(
                        opacity: _animation.value.clamp(0.0, 1.0),
                        child: SingleChildScrollView(
                          physics: _isExpanded 
                              ? const BouncingScrollPhysics() 
                              : const NeverScrollableScrollPhysics(),
                          child: Column(
                            children: [
                            TeslaMenuItem(
                              icon: Icons.trending_up,
                              title: 'Energy',
                              onTap: () {
                                // Close menu first, then navigate
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const EnergyScreen(),
                                    ),
                                  );
                                });
                              },
                            ),
                            TeslaMenuItem(
                              icon: Icons.eco,
                              title: 'Impact',
                              onTap: () {
                                // Close menu first, then navigate
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const ImpactScreen(),
                                    ),
                                  );
                                });
                              },
                            ),
                            TeslaMenuItem(
                              icon: Icons.settings,
                              title: 'Settings',
                              onTap: () {
                                // Close menu first, then navigate
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const SettingsScreen(),
                                    ),
                                  );
                                });
                              },
                            ),
                            TeslaMenuItem(
                              icon: Icons.devices_other_rounded,
                              title: 'Devices',
                              onTap: () {
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const DevicesScreen(),
                                    ),
                                  );
                                });
                              },
                            ),
                            TeslaMenuItem(
                              icon: Icons.bar_chart_rounded,
                              title: 'Statistics',
                              onTap: () {
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const StatisticsScreen(),
                                    ),
                                  );
                                });
                              },
                            ),
                            TeslaMenuItem(
                              icon: Icons.swap_horiz_rounded,
                              title: 'P2P Trading',
                              onTap: () {
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const TradingScreen(),
                                    ),
                                  );
                                });
                              },
                            ),
                            TeslaMenuItem(
                              icon: Icons.contact_support_rounded,
                              title: 'Contact',
                              onTap: () {
                                _controller.animateTo(0.0).then((_) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) => const ContactScreen(),
                                    ),
                                  );
                                });
                              },
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
        splashColor: Colors.white.withOpacity(0.08),
        highlightColor: Colors.white.withOpacity(0.04),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: 24,
            vertical: subtitle != null ? 12 : 16,
          ),
          child: Row(
            children: [
              Icon(
                icon,
                color: Colors.white.withOpacity(0.9),
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
                          color: Colors.white.withOpacity(0.5),
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
                color: Colors.white.withOpacity(0.35),
                size: 24,
              ),
            ],
          ),
        ),
      ),
    );
  }
}