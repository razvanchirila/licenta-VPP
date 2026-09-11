import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/services/user_api_service.dart';

/// Impact screen for energy visualization
/// 
/// Shows:
/// - Energy sources distribution (Solar, Battery, Grid)
/// - Time-of-Use selector with energy flow visualization
/// - Monthly savings chart
class ImpactScreen extends StatefulWidget {
  const ImpactScreen({super.key});

  @override
  State<ImpactScreen> createState() => _ImpactScreenState();
}

class _ImpactScreenState extends State<ImpactScreen> {
  // Energy sources percentages (sum to 100)
  double _solarPercent = 45.0;
  double _batteryPercent = 35.0;
  double _gridPercent = 20.0;
  double _solarKwh = 4.5;
  double _batteryKwh = 3.5;
  double _gridKwh = 2.0;

  // Time of use selection
  late String _selectedTimeOfUse;

  // Loading state
  bool _isLoading = true;

  // Energy values for each time period (kWh)
  Map<String, Map<String, double>> _energyByPeriod = {
    'Peak': {'solar': 2.8, 'battery': 4.2, 'grid': 1.5},
    'Off-Peak': {'solar': 1.2, 'battery': 2.1, 'grid': 3.8},
  };

  // Monthly savings data (last 6 months)
  List<Map<String, dynamic>> _monthlySavings = [
    {'month': 'Iun', 'savings': 85.0},
    {'month': 'Iul', 'savings': 120.0},
    {'month': 'Aug', 'savings': 145.0},
    {'month': 'Sep', 'savings': 110.0},
    {'month': 'Oct', 'savings': 95.0},
    {'month': 'Nov', 'savings': 130.0, 'current': true},
  ];

  @override
  void initState() {
    super.initState();
    _selectedTimeOfUse = appState.timeOfUse;
    _loadImpactData();
  }

  Future<void> _loadImpactData() async {
    final data = await userApiService.getEnergyImpact();
    if (!mounted) return;
    if (data != null) {
      setState(() {
        _solarPercent = (data['solar_percent'] as num).toDouble();
        _batteryPercent = (data['battery_percent'] as num).toDouble();
        _gridPercent = (data['grid_percent'] as num).toDouble();
        _solarKwh = (data['solar_kwh'] as num).toDouble();
        _batteryKwh = (data['battery_kwh'] as num).toDouble();
        _gridKwh = (data['grid_kwh'] as num).toDouble();

        if (data['peak'] != null) {
          final p = data['peak'] as Map<String, dynamic>;
          _energyByPeriod['Peak'] = {
            'solar': (p['solar'] as num).toDouble(),
            'battery': (p['battery'] as num).toDouble(),
            'grid': (p['grid'] as num).toDouble(),
          };
        }
        if (data['off_peak'] != null) {
          final op = data['off_peak'] as Map<String, dynamic>;
          _energyByPeriod['Off-Peak'] = {
            'solar': (op['solar'] as num).toDouble(),
            'battery': (op['battery'] as num).toDouble(),
            'grid': (op['grid'] as num).toDouble(),
          };
        }
        if (data['monthly_savings'] != null) {
          _monthlySavings = (data['monthly_savings'] as List<dynamic>).map((m) {
            final map = m as Map<String, dynamic>;
            return <String, dynamic>{
              'month': map['month'] as String,
              'savings': (map['savings'] as num).toDouble(),
              if (map['current'] == true) 'current': true,
            };
          }).toList();
        }
        _isLoading = false;
      });
    } else {
      setState(() => _isLoading = false);
    }
  }

