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

  test('422 validation errors are turned into Romanian messages', () async {
    Map<String, dynamic> error(String type, String field, String msg, [Map<String, dynamic>? ctx]) => {
          'type': type,
          'loc': ['body', field],
          'msg': msg,
          'input': 'x',
          if (ctx != null) 'ctx': ctx,
        };
    final cases = <List<Map<String, dynamic>>, String>{
      [
        error('string_pattern_mismatch', 'username', "String should match pattern '^[A-Za-z0-9_.-]+\$'"),
      ]: 'Numele de utilizator conține caractere nepermise',
      [
        error('string_too_short', 'password', 'String should have at least 3 characters', {'min_length': 3}),
      ]: 'Parola trebuie să aibă cel puțin 3 caractere',
      [
        error('less_than_equal', 'fixed_price_lei_kwh', 'Input should be less than or equal to 10', {'le': 10.0}),
      ]: 'Prețul fix poate fi cel mult 10',
      [
        error('greater_than', 'power_w', 'Input should be greater than 0', {'gt': 0.0}),
        error('missing', 'name', 'Field required'),
      ]: 'Puterea trebuie să fie peste 0; Numele lipsește',
      [
        error('value_error', 'password', 'Value error, parola nu poate depasi 72 de octeti'),
      ]: 'Parola: parola nu poate depasi 72 de octeti',
      [
        error('float_parsing', 'tick_seconds', 'Input should be a valid number'),
      ]: 'Câmpul tick_seconds are o valoare nevalidă',
    };

    for (final entry in cases.entries) {
      final client = clientWith((req) async => http.Response(json.encode({'detail': entry.key}), 422));
      await expectLater(
        client.post('/x', body: {}),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 422)
            .having((e) => e.message, 'message', entry.value)),
      );
    }
  });

  test('an error that is not an ApiException still gets a message for the screen', () {
    final wrapped = ApiException.from(StateError('cast'));
    expect(wrapped.statusCode, ApiException.unexpected);
    expect(wrapped.isNetworkError, isFalse);
    expect(wrapped.message, 'A apărut o eroare neașteptată');

    const original = ApiException(403, 'Acces interzis');
    expect(ApiException.from(original), same(original));
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

  test('refreshSession picks up a house assigned after login', () async {
    await auth.setSession(token: 'tok', houseId: null, username: 'nou', isAdmin: false);
    var notified = 0;
    auth.addListener(() => notified++);
    final api = UserApiService(clientWith((req) async {
      expect(req.url.path, endsWith('/auth/me'));
      return http.Response(json.encode({'user_id': 9, 'username': 'nou', 'house_id': 4, 'is_admin': false}), 200);
    }));

    await api.refreshSession();

    expect(auth.houseId, 4);
    expect(auth.token, 'tok');
    expect(notified, 1);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getInt('house_id'), 4);

    await api.refreshSession();
    expect(notified, 1, reason: 'nothing changed, nobody is notified');
  });

  test('refreshSession follows the admin flag and a removed house', () async {
    final api = UserApiService(clientWith(
      (req) async => http.Response(json.encode({'username': 'user3', 'house_id': null, 'is_admin': true}), 200),
    ));

    await api.refreshSession();

    expect(auth.houseId, isNull);
    expect(auth.isAdmin, isTrue);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getInt('house_id'), isNull);
    expect(prefs.getBool('is_admin'), isTrue);
  });
}
