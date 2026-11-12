import 'package:flutter/material.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/sim_prices.dart';
import 'package:flutter_interface/widgets/common/stat_tile.dart';

class PriceStatsSection extends StatelessWidget {
  final SimPrices prices;
  final PriceSeries series;

  const PriceStatsSection({super.key, required this.prices, required this.series});

  @override
  Widget build(BuildContext context) {
    final s = series;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Statistici și informații', style: AppText.cardTitle),
              const Icon(Icons.info_outline, color: Colors.white38, size: 18),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  label: 'Preț minim',
                  value: '${prices.min(s).toStringAsFixed(4)} lei/kWh',
                  icon: Icons.trending_down,
                  iconColor: AppColors.priceDown,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: StatCard(
                  label: 'Preț maxim',
                  value: '${prices.max(s).toStringAsFixed(4)} lei/kWh',
                  icon: Icons.trending_up,
                  iconColor: AppColors.priceUp,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  label: 'Preț mediu',
                  value: '${prices.avg(s).toStringAsFixed(4)} lei/kWh',
                  icon: Icons.analytics_outlined,
                  iconColor: Colors.white54,
                ),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: StatCard(
                  label: 'Sursă date',
                  value: 'Scenariu simulat (tip PZU)',
                  icon: Icons.memory_rounded,
                  iconColor: AppColors.teal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
