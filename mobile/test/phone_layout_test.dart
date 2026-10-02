import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_interface/core/browser_viewport.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/screens/solar_forecast_screen.dart';
import 'package:flutter_interface/screens/statistics_screen.dart';
import 'package:flutter_interface/services/solar_forecast_service.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/app_shell.dart';
import 'package:flutter_interface/widgets/ios_status_bar.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';
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

  group('usePhoneLayout', () {
    test('phones and tablets are always phone layout, whatever the width', () {
      expect(usePhoneLayout(platform: TargetPlatform.iOS, width: 390, standalone: false), isTrue);
      expect(usePhoneLayout(platform: TargetPlatform.iOS, width: 1024, standalone: false), isTrue);
      expect(usePhoneLayout(platform: TargetPlatform.android, width: 412, standalone: false), isTrue);
    });

    test('desktop browsers get the demo frame unless narrow or installed', () {
      expect(usePhoneLayout(platform: TargetPlatform.windows, width: 1440, standalone: false), isFalse);
      expect(usePhoneLayout(platform: TargetPlatform.macOS, width: 1280, standalone: false), isFalse);
      expect(usePhoneLayout(platform: TargetPlatform.windows, width: 420, standalone: false), isTrue);
      expect(usePhoneLayout(platform: TargetPlatform.windows, width: 1440, standalone: true), isTrue);
    });
  });

  group('AppShell', () {
    Future<void> pumpShell(WidgetTester tester) async {
      await tester.pumpWidget(const MaterialApp(
        builder: appBuilder,
        home: Scaffold(body: SizedBox.expand(key: Key('content'))),
      ));
      await tester.pump();
    }

    testWidgets('wide desktop window keeps the fake iOS status bar', (tester) async {
      debugDefaultTargetPlatformOverride = TargetPlatform.windows;
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);

      await pumpShell(tester);

      expect(find.byType(FakeIosStatusBar), findsOneWidget);
      expect(tester.getTopLeft(find.byKey(const Key('content'))).dy, greaterThanOrEqualTo(54));
      await tester.pumpWidget(const SizedBox.shrink());
      debugDefaultTargetPlatformOverride = null;
    });

    testWidgets('iPhone: no fake bar, content clears the notch and the home indicator', (tester) async {
      debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
      setViewport(tester, phones.last);

      await pumpShell(tester);

      expect(find.byType(FakeIosStatusBar), findsNothing);
      final content = tester.getRect(find.byKey(const Key('content')));
      expect(content.top, phones.last.topInset);
      expect(content.bottom, phones.last.size.height - phones.last.bottomInset);
      debugDefaultTargetPlatformOverride = null;
    });
  });

  group('statistics use the simulated day', () {
    test('simulatedNow prefers the current step, then the curve date, then the clock', () {
      final fallback = DateTime(2026, 10, 2, 12);
      final prices = SimPrices.fromJson(simPrices());
      expect(StatisticsRules.simulatedNow(prices, fallback), DateTime(2026, 7, 15, 13, 30));
      const empty = SimPrices(date: '2026-07-15', dtHours: 0.25, currentStep: 0, prices: []);
      expect(StatisticsRules.simulatedNow(empty, fallback), DateTime(2026, 7, 15));
      expect(StatisticsRules.simulatedNow(null, fallback), fallback);
    });

    testWidgets('the chart request ends on the simulated date, not today', (tester) async {
      setViewport(tester, phones.first);
      await withFixtures(() async {
        await pumpScreen(tester, const StatisticsScreen());
        final chart = requestLog.lastWhere((u) => u.path.endsWith('/stats/chart'));
        expect(chart.queryParameters['end_date'], simDate);
        expect(chart.queryParameters['start_date'], '2026-06-15');
      });
    });
  });

  testWidgets('forecast.solar is asked for the simulated PV site', (tester) async {
    setViewport(tester, phones.first);
    await withFixtures(() async {
      await pumpScreen(tester, const SolarForecastScreen());
      final forecast = requestLog.singleWhere((u) => u.host == 'api.forecast.solar');
      expect(forecast.path, contains('/${SiteLocation.latitude}/${SiteLocation.longitude}/'));
    });
    expect(SolarForecastService.defaultLatitude, SiteLocation.latitude);
    expect(SiteLocation.query, '46.57,26.91');
  });
}
