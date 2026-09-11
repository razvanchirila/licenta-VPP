import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import 'dart:math' as math;
import 'package:flutter_interface/services/user_api_service.dart';

/// Energy statistics screen
/// 
/// Shows:
/// - Interactive chart with Solar, Consumption, Battery data
/// - Daily/Weekly/Monthly production statistics
/// - Daily/Weekly/Monthly consumption breakdown
class EnergyScreen extends StatefulWidget {
  const EnergyScreen({super.key});

  @override
  State<EnergyScreen> createState() => _EnergyScreenState();
}

class _EnergyScreenState extends State<EnergyScreen> {
  // Period selection: 'day', 'week', 'month'
  String _selectedPeriod = 'day';
  
  // Current date for navigation
  DateTime _currentDate = DateTime.now();
  
  // Mock data storage
  late List<EnergyDataPoint> _energyData;
  
  // Chart interaction
  bool _showingTooltip = false;
  int? _touchedIndex;

  // Chart line visibility toggles
  bool _showSolar = true;
  bool _showConsumption = true;
  bool _showBattery = false;
  bool _showGrid = false;

  // Loading state
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadApiData();
  }

  Future<void> _loadApiData() async {
    setState(() => _isLoading = true);
    final dateStr = DateFormat('yyyy-MM-dd').format(_currentDate);
    final result = await userApiService.getEnergyChart(_selectedPeriod, date: dateStr);

    if (!mounted) return;
    if (result != null && result['data_points'] != null) {
      final raw = result['data_points'] as List<dynamic>;
      setState(() {
        _energyData = raw.map((p) => EnergyDataPoint(
          time: DateTime.parse(p['timestamp'] as String),
          solar: (p['solar'] as num).toDouble(),
          consumption: (p['consumption'] as num).toDouble(),
          battery: (p['battery'] as num).toDouble(),
          grid: (p['grid'] as num).toDouble(),
          solarToLoad: (p['solar_to_load'] as num).toDouble(),
          solarToBattery: (p['solar_to_battery'] as num).toDouble(),
          solarToGrid: (p['solar_to_grid'] as num).toDouble(),
          batteryToLoad: (p['battery_to_load'] as num).toDouble(),
          gridToLoad: (p['grid_to_load'] as num).toDouble(),
        )).toList();
        _isLoading = false;
      });
    } else {
      setState(() {
        _energyData = _generateDataForPeriod(_selectedPeriod, _currentDate);
        _isLoading = false;
      });
    }
  }

  List<EnergyDataPoint> _generateDataForPeriod(String period, DateTime date) {
    final random = math.Random(date.day + date.month * 31);
    final List<EnergyDataPoint> data = [];
    
    int dataPoints;
    Duration interval;
    DateTime startTime;
    
    switch (period) {
      case 'day':
        // Data points every 10 minutes for entire day (00:00 to 23:59)
        startTime = DateTime(date.year, date.month, date.day, 0, 0);
        final endTime = date.day == DateTime.now().day && date.month == DateTime.now().month && date.year == DateTime.now().year
            ? DateTime.now() 
            : DateTime(date.year, date.month, date.day, 23, 59);
        dataPoints = ((endTime.difference(startTime).inMinutes) / 10).floor().clamp(1, 144);
        interval = const Duration(minutes: 10);
        break;
      case 'week':
        // Data points every hour for the week (Monday to current day)
        final weekday = date.weekday;
        startTime = DateTime(date.year, date.month, date.day - weekday + 1, 0, 0);
        dataPoints = (date.difference(startTime).inHours).clamp(1, 168);
        interval = const Duration(hours: 1);
        break;
      case 'month':
        // Data points every 4 hours for the month (1st to current day)
        startTime = DateTime(date.year, date.month, 1, 0, 0);
        dataPoints = ((date.difference(startTime).inHours) / 4).floor().clamp(1, 186);
        interval = const Duration(hours: 4);
        break;
      default:
        startTime = DateTime.now();
        dataPoints = 0;
        interval = const Duration(hours: 1);
    }
    
    for (int i = 0; i < dataPoints; i++) {
      final time = startTime.add(interval * i);
      final hour = time.hour;
      final minute = time.minute;
      
      // Solar production curve (bell curve peaking at noon, only during daylight 6AM-8PM)
      double solar = 0.0;
      if (hour >= 6 && hour <= 20) {
        // Normalized hour for solar curve (0 at 6AM, 7 at 1PM, 14 at 8PM)
        final solarHour = (hour - 6) + (minute / 60.0);
        // Bell curve peaking at solar noon (~1PM = hour 7 of solar day)
        solar = math.sin((solarHour / 14) * math.pi) * 2.5;
        // Add some random variation (clouds, etc.)
        solar = math.max(0, solar * (0.8 + random.nextDouble() * 0.4));
      }
      
      // Consumption pattern - always present, varies by time of day
      double consumption = 0.2 + random.nextDouble() * 0.15; // Base load (fridge, standby, etc.)
      
      // Night (00:00 - 06:00): minimal consumption
      if (hour >= 0 && hour < 6) {
        consumption = 0.15 + random.nextDouble() * 0.1;
      }
      // Morning peak (06:00 - 09:00): getting ready
      else if (hour >= 6 && hour < 9) {
        consumption = 0.5 + random.nextDouble() * 0.4;
      }
      // Mid-day (09:00 - 17:00): moderate
      else if (hour >= 9 && hour < 17) {
        consumption = 0.3 + random.nextDouble() * 0.3;
      }
      // Evening peak (17:00 - 22:00): cooking, TV, etc.
      else if (hour >= 17 && hour < 22) {
        consumption = 0.8 + random.nextDouble() * 0.6;
      }
      // Late night (22:00 - 24:00): winding down
      else {
        consumption = 0.25 + random.nextDouble() * 0.15;
      }
      
      // Calculate energy balance properly:
      // If solar > consumption: excess goes to battery (charging) or grid (export)
      // If solar < consumption: deficit comes from battery (discharging) or grid (import)
      
      double battery = 0.0;
      double grid = 0.0;
      double solarToLoad = 0.0;
      double solarToBattery = 0.0;
      double solarToGrid = 0.0;
      double batteryToLoad = 0.0;
      double gridToLoad = 0.0;
      
      if (solar >= consumption) {
        // Solar covers all consumption
        solarToLoad = consumption;
        final excess = solar - consumption;
        
        // Excess goes primarily to battery, then to grid (export)
        solarToBattery = excess * 0.8; // 80% to battery
        solarToGrid = excess * 0.2;    // 20% exported
        battery = solarToBattery;      // Positive = charging
        grid = -solarToGrid;           // Negative = exporting to grid
      } else {
        // Solar doesn't cover consumption
        solarToLoad = solar;
        final deficit = consumption - solar;
        
        // Try to cover deficit with battery first (during evening/night)
        if (hour >= 17 || hour < 6) {
          batteryToLoad = math.min(deficit, 1.0 + random.nextDouble() * 0.5); // Battery can provide up to ~1.5kW
          battery = -batteryToLoad; // Negative = discharging
        }
        
        // Grid covers the rest (import)
        gridToLoad = deficit - batteryToLoad;
        grid = gridToLoad;  // Positive = importing from grid
      }
      
      data.add(EnergyDataPoint(
        time: time,
        solar: solar,
        consumption: consumption,
        battery: battery,
        grid: grid,
        // Detailed breakdown for statistics
        solarToLoad: solarToLoad,
        solarToBattery: solarToBattery,
        solarToGrid: solarToGrid,
        batteryToLoad: batteryToLoad,
        gridToLoad: gridToLoad,
      ));
    }
    
    return data;
  }

  void _navigateDate(int direction) {
    DateTime newDate;
    switch (_selectedPeriod) {
      case 'day':
        newDate = _currentDate.add(Duration(days: direction));
        break;
      case 'week':
        newDate = _currentDate.add(Duration(days: direction * 7));
        break;
      case 'month':
        newDate = DateTime(_currentDate.year, _currentDate.month + direction, _currentDate.day);
        break;
      default:
        newDate = _currentDate;
    }
    if (newDate.isAfter(DateTime.now())) newDate = DateTime.now();
    setState(() => _currentDate = newDate);
    _loadApiData();
  }

  void _changePeriod(String period) {
    setState(() => _selectedPeriod = period);
    _loadApiData();
  }

  // Calculate totals from data - using detailed breakdown for accuracy
  Map<String, double> _calculateTotals() {
    // Hours per data point based on interval
    double hoursPerPoint = _selectedPeriod == 'day' ? (10/60) : (_selectedPeriod == 'week' ? 1.0 : 4.0);
    
    // Production breakdown
    double totalSolar = 0;
    double solarToLoad = 0;
    double solarToGrid = 0;
    double solarToBattery = 0;
    
    // Consumption breakdown
    double totalConsumption = 0;
    double consumptionFromSolar = 0;
    double consumptionFromGrid = 0;
    double consumptionFromBattery = 0;
    
    for (final point in _energyData) {
      totalSolar += point.solar * hoursPerPoint;
      totalConsumption += point.consumption * hoursPerPoint;
      
      // Production breakdown
      solarToLoad += point.solarToLoad * hoursPerPoint;
      solarToGrid += point.solarToGrid * hoursPerPoint;
      solarToBattery += point.solarToBattery * hoursPerPoint;
      
      // Consumption breakdown
      consumptionFromSolar += point.solarToLoad * hoursPerPoint;
      consumptionFromGrid += point.gridToLoad * hoursPerPoint;
      consumptionFromBattery += point.batteryToLoad * hoursPerPoint;
    }
    
    return {
      'totalSolar': totalSolar,
      'solarToLoad': solarToLoad,
      'solarToGrid': solarToGrid,
      'solarToBattery': solarToBattery,
      'totalConsumption': totalConsumption,
      'consumptionFromSolar': consumptionFromSolar,
      'consumptionFromGrid': consumptionFromGrid,
      'consumptionFromBattery': consumptionFromBattery,
    };
  }

  @override
  Widget build(BuildContext context) {
    final totals = _calculateTotals();
    
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header cu back button
            _buildHeader(),
            
            // Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 8),
                    
                    // Date navigation and period selector
                    _buildDateNavigation(),
                    const SizedBox(height: 16),
                    
                    // Interactive chart
                    _buildChart(),
                    const SizedBox(height: 24),
                      
                      // Production statistics card
                      _buildProductionCard(totals),
                      const SizedBox(height: 16),
                      
                      // Consumption statistics card
                      _buildConsumptionCard(totals),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          // Back button
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios_rounded,
              color: Colors.white,
              size: 22,
            ),
          ),
          const SizedBox(width: 8),
          // Title
          Text(
            'Statistici',
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.5,
            ),
          ),
          const Spacer(),
          // Filter button to toggle chart lines
          IconButton(
            onPressed: _showChartFilterDialog,
            icon: Icon(
              Icons.tune_rounded,
              color: Colors.white.withOpacity(0.8),
              size: 24,
            ),
          ),
        ],
      ),
    );
  }

  void _showChartFilterDialog() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
          return Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: Color(0xFF1C1C1E),
              borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Handle
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Text(
                  'Afișare grafice',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 16),
                // Toggle switches
                _buildFilterToggle(
                  label: 'Solar',
                  color: const Color(0xFF3B82F6),
                  value: _showSolar,
                  onChanged: (val) {
                    setModalState(() => _showSolar = val);
                    setState(() {});
                  },
                ),
                _buildFilterToggle(
                  label: 'Consum',
                  color: const Color(0xFFEF4444),
                  value: _showConsumption,
                  onChanged: (val) {
                    setModalState(() => _showConsumption = val);
                    setState(() {});
                  },
                ),
                _buildFilterToggle(
                  label: 'Baterie',
                  color: const Color(0xFF22C55E),
                  value: _showBattery,
                  onChanged: (val) {
                    setModalState(() => _showBattery = val);
                    setState(() {});
                  },
                ),
                _buildFilterToggle(
                  label: 'Grid',
                  color: const Color(0xFFFBBF24),
                  value: _showGrid,
                  onChanged: (val) {
                    setModalState(() => _showGrid = val);
                    setState(() {});
                  },
                ),
                const SizedBox(height: 20),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildFilterToggle({
    required String label,
    required Color color,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: color,
            activeTrackColor: color.withOpacity(0.3),
            inactiveThumbColor: Colors.white.withOpacity(0.5),
            inactiveTrackColor: Colors.white.withOpacity(0.1),
          ),
        ],
      ),
    );
  }

  Widget _buildDateNavigation() {
    String dateText;
    switch (_selectedPeriod) {
      case 'day':
        dateText = DateFormat('dd/MM/yyyy').format(_currentDate);
        break;
      case 'week':
        final weekStart = _currentDate.subtract(Duration(days: _currentDate.weekday - 1));
        dateText = '${DateFormat('dd/MM').format(weekStart)} - ${DateFormat('dd/MM').format(_currentDate)}';
        break;
      case 'month':
        final monthStart = DateTime(_currentDate.year, _currentDate.month, 1);
        dateText = '${DateFormat('dd/MM').format(monthStart)} - ${DateFormat('dd/MM').format(_currentDate)}';
        break;
      default:
        dateText = DateFormat('dd/MM/yyyy').format(_currentDate);
    }
    
    final bool canGoForward = _currentDate.isBefore(DateTime.now().subtract(const Duration(days: 1)));
    
    return Row(
      children: [
        // Left arrow
        _buildNavButton(
          icon: Icons.chevron_left_rounded,
          onTap: () => _navigateDate(-1),
        ),
        const SizedBox(width: 8),
        
        // Date display
        Expanded(
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              dateText,
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        
        // Right arrow
        _buildNavButton(
          icon: Icons.chevron_right_rounded,
          onTap: canGoForward ? () => _navigateDate(1) : null,
          enabled: canGoForward,
        ),
        
        const SizedBox(width: 16),
        
        // Period selector dropdown
        _buildPeriodSelector(),
      ],
    );
  }

  Widget _buildNavButton({
    required IconData icon,
    VoidCallback? onTap,
    bool enabled = true,
  }) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: const Color(0xFF1C1C1E),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: Colors.white.withOpacity(0.08),
            width: 1,
          ),
        ),
        child: Icon(
          icon,
          color: enabled ? Colors.white : Colors.white.withOpacity(0.3),
          size: 24,
        ),
      ),
    );
  }

  Widget _buildPeriodSelector() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _selectedPeriod,
          dropdownColor: const Color(0xFF1C1C1E),
          icon: Icon(
            Icons.keyboard_arrow_down_rounded,
            color: Colors.white.withOpacity(0.6),
          ),
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          items: const [
            DropdownMenuItem(value: 'day', child: Text('Zi')),
            DropdownMenuItem(value: 'week', child: Text('Săpt.')),
            DropdownMenuItem(value: 'month', child: Text('Lună')),
          ],
          onChanged: (value) {
            if (value != null) _changePeriod(value);
          },
        ),
      ),
    );
  }

  Widget _buildChart() {
    if (_isLoading) {
      return Container(
        height: 300,
        decoration: BoxDecoration(
          color: const Color(0xFF1C1C1E),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: const Center(
          child: CircularProgressIndicator(color: Color(0xFF3B82F6)),
        ),
      );
    }

    if (_energyData.isEmpty) {
      return Container(
        height: 300,
        decoration: BoxDecoration(
          color: const Color(0xFF1C1C1E),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Center(
          child: Text(
            'Nu există date',
            style: GoogleFonts.inter(
              color: Colors.white.withOpacity(0.5),
              fontSize: 14,
            ),
          ),
        ),
      );
    }
    
    return Container(
      height: 300,
      padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: true,
            horizontalInterval: 0.5,
            verticalInterval: _getVerticalInterval(),
            getDrawingHorizontalLine: (value) {
              return FlLine(
                color: Colors.white.withOpacity(0.1),
                strokeWidth: 1,
              );
            },
            getDrawingVerticalLine: (value) {
              return FlLine(
                color: Colors.white.withOpacity(0.05),
                strokeWidth: 1,
              );
            },
          ),
          titlesData: FlTitlesData(
            show: true,
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 30,
                interval: _getBottomInterval(),
                getTitlesWidget: _bottomTitleWidgets,
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: 0.5,
                reservedSize: 40,
                getTitlesWidget: _leftTitleWidgets,
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          minX: 0,
          maxX: (_energyData.length - 1).toDouble(),
          minY: 0,
          maxY: _getMaxY(),
          lineTouchData: LineTouchData(
            enabled: true,
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (touchedSpot) => const Color(0xFF2C2C2E),
              tooltipRoundedRadius: 12,
              tooltipPadding: const EdgeInsets.all(12),
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((spot) {
                  String label;
                  Color color;
                  String suffix = '';
                  final index = spot.x.toInt();
                  
                  // Determine which line this is based on the actual bar index
                  // and which lines are currently visible
                  int actualIndex = _getActualLineIndex(spot.barIndex);
                  
                  switch (actualIndex) {
                    case 0: // Solar
                      label = 'Solar';
                      color = const Color(0xFF3B82F6);
                      break;
                    case 1: // Consumption
                      label = 'Consum';
                      color = const Color(0xFFEF4444);
                      break;
                    case 2: // Battery
                      label = 'Baterie';
                      color = const Color(0xFF22C55E);
                      if (index >= 0 && index < _energyData.length) {
                        suffix = _energyData[index].battery >= 0 ? ' (încărcare)' : ' (descărcare)';
                      }
                      break;
                    case 3: // Grid
                      label = 'Grid';
                      color = const Color(0xFFFBBF24);
                      if (index >= 0 && index < _energyData.length) {
                        suffix = _energyData[index].grid >= 0 ? ' (import)' : ' (export)';
                      }
                      break;
                    default:
                      label = '';
                      color = Colors.white;
                  }
                  return LineTooltipItem(
                    '$label: ${spot.y.toStringAsFixed(2)} kW$suffix',
                    GoogleFonts.inter(
                      color: color,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  );
                }).toList();
              },
            ),
            handleBuiltInTouches: true,
          ),
          lineBarsData: _buildLineBarsData(),
        ),
      ),
    );
  }

  // Build line bars data based on visibility toggles
  List<LineChartBarData> _buildLineBarsData() {
    final List<LineChartBarData> lines = [];
    
    if (_showSolar) {
      lines.add(_buildLineChartBarData(
        spots: _energyData.asMap().entries.map((e) => 
          FlSpot(e.key.toDouble(), e.value.solar)
        ).toList(),
        color: const Color(0xFF3B82F6),
        fillColor: const Color(0xFF3B82F6).withOpacity(0.2),
      ));
    }
    
    if (_showConsumption) {
      lines.add(_buildLineChartBarData(
        spots: _energyData.asMap().entries.map((e) => 
          FlSpot(e.key.toDouble(), e.value.consumption)
        ).toList(),
        color: const Color(0xFFEF4444),
        fillColor: const Color(0xFFEF4444).withOpacity(0.15),
      ));
    }
    
    if (_showBattery) {
      lines.add(_buildLineChartBarData(
        spots: _energyData.asMap().entries.map((e) => 
          FlSpot(e.key.toDouble(), e.value.battery.abs())
        ).toList(),
        color: const Color(0xFF22C55E),
        fillColor: const Color(0xFF22C55E).withOpacity(0.1),
      ));
    }
    
    if (_showGrid) {
      lines.add(_buildLineChartBarData(
        spots: _energyData.asMap().entries.map((e) => 
          FlSpot(e.key.toDouble(), e.value.grid.abs())
        ).toList(),
        color: const Color(0xFFFBBF24),
        fillColor: const Color(0xFFFBBF24).withOpacity(0.1),
      ));
    }
    
    return lines;
  }

  // Map bar index back to actual line type based on visibility
  int _getActualLineIndex(int barIndex) {
    int currentIndex = 0;
    
    if (_showSolar) {
      if (barIndex == currentIndex) return 0; // Solar
      currentIndex++;
    }
    if (_showConsumption) {
      if (barIndex == currentIndex) return 1; // Consumption
      currentIndex++;
    }
    if (_showBattery) {
      if (barIndex == currentIndex) return 2; // Battery
      currentIndex++;
    }
    if (_showGrid) {
      if (barIndex == currentIndex) return 3; // Grid
      currentIndex++;
    }
    
    return -1;
  }

  LineChartBarData _buildLineChartBarData({
    required List<FlSpot> spots,
    required Color color,
    required Color fillColor,
    bool showDots = false,
  }) {
    return LineChartBarData(
      spots: spots,
      isCurved: true,
      curveSmoothness: 0.3,
      color: color,
      barWidth: 2,
      isStrokeCapRound: true,
      dotData: FlDotData(show: showDots),
      belowBarData: BarAreaData(
        show: true,
        color: fillColor,
      ),
    );
  }

  double _getMaxY() {
    double maxVal = 0;
    for (final point in _energyData) {
      if (_showSolar) maxVal = math.max(maxVal, point.solar);
      if (_showConsumption) maxVal = math.max(maxVal, point.consumption);
      if (_showBattery) maxVal = math.max(maxVal, point.battery.abs());
      if (_showGrid) maxVal = math.max(maxVal, point.grid.abs());
    }
    return (maxVal * 1.2).ceilToDouble().clamp(1.0, 10.0);
  }

  double _getVerticalInterval() {
    switch (_selectedPeriod) {
      case 'day':
        return (_energyData.length / 6).ceilToDouble();
      case 'week':
        return (_energyData.length / 7).ceilToDouble();
      case 'month':
        return (_energyData.length / 10).ceilToDouble();
      default:
        return 10;
    }
  }

  double _getBottomInterval() {
    return (_energyData.length / 6).ceilToDouble().clamp(1, double.infinity);
  }

  Widget _bottomTitleWidgets(double value, TitleMeta meta) {
    final index = value.toInt();
    if (index < 0 || index >= _energyData.length) {
      return const SizedBox.shrink();
    }
    
    final time = _energyData[index].time;
    String text;
    
    switch (_selectedPeriod) {
      case 'day':
        text = DateFormat('HH:mm').format(time);
        break;
      case 'week':
        text = DateFormat('E').format(time);
        break;
      case 'month':
        text = DateFormat('dd').format(time);
        break;
      default:
        text = '';
    }
    
    return SideTitleWidget(
      axisSide: meta.axisSide,
      child: Text(
        text,
        style: GoogleFonts.inter(
          color: Colors.white.withOpacity(0.5),
          fontSize: 10,
        ),
      ),
    );
  }

  Widget _leftTitleWidgets(double value, TitleMeta meta) {
    return SideTitleWidget(
      axisSide: meta.axisSide,
      child: Text(
        value.toStringAsFixed(1),
        style: GoogleFonts.inter(
          color: Colors.white.withOpacity(0.5),
          fontSize: 10,
        ),
      ),
    );
  }

  Widget _buildProductionCard(Map<String, double> totals) {
    final totalSolar = totals['totalSolar'] ?? 0.0;
    final toLoad = totals['solarToLoad'] ?? 0.0;
    final toGrid = totals['solarToGrid'] ?? 0.0;
    final toBattery = totals['solarToBattery'] ?? 0.0;
    
    final toLoadPercent = totalSolar > 0 ? (toLoad / totalSolar * 100) : 0.0;
    final toGridPercent = totalSolar > 0 ? (toGrid / totalSolar * 100) : 0.0;
    final toBatteryPercent = totalSolar > 0 ? (toBattery / totalSolar * 100) : 0.0;
    
    return _buildStatsCard(
      title: 'Producție ${_getPeriodLabel()}:',
      totalValue: _formatEnergy(totalSolar),
      items: [
        StatsItem(
          label: 'Trimisă la sarcină',
          value: _formatEnergy(toLoad),
          percentage: toLoadPercent,
          color: const Color(0xFF3B82F6), // Blue
        ),
        StatsItem(
          label: 'Trimisă la rețea',
          value: _formatEnergy(toGrid),
          percentage: toGridPercent,
          color: const Color(0xFF6366F1), // Indigo/Purple
        ),
        StatsItem(
          label: 'Trimisă la baterie',
          value: _formatEnergy(toBattery),
          percentage: toBatteryPercent,
          color: const Color(0xFF22C55E), // Green
        ),
      ],
    );
  }

  Widget _buildConsumptionCard(Map<String, double> totals) {
    final totalConsumption = totals['totalConsumption'] ?? 0.0;
    final fromSolar = totals['consumptionFromSolar'] ?? 0.0;
    final fromGrid = totals['consumptionFromGrid'] ?? 0.0;
    final fromBattery = totals['consumptionFromBattery'] ?? 0.0;
    
    final fromSolarPercent = totalConsumption > 0 ? (fromSolar / totalConsumption * 100) : 0.0;
    final fromGridPercent = totalConsumption > 0 ? (fromGrid / totalConsumption * 100) : 0.0;
    final fromBatteryPercent = totalConsumption > 0 ? (fromBattery / totalConsumption * 100) : 0.0;
    
    return _buildStatsCard(
      title: 'Consum ${_getPeriodLabel()}:',
      totalValue: _formatEnergy(totalConsumption),
      items: [
        StatsItem(
          label: 'De la energie solară',
          value: _formatEnergy(fromSolar),
          percentage: fromSolarPercent,
          color: const Color(0xFFEF4444), // Red
        ),
        StatsItem(
          label: 'Din rețea',
          value: _formatEnergy(fromGrid),
          percentage: fromGridPercent,
          color: const Color(0xFFF97316), // Orange
        ),
        StatsItem(
          label: 'De la baterie',
          value: _formatEnergy(fromBattery),
          percentage: fromBatteryPercent,
          color: const Color(0xFF22C55E), // Green
        ),
      ],
    );
  }

  String _getPeriodLabel() {
    switch (_selectedPeriod) {
      case 'day':
        return 'zilnică';
      case 'week':
        return 'săptămânală';
      case 'month':
        return 'lunară';
      default:
        return '';
    }
  }

  String _formatEnergy(double kWh) {
    if (kWh >= 1) {
      return '${kWh.toStringAsFixed(1)} kWh';
    } else {
      return '${(kWh * 1000).toStringAsFixed(0)} Wh';
    }
  }

  Widget _buildStatsCard({
    required String title,
    required String totalValue,
    required List<StatsItem> items,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                totalValue,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // Progress bars row - full width with proportional segments
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: SizedBox(
              height: 6,
              child: Row(
                children: items.asMap().entries.map((entry) {
                  final index = entry.key;
                  final item = entry.value;
                  // Use max(5, percentage) to ensure visibility even for small percentages
                  final flex = math.max(5, item.percentage.round());
                  return Expanded(
                    flex: flex,
                    child: Container(
                      margin: EdgeInsets.only(right: index < items.length - 1 ? 2 : 0),
                      decoration: BoxDecoration(
                        color: item.color,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 16),
          
          // Stats items row
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: items.map((item) {
              return Expanded(
                child: _buildStatsItemColumn(item),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsItemColumn(StatsItem item) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${item.percentage.toStringAsFixed(item.percentage >= 10 ? 1 : 2)} %',
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.7),
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: item.color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                item.value,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          item.label,
          style: GoogleFonts.inter(
            color: Colors.white.withOpacity(0.5),
            fontSize: 11,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}

/// Data model for a single energy data point
class EnergyDataPoint {
  final DateTime time;
  final double solar;       // kW - total solar production
  final double consumption; // kW - total home consumption
  final double battery;     // kW - positive = charging, negative = discharging
  final double grid;        // kW - grid import (positive) or export (negative)
  
  // Detailed breakdown for accurate statistics
  final double solarToLoad;     // kW - solar energy going directly to consumption
  final double solarToBattery;  // kW - solar energy charging the battery
  final double solarToGrid;     // kW - solar energy exported to grid
  final double batteryToLoad;   // kW - battery energy going to consumption
  final double gridToLoad;      // kW - grid energy going to consumption

  EnergyDataPoint({
    required this.time,
    required this.solar,
    required this.consumption,
    required this.battery,
    required this.grid,
    this.solarToLoad = 0,
    this.solarToBattery = 0,
    this.solarToGrid = 0,
    this.batteryToLoad = 0,
    this.gridToLoad = 0,
  });
}

/// Statistics item for the breakdown cards
class StatsItem {
  final String label;
  final String value;
  final double percentage;
  final Color color;

  StatsItem({
    required this.label,
    required this.value,
    required this.percentage,
    required this.color,
  });
}
