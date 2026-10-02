import 'package:flutter/material.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/error_state.dart';
import 'package:flutter_interface/widgets/statistics/comparison_card.dart';
import 'package:flutter_interface/widgets/statistics/consumption_chart_card.dart';
import 'package:flutter_interface/widgets/statistics/period_selector.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';
import 'package:flutter_interface/widgets/statistics/summary_card.dart';
import 'package:flutter_interface/widgets/statistics/top_consumers_card.dart';

class StatisticsScreen extends StatefulWidget {
  const StatisticsScreen({super.key});

  @override
  State<StatisticsScreen> createState() => _StatisticsScreenState();
}

class _StatisticsScreenState extends State<StatisticsScreen> with AsyncLoader<StatisticsData, StatisticsScreen> {
  String _period = 'month';

  @override
  void initState() {
    super.initState();
    _loadStatistics();
  }

  Future<void> _loadStatistics() => load(() async {
        final results = await Future.wait<Object>([
          userApiService.getConsumptionSummary(period: _period),
          userApiService.getTopConsumers(period: _period, limit: 5),
          userApiService.getMonthlyComparison(),
          _loadChart(_period),
        ]);
        return StatisticsData(
          summary: results[0] as ConsumptionSummary,
          topConsumers: results[1] as TopConsumersResponse,
          comparison: results[2] as MonthlyComparison,
          chart: results[3] as ChartData,
        );
      });

  Future<ChartData> _loadChart(String period) async {
    SimPrices? prices;
    try {
      prices = await userApiService.getSimPrices();
    } on ApiException {
      prices = null;
    }
    final range = StatisticsRules.chartRange(period, StatisticsRules.simulatedNow(prices, DateTime.now()));
    return userApiService.getStatsChart(startDate: formatApiDate(range.$1), endDate: formatApiDate(range.$2));
  }

  void _changePeriod(String period) {
    setState(() => _period = period);
    _loadStatistics();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Statistici consum'),
        backgroundColor: AppColors.surface,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: state.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (message) => Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: StatsPeriodSelector(selected: _period, onChanged: _changePeriod),
            ),
            Expanded(child: ErrorState(message: message, onRetry: _loadStatistics, accent: AppColors.blue)),
          ],
        ),
        data: _buildContent,
      ),
    );
  }

  Widget _buildContent(StatisticsData data) {
    return RefreshIndicator(
      onRefresh: _loadStatistics,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            StatsPeriodSelector(selected: _period, onChanged: _changePeriod),
            const SizedBox(height: 16),
            ConsumptionSummaryCard(summary: data.summary),
            const SizedBox(height: 16),
            MonthlyComparisonCard(comparison: data.comparison),
            const SizedBox(height: 16),
            ConsumptionChartCard(chart: data.chart),
            const SizedBox(height: 16),
            TopConsumersCard(top: data.topConsumers),
          ],
        ),
      ),
    );
  }
}
