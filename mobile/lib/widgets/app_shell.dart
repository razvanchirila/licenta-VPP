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

    final browserInsets = browserSafeArea();
    return ColoredBox(
      color: AppColors.deepBackground,
      child: MediaQuery(
        data: media.copyWith(
          padding: _max(media.padding, browserInsets),
          viewPadding: _max(media.viewPadding, browserInsets),
        ),
        child: SafeArea(child: child),
      ),
    );
  }

  static EdgeInsets _max(EdgeInsets a, EdgeInsets b) => EdgeInsets.fromLTRB(
        a.left > b.left ? a.left : b.left,
        a.top > b.top ? a.top : b.top,
        a.right > b.right ? a.right : b.right,
        a.bottom > b.bottom ? a.bottom : b.bottom,
      );
}
