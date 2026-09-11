import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// User API Service for Flutter - connects to port 8001
/// 
/// Handles authentication and user-specific endpoints
class UserApiService {
  /// Base URL for User API
  final String baseUrl;
  
  /// HTTP client
  final http.Client _client;
  
  /// JWT token storage key
  static const String _tokenKey = 'jwt_token';
  static const String _houseIdKey = 'house_id';
  
  /// Current JWT token
  String? _token;
  int? _houseId;
  
  /// Timeout duration
  static const Duration timeout = Duration(seconds: 10);
  
  UserApiService({
    this.baseUrl = 'http://localhost:8001',
    http.Client? client,
  }) : _client = client ?? http.Client();
  
  /// Initialize - load token from storage
  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    _houseId = prefs.getInt(_houseIdKey);
  }
  
  /// Check if user is logged in
  bool get isLoggedIn => _token != null;
  
  /// Get current house ID
  int? get houseId => _houseId;
  
  /// Get authorization headers
  Map<String, String> get _authHeaders => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };
  
  void dispose() {
    _client.close();
  }
  
  // ============================================================
  // AUTHENTICATION
  // ============================================================
  
  /// Register a new user
  Future<Map<String, dynamic>?> register(String username, String password) async {
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'username': username, 'password': password}),
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {'error': json.decode(response.body)['detail'] ?? 'Registration failed'};
    } catch (e) {
      return {'error': 'Connection error: $e'};
    }
  }
  
  /// Login and store token
  Future<bool> login(String username, String password) async {
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'username': username, 'password': password}),
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _token = data['access_token'];
        _houseId = data['house_id'];
        
        // Save to storage
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_tokenKey, _token!);
        if (_houseId != null) {
          await prefs.setInt(_houseIdKey, _houseId!);
        }
        
        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }
  
  /// Logout - clear token
  Future<void> logout() async {
    _token = null;
    _houseId = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_houseIdKey);
  }
  
  // ============================================================
  // MY HOUSE ENDPOINTS
  // ============================================================
  
  /// Get my house info
  Future<Map<String, dynamic>?> getMyHouse() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/house'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching house: $e');
      return null;
    }
  }
  
  /// Get my devices
  Future<List<dynamic>?> getMyDevices() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/devices'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return null;
    } catch (e) {
      print('Error fetching devices: $e');
      return null;
    }
  }
  
  /// Toggle a device
  Future<Map<String, dynamic>?> toggleDevice(int deviceId) async {
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/me/devices/$deviceId/toggle'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error toggling device: $e');
      return null;
    }
  }
  
  /// Create a new device
  Future<Map<String, dynamic>?> createDevice({
    required String name,
    required double powerW,
    bool critical = false,
    bool statusOn = false,
  }) async {
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/me/devices'),
        headers: _authHeaders,
        body: json.encode({
          'name': name,
          'power_w': powerW,
          'critical': critical,
          'status_on': statusOn,
        }),
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      final error = json.decode(response.body);
      return {'error': error['detail'] ?? 'Failed to create device'};
    } catch (e) {
      print('Error creating device: $e');
      return {'error': 'Connection error: $e'};
    }
  }
  
  /// Update a device
  Future<Map<String, dynamic>?> updateDevice(
    int deviceId, {
    String? name,
    double? powerW,
    bool? critical,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (name != null) body['name'] = name;
      if (powerW != null) body['power_w'] = powerW;
      if (critical != null) body['critical'] = critical;
      
      final response = await _client.put(
        Uri.parse('$baseUrl/me/devices/$deviceId'),
        headers: _authHeaders,
        body: json.encode(body),
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      final error = json.decode(response.body);
      return {'error': error['detail'] ?? 'Failed to update device'};
    } catch (e) {
      print('Error updating device: $e');
      return {'error': 'Connection error: $e'};
    }
  }
  
  /// Delete a device
  Future<Map<String, dynamic>?> deleteDevice(int deviceId) async {
    try {
      final response = await _client.delete(
        Uri.parse('$baseUrl/me/devices/$deviceId'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      final error = json.decode(response.body);
      return {'error': error['detail'] ?? 'Failed to delete device'};
    } catch (e) {
      print('Error deleting device: $e');
      return {'error': 'Connection error: $e'};
    }
  }
  
  /// Get today's energy summary
  Future<Map<String, dynamic>?> getEnergyToday() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/energy/today'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching energy today: $e');
      return null;
    }
  }
  
  /// Get energy history
  Future<List<dynamic>?> getEnergyHistory({int days = 7}) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/energy/history?days=$days'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body) as List<dynamic>;
      }
      return null;
    } catch (e) {
      print('Error fetching energy history: $e');
      return null;
    }
  }
  
  // ============================================================
  // STATISTICS ENDPOINTS
  // ============================================================
  
  /// Get consumption summary for a period
  Future<Map<String, dynamic>?> getConsumptionSummary({String period = 'month'}) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/stats/summary?period=$period'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching consumption summary: $e');
      return null;
    }
  }
  
  /// Get top energy consuming devices
  Future<Map<String, dynamic>?> getTopConsumers({String period = 'month', int limit = 10}) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/stats/top-consumers?period=$period&limit=$limit'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching top consumers: $e');
      return null;
    }
  }
  
  /// Get chart data for consumption visualization
  Future<Map<String, dynamic>?> getChartData({
    required String startDate,
    required String endDate,
  }) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/stats/chart?start_date=$startDate&end_date=$endDate'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching chart data: $e');
      return null;
    }
  }
  
  /// Get monthly comparison
  Future<Map<String, dynamic>?> getMonthlyComparison() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/stats/comparison'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching monthly comparison: $e');
      return null;
    }
  }
  
  /// Check API health
  Future<bool> isApiAvailable() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/health'),
      ).timeout(timeout);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  // ============================================================
  // P2P TRADING ENDPOINTS
  // ============================================================
  
  /// Get trading preferences for my house
  Future<Map<String, dynamic>?> getTradingPreferences() async {
    if (_houseId == null) return null;
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/trading/preferences/$_houseId'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching trading preferences: $e');
      return null;
    }
  }
  
  /// Update trading preferences
  Future<Map<String, dynamic>?> updateTradingPreferences({
    bool? sellingEnabled,
    bool? buyingEnabled,
    String? priceMode,
    double? fixedPriceLeiKwh,
    double? discountPercent,
    double? minSellPriceLeiKwh,
  }) async {
    if (_houseId == null) return null;
    try {
      final body = <String, dynamic>{};
      if (sellingEnabled != null) body['selling_enabled'] = sellingEnabled;
      if (buyingEnabled != null) body['buying_enabled'] = buyingEnabled;
      if (priceMode != null) body['price_mode'] = priceMode;
      if (fixedPriceLeiKwh != null) body['fixed_price_lei_kwh'] = fixedPriceLeiKwh;
      if (discountPercent != null) body['discount_percent'] = discountPercent;
      if (minSellPriceLeiKwh != null) body['min_sell_price_lei_kwh'] = minSellPriceLeiKwh;
      
      final response = await _client.put(
        Uri.parse('$baseUrl/trading/preferences/$_houseId'),
        headers: _authHeaders,
        body: json.encode(body),
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      final error = json.decode(response.body);
      return {'error': error['detail'] ?? 'Failed to update trading preferences'};
    } catch (e) {
      print('Error updating trading preferences: $e');
      return {'error': 'Connection error: $e'};
    }
  }
  
  /// Get trading history
  Future<Map<String, dynamic>?> getTradingHistory({int limit = 50, String? transactionType}) async {
    if (_houseId == null) return null;
    try {
      var url = '$baseUrl/trading/history/$_houseId?limit=$limit';
      if (transactionType != null) url += '&transaction_type=$transactionType';
      
      final response = await _client.get(
        Uri.parse(url),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching trading history: $e');
      return null;
    }
  }
  
  /// Get trading statistics
  Future<Map<String, dynamic>?> getTradingStats() async {
    if (_houseId == null) return null;
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/trading/stats/$_houseId'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching trading stats: $e');
      return null;
    }
  }
  
  // ============================================================
  // WALLET ENDPOINTS
  // ============================================================
  
  /// Get wallet info
  Future<Map<String, dynamic>?> getWallet() async {
    if (_houseId == null) return null;
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/wallet/$_houseId'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching wallet: $e');
      return null;
    }
  }
  
  /// Get wallet transactions
  Future<Map<String, dynamic>?> getWalletTransactions({int limit = 50, String? transactionType}) async {
    if (_houseId == null) return null;
    try {
      var url = '$baseUrl/wallet/$_houseId/transactions?limit=$limit';
      if (transactionType != null) url += '&transaction_type=$transactionType';
      
      final response = await _client.get(
        Uri.parse(url),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching wallet transactions: $e');
      return null;
    }
  }
  
  /// Transfer energy to VPP reserve
  Future<Map<String, dynamic>?> transferToVPP(double energyKwh) async {
    if (_houseId == null) return null;
    try {
      final response = await _client.post(
        Uri.parse('$baseUrl/wallet/$_houseId/transfer-to-vpp'),
        headers: _authHeaders,
        body: json.encode({'energy_kwh': energyKwh}),
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      final error = json.decode(response.body);
      return {'error': error['detail'] ?? 'Failed to transfer to VPP'};
    } catch (e) {
      print('Error transferring to VPP: $e');
      return {'error': 'Connection error: $e'};
    }
  }
  
  // ============================================================
  // OPCOM PRICE ENDPOINTS
  // ============================================================
  
  /// Get OPCOM prices for a period
  /// [period] - "1Z" (day), "1S" (week), "1L" (month), "6L", "1A"
  /// [date] - Optional date in DD/MM/YYYY format
  Future<Map<String, dynamic>?> getOpcomPrices({
    String period = '1Z',
    String? date,
  }) async {
    try {
      var url = '$baseUrl/trading/opcom/prices?period=$period';
      if (date != null) url += '&date=$date';
      
      final response = await _client.get(
        Uri.parse(url),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching OPCOM prices: $e');
      return null;
    }
  }
  
  /// Get current OPCOM price
  Future<Map<String, dynamic>?> getOpcomCurrentPrice() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/trading/opcom/current'),
        headers: _authHeaders,
      ).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching current OPCOM price: $e');
      return null;
    }
  }
  
  /// Get OPCOM price history
  /// [days] - Number of days of history (1-365)
  Future<Map<String, dynamic>?> getOpcomPriceHistory({int days = 7}) async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/trading/opcom/history?days=$days'),
        headers: _authHeaders,
      ).timeout(timeout);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching OPCOM price history: $e');
      return null;
    }
  }

  // ============================================================
  // SETTINGS ENDPOINTS
  // ============================================================

  /// Get house settings (mode + backup reserve)
  Future<Map<String, dynamic>?> getSettings() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/settings'),
        headers: _authHeaders,
      ).timeout(timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Update house settings (mode and/or backup reserve)
  Future<Map<String, dynamic>?> updateSettings({
    String? mode,
    double? backupReservePercent,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (mode != null) body['mode'] = mode;
      if (backupReservePercent != null) body['backup_reserve_percent'] = backupReservePercent;

      final response = await _client.put(
        Uri.parse('$baseUrl/me/settings'),
        headers: _authHeaders,
        body: json.encode(body),
      ).timeout(timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {'error': json.decode(response.body)['detail'] ?? 'Failed to update settings'};
    } catch (e) {
      return {'error': 'Connection error: $e'};
    }
  }

  // ============================================================
  // ENERGY CHART & IMPACT ENDPOINTS
  // ============================================================

  /// Get energy chart data (solar/consumption/battery/grid over time)
  /// [period] - "day", "week", or "month"
  /// [date]   - "YYYY-MM-DD", defaults to today
  Future<Map<String, dynamic>?> getEnergyChart(String period, {String? date}) async {
    try {
      final params = <String, String>{'period': period};
      if (date != null) params['date'] = date;
      final uri = Uri.parse('$baseUrl/me/energy/chart').replace(queryParameters: params);
      final response = await _client.get(uri, headers: _authHeaders).timeout(timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  /// Get energy impact data (source distribution, peak/off-peak, monthly savings)
  Future<Map<String, dynamic>?> getEnergyImpact() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/me/energy/impact'),
        headers: _authHeaders,
      ).timeout(timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }
}

/// Singleton instance
final userApiService = UserApiService();
