import 'package:flutter/material.dart';
import 'dart:async';

/// Widget care simulează status bar-ul iOS cu Dynamic Island
/// pentru a face aplicația să arate ca pe un iPhone în videoclipuri
class IosStatusBar extends StatefulWidget {
  final Widget child;
  final Color backgroundColor;
  
  const IosStatusBar({
    super.key,
    required this.child,
    this.backgroundColor = Colors.transparent,
  });

  @override
  State<IosStatusBar> createState() => _IosStatusBarState();
}

class _IosStatusBarState extends State<IosStatusBar> {
  late Timer _timer;
  String _currentTime = '';
  
  @override
  void initState() {
    super.initState();
    _updateTime();
    // Actualizează ora la fiecare secundă
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _updateTime());
  }
  
  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }
  
  void _updateTime() {
    final now = DateTime.now();
    setState(() {
      _currentTime = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // iOS Status Bar simulat
        Container(
          color: widget.backgroundColor,
          child: SafeArea(
            bottom: false,
            child: Container(
              height: 54,
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Ora - stânga
                  Positioned(
                    left: 0,
                    child: Text(
                      _currentTime,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                        decoration: TextDecoration.none, // Elimină sublinierea
                      ),
                    ),
                  ),
                  
                  // Dynamic Island - centru
                  Center(
                    child: Container(
                      width: 126,
                      height: 37,
                      decoration: BoxDecoration(
                        color: Colors.black,
                        borderRadius: BorderRadius.circular(24),
                      ),
                    ),
                  ),
                  
                  // Iconițe dreapta - Signal, WiFi, Baterie
                  Positioned(
                    right: 0,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Signal cellular
                        _buildCellularSignal(),
                        const SizedBox(width: 6),
                        // WiFi
                        const Icon(
                          Icons.wifi_rounded,
                          color: Colors.white,
                          size: 18,
                        ),
                        const SizedBox(width: 6),
                        // Baterie
                        _buildBatteryIndicator(),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        // Conținutul aplicației
        Expanded(child: widget.child),
      ],
    );
  }
  
  /// Construiește indicatorul de semnal cellular (4 bare)
  Widget _buildCellularSignal() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        _buildSignalBar(4, true),
        const SizedBox(width: 1.5),
        _buildSignalBar(6, true),
        const SizedBox(width: 1.5),
        _buildSignalBar(8, true),
        const SizedBox(width: 1.5),
        _buildSignalBar(11, true),
      ],
    );
  }
  
  Widget _buildSignalBar(double height, bool active) {
    return Container(
      width: 3,
      height: height,
      decoration: BoxDecoration(
        color: active ? Colors.white : Colors.white.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(1),
      ),
    );
  }
  
  /// Construiește indicatorul de baterie stil iOS
  Widget _buildBatteryIndicator() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 25,
          height: 12,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.white, width: 1),
            borderRadius: BorderRadius.circular(3),
          ),
          child: Padding(
            padding: const EdgeInsets.all(1.5),
            child: Row(
              children: [
                Expanded(
                  flex: 85, // 85% baterie
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(1),
                    ),
                  ),
                ),
                const Expanded(flex: 15, child: SizedBox()),
              ],
            ),
          ),
        ),
        // Capătul bateriei
        Container(
          width: 2,
          height: 5,
          margin: const EdgeInsets.only(left: 1),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: const BorderRadius.horizontal(right: Radius.circular(1)),
          ),
        ),
      ],
    );
  }
}
