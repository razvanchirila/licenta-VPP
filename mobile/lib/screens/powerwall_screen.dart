import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_interface/widgets/header.dart';
import 'package:flutter_interface/widgets/house_section.dart';
import 'package:flutter_interface/widgets/bottom_menu.dart';
import 'package:flutter_interface/widgets/smart_stack/smart_stack.dart';
import 'package:flutter_interface/models/weather_data.dart';
import 'package:flutter_interface/models/price_data.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/services/weather_service.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/screens/trading_screen.dart';
import 'package:flutter_interface/screens/solar_forecast_screen.dart';

class PowerwallScreen extends StatefulWidget {
  final VoidCallback? onLogout;
  
  const PowerwallScreen({super.key, this.onLogout});

  @override
  State<PowerwallScreen> createState() => _PowerwallScreenState();
}

class _PowerwallScreenState extends State<PowerwallScreen> with TickerProviderStateMixin {
  // Date pentru UI
  // Image is now derived from AppState based on isDayMode and allLightsOn
  String get currentImage => appState.getHouseImagePath();
  
  WeatherData currentWeather = WeatherData.sunny;
  bool _isLoadingWeather = false;
  bool _isLoadingPrice = false;
  
  // Debounce pentru butonul de profil
  bool _isProcessingTap = false;
  
  // Scenarii de test pentru flow-uri (taste 1-4)
  // 1 = Solar produce mult, bateria se încarcă
  // 2 = Consum mare, bateria se descarcă
  // 3 = Export în grid (surplus solar)
  // 4 = Import din grid (consum > producție)
  static const List<Map<String, dynamic>> _flowScenarios = [
    {
      'name': '1. Solar → Baterie (încărcare)',
      'solar': 6.0,
      'batteryPercent': 45,
      'consumption': 1.5,
      'isDay': true,
    },
    {
      'name': '2. Baterie → Casă (descărcare)',
      'solar': 0.0,
      'batteryPercent': 75,
      'consumption': 3.5,
      'isDay': false,
    },
    {
      'name': '3. Solar → Grid (export)',
      'solar': 8.0,
      'batteryPercent': 95,
      'consumption': 1.0,
      'isDay': true,
    },
    {
      'name': '4. Grid → Casă (import)',
      'solar': 0.5,
      'batteryPercent': 10,
      'consumption': 5.0,
      'isDay': false,
    },
  ];
  
  // Focus node pentru keyboard
  final FocusNode _focusNode = FocusNode();
  
  /// Aplică un scenariu de flow bazat pe index (0-3)
  void _applyFlowScenario(int index) {
    if (index < 0 || index >= _flowScenarios.length) return;
    
    final scenario = _flowScenarios[index];
    setState(() {
      appState.solarPower = scenario['solar'] as double;
      appState.setBatteryPercentage((scenario['batteryPercent'] as int).toDouble());
      
      // Setează modul zi/noapte
      final isDay = scenario['isDay'] as bool;
      appState.setDayMode(isDay);
      
      if (isDay) {
        currentWeather = WeatherData.sunny;
        appState.weatherDescription = 'Însorit';
        appState.weatherIcon = Icons.wb_sunny_rounded;
      } else {
        currentWeather = WeatherData.cloudy;
        appState.weatherDescription = 'Noapte';
        appState.weatherIcon = Icons.nightlight_round;
      }
    });
    
    print('🎬 Scenariu activat: ${scenario['name']}');
  }
  
  /// Handler pentru taste
  void _handleKeyEvent(KeyEvent event) {
    if (event is KeyDownEvent) {
      final key = event.logicalKey;
      
      if (key == LogicalKeyboardKey.digit1 || key == LogicalKeyboardKey.numpad1) {
        _applyFlowScenario(0);
      } else if (key == LogicalKeyboardKey.digit2 || key == LogicalKeyboardKey.numpad2) {
        _applyFlowScenario(1);
      } else if (key == LogicalKeyboardKey.digit3 || key == LogicalKeyboardKey.numpad3) {
        _applyFlowScenario(2);
      } else if (key == LogicalKeyboardKey.digit4 || key == LogicalKeyboardKey.numpad4) {
        _applyFlowScenario(3);
      }
    }
  }
  
