import 'package:flutter/foundation.dart';
import 'package:flutter/painting.dart';

import 'browser_viewport_stub.dart' if (dart.library.js_interop) 'browser_viewport_web.dart' as impl;

const double phoneLayoutMaxWidth = 600;

/// Flutter web always reports zero view padding, so the notch and the home
/// indicator are read from CSS env(safe-area-inset-*) instead.
EdgeInsets browserSafeArea() {
  final v = impl.safeAreaInsets();
  return EdgeInsets.fromLTRB(v[3], v[0], v[1], v[2]);
}

bool isBrowserStandalone() => impl.isStandalone();

/// The operator panel is served next to the web build; other builds have no such address.
String? operatorPanelUrl() => kIsWeb ? '${Uri.base.origin}/admin/' : null;

/// False when the page could not be opened (pop-up blocked, or not a web build).
bool openBrowserPage(String url) => impl.openPage(url);

/// Phone: full screen with the real status bar. Desktop: the fake iOS status bar demo frame.
bool usePhoneLayout({required TargetPlatform platform, required double width, required bool standalone}) =>
    platform == TargetPlatform.iOS || platform == TargetPlatform.android || standalone || width < phoneLayoutMaxWidth;
