import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/app_shell.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'fixtures.dart';

class PhoneViewport {
  final String name;
  final Size size;
  final double devicePixelRatio;
  final double topInset;
  final double bottomInset;

  const PhoneViewport(this.name, this.size, this.devicePixelRatio, this.topInset, this.bottomInset);

  @override
  String toString() => name;
}

/// Logical sizes and the standalone (home screen) safe-area insets of the phones used at the presentation.
const List<PhoneViewport> phones = [
  PhoneViewport('iPhone SE 375x667', Size(375, 667), 2, 20, 0),
  PhoneViewport('iPhone 14 390x844', Size(390, 844), 3, 47, 34),
];

/// Inter runs about 10 % wider than the Roboto that stands in for it.
const double interToRobotoWidth = 1.1;

/// The default test font draws every glyph 1 em wide, which reports overflows that never
/// happen on a phone. Roboto stands in for Inter (google_fonts cannot download in tests);
/// weight 600 uses Roboto Bold so the estimate errs on the wide side.
Future<void> loadTestFonts() async {
  final exe = Platform.resolvedExecutable.replaceAll(r'\', '/');
  final dir = '${exe.substring(0, exe.indexOf('/bin/cache/'))}/bin/cache/artifacts/material_fonts';
  const files = {
    100: 'thin',
    200: 'thin',
    300: 'light',
    400: 'regular',
    500: 'medium',
    600: 'bold',
    700: 'bold',
    800: 'black',
    900: 'black',
  };
  Future<void> load(String family, String file) async {
    final bytes = File('$dir/roboto-$file.ttf').readAsBytesSync();
    await (FontLoader(family)..addFont(Future.value(ByteData.sublistView(bytes)))).load();
  }

  for (final entry in files.entries) {
    final weight = entry.key == 400 ? 'regular' : '${entry.key}';
    final italic = entry.key == 400 ? 'italic' : '${entry.key}italic';
    final italicFile = entry.value == 'regular' ? 'italic' : '${entry.value}italic';
    await load('Inter_$weight', entry.value);
    await load('Inter_$italic', italicFile);
  }
  await load('Inter', 'regular');
  await load('Roboto', 'regular');
}

void setViewport(WidgetTester tester, PhoneViewport phone) {
  final dpr = phone.devicePixelRatio;
  tester.view.devicePixelRatio = dpr;
  tester.view.physicalSize = phone.size * dpr;
  tester.view.padding = FakeViewPadding(top: phone.topInset * dpr, bottom: phone.bottomInset * dpr);
  tester.view.viewPadding = FakeViewPadding(top: phone.topInset * dpr, bottom: phone.bottomInset * dpr);
  tester.platformDispatcher.textScaleFactorTestValue = interToRobotoWidth;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

/// Screens call the global `userApiService`, whose http.Client is created lazily: running the
/// whole test inside [http.runWithClient] makes it (and forecast.solar) hit the fixtures.
Future<void> withFixtures(Future<void> Function() body) => http.runWithClient(body, fixtureClient);

Future<void> pumpFrames(WidgetTester tester, {int frames = 15}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> pumpScreen(WidgetTester tester, Widget screen) async {
  await tester.pumpWidget(MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: AppTheme.theme,
    builder: appBuilder,
    home: screen,
  ));
  await pumpFrames(tester);
}

/// Taps [finder] and lets the transition finish; fails on any layout exception (overflow included).
Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pump();
  await tester.tap(finder);
  await pumpFrames(tester);
  expect(tester.takeException(), isNull);
}

Future<void> popRoute(WidgetTester tester) async {
  tester.state<NavigatorState>(find.byType(Navigator).first).pop();
  await pumpFrames(tester);
}