  void _onAppStateChanged() {
    // Rebuild when devices change
    if (mounted) {
      setState(() {});
    }
  }

  /// Încarcă vremea de la API
  Future<void> _loadWeather() async {
    if (_isLoadingWeather) return;
    
    setState(() => _isLoadingWeather = true);
    
    try {
      // Încarcă vremea pentru București (sau altă locație)
      final weather = await weatherService.getWeatherBucharest();
      
      if (mounted && weather != null) {
        setState(() {
          currentWeather = weather;
          // Actualizează imaginea de fundal bazat pe vreme
          _updateBackgroundForWeather(weather);
          // Actualizează puterea solară bazat pe favorabilitate
          _updateSolarPowerForWeather(weather);
        });
      }
    } catch (e) {
      print('Eroare la încărcarea vremii: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoadingWeather = false);
      }
    }
  }
  
  /// Actualizează modul zi/noapte bazat pe vreme
  void _updateBackgroundForWeather(WeatherData weather) {
    // Update AppState day mode based on weather condition
    // Rainy/stormy = night mode, otherwise = day mode
    final isDay = weather.condition != WeatherCondition.rainy &&
                  weather.condition != WeatherCondition.stormy;
    appState.setDayMode(isDay);
  }
  
  /// Actualizează puterea solară bazat pe favorabilitatea vremii
  void _updateSolarPowerForWeather(WeatherData weather) {
    // Putere solară maximă: 8 kW
    // Ajustăm bazat pe favorabilitatea solară (0.0 - 1.0)
    final maxSolarPower = 8.0;
    appState.solarPower = maxSolarPower * weather.solarFavorability;
    
    // Update outdoor temperature from weather data
    appState.outdoorTemperature = weather.temperature.value;
    
    // Update weather description and icon
    appState.weatherDescription = weather.description;
    appState.weatherIcon = weather.icon;
  }
  
  /// Încarcă prețurile OPCOM de la API
  Future<void> _loadOpcomPrices() async {
    if (_isLoadingPrice) return;
    
    setState(() => _isLoadingPrice = true);
    
    try {
      final result = await userApiService.getOpcomPrices(period: '1Z');
      
      if (mounted && result != null && result['success'] == true && result['data'] != null) {
        final priceData = PriceData.fromJson(result['data']);
        appState.updatePriceData(priceData);
      } else {
        // Fallback: generează date demo
        appState.updatePriceData(_generateFallbackPriceData());
      }
    } catch (e) {
      print('Eroare la încărcarea prețurilor OPCOM: $e');
      // Fallback: generează date demo
      if (mounted) {
        appState.updatePriceData(_generateFallbackPriceData());
      }
    } finally {
      if (mounted) {
        setState(() => _isLoadingPrice = false);
      }
    }
  }
  
