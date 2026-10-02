import 'package:flutter/material.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/consumption_stats.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/statistics/statistics_data.dart';

class TopConsumersCard extends StatelessWidget {
  final TopConsumersResponse top;

  const TopConsumersCard({super.key, required this.top});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      identifier: 'stats-top-consumers',
      child: SurfaceCard(
        bordered: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Top consumatori', style: statsCardTitle),
            const SizedBox(height: 16),
            if (top.devices.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Text('Nu există date de consum', style: TextStyle(color: AppColors.textSecondary)),
                ),
              )
            else
              for (var i = 0; i < top.devices.length; i++) _ConsumerRow(device: top.devices[i], rank: i + 1),
          ],
        ),
      ),
    );
  }
}

class _ConsumerRow extends StatelessWidget {
  final DeviceConsumption device;
  final int rank;

  const _ConsumerRow({required this.device, required this.rank});

  @override
  Widget build(BuildContext context) {
    final color = StatisticsRules.rankColor(rank);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
            child: Center(child: Text('$rank', style: TextStyle(fontWeight: FontWeight.bold, color: color))),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  device.deviceName,
                  style: const TextStyle(fontWeight: FontWeight.w500, color: Colors.white),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (device.percentageOfTotal / 100).clamp(0.0, 1.0),
                    backgroundColor: AppColors.textSecondary.withValues(alpha: 0.1),
                    valueColor: AlwaysStoppedAnimation(color),
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
                formatKwh(device.totalKwh, decimals: 2),
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
              ),
              Text(
                '${device.percentageOfTotal.toStringAsFixed(1)}%',
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
