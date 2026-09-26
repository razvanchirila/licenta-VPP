import 'package:flutter/material.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/energy.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/async_body.dart';
import 'package:flutter_interface/widgets/common/screen_header.dart';
import 'package:flutter_interface/widgets/common/section_header.dart';
import 'package:flutter_interface/widgets/impact/energy_sources_card.dart';
import 'package:flutter_interface/widgets/impact/impact_palette.dart';
import 'package:flutter_interface/widgets/impact/monthly_savings_card.dart';
import 'package:flutter_interface/widgets/impact/time_of_use_card.dart';

class ImpactScreen extends StatefulWidget {
  const ImpactScreen({super.key});

  @override
  State<ImpactScreen> createState() => _ImpactScreenState();
}

class _ImpactScreenState extends State<ImpactScreen> with AsyncLoader<EnergyImpact, ImpactScreen> {
  @override
  void initState() {
    super.initState();
    _loadImpact();
  }

  Future<void> _loadImpact() => load(userApiService.getEnergyImpact);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ScreenHeader(
              title: 'Impact',
              actions: [
                IconButton(
                  onPressed: _loadImpact,
                  icon: Icon(Icons.refresh_rounded, color: Colors.white.withValues(alpha: 0.8)),
                ),
              ],
            ),
            Expanded(
              child: AsyncBody<EnergyImpact>(
                value: state,
                onRetry: _loadImpact,
                accent: ImpactPalette.solar,
                builder: _buildContent,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(EnergyImpact impact) {
    return RefreshIndicator(
      onRefresh: _loadImpact,
      color: ImpactPalette.solar,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 16),
            SectionHeader(
              icon: Icons.pie_chart_rounded,
              title: 'Surse de energie',
              subtitle: 'Distribuția energiei consumate în ziua simulată ${impact.date}',
            ),
            const SizedBox(height: 16),
            EnergySourcesCard(impact: impact),
            const SizedBox(height: 24),
            const SectionHeader(
              icon: Icons.access_time_rounded,
              title: 'Consum pe tarif',
              subtitle: 'Energia folosită pe intervale orare',
            ),
            const SizedBox(height: 16),
            TimeOfUseCard(impact: impact),
            const SizedBox(height: 24),
            const SectionHeader(
              icon: Icons.savings_rounded,
              title: 'Economii lunare',
              subtitle: 'Față de un consum acoperit integral din rețea',
            ),
            const SizedBox(height: 16),
            MonthlySavingsCard(months: impact.monthlySavings),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}
