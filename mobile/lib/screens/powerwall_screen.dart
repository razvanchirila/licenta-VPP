import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_interface/core/browser_viewport.dart';
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

  /// The smart stack sits this far above the bottom edge, clear of the collapsed menu sheet.
  static const double _stackGap = 14;

  House? _house;
  SimPrices? _prices;
  ApiException? _error;
  bool _loading = true;
  bool _refreshing = false;
  Timer? _timer;
  bool _isProcessingTap = false;
  late final AppLifecycleListener _lifecycle;
  final Map<String, (Object?, Widget)> _sections = {};

  @override
  void initState() {
    super.initState();
    appState.addListener(_onAppStateChanged);
    _lifecycle = AppLifecycleListener(onHide: _stopRefresh, onShow: _startRefresh);
    _syncSession();
    _startRefresh();
    _loadWeather();

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
    _stopRefresh();
    _lifecycle.dispose();
    appState.removeListener(_onAppStateChanged);
    super.dispose();
  }

  void _onAppStateChanged() {
    if (mounted) setState(() {});
  }

  /// Polls only while the app is on screen; coming back refreshes right away.
  void _startRefresh() {
    _timer?.cancel();
    _refresh();
    _timer = Timer.periodic(_refreshInterval, (_) => _refresh());
  }

  void _stopRefresh() {
    _timer?.cancel();
    _timer = null;
  }

  /// Hands back the same widget instance while [deps] are equal, so a refresh that did not change
  /// a section's data skips rebuilding and repainting it.
  Widget _section(String slot, Object? deps, Widget Function() build) {
    final previous = _sections[slot];
    if (previous != null && previous.$1 == deps) return previous.$2;
    final widget = build();
    _sections[slot] = (deps, widget);
    return widget;
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
      final house = results[0] as House;
      final prices = results[1] as SimPrices? ?? _prices;
      setState(() {
        _house = house;
        _prices = prices;
        _error = null;
        _loading = false;
      });
      _updateDayMode(prices);
      appState.setIndoorTemperature(house.lastStep?.tempInC);
      // an operator gave the account a house while the app was open
      if (house.id != authState.houseId) _syncSession();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = ApiException.from(e);
        _loading = false;
      });
    } finally {
      _refreshing = false;
    }
  }

  Future<void> _syncSession() async {
    try {
      await userApiService.refreshSession();
    } catch (_) {
      // the copy saved at login stays; an expired token already logged the user out
    }
  }

  /// The spinner is cleared by the refresh that ends next, this one or one already on its way.
  void _retry() {
    setState(() => _loading = true);
    _syncSession();
    _refresh();
  }

  /// The price curve is optional: the dashboard still works without it.
  Future<SimPrices?> _fetchPricesOrNull() async {
    try {
      return await userApiService.getSimPrices();
    } catch (_) {
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
        description: 'Vreme',
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
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.green));
    }
    final house = _house;
    if (house == null) {
      return SafeArea(
        child: HomeErrorState(
          error: _error,
          isAdmin: authState.isAdmin,
          operatorPanelUrl: operatorPanelUrl(),
          onRetry: _retry,
          onLogout: userApiService.logout,
        ),
      );
    }
    return _buildDashboard(house);
  }

  Widget _buildDashboard(House house) {
    final step = house.lastStep;
    final batteryKw = step?.batteryKw ?? 0.0;
    final prices = _prices;
    final price = prices == null || prices.isEmpty ? null : prices.currentValue(PriceSeries.import);
    final insets = MediaQuery.paddingOf(context);
    final top = insets.top;
    final userName = authState.username ?? '';
    final status = batteryStatusLabel(house);
    final discharging = isBatteryDischarging(batteryKw);
    final image = appState.getHouseImagePath();
    final percent = house.batteryPercent.round();
    final gridKw = step?.gridKw ?? 0.0;
    final neighbourKw = step != null && step.p2pEnabled ? step.p2pKw : null;
    final solarKw = step?.pvKw ?? 0.0;
    final homeKw = step?.loadKw ?? house.currentConsumptionKw;
    final rising = prices?.isRising(PriceSeries.import) ?? false;

    return Stack(
      children: [
        Padding(
          padding: EdgeInsets.only(top: top),
          child: Column(
            children: [
              _section(
                'header',
                (userName, status, discharging, DateTime.now().hour),
                () => Header(
                  userName: userName,
                  status: status,
                  isDischarging: discharging,
                  notificationCount: 0,
                  onProfileTap: _showProfileMenu,
                ),
              ),
              if (_error != null) ConnectionBanner(message: _error!.message, offline: _error!.isNetworkError),
              Expanded(
                child: _section(
                  'house',
                  (image, batteryKw, percent, gridKw, neighbourKw, solarKw, homeKw),
                  () => HouseSection(
                    houseImage: image,
                    batteryPower: batteryKw,
                    powerwallPercentage: percent,
                    gridPower: gridKw,
                    neighbourPower: neighbourKw,
                    solarPower: solarKw,
                    homePower: homeKw,
                  ),
                ),
              ),
              SizedBox(height: OverlayBottomMenu.collapsedHeight(insets.bottom) + _stackGap + SmartStack.height + 8),
            ],
          ),
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: OverlayBottomMenu.collapsedHeight(insets.bottom) + _stackGap,
          child: _section(
            'stack',
            (house.battery, house.batteryPercent, homeKw, price, rising),
            () => RepaintBoundary(
              child: SmartStack(
                battery: house.battery,
                batteryPercent: house.batteryPercent,
                currentConsumptionKw: homeKw,
                pricePerKwh: price,
                isPriceRising: rising,
                onPriceTap: () => _push(const TradingScreen()),
              ),
            ),
          ),
        ),
        const Positioned(left: 0, right: 0, bottom: 0, child: RepaintBoundary(child: OverlayBottomMenu())),
        Positioned(
          right: 80,
          top: 8 + top,
          child: SolarForecastButton(onTap: () => _push(const SolarForecastScreen())),
        ),
        if (step != null) Positioned(left: 24, top: 60 + top, child: SimTimeChip(time: prices?.current?.timestamp)),
      ],
    );
  }
}