  /// Generează date de preț demo când API-ul nu e disponibil
  PriceData _generateFallbackPriceData() {
    final now = DateTime.now();
    final prices = <PricePoint>[];
    
    // Generează 24 prețuri orare cu pattern realist
    for (int hour = 0; hour < 24; hour++) {
      // Pattern: preț mai mic noaptea, mai mare ziua
      final basePrice = 450.0;
      final hourFactor = 1 + 0.3 * _sin((hour - 6) * 3.14159 / 12);
      final noise = (hour * 7 % 60) - 30;
      final priceMwh = basePrice * hourFactor + noise;
      
      prices.add(PricePoint(
        timestamp: DateTime(now.year, now.month, now.day, hour),
        priceLeiMwh: priceMwh,
        priceLeiKwh: priceMwh / 1000,
        hour: hour,
      ));
    }
    
    final priceValues = prices.map((p) => p.priceLeiMwh).toList();
    final minPrice = priceValues.reduce((a, b) => a < b ? a : b);
    final maxPrice = priceValues.reduce((a, b) => a > b ? a : b);
    final avgPrice = priceValues.reduce((a, b) => a + b) / priceValues.length;
    final currentPrice = prices[now.hour].priceLeiMwh;
    final prevPrice = prices[(now.hour - 1 + 24) % 24].priceLeiMwh;
    final change = currentPrice - prevPrice;
    final changePercent = (change / prevPrice) * 100;
    
    return PriceData(
      date: '${now.day.toString().padLeft(2, '0')}/${now.month.toString().padLeft(2, '0')}/${now.year}',
      period: '1Z',
      prices: prices,
      statistics: PriceStats(
        minLeiMwh: minPrice,
        maxLeiMwh: maxPrice,
        avgLeiMwh: avgPrice,
        minLeiKwh: minPrice / 1000,
        maxLeiKwh: maxPrice / 1000,
        avgLeiKwh: avgPrice / 1000,
      ),
      change: PriceChange(
        absoluteLeiMwh: change,
        absoluteLeiKwh: change / 1000,
        percent: changePercent,
        direction: change > 0 ? 'up' : (change < 0 ? 'down' : 'unchanged'),
      ),
      currentPriceLeiMwh: currentPrice,
      currentPriceLeiKwh: currentPrice / 1000,
      currentHour: now.hour,
      source: 'Demo',
      dataPoints: 24,
    );
  }
  
  double _sin(double x) {
    x = x % (2 * 3.14159);
    if (x > 3.14159) x -= 2 * 3.14159;
    return x - (x * x * x) / 6 + (x * x * x * x * x) / 120;
  }
  
