import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/formatters.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/device.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/async_body.dart';
import 'package:flutter_interface/widgets/common/screen_header.dart';
import 'package:flutter_interface/widgets/common/section_header.dart';
import 'package:flutter_interface/widgets/devices/add_device_sheet.dart';
import 'package:flutter_interface/widgets/devices/device_card.dart';
import 'package:flutter_interface/widgets/devices/total_consumption_card.dart';

class DevicesScreen extends StatefulWidget {
  const DevicesScreen({super.key});

  @override
  State<DevicesScreen> createState() => _DevicesScreenState();
}

class _DevicesScreenState extends State<DevicesScreen> with AsyncLoader<List<Device>, DevicesScreen> {
  final Set<int> _busy = {};

  List<Device> get _devices => state.data ?? const [];

  @override
  void initState() {
    super.initState();
    _loadDevices();
  }

  Future<void> _loadDevices() => load(userApiService.getMyDevices);

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message, style: GoogleFonts.inter(color: Colors.white)),
        backgroundColor: isError ? AppColors.red : AppColors.green,
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _toggleDevice(Device device) async {
    if (_busy.contains(device.id)) return;
    setState(() => _busy.add(device.id));
    try {
      final updated = await userApiService.toggleDevice(device.id);
      if (!mounted) return;
      updateData(_devices.map((d) => d.id == updated.id ? updated : d).toList());
    } on ApiException catch (e) {
      _showSnackBar(e.message, isError: true);
    } finally {
      if (mounted) setState(() => _busy.remove(device.id));
    }
  }

  Future<void> _deleteDevice(Device device) async {
    final confirmed = await _confirmDelete(device);
    if (confirmed != true || !mounted) return;
    try {
      await userApiService.deleteDevice(device.id);
      if (!mounted) return;
      updateData(_devices.where((d) => d.id != device.id).toList());
      _showSnackBar('${device.name} a fost șters');
    } on ApiException catch (e) {
      _showSnackBar(e.message, isError: true);
    }
  }

  Future<bool?> _confirmDelete(Device device) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text('Ștergi ${device.name}?', style: GoogleFonts.inter(color: Colors.white)),
        content: Text(
          'Dispozitivul și istoricul lui de consum vor fi eliminate.',
          style: GoogleFonts.inter(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Anulează', style: GoogleFonts.inter(color: Colors.white54)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text('Șterge', style: GoogleFonts.inter(color: AppColors.red)),
          ),
        ],
      ),
    );
  }

  Future<void> _addDevice() async {
    final created = await AddDeviceSheet.show(context);
    if (created != null && mounted) {
      updateData([..._devices, created]);
      _showSnackBar('${created.name} a fost adăugat');
    }
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
              title: 'Dispozitive',
              actions: [
                IconButton(
                  onPressed: _addDevice,
                  icon: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppColors.green.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.add_rounded, color: AppColors.green, size: 22),
                  ),
                ),
              ],
            ),
            Expanded(
              child: AsyncBody<List<Device>>(value: state, onRetry: _loadDevices, builder: _buildList),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildList(List<Device> devices) {
    final critical = devices.where((d) => d.critical).toList();
    final nonCritical = devices.where((d) => !d.critical).toList();
    final active = devices.where((d) => d.statusOn);
    final totalWatts = active.fold<double>(0, (sum, d) => sum + d.currentPowerKw * 1000);

    return RefreshIndicator(
      onRefresh: _loadDevices,
      color: AppColors.green,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 8),
            TotalConsumptionCard(totalWatts: totalWatts, activeCount: active.length),
            const SizedBox(height: 24),
            const SectionHeader(
              icon: Icons.priority_high_rounded,
              title: 'Dispozitive critice',
              subtitle: 'Mereu pornite, nu pot fi oprite',
              color: AppColors.red,
            ),
            const SizedBox(height: 12),
            if (critical.isEmpty) _emptyHint('Niciun dispozitiv critic'),
            ...critical.map(_deviceCard),
            const SizedBox(height: 24),
            const SectionHeader(
              icon: Icons.devices_other_rounded,
              title: 'Alte dispozitive',
              subtitle: 'Control manual, ține apăsat pentru ștergere',
              color: AppColors.blue,
            ),
            const SizedBox(height: 12),
            if (nonCritical.isEmpty) _emptyHint('Niciun dispozitiv. Adaugă unul cu +'),
            ...nonCritical.map(_deviceCard),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _deviceCard(Device device) => DeviceCard(
        device: device,
        busy: _busy.contains(device.id),
        onToggle: () => _toggleDevice(device),
        onTap: () => _showDetails(device),
        onLongPress: device.critical ? null : () => _deleteDevice(device),
      );

  Future<void> _showDetails(Device device) {
    final rows = <MapEntry<String, String>>[
      MapEntry('Putere nominală', formatPowerW(device.powerW)),
      MapEntry('Program', device.scheduleText),
      MapEntry('Consum acum', device.currentDrawText.replaceFirst('acum ', '')),
      MapEntry('Energie consumată', formatKwh(device.accumulatedEnergyKwh, decimals: 2)),
      MapEntry('Tip', device.critical ? 'critic, nu poate fi oprit' : 'necritic'),
      MapEntry('Stare', device.statusOn ? 'pornit' : 'oprit'),
    ];
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text(device.name, style: GoogleFonts.inter(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Expanded(child: Text(row.key, style: GoogleFonts.inter(color: Colors.white54, fontSize: 13))),
                    Text(row.value, style: GoogleFonts.inter(color: Colors.white, fontSize: 13)),
                  ],
                ),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Închide', style: GoogleFonts.inter(color: Colors.white54)),
          ),
        ],
      ),
    );
  }

  Widget _emptyHint(String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Text(text, style: GoogleFonts.inter(color: Colors.white38, fontSize: 13)),
      );
}