  // Colors
  static const Color solarColor = Color(0xFFFBBF24);
  static const Color batteryColor = Color(0xFF22C55E);
  static const Color gridColor = Color(0xFF64748B);
  static const Color peakColor = Color(0xFFEF4444);
  static const Color offPeakColor = Color(0xFF3B82F6);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(color: Color(0xFFFBBF24)),
                    )
                  : _buildContent(),
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
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios_rounded,
              color: Colors.white,
              size: 22,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            'Impact',
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          
          // Section 1: Energy Sources Distribution
          _buildSectionHeader(
            icon: Icons.pie_chart_rounded,
            title: 'Surse de energie',
            subtitle: 'Distribuția energiei consumate azi',
          ),
          const SizedBox(height: 16),
          _buildEnergySourcesCard(),
          const SizedBox(height: 24),
          
          // Section 2: Time of Use
          _buildSectionHeader(
            icon: Icons.access_time_rounded,
            title: 'Consum pe tarif',
            subtitle: 'Energia folosită pe intervale orare',
          ),
          const SizedBox(height: 16),
          _buildTimeOfUseCard(),
          const SizedBox(height: 24),
          
          // Section 3: Monthly Savings
          _buildSectionHeader(
            icon: Icons.savings_rounded,
            title: 'Economii lunare',
            subtitle: 'Bani economisiți în ultimele 6 luni',
          ),
          const SizedBox(height: 16),
          _buildMonthlySavingsCard(),
          
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: const Color(0xFF1C1C1E),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(
            icon,
            color: Colors.white.withOpacity(0.8),
            size: 22,
          ),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              subtitle,
              style: GoogleFonts.inter(
                color: Colors.white.withOpacity(0.5),
                fontSize: 13,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Section 1: Donut chart showing energy sources
  Widget _buildEnergySourcesCard() {
    // Calculate self-consumption (without grid)
    final selfConsumption = _solarPercent + _batteryPercent;
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Left side - Legend with consumption values
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildLegendItemWithValue(
                  color: solarColor,
                  label: 'Solar',
                  percent: _solarPercent,
                  kwh: _solarKwh,
                ),
                const SizedBox(height: 14),
                _buildLegendItemWithValue(
                  color: batteryColor,
                  label: 'Baterie',
                  percent: _batteryPercent,
                  kwh: _batteryKwh,
                ),
                const SizedBox(height: 14),
                _buildLegendItemWithValue(
                  color: gridColor,
                  label: 'Rețea',
                  percent: _gridPercent,
                  kwh: _gridKwh,
                ),
              ],
            ),
          ),
          // Right side - Donut chart
          SizedBox(
            width: 130,
            height: 130,
            child: CustomPaint(
              painter: DonutChartPainter(
                solarPercent: _solarPercent,
                batteryPercent: _batteryPercent,
                gridPercent: _gridPercent,
                solarColor: solarColor,
                batteryColor: batteryColor,
                gridColor: gridColor,
              ),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${selfConsumption.toInt()}%',
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      'Consum propriu',
                      style: GoogleFonts.inter(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItemWithValue({
    required Color color,
    required String label,
    required double percent,
    required double kwh,
  }) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: GoogleFonts.inter(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 12,
                ),
              ),
              Row(
                children: [
                  Text(
                    '${percent.toInt()}%',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${kwh.toStringAsFixed(1)} kWh',
                    style: GoogleFonts.inter(
                      color: Colors.white.withOpacity(0.4),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLegendItem({
    required Color color,
    required String label,
    required String value,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(width: 8),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: GoogleFonts.inter(
                color: Colors.white.withOpacity(0.6),
                fontSize: 12,
              ),
            ),
            Text(
              value,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Section 2: Time of Use selector with vertical bars
  Widget _buildTimeOfUseCard() {
    final currentPeriodData = _energyByPeriod[_selectedTimeOfUse]!;
    final maxValue = 5.0; // Max kWh for scaling bars
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          // Time of Use selector
          Row(
            children: [
              Expanded(
                child: _buildTimeOfUseButton(
                  label: 'Peak',
                  subtitle: '17:00 - 22:00',
                  color: peakColor,
                  isSelected: _selectedTimeOfUse == 'Peak',
                  onTap: () {
                    setState(() => _selectedTimeOfUse = 'Peak');
                    appState.timeOfUse = 'Peak';
                  },
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildTimeOfUseButton(
                  label: 'Off-Peak',
                  subtitle: '22:00 - 17:00',
                  color: offPeakColor,
                  isSelected: _selectedTimeOfUse == 'Off-Peak',
                  onTap: () {
                    setState(() => _selectedTimeOfUse = 'Off-Peak');
                    appState.timeOfUse = 'Off-Peak';
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // Vertical bars
          SizedBox(
            height: 130,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                _buildVerticalBar(
                  color: solarColor,
                  value: currentPeriodData['solar']!,
                  maxValue: maxValue,
                  label: 'Solar',
                ),
                _buildVerticalBar(
                  color: batteryColor,
                  value: currentPeriodData['battery']!,
                  maxValue: maxValue,
                  label: 'Baterie',
                ),
                _buildVerticalBar(
                  color: gridColor,
                  value: currentPeriodData['grid']!,
                  maxValue: maxValue,
                  label: 'Rețea',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeOfUseButton({
    required String label,
    required String subtitle,
    required Color color,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
        decoration: BoxDecoration(
          color: isSelected 
              ? Colors.white.withOpacity(0.10) 
              : Colors.white.withOpacity(0.03),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected 
                ? Colors.white.withOpacity(0.25) 
                : Colors.white.withOpacity(0.06),
            width: 1,
          ),
        ),
        child: Column(
          children: [
            Text(
              label,
              style: GoogleFonts.inter(
                color: isSelected 
                    ? Colors.white 
                    : Colors.white.withOpacity(0.4),
                fontSize: 16,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: GoogleFonts.inter(
                color: isSelected 
                    ? Colors.white.withOpacity(0.6) 
                    : Colors.white.withOpacity(0.25),
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVerticalBar({
    required Color color,
    required double value,
    required double maxValue,
    required String label,
  }) {
    final maxBarHeight = 70.0; // Fixed max height for bar
    final barHeight = (value / maxValue) * maxBarHeight;
    
    return SizedBox(
      width: 60,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Value label
          Text(
            '${value.toStringAsFixed(1)}',
            style: GoogleFonts.inter(
              color: color,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            'kWh',
            style: GoogleFonts.inter(
              color: Colors.white.withOpacity(0.4),
              fontSize: 10,
            ),
          ),
          const SizedBox(height: 6),
          // Bar
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            width: 50,
            height: barHeight,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(6),
              boxShadow: [
                BoxShadow(
                  color: color.withOpacity(0.4),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          // Label
          Text(
            label,
            style: GoogleFonts.inter(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  /// Section 3: Monthly savings bar chart
  Widget _buildMonthlySavingsCard() {
    final maxSavings = _monthlySavings
        .map((m) => m['savings'] as double)
        .reduce((a, b) => a > b ? a : b);
    
    // Calculate total savings
    final totalSavings = _monthlySavings
        .map((m) => m['savings'] as double)
        .reduce((a, b) => a + b);
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          // Total savings header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Total economisit',
                    style: GoogleFonts.inter(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${totalSavings.toInt()} RON',
                    style: GoogleFonts.inter(
                      color: batteryColor,
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: batteryColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.trending_up_rounded,
                      color: batteryColor,
                      size: 18,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '+12%',
                      style: GoogleFonts.inter(
                        color: batteryColor,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // Bar chart
          SizedBox(
            height: 130,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: _monthlySavings.map((monthData) {
                final isCurrent = monthData['current'] == true;
                final savings = monthData['savings'] as double;
                
                return _buildMonthlyBar(
                  month: monthData['month'] as String,
                  savings: savings,
                  maxSavings: maxSavings,
                  isCurrent: isCurrent,
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMonthlyBar({
    required String month,
    required double savings,
    required double maxSavings,
    required bool isCurrent,
  }) {
    final color = isCurrent ? batteryColor : Colors.white.withOpacity(0.3);
    final maxBarHeight = 80.0; // Fixed max height for bar
    final barHeight = (savings / maxSavings) * maxBarHeight;
    
    return SizedBox(
      width: 44,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Value
          Text(
            '${savings.toInt()}',
            style: GoogleFonts.inter(
              color: isCurrent ? batteryColor : Colors.white.withOpacity(0.5),
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          // Bar
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOutCubic,
            width: 36,
            height: barHeight,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(6),
              boxShadow: isCurrent
                  ? [
                      BoxShadow(
                        color: batteryColor.withOpacity(0.4),
                        blurRadius: 8,
                        offset: const Offset(0, 4),
                      ),
                    ]
                  : null,
            ),
          ),
          const SizedBox(height: 8),
          // Month label
          Text(
            month,
            style: GoogleFonts.inter(
              color: isCurrent ? Colors.white : Colors.white.withOpacity(0.5),
              fontSize: 12,
              fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}

/// Custom painter for donut chart with glow effect
class DonutChartPainter extends CustomPainter {
  final double solarPercent;
  final double batteryPercent;
  final double gridPercent;
  final Color solarColor;
  final Color batteryColor;
  final Color gridColor;

  DonutChartPainter({
    required this.solarPercent,
    required this.batteryPercent,
    required this.gridPercent,
    required this.solarColor,
    required this.batteryColor,
    required this.gridColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    final strokeWidth = 12.0;
    final rect = Rect.fromCircle(center: center, radius: radius - strokeWidth / 2);
    
    const startAngle = -90.0 * (3.14159 / 180); // Start from top
    final total = solarPercent + batteryPercent + gridPercent;
    
    // Calculate sweep angles
    final solarSweep = (solarPercent / total) * 2 * 3.14159;
    final batterySweep = (batteryPercent / total) * 2 * 3.14159;
    final gridSweep = (gridPercent / total) * 2 * 3.14159;
    
    // Glow paint (drawn first, behind the main arcs)
    final glowPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth + 8
      ..strokeCap = StrokeCap.butt
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
    
    // Draw glow for solar arc
    glowPaint.color = solarColor.withOpacity(0.4);
    canvas.drawArc(rect, startAngle, solarSweep, false, glowPaint);
    
    // Draw glow for battery arc
    glowPaint.color = batteryColor.withOpacity(0.4);
    canvas.drawArc(rect, startAngle + solarSweep, batterySweep, false, glowPaint);
    
    // Draw glow for grid arc
    glowPaint.color = gridColor.withOpacity(0.3);
    canvas.drawArc(rect, startAngle + solarSweep + batterySweep, gridSweep, false, glowPaint);
    
    // Main paint
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.butt;
    
    // Draw solar arc
    paint.color = solarColor;
    canvas.drawArc(rect, startAngle, solarSweep, false, paint);
    
    // Draw battery arc
    paint.color = batteryColor;
    canvas.drawArc(rect, startAngle + solarSweep, batterySweep, false, paint);
    
    // Draw grid arc
    paint.color = gridColor;
    canvas.drawArc(rect, startAngle + solarSweep + batterySweep, gridSweep, false, paint);
  }

  @override
  bool shouldRepaint(covariant DonutChartPainter oldDelegate) {
    return oldDelegate.solarPercent != solarPercent ||
        oldDelegate.batteryPercent != batteryPercent ||
        oldDelegate.gridPercent != gridPercent;
  }
}
