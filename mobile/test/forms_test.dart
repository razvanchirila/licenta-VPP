import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_interface/main.dart';
import 'package:flutter_interface/screens/devices_screen.dart';
import 'package:flutter_interface/screens/settings_screen.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/home/home_error_state.dart';
import 'package:flutter_interface/widgets/house/flow_indicators.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fixtures.dart';
import 'support/harness.dart';

Map<String, dynamic> sentBody(int index) => json.decode(writeLog[index].body) as Map<String, dynamic>;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(loadTestFonts);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    requestLog.clear();
    writeLog.clear();
    await authState.setSession(token: 'tok', houseId: houseId, username: 'user3', isAdmin: false);
  });

  group('device form', () {
    SwitchListTile startSwitch(WidgetTester tester) => tester.widget<SwitchListTile>(
          find.descendant(of: find.bySemanticsIdentifier('device-form-start'), matching: find.byType(SwitchListTile)),
        );

    testWidgets('a critical device is always created switched on', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, const DevicesScreen());
        await tapAndSettle(tester, find.byIcon(Icons.add_rounded));

        expect(startSwitch(tester).value, isFalse);
        expect(startSwitch(tester).onChanged, isNotNull);

        await tapAndSettle(tester, find.bySemanticsIdentifier('device-form-critical'));
        expect(startSwitch(tester).value, isTrue);
        expect(startSwitch(tester).onChanged, isNull, reason: 'the switch is locked while the device is critical');
        expect(find.text('Un dispozitiv critic este mereu pornit'), findsOneWidget);

        await tester.enterText(find.byType(TextField).first, 'Aparat medical');
        await tester.enterText(find.byType(TextField).last, '80');
        await tapAndSettle(tester, find.widgetWithText(ElevatedButton, 'Adaugă dispozitiv'));

        expect(writeLog.single.method, 'POST');
        expect(sentBody(0), {'name': 'Aparat medical', 'power_w': 80.0, 'critical': true, 'status_on': true});
        expect(find.text('Aparat medical a fost adăugat'), findsOneWidget);
      });
    });

    testWidgets('a device that is not critical keeps the chosen start state', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, const DevicesScreen());
        await tapAndSettle(tester, find.byIcon(Icons.add_rounded));

        await tapAndSettle(tester, find.bySemanticsIdentifier('device-form-critical'));
        await tapAndSettle(tester, find.bySemanticsIdentifier('device-form-critical'));
        expect(startSwitch(tester).value, isFalse);

        await tester.enterText(find.byType(TextField).first, 'Televizor');
        await tester.enterText(find.byType(TextField).last, '120');
        await tapAndSettle(tester, find.widgetWithText(ElevatedButton, 'Adaugă dispozitiv'));

        expect(sentBody(0)['critical'], isFalse);
        expect(sentBody(0)['status_on'], isFalse);
      });
    });

    testWidgets('editing from the details dialog sends name and power', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, const DevicesScreen());
        await tapAndSettle(tester, find.text('Mașină de spălat vase'));
        await tapAndSettle(tester, find.text('Editează'));

        expect(find.text('Editează dispozitivul'), findsWidgets);
        expect(find.bySemanticsIdentifier('device-form-start'), findsNothing);
        expect(find.widgetWithText(TextField, '1800'), findsOneWidget);

        await tester.enterText(find.byType(TextField).first, 'Mașină de vase');
        await tester.enterText(find.byType(TextField).last, '1750,5');
        await tapAndSettle(tester, find.widgetWithText(ElevatedButton, 'Editează dispozitivul'));

        expect(writeLog.single.method, 'PUT');
        expect(writeLog.single.url.path, endsWith('/me/devices/3'));
        expect(sentBody(0), {'name': 'Mașină de vase', 'power_w': 1750.5, 'critical': false});
        expect(find.text('Mașină de vase a fost actualizat'), findsOneWidget);
      });
    });

    testWidgets('making a switched-off device critical also switches it on', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, const DevicesScreen());
        await tapAndSettle(tester, find.text('Mașină de spălat vase'));
        await tapAndSettle(tester, find.text('Editează'));
        await tapAndSettle(tester, find.bySemanticsIdentifier('device-form-critical'));
        expect(find.textContaining('La salvare dispozitivul va fi pornit'), findsOneWidget);
        await tapAndSettle(tester, find.widgetWithText(ElevatedButton, 'Editează dispozitivul'));

        expect(sentBody(0)['critical'], isTrue);
        expect(sentBody(0)['status_on'], isTrue);
      });
    });
  });

  group('trading settings', () {
    Finder priceField() =>
        find.descendant(of: find.bySemanticsIdentifier('trading-fixed-price'), matching: find.byType(TextField));

    testWidgets('a fixed price over the limit is refused inline and not saved', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, const TradingScreen());
        await tapAndSettle(tester, find.text('Setări'));
        await tapAndSettle(tester, find.text('Preț fix'));

        await tester.enterText(priceField(), '25');
        await pumpFrames(tester, frames: 3);
        expect(find.text('Prețul poate fi cel mult 10 lei/kWh'), findsOneWidget);

        await tapAndSettle(tester, find.bySemanticsIdentifier('trading-save'));
        expect(writeLog, isEmpty);
        expect(find.text('Preferințe salvate'), findsNothing);
        expect(find.text('Corectează prețul fix înainte de salvare'), findsOneWidget);

        // the snackbar covers the save button until it goes away
        await tester.pump(const Duration(seconds: 5));
        await pumpFrames(tester);
        await tester.enterText(priceField(), '0,95');
        await pumpFrames(tester, frames: 3);
        expect(find.text('Prețul poate fi cel mult 10 lei/kWh'), findsNothing);
        await tapAndSettle(tester, find.bySemanticsIdentifier('trading-save'));
        expect(sentBody(0)['fixed_price_lei_kwh'], 0.95);
        expect(sentBody(0)['price_mode'], 'fixed');
      });
    });

    testWidgets('the balance limit and the P2P price share come from /api/config', (tester) async {
      setViewport(tester, phones.last);
      await withFixtures(() async {
        await pumpScreen(tester, const TradingScreen());
        await tapAndSettle(tester, find.text('Setări'));
        expect(find.textContaining('soldul este de cel puțin 8 lei'), findsOneWidget);
        expect(find.textContaining('60% din prețul de import'), findsOneWidget);
      });
    });
  });

  testWidgets('settings explain that the mode has no effect while MPC runs', (tester) async {
    setViewport(tester, phones.first);
    await withFixtures(() async {
      await pumpScreen(tester, const SettingsScreen());
      expect(find.bySemanticsIdentifier('settings-mode-note'), findsOneWidget);
      expect(find.textContaining('optimizatorul MPC'), findsOneWidget);
      expect(find.text('Mod Profit'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('home without a house', () {
    const noHouse = ApiException(403, 'Utilizatorul nu are o casa asignata');

    Future<void> pump(WidgetTester tester, {required bool isAdmin, required VoidCallback onLogout}) =>
        tester.pumpWidget(MaterialApp(
          home: Scaffold(
            body: HomeErrorState(
              error: noHouse,
              isAdmin: isAdmin,
              operatorPanelUrl: 'http://vpp.test/admin/',
              onRetry: () {},
              onLogout: onLogout,
            ),
          ),
        ));

    testWidgets('an operator is sent to the operator panel', (tester) async {
      setViewport(tester, phones.first);
      var loggedOut = false;
      await pump(tester, isAdmin: true, onLogout: () => loggedOut = true);

      expect(find.textContaining('cont de operator'), findsOneWidget);
      expect(find.textContaining('Cere administratorului'), findsNothing);
      expect(find.text('Deschide panoul de operator'), findsOneWidget);
      expect(find.text('http://vpp.test/admin/'), findsOneWidget);
      expect(find.text('Reîncearcă'), findsNothing);
      expect(tester.takeException(), isNull);

      await tester.tap(find.text('Deconectare'));
      expect(loggedOut, isTrue);
    });

    testWidgets('a user is told to ask the administrator', (tester) async {
      setViewport(tester, phones.first);
      await pump(tester, isAdmin: false, onLogout: () {});

      expect(find.textContaining('Cere administratorului'), findsOneWidget);
      expect(find.text('Deschide panoul de operator'), findsNothing);
      expect(find.text('Reîncearcă'), findsOneWidget);
    });
  });

  testWidgets('home shows the indoor temperature of the last step and the neighbours flow', (tester) async {
    setViewport(tester, phones.last);
    await withFixtures(() async {
      await tester.pumpWidget(const VppSimulatorApp());
      await pumpFrames(tester);

      expect(find.text('21°'), findsOneWidget);
      expect(find.text('22°'), findsNothing);
      expect(find.text('VECINI'), findsOneWidget);
      expect(requestLog.any((u) => u.path.endsWith('/auth/me')), isTrue, reason: 'the stored user is refreshed');
      await tester.pumpWidget(const SizedBox.shrink());
    });
  });

  testWidgets('the neighbours label carries the direction of the trade', (tester) async {
    Future<void> pump(double kw) =>
        tester.pumpWidget(MaterialApp(home: Scaffold(body: Center(child: NeighbourIndicator(value: kw)))));

    await pump(0.42);
    expect(find.text('0.4 kW'), findsOneWidget);
    expect(find.text('DE LA VECINI'), findsOneWidget);
    await pump(-1.3);
    expect(find.text('1.3 kW'), findsOneWidget);
    expect(find.text('CĂTRE VECINI'), findsOneWidget);
    await pump(0);
    expect(find.text('VECINI'), findsOneWidget);
  });
}
