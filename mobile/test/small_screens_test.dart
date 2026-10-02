import 'package:flutter/material.dart';
import 'package:flutter_interface/main.dart';
import 'package:flutter_interface/screens/contact_screen.dart';
import 'package:flutter_interface/screens/devices_screen.dart';
import 'package:flutter_interface/screens/energy_screen.dart';
import 'package:flutter_interface/screens/impact_screen.dart';
import 'package:flutter_interface/screens/settings_screen.dart';
import 'package:flutter_interface/screens/solar_forecast_screen.dart';
import 'package:flutter_interface/screens/statistics_screen.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/bottom_menu.dart';
import 'package:flutter_interface/widgets/ios_status_bar.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fixtures.dart';
import 'support/harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(loadTestFonts);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    requestLog.clear();
    await authState.setSession(token: 'tok', houseId: houseId, username: 'user3', isAdmin: false);
  });

  group('touch targets of at least 44 px on ${phones.first}', () {
    final screens = <String, Widget Function()>{
      'home': () => const VppSimulatorApp(),
      'energy': () => const EnergyScreen(),
      'impact': () => const ImpactScreen(),
      'settings': () => const SettingsScreen(),
      'devices': () => const DevicesScreen(),
      'statistics': () => const StatisticsScreen(),
      'trading': () => const TradingScreen(),
      'solar forecast': () => const SolarForecastScreen(),
      'contact': () => const ContactScreen(),
    };
    for (final entry in screens.entries) {
      testWidgets(entry.key, (tester) async {
        setViewport(tester, phones.first);
        final semantics = tester.ensureSemantics();
        await withFixtures(() async {
          final screen = entry.value();
          if (screen is VppSimulatorApp) {
            await tester.pumpWidget(screen);
            await pumpFrames(tester);
          } else {
            await pumpScreen(tester, screen);
          }
          await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
        });
        semantics.dispose();
      });
    }
  });

  for (final phone in phones) {
    group('$phone', () {
      testWidgets('login, both modes', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await authState.clear();
          await tester.pumpWidget(const VppSimulatorApp());
          await pumpFrames(tester);
          expect(find.text('Autentificare'), findsOneWidget);
          await tapAndSettle(tester, find.text('Nu ai cont? Înregistrează-te'));
          await tapAndSettle(tester, find.text('Înregistrare'));
          expect(find.text('Minim 3 caractere'), findsNothing);
          expect(find.text('Introdu numele de utilizator'), findsOneWidget);
        });
      });

      testWidgets('home dashboard, smart stack pages, menu and profile sheet', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await tester.pumpWidget(const VppSimulatorApp());
          await pumpFrames(tester);
          expect(find.byType(FakeIosStatusBar), findsNothing);
          expect(find.textContaining('Simulare 15/07'), findsOneWidget);
          expect(tester.takeException(), isNull);

          for (var page = 0; page < 2; page++) {
            await tester.fling(find.byType(PageView), const Offset(0, -60), 800);
            await pumpFrames(tester);
            expect(tester.takeException(), isNull);
          }

          await tester.tap(find.byIcon(Icons.person_rounded).first);
          await pumpFrames(tester);
          expect(find.text('Deconectare'), findsOneWidget);
          expect(tester.takeException(), isNull);
          await popRoute(tester);

          final menu = tester.getRect(find.byType(OverlayBottomMenu));
          await tester.tapAt(Offset(menu.center.dx, menu.top + 15));
          await pumpFrames(tester);
          expect(tester.getRect(find.byType(OverlayBottomMenu)).height, greaterThan(300));
          expect(tester.takeException(), isNull);
        });
      });

      testWidgets('home popups: battery details and climate control', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await tester.pumpWidget(const VppSimulatorApp());
          await pumpFrames(tester);
          for (var page = 0; page < 2; page++) {
            await tester.fling(find.byType(PageView), const Offset(0, -60), 800);
            await pumpFrames(tester);
          }
          await tapAndSettle(tester, find.text('Autonomie'));
          expect(find.text('Bateria casei'), findsOneWidget);
          await popRoute(tester);

          for (var page = 0; page < 2; page++) {
            await tester.fling(find.byType(PageView), const Offset(0, 60), 800);
            await pumpFrames(tester);
          }
          await tapAndSettle(tester, find.text('Interior'));
          expect(find.text('Control Climă'), findsOneWidget);
          await tapAndSettle(tester, find.byIcon(Icons.schedule_rounded));
          expect(find.text('Programare Automată'), findsOneWidget);
          await popRoute(tester);
          await tapAndSettle(tester, find.byIcon(Icons.keyboard_arrow_down_rounded));
        });
      });

      testWidgets('energy: day, week, month', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const EnergyScreen());
          expect(tester.takeException(), isNull);
          for (final period in ['Săpt.', 'Lună']) {
            await tester.tap(find.byType(DropdownButton<String>));
            await pumpFrames(tester);
            await tester.tap(find.text(period).last);
            await pumpFrames(tester);
            expect(tester.takeException(), isNull);
          }
          await tapAndSettle(tester, find.byIcon(Icons.tune_rounded));
        });
      });

      testWidgets('impact', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const ImpactScreen());
          expect(find.text('Surse de energie'), findsOneWidget);
          expect(tester.takeException(), isNull);
        });
      });

      testWidgets('settings', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const SettingsScreen());
          expect(find.text('Mod Profit'), findsOneWidget);
          expect(tester.takeException(), isNull);
        });
      });

      testWidgets('devices list and details dialog', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const DevicesScreen());
          expect(find.text('Încărcător mașină electrică'), findsOneWidget);
          expect(tester.takeException(), isNull);
          await tapAndSettle(tester, find.text('Pompă de căldură aer-apă (încălzire și ACM)'));
          await tapAndSettle(tester, find.text('Închide'));
          await tapAndSettle(tester, find.byIcon(Icons.add_rounded));
        });
      });

      testWidgets('statistics: every period', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const StatisticsScreen());
          expect(tester.takeException(), isNull);
          for (final period in ['Zi', 'Săptămână', 'An', 'Lună']) {
            await tapAndSettle(tester, find.text(period));
          }
        });
      });

      testWidgets('trading: all four tabs', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const TradingScreen());
          expect(tester.takeException(), isNull);
          for (final tab in ['Portofel', 'Istoric', 'Setări', 'Preț']) {
            await tapAndSettle(tester, find.text(tab));
          }
        });
      });

      testWidgets('trading: trade details sheet and VPP transfer dialog', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const TradingScreen());
          await tapAndSettle(tester, find.text('Istoric'));
          await tapAndSettle(tester, find.textContaining('12.345 kWh @').first);
          await tapAndSettle(tester, find.text('Închide'));
          await tapAndSettle(tester, find.text('Portofel'));
          await tapAndSettle(tester, find.text('Transferă energie în rezerva VPP').first);
          expect(find.text('Anulează'), findsOneWidget);
        });
      });

      testWidgets('solar forecast', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const SolarForecastScreen());
          expect(find.text('Predicții Solare'), findsOneWidget);
          expect(tester.takeException(), isNull);
        });
      });

      testWidgets('contact', (tester) async {
        setViewport(tester, phone);
        await withFixtures(() async {
          await pumpScreen(tester, const ContactScreen());
          expect(tester.takeException(), isNull);
        });
      });
    });
  }
}
