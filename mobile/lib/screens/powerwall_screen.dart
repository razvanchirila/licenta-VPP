import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_interface/core/energy_flow.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/screens/solar_forecast_screen.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/services/weather_service.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/widgets/bottom_menu.dart';
import 'package:flutter_interface/widgets/header.dart';
import 'package:flutter_interface/widgets/home/home_error_state.dart';
import 'package:flutter_interface/widgets/home/home_overlays.dart';
import 'package:flutter_interface/widgets/house/house_section.dart';
import 'package:flutter_interface/widgets/smart_stack/smart_stack.dart';

class PowerwallScreen extends StatefulWidget {
  const PowerwallScreen({super.key});

  @override
  State<PowerwallScreen> createState() => _PowerwallScreenState();
}

class _PowerwallScreenState extends State<PowerwallScreen> {
  static const Duration _refreshInterval = Duration(seconds: 5);

  House? _house;
  SimPrices? _prices;
  ApiException? _error;
  bool _loading = true;
  bool _refreshing = false;
  Timer? _timer;
  bool _isProcessingTap = false;

  @override
  void initState() {
    super.initState();
    appState.addListener(_onAppStateChanged);
    _refresh();
    _loadWeather();
    _timer = Timer.periodic(_refreshInterval, (_) => _refresh());

    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: AppColors.deepBackground,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    appState.removeListener(_onAppStateChanged);
    super.dispose();
  }

  void _onAppStateChanged() {
    if (mounted) setState(() {});
  }

  /// Previously loaded data stays on screen until the next successful refresh.
  Future<void> _refresh() async {
    if (_refreshing) return;
    _refreshing = true;
    try {
      final results = await Future.wait<Object?>([
        userApiService.getMyHouse(),
        _fetchPricesOrNull(),
      ]);
      if (!mounted) return;
      final prices = results[1] as SimPrices? ?? _prices;
      setState(() {
        _house = results[0] as House;
        _prices = prices;
        _error = null;
        _loading = false;
      });
      _updateDayMode(prices);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    } finally {
      _refreshing = false;
    }
  }

  /// The price curve is optional: the dashboard still works without it.
  Future<SimPrices?> _fetchPricesOrNull() async {
    try {
      return await userApiService.getSimPrices();
    } on ApiException {
      return null;
    }
  }

  /// Day/night image follows the simulated clock (06:00-20:00 = day).
  void _updateDayMode(SimPrices? prices) {
    final t = prices?.current?.timestamp;
    if (t == null) return;
    appState.setDayMode(t.hour >= 6 && t.hour < 20);
  }

  Future<void> _loadWeather() async {
    final weather = await weatherService.getSiteWeather();
    if (!mounted) return;
    if (weather == null) {
      appState.setWeather(
        temperature: null,
        description: weatherService.isConfigured ? 'Vreme indisponibilă' : 'Vreme neconfigurată',
        icon: Icons.cloud_off_rounded,
      );
      return;
    }
    appState.setWeather(
      temperature: weather.temperature.value,
      description: weather.description,
      icon: weather.icon,
    );
  }

  void _push(Widget screen) => Navigator.push(context, MaterialPageRoute(builder: (_) => screen));

  /// Debounced so a double tap does not open two sheets.
  void _showProfileMenu() {
    if (_isProcessingTap) return;
    _isProcessingTap = true;
    showProfileMenu(
      context,
      username: authState.username ?? '-',
      houseName: _house?.name ?? 'Fără casă asignată',
      onLogout: userApiService.logout,
    );
    Future.delayed(const Duration(milliseconds: 300), () {
      if (mounted) _isProcessingTap = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0.0, -0.3),
            radius: 1.2,
            colors: [AppColors.surfaceAlt, AppColors.background, AppColors.deepBackground, Color(0xFF050505)],
            stops: [0.0, 0.3, 0.6, 1.0],
          ),
        ),
        child: SafeArea(top: false, child: _buildBody()),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.green));
    }
    final house = _house;
    if (house == null) {
      return HomeErrorState(error: _error, onRetry: _refresh, onLogout: userApiService.logout);
    }
    return _buildDashboard(house);
  }

  Widget _buildDashboard(House house) {
    final step = house.lastStep;
    final batteryKw = step?.batteryKw ?? 0.0;
    final prices = _prices;
    final price = prices == null || prices.isEmpty ? null : prices.currentValue(PriceSeries.import);

    return Stack(
      children: [
        Column(
          children: [
            Header(
              userName: authState.username ?? '',
              status: batteryStatusLabel(house),
              isDischarging: isBatteryDischarging(batteryKw),
              notificationCount: 0,
              onProfileTap: _showProfileMenu,
            ),
            if (_error != null) ConnectionBanner(message: _error!.message),
            Expanded(
              child: HouseSection(
                houseImage: appState.getHouseImagePath(),
                batteryPower: batteryKw,
                powerwallPercentage: house.batteryPercent.round(),
                gridPower: step?.gridKw ?? 0.0,
                solarPower: step?.pvKw ?? 0.0,
                homePower: step?.loadKw ?? house.currentConsumptionKw,
              ),
            ),
            const SizedBox(height: 160),
          ],
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 100,
          child: SmartStack(
            battery: house.battery,
            batteryPercent: house.batteryPercent,
            currentConsumptionKw: step?.loadKw ?? house.currentConsumptionKw,
            pricePerKwh: price,
            isPriceRising: prices?.isRising(PriceSeries.import) ?? false,
            onPriceTap: () => _push(const TradingScreen()),
          ),
        ),
        const Positioned(left: 0, right: 0, bottom: 0, child: OverlayBottomMenu()),
        Positioned(
          right: 80,
          top: 8,
          child: SolarForecastButton(onTap: () => _push(const SolarForecastScreen())),
        ),
        if (step != null) Positioned(left: 24, top: 60, child: SimTimeChip(time: prices?.current?.timestamp)),
      ],
    );
  }
}
