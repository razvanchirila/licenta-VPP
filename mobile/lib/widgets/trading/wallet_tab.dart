import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/trading.dart';
import 'package:flutter_interface/widgets/common/stat_tile.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';
import 'package:flutter_interface/widgets/trading/trading_data.dart';

class WalletTab extends StatelessWidget {
  final Wallet wallet;
  final TradingStats stats;
  final List<WalletTx> transactions;
  final Future<void> Function() onRefresh;
  final VoidCallback onTransfer;

  const WalletTab({
    super.key,
    required this.wallet,
    required this.stats,
    required this.transactions,
    required this.onRefresh,
    required this.onTransfer,
  });

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
            _WalletCard(wallet: wallet),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: onTransfer,
                icon: const Icon(Icons.hub_rounded, size: 18),
                label: const Text('Transferă energie în rezerva VPP'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white,
                  side: BorderSide(color: AppColors.tradingAccent.withValues(alpha: 0.5)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            const SizedBox(height: 24),
            _TradingStatsCard(stats: stats),
            const SizedBox(height: 24),
            Text('Tranzacții recente', style: AppText.sectionTitle),
            const SizedBox(height: 12),
            ...transactions.take(15).map((tx) => _WalletTransactionTile(tx: tx)),
            if (transactions.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text('Nicio tranzacție încă', style: GoogleFonts.inter(color: Colors.white54)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _WalletCard extends StatelessWidget {
  final Wallet wallet;

  const _WalletCard({required this.wallet});

  @override
  Widget build(BuildContext context) {
    final w = wallet;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.surface, Color(0xFF2D2D44)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.tradingAccent.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_balance_wallet, color: AppColors.tradingAccent, size: 28),
              const SizedBox(width: 12),
              Text('Portofel virtual', style: GoogleFonts.inter(color: Colors.white, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 20),
          Semantics(
            container: true,
            identifier: 'wallet-balance',
            label: 'Sold',
            value: formatLei(w.balanceLei),
            excludeSemantics: true,
            child: Text(
              formatLei(w.balanceLei),
              style: GoogleFonts.inter(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: StatTile(
                    label: 'Câștigat', value: '+${formatLei(w.totalEarnedLei)}', valueStyle: _value(Colors.green)),
              ),
              Expanded(
                child: StatTile(
                    label: 'Cheltuit', value: '-${formatLei(w.totalSpentLei)}', valueStyle: _value(Colors.red)),
              ),
              Expanded(
                child: StatTile(
                  label: 'Rezervă VPP',
                  value: formatKwh(w.vppReservedKwh, decimals: 2),
                  valueStyle: _value(Colors.white),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  TextStyle _value(Color color) => GoogleFonts.inter(color: color, fontWeight: FontWeight.w600);
}

class _TradingStatsCard extends StatelessWidget {
  final TradingStats stats;

  const _TradingStatsCard({required this.stats});

  @override
  Widget build(BuildContext context) {
    final s = stats;
    return SurfaceCard(
      padding: const EdgeInsets.all(16),
      radius: 12,
      bordered: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Statistici trading (decontate)',
              style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: _stat('Vândut', formatKwh(s.totalEnergySoldKwh, decimals: 2), Colors.green)),
              Expanded(child: _stat('Cumpărat', formatKwh(s.totalEnergyBoughtKwh, decimals: 2), Colors.orange)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _stat('Tranzacții vânzare', '${s.sellCount}', Colors.green)),
              Expanded(child: _stat('Tranzacții cumpărare', '${s.buyCount}', Colors.orange)),
            ],
          ),
          const SizedBox(height: 12),
          _stat(
            'Câștig net',
            formatLei(s.netEarningsLei, signed: true),
            s.netEarningsLei >= 0 ? Colors.green : Colors.red,
          ),
        ],
      ),
    );
  }

  Widget _stat(String label, String value, Color color) =>
      StatTile(label: label, value: value, valueStyle: GoogleFonts.inter(color: color, fontWeight: FontWeight.w600));
}

class _WalletTransactionTile extends StatelessWidget {
  final WalletTx tx;

  const _WalletTransactionTile({required this.tx});

  @override
  Widget build(BuildContext context) {
    final isCredit = tx.isCredit;
    final color = isCredit ? Colors.green : Colors.red;
    return SurfaceCard(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      radius: 8,
      bordered: false,
      child: Row(
        children: [
          Icon(isCredit ? Icons.arrow_downward : Icons.arrow_upward, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  tx.description.isNotEmpty ? tx.description : walletTxTypeLabel(tx.transactionType),
                  style: GoogleFonts.inter(color: Colors.white, fontSize: 13),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  '${walletTxTypeLabel(tx.transactionType)} · ${formatSimTime(tx.simTimestamp)}',
                  style: GoogleFonts.inter(color: Colors.white38, fontSize: 11),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '${isCredit ? '+' : '-'}${formatLei(tx.amountLei)}',
            style: GoogleFonts.inter(color: color, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
