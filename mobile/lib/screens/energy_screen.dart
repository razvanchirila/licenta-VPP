import 'package:flutter/material.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/screen_header.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/energy/chart_filter_sheet.dart';
import 'package:flutter_interface/widgets/energy/date_navigation.dart';
import 'package:flutter_interface/widgets/energy/energy_breakdown.dart';
import 'package:flutter_interface/widgets/energy/energy_breakdown_card.dart';
import 'package:flutter_interface/widgets/energy/energy_line_chart.dart';
import 'package:flutter_interface/widgets/energy/energy_period.dart';
import 'package:flutter_interface/widgets/error_state.dart';

class EnergyScreen extends StatefulWidget {
  const EnergyScreen({super.key});

  @override
  State<EnergyScreen> createState() => _EnergyScreenState();
}

class _EnergyScreenState extends State<EnergyScreen> with AsyncLoader<EnergyChart, EnergyScreen> {
  String _period = EnergyPeriod.day;

  /// Reference date; null means "the simulated day" (backend default).
  DateTime? _currentDate;

  EnergySeriesVisibility _visibility = const EnergySeriesVisibility();

  @override
  void initState() {
    super.initState();
    _loadChart();
  }

  /// The previous chart is kept while loading so the cards do not flash to zero.
  Future<void> _loadChart() async {
    final date = _currentDate;
    final chart = await load(
      () => userApiService.getEnergyChart(_period, date: date == null ? null : formatApiDate(date)),
      keepPrevious: true,
    );
    // Anchor navigation on the date the backend actually used.
    if (chart != null && _currentDate == null) {
      setState(() => _currentDate = DateTime.tryParse(chart.date));
    }
  }

  void _navigateDate(int direction) {
    setState(() => _currentDate = EnergyPeriod.shift(_currentDate ?? DateTime.now(), _period, direction));
    _loadChart();
  }

  void _changePeriod(String period) {
    setState(() => _period = period);
    _loadChart();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ScreenHeader(
              title: 'Energie',
              actions: [
                IconButton(
                  onPressed: () => showChartFilterSheet(
                    context,
                    visibility: _visibility,
                    onChanged: (v) => setState(() => _visibility = v),
                  ),
                  tooltip: 'Serii afișate',
                  icon: Icon(Icons.tune_rounded, color: Colors.white.withValues(alpha: 0.8), size: 24),
                ),
              ],
            ),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    final navigation = DateNavigation(
      label: EnergyPeriod.label(_currentDate, _period),
      period: _period,
      onPrevious: () => _navigateDate(-1),
      onNext: () => _navigateDate(1),
      onPeriodChanged: _changePeriod,
    );

    if (state.hasError) {
      return Column(
        children: [
          Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: navigation),
          Expanded(child: ErrorState(message: state.error!, onRetry: _loadChart, accent: AppColors.blue)),
        ],
      );
    }

    final chart = state.data;
    final points = chart?.points ?? const <EnergyPoint>[];
    final breakdown = EnergyBreakdown.fromPoints(points, chart?.hoursPerPoint ?? 0.25);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          navigation,
          const SizedBox(height: 16),
          _buildChartCard(points),
          const SizedBox(height: 24),
          _buildProductionCard(breakdown),
          const SizedBox(height: 16),
          _buildConsumptionCard(breakdown),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildChartCard(List<EnergyPoint> points) {
    final Widget content;
    if (state.isLoading) {
      content = const Center(child: CircularProgressIndicator(color: AppColors.blue));
    } else if (points.isEmpty) {
      content = Center(
        child: Text(
          'Nu există date simulate pentru această perioadă',
          textAlign: TextAlign.center,
          style: AppText.subtitle.copyWith(fontSize: 14),
        ),
      );
    } else {
      content = EnergyLineChart(points: points, period: _period, visibility: _visibility);
    }

    return Semantics(
      container: true,
      identifier: 'energy-chart',
      label: state.isLoading
          ? 'Grafic energie, se încarcă'
          : points.isEmpty
              ? null
              : 'Grafic energie, ${points.length} puncte',
      excludeSemantics: state.isLoading || points.isNotEmpty,
      child: SizedBox(
        height: 300,
        child: SurfaceCard(
          padding: points.isEmpty || state.isLoading ? EdgeInsets.zero : const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: content,
        ),
      ),
    );
  }

  Widget _buildProductionCard(EnergyBreakdown b) {
    return BreakdownCard(
      title: 'Producție ${EnergyPeriod.adjective(_period)}:',
      totalValue: formatEnergyKwh(b.totalSolar),
      semanticsId: 'energy-production-total',
      items: [
        _productionItem('Consum direct', b.solarToLoad, AppColors.blue, b),
        _productionItem('În baterie', b.solarToBattery, AppColors.green, b),
        _productionItem('La vecini', b.solarToNeighbours, AppColors.purple, b),
        _productionItem('În rețea', b.solarToGrid, AppColors.indigo, b),
      ],
    );
  }

  Widget _buildConsumptionCard(EnergyBreakdown b) {
    return BreakdownCard(
      title: 'Consum ${EnergyPeriod.adjective(_period, feminine: false)}:',
      totalValue: formatEnergyKwh(b.totalConsumption),
      semanticsId: 'energy-consumption-total',
      items: [
        _consumptionItem('Din solar', b.consumptionFromSolar, AppColors.red, b),
        _consumptionItem('Din baterie', b.consumptionFromBattery, AppColors.green, b),
        _consumptionItem('De la vecini', b.consumptionFromNeighbours, AppColors.purple, b),
        _consumptionItem('Din rețea', b.consumptionFromGrid, AppColors.orange, b),
      ],
    );
  }

  BreakdownItem _productionItem(String label, double kWh, Color color, EnergyBreakdown b) =>
      BreakdownItem(label: label, value: formatEnergyKwh(kWh), percentage: b.productionPercent(kWh), color: color);

  BreakdownItem _consumptionItem(String label, double kWh, Color color, EnergyBreakdown b) =>
      BreakdownItem(label: label, value: formatEnergyKwh(kWh), percentage: b.consumptionPercent(kWh), color: color);
}
