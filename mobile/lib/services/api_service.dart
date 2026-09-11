import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'package:flutter_interface/models/house_state.dart';

/// API Service for communicating with the VPP Simulator backend
/// 
/// This service handles all HTTP requests to the FastAPI backend,
/// including house configuration, mode changes, and simulation data.
class ApiService {
  /// Base URL for the API (default: localhost:8000)
  final String baseUrl;
  
  /// HTTP client for making requests
  final http.Client _client;
  
  /// Default house ID to control
  final int defaultHouseId;
  
  /// Timeout duration for requests
  static const Duration timeout = Duration(seconds: 10);
  
  ApiService({
    this.baseUrl = 'http://localhost:8000',
    this.defaultHouseId = 1,
    http.Client? client,
  }) : _client = client ?? http.Client();
  
  /// Dispose the HTTP client
  void dispose() {
    _client.close();
  }
  
  // ============================================================
  // HEALTH & STATUS
  // ============================================================
  
  /// Check if the API is available
  Future<bool> isApiAvailable() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/health'))
          .timeout(timeout);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
  
  /// Get API health status
  Future<Map<String, dynamic>?> getHealth() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/health'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      return null;
    }
  }
  
  // ============================================================
  // HOUSE ENDPOINTS
  // ============================================================
  
  /// Get house details by ID
  Future<HouseState?> getHouse(int houseId) async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/houses/$houseId'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return HouseState.fromJson(data);
      }
      return null;
    } catch (e) {
      print('Error fetching house $houseId: $e');
      return null;
    }
  }
  
  /// Get house with default ID
  Future<HouseState?> getDefaultHouse() async {
    return getHouse(defaultHouseId);
  }
  
  /// Change house operating mode (Eco/Profit)
  Future<bool> setHouseMode(int houseId, String mode) async {
    try {
      final response = await _client
          .post(
            Uri.parse('$baseUrl/api/houses/$houseId/mode'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'mode': mode}),
          )
          .timeout(timeout);
      
      return response.statusCode == 200;
    } catch (e) {
      print('Error setting house mode: $e');
      return false;
    }
  }
  
  /// Set mode for default house
  Future<bool> setDefaultHouseMode(String mode) async {
    return setHouseMode(defaultHouseId, mode);
  }
  
  /// Get house battery status
  Future<Map<String, dynamic>?> getHouseBattery(int houseId) async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/houses/$houseId/battery'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching house battery: $e');
      return null;
    }
  }
  
  /// Get house devices
  Future<List<dynamic>?> getHouseDevices(int houseId) async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/houses/$houseId/devices'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['devices'] as List<dynamic>?;
      }
      return null;
    } catch (e) {
      print('Error fetching house devices: $e');
      return null;
    }
  }
  
  /// Toggle a device on/off
  Future<bool> toggleDevice(int houseId, int deviceId) async {
    try {
      final response = await _client
          .post(Uri.parse('$baseUrl/api/houses/$houseId/devices/$deviceId/toggle'))
          .timeout(timeout);
      
      return response.statusCode == 200;
    } catch (e) {
      print('Error toggling device: $e');
      return false;
    }
  }
  
  // ============================================================
  // VPP ENDPOINTS
  // ============================================================
  
  /// Get VPP state
  Future<Map<String, dynamic>?> getVppState() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/vpp/state'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching VPP state: $e');
      return null;
    }
  }
  
  /// Get VPP statistics
  Future<Map<String, dynamic>?> getVppStats() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/vpp/stats'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching VPP stats: $e');
      return null;
    }
  }
  
  // ============================================================
  // SIMULATION ENDPOINTS
  // ============================================================
  
  /// Initialize simulation with houses
  Future<Map<String, dynamic>?> initSimulation({
    int numHouses = 10,
    double batteryRatio = 0.80,
    bool useOpcomPrices = false,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/api/sim/init').replace(queryParameters: {
        'num_houses': numHouses.toString(),
        'houses_with_battery_ratio': batteryRatio.toString(),
        'use_opcom_prices': useOpcomPrices.toString(),
      });
      
      final response = await _client.post(uri).timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error initializing simulation: $e');
      return null;
    }
  }
  
  /// Run one simulation step (1 hour)
  Future<Map<String, dynamic>?> simulateStep({int? hour, double? price}) async {
    try {
      final response = await _client
          .post(
            Uri.parse('$baseUrl/api/sim/step'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              if (hour != null) 'hour': hour,
              if (price != null) 'price': price,
            }),
          )
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error simulating step: $e');
      return null;
    }
  }
  
  /// Run 24-hour simulation
  Future<Map<String, dynamic>?> simulateDay() async {
    try {
      final response = await _client
          .post(Uri.parse('$baseUrl/api/sim/day'))
          .timeout(const Duration(seconds: 30));
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error simulating day: $e');
      return null;
    }
  }
  
  /// Get simulation history
  Future<Map<String, dynamic>?> getSimulationHistory() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/sim/history'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching simulation history: $e');
      return null;
    }
  }
  
  /// Reset simulation
  Future<bool> resetSimulation() async {
    try {
      final response = await _client
          .post(Uri.parse('$baseUrl/api/sim/reset'))
          .timeout(timeout);
      
      return response.statusCode == 200;
    } catch (e) {
      print('Error resetting simulation: $e');
      return false;
    }
  }
  
  // ============================================================
  // CONFIGURATION ENDPOINTS
  // ============================================================
  
  /// Get current configuration
  Future<Map<String, dynamic>?> getConfig() async {
    try {
      final response = await _client
          .get(Uri.parse('$baseUrl/api/config'))
          .timeout(timeout);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error fetching config: $e');
      return null;
    }
  }
  
  /// Update battery configuration
  Future<bool> updateBatteryConfig({
    double? capacityKwh,
    double? socMinRatio,
    double? pChMaxKw,
    double? pDisMaxKw,
  }) async {
    try {
      final response = await _client
          .post(
            Uri.parse('$baseUrl/api/config/battery'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              if (capacityKwh != null) 'capacity_kwh': capacityKwh,
              if (socMinRatio != null) 'soc_min_ratio': socMinRatio,
              if (pChMaxKw != null) 'p_ch_max_kw': pChMaxKw,
              if (pDisMaxKw != null) 'p_dis_max_kw': pDisMaxKw,
            }),
          )
          .timeout(timeout);
      
      return response.statusCode == 200;
    } catch (e) {
      print('Error updating battery config: $e');
      return false;
    }
  }
}

/// Singleton instance for easy access throughout the app
final apiService = ApiService();
