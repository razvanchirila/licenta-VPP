import 'dart:ui' show Tristate;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_interface/main.dart';
import 'package:flutter_interface/screens/contact_screen.dart';
import 'package:flutter_interface/screens/devices_screen.dart';
import 'package:flutter_interface/screens/statistics_screen.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/app_shell.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fixtures.dart';
import 'support/harness.dart';

SemanticsData semanticsOf(WidgetTester tester, String id) =>
    tester.getSemantics(find.bySemanticsIdentifier(id)).getSemanticsData();

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(loadTestFonts);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    requestLog.clear();
    await authState.setSession(token: 'tok', houseId: houseId, username: 'user3', isAdmin: false);
  });

  testWidgets('login fields, button and the server error are exposed', (tester) async {
    setViewport(tester, phones.last);
    final handle = tester.ensureSemantics();
    await withFixtures(() async {
      await authState.clear();
      await tester.pumpWidget(const VppSimulatorApp());
      await pumpFrames(tester);

      expect(semanticsOf(tester, 'login-submit').label, 'Autentificare');
      await tester.enterText(find.byType(TextFormField).first, 'user3');
      await tester.enterText(find.byType(TextFormField).last, 'gresita');
      await tester.tap(find.text('Autentificare'));
      await pumpFrames(tester);

      final error = semanticsOf(tester, 'login-error');
      expect(error.label, 'Not found');
      expect(error.flagsCollection.isLiveRegion, isTrue);
      expect(find.bySemanticsIdentifier('login-username'), findsOneWidget);
      expect(find.bySemanticsIdentifier('login-password'), findsOneWidget);
    });
    handle.dispose();
  });

  testWidgets('home values read as one label/value pair each', (tester) async {
    setViewport(tester, phones.last);
    final handle = tester.ensureSemantics();
    await withFixtures(() async {
      await tester.pumpWidget(const VppSimulatorApp());
      await pumpFrames(tester);

      expect(semanticsOf(tester, 'home-solar').label, 'SOLAR');
      expect(semanticsOf(tester, 'home-solar').value, '8.1 kW');
      expect(semanticsOf(tester, 'home-load').value, '14.7 kW');
      expect(semanticsOf(tester, 'home-battery').value, '6.5 kW descărcare');
      expect(semanticsOf(tester, 'home-grid').value, '0.0 kW');
      expect(semanticsOf(tester, 'home-soc').value, '68%');
      expect(semanticsOf(tester, 'home-sim-clock').label, startsWith('Simulare '));

      expect(find.bySemanticsIdentifier('menu-energie'), findsNothing);
      await tapAndSettle(tester, find.bySemanticsIdentifier('menu-toggle'));
      for (final id in ['energie', 'impact', 'setari', 'dispozitive', 'statistici', 'trading', 'contact']) {
        final entry = semanticsOf(tester, 'menu-$id');
        expect(entry.flagsCollection.isButton, isTrue, reason: id);
      }
      await tester.pumpWidget(const SizedBox.shrink());
    });
    handle.dispose();
  });

  testWidgets('device switches report their state; critical ones are disabled', (tester) async {
    setViewport(tester, phones.last);
    final handle = tester.ensureSemantics();
    await withFixtures(() async {
      await pumpScreen(tester, const DevicesScreen());
      for (final d in devices) {
        final toggle = semanticsOf(tester, 'device-${d['id']}-toggle');
        expect(toggle.flagsCollection.isToggled, d['status_on'] == true ? Tristate.isTrue : Tristate.isFalse);
        expect(toggle.flagsCollection.isEnabled, d['critical'] == true ? Tristate.isFalse : Tristate.isTrue);
      }
    });
    handle.dispose();
  });

  testWidgets('the desktop status bar is not hidden by the page route', (tester) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.windows;
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final handle = tester.ensureSemantics();

    await tester.pumpWidget(const MaterialApp(builder: appBuilder, home: Scaffold(body: Text('pagina'))));
    await tester.pump();

    expect(semanticsOf(tester, 'fake-status-bar').label, 'Bară de stare demonstrativă');
    expect(find.bySemanticsLabel('pagina'), findsOneWidget);
    handle.dispose();
    debugDefaultTargetPlatformOverride = null;
  });

  for (final entry in <String, Widget Function()>{
    'statistics': () => const StatisticsScreen(),
    'trading': () => const TradingScreen(),
    'contact': () => const ContactScreen(),
  }.entries) {
    testWidgets('${entry.key}: the back button has a Romanian tooltip', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, entry.value());
        expect(find.byTooltip('Înapoi'), findsOneWidget);
        expect(find.byTooltip('Back'), findsNothing);
        expect(find.bySemanticsIdentifier('back'), findsOneWidget);
      });
    });
  }
}
