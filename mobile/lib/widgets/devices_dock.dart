import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/state/app_state.dart';

/// Dock pentru quick access la devices
/// Folosește același design glassmorphism ca bottom sheet
class DevicesDock extends StatefulWidget {
  final int batteryPercent;
  final double batteryCapacityKwh;
  
  const DevicesDock({
    super.key,
    this.batteryPercent = 74,
    this.batteryCapacityKwh = 13.5,
  });

  @override
  State<DevicesDock> createState() => _DevicesDockState();
}

class _DevicesDockState extends State<DevicesDock> {
  @override
  void initState() {
    super.initState();
    appState.addListener(_onStateChanged);
  }

  @override
  void dispose() {
    appState.removeListener(_onStateChanged);
    super.dispose();
  }

  void _onStateChanged() {
    if (mounted) setState(() {});
  }
  
  /// Calculează orele estimate de funcționare a bateriei
  String _calculateBatteryHours() {
    final totalConsumptionKw = appState.totalDevicePowerKw;
    if (totalConsumptionKw <= 0) return '∞';
    
    // Energie disponibilă în baterie (kWh)
    final availableEnergy = widget.batteryCapacityKwh * (widget.batteryPercent / 100);
    
    // Ore = energie / consum
    final hours = availableEnergy / totalConsumptionKw;
    
    if (hours >= 24) {
      return '${(hours / 24).toStringAsFixed(1)}d';
    } else if (hours >= 1) {
      return '${hours.toStringAsFixed(1)}h';
    } else {
      return '${(hours * 60).toStringAsFixed(0)}m';
    }
  }

  @override
  Widget build(BuildContext context) {
    // Filtrăm doar device-urile non-critice (care pot fi toggle)
    final toggleableDevices = appState.devices.where((d) => !d.isCritical).toList();
    final batteryHours = _calculateBatteryHours();

    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
        child: Container(
          width: double.infinity,
          margin: const EdgeInsets.symmetric(horizontal: 0),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0xFF1A1A1A).withOpacity(0.75),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              // Device buttons (expandable)
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      // Icon label
                      Icon(
                        Icons.devices_rounded,
                        color: Colors.white.withOpacity(0.4),
                        size: 16,
                      ),
                      const SizedBox(width: 10),
                      // Device buttons
                      ...toggleableDevices.map((device) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: _DeviceDockButton(
                          device: device,
                          onTap: () => appState.toggleDevice(device.id),
                        ),
                      )),
                    ],
                  ),
                ),
              ),
              
              // Separator
              Container(
                width: 1,
                height: 36,
                margin: const EdgeInsets.symmetric(horizontal: 12),
                color: Colors.white.withOpacity(0.15),
              ),
              
              // Battery runtime estimate
              Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.schedule_rounded,
                        color: Colors.white.withOpacity(0.5),
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        batteryHours,
                        style: GoogleFonts.inter(
                          color: const Color(0xFF22C55E),
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    'autonomie',
                    style: GoogleFonts.inter(
                      color: Colors.white.withOpacity(0.4),
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Buton individual pentru device în dock
class _DeviceDockButton extends StatelessWidget {
  final DeviceState device;
  final VoidCallback onTap;

  const _DeviceDockButton({
    required this.device,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isOn = device.isOn;
    final color = isOn ? const Color(0xFF22C55E) : Colors.white.withOpacity(0.3);

    return Tooltip(
      message: '${device.name}\n${device.powerWatts}W',
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: isOn 
                ? const Color(0xFF22C55E).withOpacity(0.2)
                : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isOn 
                  ? const Color(0xFF22C55E).withOpacity(0.5)
                  : Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: Icon(
            device.icon,
            color: color,
            size: 20,
          ),
        ),
      ),
    );
  }
}
