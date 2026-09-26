import 'dart:convert';

import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late AuthState auth;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    auth = AuthState();
    await auth.setSession(token: 'tok', houseId: 3, username: 'user3', isAdmin: false);
  });

  ApiClient clientWith(Future<http.Response> Function(http.Request) handler) =>
      ApiClient(auth: auth, baseUrl: 'http://test/api', client: MockClient(handler));

  test('sends the JWT header and decodes JSON', () async {
    http.Request? seen;
    final client = clientWith((req) async {
      seen = req;
      return http.Response(json.encode({'ok': true, 'value': 1.5}), 200);
    });

    final result = await client.get('/me/house') as Map<String, dynamic>;

    expect(result['ok'], isTrue);
    expect(seen!.headers['Authorization'], 'Bearer tok');
    expect(seen!.url.toString(), 'http://test/api/me/house');
  });

  test('encodes query parameters and skips null values', () async {
    http.Request? seen;
    final client = clientWith((req) async {
      seen = req;
      return http.Response('{}', 200);
    });

    await client.get('/me/energy/chart', query: {'period': 'day', 'date': '2026-09-11', 'x': null});

    expect(seen!.url.queryParameters, {'period': 'day', 'date': '2026-09-11'});
  });

  test('401 clears the session and throws ApiException', () async {
    var notified = 0;
    auth.addListener(() => notified++);
    final client = clientWith((req) async => http.Response('{"detail": "Not authenticated"}', 401));

    expect(auth.isLoggedIn, isTrue);
    await expectLater(
      client.get('/me/house'),
      throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 401)),
    );
    expect(auth.isLoggedIn, isFalse);
    expect(auth.houseId, isNull);
    expect(notified, greaterThan(0));

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('jwt_token'), isNull);
  });

  test('401 on login shows the server message and keeps nothing to clear', () async {
    await auth.clear();
    final client = clientWith(
      (req) async => http.Response('{"detail": "Utilizator sau parola gresita"}', 401),
    );

    await expectLater(
      client.post('/auth/login', body: {'username': 'u', 'password': 'x'}, withAuth: false),
      throwsA(isA<ApiException>()
          .having((e) => e.statusCode, 'statusCode', 401)
          .having((e) => e.message, 'message', 'Utilizator sau parola gresita')),
    );
  });

  test('401 on an anonymous call does not clear an existing session', () async {
    var notified = 0;
    auth.addListener(() => notified++);
    final client = clientWith((req) async => http.Response('{"detail": "Cont dezactivat"}', 401));

    await expectLater(
      client.post('/auth/login', body: {}, withAuth: false),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Cont dezactivat')),
    );
    expect(auth.isLoggedIn, isTrue);
    expect(notified, 0);
  });

  test('FastAPI detail message is surfaced, including validation lists', () async {
    final client = clientWith((req) async {
      if (req.url.path.endsWith('/a')) {
        return http.Response('{"detail": "Casa nu exista"}', 404);
      }
      return http.Response(
        json.encode({
          'detail': [
            {
              'type': 'value_error',
              'loc': ['body', 'power_w'],
              'msg': 'power_w too large'
            }
          ]
        }),
        422,
      );
    });

    await expectLater(
      client.get('/a'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Casa nu exista')),
    );
    await expectLater(
      client.post('/b', body: {}),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('power_w too large'))),
    );
  });

  test('network failure becomes ApiException with status 0', () async {
    final client = clientWith((req) async => throw http.ClientException('refused'));

    await expectLater(
      client.get('/me/house'),
      throwsA(isA<ApiException>().having((e) => e.isNetworkError, 'isNetworkError', isTrue)),
    );
    expect(auth.isLoggedIn, isTrue, reason: 'a network error must not log the user out');
  });

  test('login stores the session from the backend response', () async {
    await auth.clear();
    final client = clientWith((req) async {
      expect(req.headers.containsKey('Authorization'), isFalse);
      return http.Response(
        json.encode({
          'access_token': 'new-token',
          'token_type': 'bearer',
          'user_id': 7,
          'username': 'user7',
          'house_id': 7,
          'is_admin': false,
        }),
        200,
      );
    });
    final api = UserApiService(client);

    await api.login('user7', 'parola123');

    expect(auth.token, 'new-token');
    expect(auth.houseId, 7);
    expect(auth.username, 'user7');
  });
}
