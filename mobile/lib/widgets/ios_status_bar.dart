import 'dart:async';

import 'package:flutter/material.dart';

/// Desktop browsers only; phones get the real status bar (see AppShell).
const bool kShowFakeIosStatusBar = true;

class FakeIosStatusBar extends StatefulWidget {
  final Widget child;
  final Color backgroundColor;

  const FakeIosStatusBar({
    super.key,
    required this.child,
    this.backgroundColor = Colors.transparent,
  });

  @override
  State<FakeIosStatusBar> createState() => _FakeIosStatusBarState();
}

class _FakeIosStatusBarState extends State<FakeIosStatusBar> {
  Timer? _timer;
  String _currentTime = '';

  @override
  void initState() {
    super.initState();
    _updateTime();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _updateTime());
  }

  @override
  void dispose() {
    _timer?.cancel();
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
                  Positioned(
                    left: 0,
                    child: Text(
                      _currentTime,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                        decoration: TextDecoration.none,
                      ),
                    ),
                  ),
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
                  const Positioned(
                    right: 0,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _CellularSignal(),
                        SizedBox(width: 6),
                        Icon(Icons.wifi_rounded, color: Colors.white, size: 18),
                        SizedBox(width: 6),
                        _BatteryIndicator(),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        Expanded(child: widget.child),
      ],
    );
  }
}

class _CellularSignal extends StatelessWidget {
  const _CellularSignal();

  @override
  Widget build(BuildContext context) {
    return const Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        _SignalBar(4),
        SizedBox(width: 1.5),
        _SignalBar(6),
        SizedBox(width: 1.5),
        _SignalBar(8),
        SizedBox(width: 1.5),
        _SignalBar(11),
      ],
    );
  }
}

class _SignalBar extends StatelessWidget {
  final double height;
  const _SignalBar(this.height);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 3,
      height: height,
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(1)),
    );
  }
}

class _BatteryIndicator extends StatelessWidget {
  const _BatteryIndicator();

  @override
  Widget build(BuildContext context) {
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
                  flex: 85,
                  child: Container(
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(1)),
                  ),
                ),
                const Expanded(flex: 15, child: SizedBox()),
              ],
            ),
          ),
        ),
        Container(
          width: 2,
          height: 5,
          margin: const EdgeInsets.only(left: 1),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.horizontal(right: Radius.circular(1)),
          ),
        ),
      ],
    );
  }
}
