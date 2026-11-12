import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const String _apiUrlDefine = String.fromEnvironment('API_URL');

/// Base URL of the backend, overridable at build time:
/// `flutter run --dart-define=API_URL=http://192.168.1.10:8000/api`.
/// Without it the web build calls `/api` on the origin it was served from
/// (nginx in the Docker image forwards it to the backend).
String defaultApiBaseUrl() {
  if (_apiUrlDefine.isNotEmpty) return _apiUrlDefine;
  if (kIsWeb) return '${Uri.base.origin}/api';
  return 'http://127.0.0.1:8000/api';
}

class ApiException implements Exception {
  /// HTTP status code, 0 for network / timeout errors, [unexpected] for a failure inside the app.
  final int statusCode;
  final String message;

  const ApiException(this.statusCode, this.message);

  static const int unexpected = -1;

  /// Anything thrown while loading (a cast, a parsing bug) still has to reach the screen as an error.
  factory ApiException.from(Object error) =>
      error is ApiException ? error : const ApiException(unexpected, 'A apărut o eroare neașteptată');

  bool get isNetworkError => statusCode == 0;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class AuthState extends ChangeNotifier {
  static const _tokenKey = 'jwt_token';
  static const _houseIdKey = 'house_id';
  static const _usernameKey = 'username';
  static const _isAdminKey = 'is_admin';

  String? _token;
  int? _houseId;
  String? _username;
  bool _isAdmin = false;

  String? get token => _token;
  int? get houseId => _houseId;
  String? get username => _username;
  bool get isAdmin => _isAdmin;
  bool get isLoggedIn => _token != null;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    _houseId = prefs.getInt(_houseIdKey);
    _username = prefs.getString(_usernameKey);
    _isAdmin = prefs.getBool(_isAdminKey) ?? false;
    notifyListeners();
  }

  Future<void> setSession({
    required String token,
    required int? houseId,
    required String username,
    required bool isAdmin,
  }) async {
    _token = token;
    _houseId = houseId;
    _username = username;
    _isAdmin = isAdmin;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    if (houseId != null) {
      await prefs.setInt(_houseIdKey, houseId);
    } else {
      await prefs.remove(_houseIdKey);
    }
    await prefs.setString(_usernameKey, username);
    await prefs.setBool(_isAdminKey, isAdmin);
    notifyListeners();
  }

  /// House and role as the server sees them now; the token stays the same.
  Future<void> updateUser({required int? houseId, required bool isAdmin}) async {
    if (_token == null || (houseId == _houseId && isAdmin == _isAdmin)) return;
    _houseId = houseId;
    _isAdmin = isAdmin;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    if (houseId != null) {
      await prefs.setInt(_houseIdKey, houseId);
    } else {
      await prefs.remove(_houseIdKey);
    }
    await prefs.setBool(_isAdminKey, isAdmin);
  }

  Future<void> clear() async {
    if (_token == null && _houseId == null) return;
    _token = null;
    _houseId = null;
    _username = null;
    _isAdmin = false;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_houseIdKey);
    await prefs.remove(_usernameKey);
    await prefs.remove(_isAdminKey);
  }
}

/// A 401 on an *authenticated* call means the token expired: the session is
/// cleared so the UI falls back to login. A 401 on an anonymous call (login,
/// register) is a normal error and carries the server message.
class ApiClient {
  final String baseUrl;
  final AuthState auth;
  final http.Client _client;
  final Duration timeout;

