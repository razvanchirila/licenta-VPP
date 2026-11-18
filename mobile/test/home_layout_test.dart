import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_interface/main.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/bottom_menu.dart';
import 'package:flutter_interface/widgets/smart_stack/smart_stack.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/fixtures.dart';
import 'support/harness.dart';

/// Phones the app is opened on from the home screen (standalone), with their safe-area insets.
const List<PhoneViewport> homeScreenPhones = [
  PhoneViewport('iPhone SE 375x667', Size(375, 667), 2, 20, 0),
  PhoneViewport('iPhone 14 390x844', Size(390, 844), 3, 47, 34),
  PhoneViewport('iPhone 14 Pro 393x852', Size(393, 852), 3, 59, 34),
  PhoneViewport('iPhone 14 Pro Max 430x932', Size(430, 932), 3, 59, 34),
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(loadTestFonts);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    requestLog.clear();
    await authState.setSession(token: 'tok', houseId: houseId, username: 'user3', isAdmin: false);
  });

  for (final phone in homeScreenPhones) {
    testWidgets('$phone: edge to edge home, flow labels clear of the card row', (tester) async {
      debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
      setViewport(tester, phone);
      await withFixtures(() async {
        await tester.pumpWidget(const VppSimulatorApp());
        await pumpFrames(tester);
        expect(tester.takeException(), isNull);

        final screen = Offset.zero & phone.size;
        final menu = tester.getRect(find.byType(OverlayBottomMenu));
        expect(menu.bottom, screen.bottom, reason: 'the menu sheet reaches the bottom edge');
        final handleBar = tester.getRect(
          find.descendant(of: find.bySemanticsIdentifier('menu-toggle'), matching: find.byType(AnimatedContainer)),
        );
        expect(handleBar.bottom, lessThanOrEqualTo(screen.bottom - phone.bottomInset),
            reason: 'the visible handle sits above the home indicator');
        expect(menu.height, lessThanOrEqualTo(70), reason: 'the collapsed sheet stays thin');

        final cards = tester.getRect(find.byType(SmartStack));
        expect(cards.bottom, lessThanOrEqualTo(menu.top));
        for (final caption in ['BATERIE', 'REȚEA', 'VECINI', '68%']) {
          final label = tester.getRect(find.text(caption));
          expect(label.bottom, lessThanOrEqualTo(cards.top), reason: '$caption overlaps the card row');
          expect(label.top, greaterThanOrEqualTo(phone.topInset));
        }

        // 'CĂTRE VECINI' is about 25 px wider on each side than the idle label measured here
        final neighbours = tester.getRect(find.text('VECINI'));
        expect(neighbours.left, greaterThanOrEqualTo(25), reason: 'neighbours label leaves the screen');
        expect(neighbours.right + 25, lessThan(tester.getRect(find.bySemanticsIdentifier('home-battery')).left),
            reason: 'neighbours label runs into the battery label');

        final greeting = tester.getRect(find.textContaining('user3'));
        expect(greeting.top, greaterThanOrEqualTo(phone.topInset > 0 ? phone.topInset + 20 : 0),
            reason: 'header clear of the band iOS blurs under the status bar');

        for (final text in ['Vreme', 'Interior']) {
          final paragraph = tester.renderObject<RenderParagraph>(find.text(text));
          expect(paragraph.didExceedMaxLines, isFalse, reason: '$text is truncated');
        }
      });
      await tester.pumpWidget(const SizedBox.shrink());
      debugDefaultTargetPlatformOverride = null;
    });
  }
}