  /// Navighează la pagina de P2P Trading
  void _navigateToTrading() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const TradingScreen()),
    );
  }

  /// Toggle weather mode between day (sunny) and night (rainy)
  /// Updates AppState.isDayMode and syncs weather data for solar calculations
  /// _Requirements: 2.3, 4.4_
  void _toggleWeather() {
    // Toggle day mode in AppState - image updates automatically via getter
    appState.toggleDayMode();
    
    // Keep weather data sync for solar calculations
    setState(() {
      if (appState.isDayMode) {
        currentWeather = WeatherData.sunny;
        appState.solarPower = 3.1;
        appState.weatherDescription = 'Însorit';
        appState.weatherIcon = Icons.wb_sunny_rounded;
      } else {
        currentWeather = WeatherData.rainy;
        appState.solarPower = 1.2;
        appState.weatherDescription = 'Ploios';
        appState.weatherIcon = Icons.water_drop_rounded;
      }
    });
  }

  @override
  void initState() {
    super.initState();
    
    // Listen to AppState changes (devices toggle)
    appState.addListener(_onAppStateChanged);
    
    // Încarcă vremea și prețurile la pornire
    _loadWeather();
    _loadOpcomPrices();
    
    // Setează bara de status transparentă
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0A0A0A),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
  }

  @override
  void dispose() {
    appState.removeListener(_onAppStateChanged);
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardListener(
      focusNode: _focusNode,
      autofocus: true,
      onKeyEvent: _handleKeyEvent,
      child: Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0.0, -0.3), // Centrat puțin mai sus
            radius: 1.2,
            colors: [
              Color(0xFF1A1A1A), // Gri închis în centru
              Color(0xFF121212), // Gri mai închis
              Color(0xFF0A0A0A), // Aproape negru
              Color(0xFF050505), // Negru la margini
            ],
            stops: [0.0, 0.3, 0.6, 1.0],
          ),
        ),
        child: SafeArea(
          top: false, // iOS status bar simulat se ocupă de partea de sus
          child: Stack(
            children: [
              // Conținutul principal (nu se va redimensiona)
              Column(
                children: [
                  // Header cu adresa și status
                  Builder(
                    builder: (context) {
                      final flows = appState.calculateEnergyFlows();
                      return Header(
                        address: 'Str. Victoriei 123',
                        status: flows.batteryPower < 0 ? 'Bateria se descarcă' : 'Bateria se încarcă',
                        isDischarging: flows.batteryPower < 0,
                    notificationCount: 0,
                        onProfileTap: () {
                          // Previne spam-ul pe buton
                          if (_isProcessingTap) return;
                          _isProcessingTap = true;
                          
                          // Show profile menu
                          showModalBottomSheet(
                            context: context,
                            backgroundColor: Colors.transparent,
                            builder: (context) => Container(
                              decoration: BoxDecoration(
                                color: const Color(0xFF1E1E1E),
                                borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
                              ),
                              padding: const EdgeInsets.all(20),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 40,
                                    height: 4,
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade600,
                                      borderRadius: BorderRadius.circular(2),
                                    ),
                                  ),
                                  const SizedBox(height: 20),
                                  ListTile(
                                    leading: const Icon(Icons.wb_sunny, color: Colors.amber),
                                    title: const Text('Toggle Weather', style: TextStyle(color: Colors.white)),
                                    onTap: () {
                                      Navigator.pop(context);
                                      _toggleWeather();
                                    },
                                  ),
                                  ListTile(
                                    leading: const Icon(Icons.logout, color: Colors.red),
                                    title: const Text('Logout', style: TextStyle(color: Colors.white)),
                                    onTap: () {
                                      Navigator.pop(context);
                                      widget.onLogout?.call();
                                    },
                                  ),
                                ],
                              ),
                            ),
                          );
                          
                          // Permite următorul tap după 300ms
                          Future.delayed(const Duration(milliseconds: 300), () {
                            if (mounted) {
                              _isProcessingTap = false;
                            }
                          });
                        },
                      );
                    },
                  ),
                  
                  // Casa cu indicatori și linii integrate
                  Expanded(
                    child: Builder(
                      builder: (context) {
                        // Calculate energy flows based on current state
                        final flows = appState.calculateEnergyFlows();
                        return HouseSection(
                          houseImage: currentImage,
                          batteryPower: flows.batteryPower,
                          powerwallPercentage: flows.batteryPercentage,
                          gridPower: flows.gridPower,
                          solarPower: flows.solarPower,
                          homePower: flows.homePower,
                        );
                      },
                    ),
                  ),
                  
                  // Spațiu pentru dock și meniul collapsed
                  const SizedBox(height: 160),
                ],
              ),
              
              // Smart Stack (replaces DevicesDock) - full width
              Positioned(
                left: 0,
                right: 0,
                bottom: 100,
                child: Builder(
                  builder: (context) {
                    final flows = appState.calculateEnergyFlows();
                    return SmartStack(
                      batteryPercent: flows.batteryPercentage.toDouble(),
                      batteryCapacityKwh: 13.5,
                      pricePerKwh: appState.currentPriceLeiKwh,
                      isPriceRising: appState.isPriceRising,
                      onPriceTap: _navigateToTrading,
                    );
                  },
                ),
              ),
              
              // Meniu overlay (se suprapune peste conținut)
              const Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: OverlayBottomMenu(),
              ),
              
              // Solar Forecast button
              Positioned(
                right: 80,
                top: 8,
                child: GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const SolarForecastScreen()),
                    );
                  },
                  child: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: const Color(0xFFFBBF24).withOpacity(0.2),
                      borderRadius: BorderRadius.circular(22),
                      border: Border.all(
                        color: const Color(0xFFFBBF24).withOpacity(0.4),
                        width: 1,
                      ),
                    ),
                    child: const Icon(
                      Icons.wb_sunny_rounded,
                      color: Color(0xFFFBBF24),
                      size: 22,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
    );
  }
}