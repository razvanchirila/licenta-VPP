import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/models/device.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/models/json_utils.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_interface/services/api_client.dart';

/// Every method throws [ApiException] on failure; no null or mock fallbacks.
class UserApiService {
  final ApiClient client;
  AuthState get auth => client.auth;

  UserApiService(this.client);

  int _requireHouse() {
    final id = auth.houseId;
    if (id == null) {
      throw const ApiException(403, 'Contul nu are o casă asignată');
    }
    return id;
  }

  Future<void> login(String username, String password) async {
    final data = asMap(await client.post(
      '/auth/login',
      body: {'username': username, 'password': password},
      withAuth: false,
    ));
    final token = data['access_token']?.toString();
    if (token == null || token.isEmpty) {
      throw const ApiException(500, 'Răspuns de autentificare invalid');
    }
    await auth.setSession(
      token: token,
      houseId: asIntOrNull(data['house_id']),
      username: asString(data['username'], username),
      isAdmin: asBool(data['is_admin']),
    );
  }

  Future<void> register(String username, String password) async {
    await client.post(
      '/auth/register',
      body: {'username': username, 'password': password},
      withAuth: false,
    );
  }

  Future<void> logout() => auth.clear();

  /// The backend reads house and role on every request, so the copy saved at login can go stale.
  Future<void> refreshSession() async {
    final data = asMap(await client.get('/auth/me'));
    await auth.updateUser(houseId: asIntOrNull(data['house_id']), isAdmin: asBool(data['is_admin']));
  }

  Future<House> getMyHouse() async => House.fromJson(asMap(await client.get('/me/house')));

  Future<HouseSettings> getSettings() async => HouseSettings.fromJson(asMap(await client.get('/me/settings')));

  Future<HouseSettings> updateSettings({String? mode, double? backupReservePercent}) async {
    final body = <String, dynamic>{
      if (mode != null) 'mode': mode,
      if (backupReservePercent != null) 'backup_reserve_percent': backupReservePercent,
    };
    return HouseSettings.fromJson(asMap(await client.put('/me/settings', body: body)));
  }

  Future<List<Device>> getMyDevices() async => asMapList(await client.get('/me/devices')).map(Device.fromJson).toList();

  Future<Device> toggleDevice(int deviceId) async =>
      Device.fromJson(asMap(await client.post('/me/devices/$deviceId/toggle')));

  Future<Device> createDevice({
    required String name,
    required double powerW,
    bool critical = false,
    bool statusOn = false,
  }) async =>
      Device.fromJson(asMap(await client.post('/me/devices', body: {
        'name': name,
        'power_w': powerW,
        'critical': critical,
        'status_on': statusOn,
      })));

  Future<Device> updateDevice(int deviceId, {String? name, double? powerW, bool? critical, bool? statusOn}) async =>
      Device.fromJson(asMap(await client.put('/me/devices/$deviceId', body: {
        if (name != null) 'name': name,
        if (powerW != null) 'power_w': powerW,
        if (critical != null) 'critical': critical,
        if (statusOn != null) 'status_on': statusOn,
      })));

  Future<void> deleteDevice(int deviceId) => client.delete('/me/devices/$deviceId');

  Future<EnergyChart> getEnergyChart(String period, {String? date}) async =>
      EnergyChart.fromJson(asMap(await client.get('/me/energy/chart', query: {'period': period, 'date': date})));

  Future<EnergyImpact> getEnergyImpact() async => EnergyImpact.fromJson(asMap(await client.get('/me/energy/impact')));

  Future<ConsumptionSummary> getConsumptionSummary({String period = 'month'}) async =>
      ConsumptionSummary.fromJson(asMap(await client.get('/stats/summary', query: {'period': period})));

  Future<TopConsumersResponse> getTopConsumers({String period = 'month', int limit = 10}) async =>
      TopConsumersResponse.fromJson(
          asMap(await client.get('/stats/top-consumers', query: {'period': period, 'limit': limit})));

  Future<ChartData> getStatsChart({required String startDate, required String endDate}) async => ChartData.fromJson(
      asMap(await client.get('/stats/chart', query: {'start_date': startDate, 'end_date': endDate})));

  Future<MonthlyComparison> getMonthlyComparison() async =>
      MonthlyComparison.fromJson(asMap(await client.get('/stats/comparison')));

  Future<TradingPrefs> getTradingPreferences() async =>
      TradingPrefs.fromJson(asMap(await client.get('/trading/preferences/${_requireHouse()}')));

  Future<TradingPrefs> updateTradingPreferences({
    bool? sellingEnabled,
    bool? buyingEnabled,
    String? priceMode,
    double? fixedPriceLeiKwh,
    double? discountPercent,
    double? minSellPriceLeiKwh,
  }) async =>
      TradingPrefs.fromJson(asMap(await client.put('/trading/preferences/${_requireHouse()}', body: {
        if (sellingEnabled != null) 'selling_enabled': sellingEnabled,
        if (buyingEnabled != null) 'buying_enabled': buyingEnabled,
        if (priceMode != null) 'price_mode': priceMode,
        if (fixedPriceLeiKwh != null) 'fixed_price_lei_kwh': fixedPriceLeiKwh,
        if (discountPercent != null) 'discount_percent': discountPercent,
        if (minSellPriceLeiKwh != null) 'min_sell_price_lei_kwh': minSellPriceLeiKwh,
      })));

  Future<List<Trade>> getTradingHistory({int limit = 50, String? transactionType, String? status}) async {
    final data = asMap(await client.get('/trading/history/${_requireHouse()}',
        query: {'limit': limit, 'transaction_type': transactionType, 'status': status}));
    return asMapList(data['transactions']).map(Trade.fromJson).toList();
  }

  Future<TradingStats> getTradingStats() async =>
      TradingStats.fromJson(asMap(await client.get('/trading/stats/${_requireHouse()}')));

  Future<Wallet> getWallet() async => Wallet.fromJson(asMap(await client.get('/wallet/${_requireHouse()}')));

  Future<List<WalletTx>> getWalletTransactions({int limit = 50, String? transactionType}) async {
    final data = asMap(await client
        .get('/wallet/${_requireHouse()}/transactions', query: {'limit': limit, 'transaction_type': transactionType}));
    return asMapList(data['transactions']).map(WalletTx.fromJson).toList();
  }

  Future<VppTransferResult> transferToVpp(double energyKwh) async => VppTransferResult.fromJson(
      asMap(await client.post('/wallet/${_requireHouse()}/transfer-to-vpp', body: {'energy_kwh': energyKwh})));

  Future<SimPrices> getSimPrices() async => SimPrices.fromJson(asMap(await client.get('/sim/prices')));

  Future<SimConfig> getSimConfig() async => SimConfig.fromJson(asMap(await client.get('/config')));
}

final AuthState authState = AuthState();
final ApiClient apiClient = ApiClient(auth: authState);
final UserApiService userApiService = UserApiService(apiClient);
