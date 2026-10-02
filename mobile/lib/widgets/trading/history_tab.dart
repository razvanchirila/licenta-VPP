import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_interface/widgets/trading/trading_data.dart';

class HistoryTab extends StatelessWidget {
  final List<Trade> trades;
  final Future<void> Function() onRefresh;

  const HistoryTab({super.key, required this.trades, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      color: AppColors.tradingAccent,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Istoric trading P2P', style: AppText.sectionTitle),
            const SizedBox(height: 12),
            ...trades.map((t) => _TradeTile(trade: t, onTap: () => showTradeDetails(context, t))),
            if (trades.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Semantics(
                    container: true,
                    identifier: 'trading-history-empty',
                    child: Text('Nicio tranzacție P2P încă', style: GoogleFonts.inter(color: Colors.white54)),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _TradeTile extends StatelessWidget {
  final Trade trade;
  final VoidCallback onTap;

  const _TradeTile({required this.trade, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isSell = trade.isSell;
    final color = trade.isRejected ? Colors.white38 : (isSell ? Colors.green : Colors.orange);
    final counterparty = trade.counterpartyHouseId?.toString() ?? '?';

    return Semantics(
      container: true,
      identifier: 'trade-${trade.id}',
      button: true,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
                child: Icon(trade.isRejected ? Icons.block : (isSell ? Icons.sell : Icons.shopping_cart),
                    color: color, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${isSell ? 'Vândut către casa' : 'Cumpărat de la casa'} $counterparty'
                      '${trade.isRejected ? ' (respinsă)' : ''}',
                      style: GoogleFonts.inter(color: Colors.white, fontSize: 13),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${trade.energyKwh.toStringAsFixed(3)} kWh @ ${trade.priceLeiKwh.toStringAsFixed(2)} lei/kWh · '
                      '${formatSimTime(trade.simTimestamp)}',
                      style: GoogleFonts.inter(color: Colors.white54, fontSize: 11),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${isSell ? '+' : '-'}${formatLei(trade.totalValueLei)}',
                    style: GoogleFonts.inter(
                      color: color,
                      fontWeight: FontWeight.w600,
                      decoration: trade.isRejected ? TextDecoration.lineThrough : null,
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.white24, size: 16),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

void showTradeDetails(BuildContext context, Trade trade) {
  final isSell = trade.isSell;
  final color = isSell ? Colors.green : Colors.orange;
  final counterparty = trade.counterpartyHouseId?.toString() ?? '?';
  final savings = tradeSavingsLei(trade);

  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => Container(
      padding: AppTheme.sheetPadding(context, 24),
      decoration: AppTheme.sheetDecoration(),
      child: SingleChildScrollView(
          child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
                child: Icon(isSell ? Icons.sell : Icons.shopping_cart, color: color, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(isSell ? 'Energie vândută' : 'Energie cumpărată', style: AppText.sectionTitle),
                    Text(
                      isSell ? 'Către casa $counterparty' : 'De la casa $counterparty',
                      style: GoogleFonts.inter(color: Colors.white54, fontSize: 14),
                    ),
                  ],
                ),
              ),
              Text(
                '${isSell ? '+' : '-'}${formatLei(trade.totalValueLei)}',
                style: GoogleFonts.inter(color: color, fontSize: 20, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 24),
          _DetailRow('Energie', '${trade.energyKwh.toStringAsFixed(3)} kWh'),
          _DetailRow('Preț P2P', '${trade.priceLeiKwh.toStringAsFixed(2)} lei/kWh'),
          _DetailRow('Preț rețea', '${trade.gridPriceLeiKwh.toStringAsFixed(2)} lei/kWh'),
          if (!isSell && savings > 0) _DetailRow('Economie', formatLei(savings), valueColor: Colors.green),
          _DetailRow(
            'Stare',
            trade.isRejected ? 'Respinsă' : 'Decontată',
            valueColor: trade.isRejected ? Colors.red : Colors.green,
          ),
          if (trade.reason != null && trade.reason!.isNotEmpty) _DetailRow('Motiv', trade.reason!),
          const Divider(color: Colors.white12, height: 24),
          _DetailRow('Vânzător', 'Casa ${trade.sellerHouseId}'),
          _DetailRow('Cumpărător', 'Casa ${trade.buyerHouseId}'),
          _DetailRow('Ora simulării', formatSimTime(trade.simTimestamp)),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: () => Navigator.pop(context),
              style: TextButton.styleFrom(
                backgroundColor: Colors.white.withValues(alpha: 0.1),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: Text('Închide', style: GoogleFonts.inter(color: Colors.white70)),
            ),
          ),
        ],
      )),
    ),
  );
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _DetailRow(this.label, this.value, {this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: GoogleFonts.inter(color: Colors.white54, fontSize: 14)),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: GoogleFonts.inter(color: valueColor ?? Colors.white, fontSize: 14, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