  ApiClient({
    required this.auth,
    String? baseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 10),
  })  : baseUrl = baseUrl ?? defaultApiBaseUrl(),
        _client = client ?? http.Client();

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final params = <String, String>{};
    query?.forEach((k, v) {
      if (v != null) params[k] = v.toString();
    });
    return Uri.parse('$baseUrl$path').replace(
      queryParameters: params.isEmpty ? null : params,
    );
  }

  Map<String, String> _headers({bool withAuth = true}) => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (withAuth && auth.token != null) 'Authorization': 'Bearer ${auth.token}',
      };

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _send(() => _client.get(_uri(path, query), headers: _headers()));

  Future<dynamic> post(String path, {Object? body, bool withAuth = true}) => _send(
        () => _client.post(
          _uri(path),
          headers: _headers(withAuth: withAuth),
          body: body == null ? null : json.encode(body),
        ),
        withAuth: withAuth,
      );

  Future<dynamic> put(String path, {Object? body}) =>
      _send(() => _client.put(_uri(path), headers: _headers(), body: json.encode(body ?? {})));

  Future<dynamic> delete(String path) => _send(() => _client.delete(_uri(path), headers: _headers()));

  Future<dynamic> _send(Future<http.Response> Function() request, {bool withAuth = true}) async {
    // Decided before the request so a token cleared meanwhile does not matter.
    final authenticated = withAuth && auth.token != null;

    http.Response response;
    try {
      response = await request().timeout(timeout);
    } on TimeoutException {
      throw const ApiException(0, 'Serverul nu a răspuns la timp');
    } catch (e) {
      throw const ApiException(0, 'Nu se poate contacta serverul');
    }

    if (response.statusCode == 401 && authenticated) {
      await auth.clear();
      throw const ApiException(401, 'Sesiune expirată, autentifică-te din nou');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(response.statusCode, _errorMessage(response));
    }
    if (response.body.isEmpty) return null;
    try {
      return json.decode(utf8.decode(response.bodyBytes));
    } catch (_) {
      throw ApiException(response.statusCode, 'Răspuns invalid de la server');
    }
  }

  /// Extracts FastAPI's `{"detail": ...}`: a string, or the list of validation errors of a 422.
  static String _errorMessage(http.Response response) {
    try {
      final decoded = json.decode(utf8.decode(response.bodyBytes));
      final detail = decoded is Map ? decoded['detail'] : null;
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        return detail.map((e) => e is Map ? _validationMessage(e) : e.toString()).join('; ');
      }
    } catch (_) {}
    return 'Eroare HTTP ${response.statusCode}';
  }
}

const Map<String, String> _fieldLabels = {
  'username': 'Numele de utilizator',
  'password': 'Parola',
  'name': 'Numele',
  'power_w': 'Puterea',
  'mode': 'Modul',
  'backup_reserve_percent': 'Rezerva',
  'fixed_price_lei_kwh': 'Prețul fix',
  'discount_percent': 'Reducerea',
  'min_sell_price_lei_kwh': 'Prețul minim',
  'energy_kwh': 'Energia',
};

/// One entry of a pydantic error list (`type`, `loc`, `msg`, `ctx`) as a Romanian sentence.
String _validationMessage(Map<dynamic, dynamic> error) {
  final loc = error['loc'];
  final field = loc is List && loc.isNotEmpty ? loc.last.toString() : '';
  final label = _fieldLabels[field] ?? (field.isEmpty ? 'Valoarea' : 'Câmpul $field');
  final ctx = error['ctx'] is Map ? error['ctx'] as Map : const {};
  String limit(String key) {
    final v = ctx[key];
    return v is num && v == v.roundToDouble() ? v.round().toString() : '$v';
  }

  switch (error['type']) {
    case 'missing':
      return '$label lipsește';
    case 'string_too_short':
      return '$label trebuie să aibă cel puțin ${limit('min_length')} caractere';
    case 'string_too_long':
      return '$label poate avea cel mult ${limit('max_length')} caractere';
    case 'string_pattern_mismatch':
      return '$label conține caractere nepermise';
    case 'greater_than':
      return '$label trebuie să fie peste ${limit('gt')}';
    case 'greater_than_equal':
      return '$label trebuie să fie cel puțin ${limit('ge')}';
    case 'less_than':
      return '$label trebuie să fie sub ${limit('lt')}';
    case 'less_than_equal':
      return '$label poate fi cel mult ${limit('le')}';
    case 'value_error':
      // the validators in schemas.py raise ValueError with their own text
      return '$label: ${(error['msg'] ?? '').toString().replaceFirst('Value error, ', '')}';
  }
  return '$label are o valoare nevalidă';
}
