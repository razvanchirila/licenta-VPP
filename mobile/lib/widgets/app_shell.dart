import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_interface/core/browser_viewport.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/ios_status_bar.dart';

/// `MaterialApp.builder`: clamps the system text scale and picks the phone or desktop frame.
Widget appBuilder(BuildContext context, Widget? child) {
  final media = MediaQuery.of(context);
  return MediaQuery(
    data: media.copyWith(textScaler: TextScaler.linear(media.textScaler.scale(1.0).clamp(0.8, 1.2))),
    child: AppShell(child: child ?? const SizedBox.shrink()),
  );
}

class AppShell extends StatelessWidget {
  final Widget child;

  const AppShell({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    final phone = usePhoneLayout(
      platform: defaultTargetPlatform,
      width: media.size.width,
      standalone: isBrowserStandalone(),
    );
    if (!phone && kShowFakeIosStatusBar) {
      return FakeIosStatusBar(backgroundColor: AppColors.deepBackground, child: child);
    }

    // The app draws edge to edge (under the status bar and the home indicator); the insets only
    // reach the screens through MediaQuery, so backgrounds and sheets still fill the screen.
    // iOS also blurs content in a band just below a translucent status bar, so every screen starts
    // a little lower than the bare safe area.
    final measured = _max(media.padding, browserSafeArea());
    final insets = measured.top > 0 ? measured.copyWith(top: measured.top + statusBarClearance) : measured;
    return ColoredBox(
      color: AppColors.deepBackground,
      child: MediaQuery(
        data: media.copyWith(
          padding: insets,
          viewPadding: _max(media.viewPadding, insets),
        ),
        child: child,
      ),
    );
  }

  static const double statusBarClearance = 24;

  static EdgeInsets _max(EdgeInsets a, EdgeInsets b) => EdgeInsets.fromLTRB(
        a.left > b.left ? a.left : b.left,
        a.top > b.top ? a.top : b.top,
        a.right > b.right ? a.right : b.right,
        a.bottom > b.bottom ? a.bottom : b.bottom,
      );
}
