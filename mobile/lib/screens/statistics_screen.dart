import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../services/user_api_service.dart';
import '../models/consumption_stats.dart';
import '../core/theme.dart';

/// Color constants for statistics screen
class _AppColors {
  static const Color background = Color(0xFF121212);
  static const Color surface = Color(0xFF1C1C1E);
  static const Color primary = Color(0xFF3B82F6);
  static const Color textPrimary = Colors.white;
  static Color textSecondary = Colors.white.withOpacity(0.6);
}

/// Statistics screen showing energy consumption analytics.
class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen> {
  String _selectedPeriod = 'month';
  bool _isLoading = true;
  
  ConsumptionSummary? _summary;
  TopConsumersResponse? _topConsumers;
  MonthlyComparison? _comparison;
  ChartData? _chartData;
  
  @override
  void initState() {
    super.initState();
    _loadData();
  }
  
  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    
    try {
      // Load all data in parallel
      final results = await Future.wait([
        userApiService.getConsumptionSummary(period: _selectedPeriod),
        userApiService.getTopConsumers(period: _selectedPeriod, limit: 5),
        userApiService.getMonthlyComparison(),
        _loadChartData(),
      ]);
      
      setState(() {
        if (results[0] != null) {
          _summary = ConsumptionSummary.fromJson(results[0] as Map<String, dynamic>);
        }
        if (results[1] != null) {
          _topConsumers = TopConsumersResponse.fromJson(results[1] as Map<String, dynamic>);
        }
        if (results[2] != null) {
          _comparison = MonthlyComparison.fromJson(results[2] as Map<String, dynamic>);
        }
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Eroare la încărcarea datelor: $e')),
        );
      }
    }
  }
  
  Future<Map<String, dynamic>?> _loadChartData() async {
    final now = DateTime.now();
    DateTime startDate;
    
    switch (_selectedPeriod) {
      case 'day':
        startDate = now.subtract(const Duration(days: 1));
        break;
      case 'week':
        startDate = now.subtract(const Duration(days: 7));
        break;
      case 'month':
        startDate = DateTime(now.year, now.month - 1, now.day);
        break;
      case 'year':
        startDate = DateTime(now.year - 1, now.month, now.day);
        break;
      default:
        startDate = DateTime(now.year, now.month, 1);
    }
    
    final result = await userApiService.getChartData(
      startDate: DateFormat('yyyy-MM-dd').format(startDate),
      endDate: DateFormat('yyyy-MM-dd').format(now),
    );
    
    if (result != null) {
      _chartData = ChartData.fromJson(result);
    }
    return result;
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _AppColors.background,
      appBar: AppBar(
        title: const Text('Statistici Consum'),
        backgroundColor: _AppColors.surface,
        foregroundColor: _AppColors.textPrimary,
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildPeriodSelector(),
                    const SizedBox(height: 16),
                    _buildSummaryCard(),
                    const SizedBox(height: 16),
                    _buildComparisonCard(),
                    const SizedBox(height: 16),
                    _buildChartCard(),
                    const SizedBox(height: 16),
                    _buildTopConsumersCard(),
                  ],
                ),
              ),
            ),
    );
  }
  
  Widget _buildPeriodSelector() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: _AppColors.surface,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          _buildPeriodButton('day', 'Zi'),
          _buildPeriodButton('week', 'Săptămână'),
          _buildPeriodButton('month', 'Lună'),
          _buildPeriodButton('year', 'An'),
        ],
      ),
    );
  }
  
  Widget _buildPeriodButton(String period, String label) {
    final isSelected = _selectedPeriod == period;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          if (_selectedPeriod != period) {
            setState(() => _selectedPeriod = period);
            _loadData();
          }
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? _AppColors.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: isSelected ? Colors.white : _AppColors.textSecondary,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildSummaryCard() {
    if (_summary == null) {
      return _buildEmptyCard('Nu există date pentru această perioadă');
    }
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Sumar Consum',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildStatItem(
                  'Total',
                  '${_summary!.totalKwh.toStringAsFixed(2)} kWh',
                  Icons.bolt,
                  _AppColors.primary,
                ),
              ),
              Expanded(
                child: _buildStatItem(
                  'Cost Estimat',
                  '${_summary!.estimatedCost.toStringAsFixed(2)} ${_summary!.currency}',
                  Icons.attach_money,
                  Colors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildStatItem(
                  'Medie Zilnică',
                  '${_summary!.averageDailyKwh.toStringAsFixed(2)} kWh',
                  Icons.calendar_today,
                  Colors.blue,
                ),
              ),
              Expanded(
                child: _buildStatItem(
                  'Perioada Anterioară',
                  '${_summary!.previousPeriodKwh.toStringAsFixed(2)} kWh',
                  Icons.history,
                  Colors.grey,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: _AppColors.textSecondary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: _AppColors.textPrimary,
          ),
        ),
      ],
    );
  }

  
  Widget _buildComparisonCard() {
    if (_comparison == null) {
      return const SizedBox.shrink();
    }
    
    final isIncrease = _comparison!.trend == 'increased';
    final isDecrease = _comparison!.trend == 'decreased';
    
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Comparație Lunară',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: _AppColors.textPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: isIncrease
                      ? Colors.red.withOpacity(0.1)
                      : isDecrease
                          ? Colors.green.withOpacity(0.1)
                          : Colors.grey.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      isIncrease
                          ? Icons.arrow_upward
                          : isDecrease
                              ? Icons.arrow_downward
                              : Icons.remove,
                      size: 16,
                      color: isIncrease
                          ? Colors.red
                          : isDecrease
                              ? Colors.green
                              : Colors.grey,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${_comparison!.changePercent?.abs().toStringAsFixed(1) ?? '0'}%',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: isIncrease
                            ? Colors.red
                            : isDecrease
                                ? Colors.green
                                : Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _comparison!.currentMonth,
                      style: TextStyle(
                        fontSize: 12,
                        color: _AppColors.textSecondary,
                      ),
                    ),
                    Text(
                      '${_comparison!.currentMonthKwh.toStringAsFixed(2)} kWh',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: _AppColors.textPrimary,
                      ),
                    ),
                    if (_comparison!.isProjection)
                      Text(
                        'Proiecție: ${_comparison!.projectedTotalKwh.toStringAsFixed(2)} kWh',
                        style: TextStyle(
                          fontSize: 12,
                          color: _AppColors.textSecondary,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _comparison!.previousMonth,
                      style: TextStyle(
                        fontSize: 12,
                        color: _AppColors.textSecondary,
                      ),
                    ),
                    Text(
                      '${_comparison!.previousMonthKwh.toStringAsFixed(2)} kWh',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: _AppColors.textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Widget _buildChartCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Evoluție Consum',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _AppColors.textPrimary,
            ),
          ),
          if (_chartData != null)
            Text(
              'Granularitate: ${_chartData!.granularity}',
              style: TextStyle(
                fontSize: 12,
                color: _AppColors.textSecondary,
              ),
            ),
          const SizedBox(height: 16),
          SizedBox(
            height: 200,
            child: _chartData == null || _chartData!.dataPoints.isEmpty
                ? Center(
                    child: Text(
                      'Nu există date pentru grafic',
                      style: TextStyle(color: _AppColors.textSecondary),
                    ),
                  )
                : LineChart(
                    LineChartData(
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: false,
                        horizontalInterval: _getChartInterval(),
                        getDrawingHorizontalLine: (value) => FlLine(
                          color: _AppColors.textSecondary.withOpacity(0.2),
                          strokeWidth: 1,
                        ),
                      ),
                      titlesData: FlTitlesData(
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 40,
                            getTitlesWidget: (value, meta) => Text(
                              value.toStringAsFixed(1),
                              style: TextStyle(
                                fontSize: 10,
                                color: _AppColors.textSecondary,
                              ),
                            ),
                          ),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 30,
                            interval: _getBottomTitleInterval(),
                            getTitlesWidget: (value, meta) {
                              final index = value.toInt();
                              if (index < 0 || index >= _chartData!.dataPoints.length) {
                                return const SizedBox.shrink();
                              }
                              final date = _chartData!.dataPoints[index].timestamp;
                              return Text(
                                _formatChartDate(date),
                                style: TextStyle(
                                  fontSize: 10,
                                  color: _AppColors.textSecondary,
                                ),
                              );
                            },
                          ),
                        ),
                        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      ),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: _chartData!.dataPoints
                              .asMap()
                              .entries
                              .map((e) => FlSpot(e.key.toDouble(), e.value.valueKwh))
                              .toList(),
                          isCurved: true,
                          color: _AppColors.primary,
                          barWidth: 3,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(
                            show: true,
                            color: _AppColors.primary.withOpacity(0.1),
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }
  
  double _getChartInterval() {
    if (_chartData == null || _chartData!.dataPoints.isEmpty) return 1;
    final maxValue = _chartData!.dataPoints
        .map((e) => e.valueKwh)
        .reduce((a, b) => a > b ? a : b);
    return maxValue > 0 ? maxValue / 4 : 1;
  }
  
  double _getBottomTitleInterval() {
    if (_chartData == null) return 1;
    final count = _chartData!.dataPoints.length;
    if (count <= 7) return 1;
    if (count <= 14) return 2;
    if (count <= 30) return 5;
    return 7;
  }
  
  String _formatChartDate(DateTime date) {
    if (_chartData?.granularity == 'hourly') {
      return DateFormat('HH:mm').format(date);
    } else if (_chartData?.granularity == 'daily') {
      return DateFormat('dd/MM').format(date);
    } else {
      return DateFormat('dd/MM').format(date);
    }
  }
  
  Widget _buildTopConsumersCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Top Consumatori',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          if (_topConsumers == null || _topConsumers!.devices.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(
                  'Nu există date de consum',
                  style: TextStyle(color: _AppColors.textSecondary),
                ),
              ),
            )
          else
            ...List.generate(
              _topConsumers!.devices.length,
              (index) => _buildConsumerItem(_topConsumers!.devices[index], index + 1),
            ),
        ],
      ),
    );
  }
  
  Widget _buildConsumerItem(DeviceConsumption device, int rank) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: _getRankColor(rank).withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '$rank',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _getRankColor(rank),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  device.deviceName,
                  style: TextStyle(
                    fontWeight: FontWeight.w500,
                    color: _AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: device.percentageOfTotal / 100,
                    backgroundColor: _AppColors.textSecondary.withOpacity(0.1),
                    valueColor: AlwaysStoppedAnimation(_getRankColor(rank)),
                    minHeight: 6,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${device.totalKwh.toStringAsFixed(2)} kWh',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _AppColors.textPrimary,
                ),
              ),
              Text(
                '${device.percentageOfTotal.toStringAsFixed(1)}%',
                style: TextStyle(
                  fontSize: 12,
                  color: _AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  Color _getRankColor(int rank) {
    switch (rank) {
      case 1:
        return Colors.amber;
      case 2:
        return Colors.grey;
      case 3:
        return Colors.brown;
      default:
        return _AppColors.primary;
    }
  }
  
  Widget _buildEmptyCard(String message) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Center(
        child: Text(
          message,
          style: TextStyle(color: _AppColors.textSecondary),
        ),
      ),
    );
  }
}
