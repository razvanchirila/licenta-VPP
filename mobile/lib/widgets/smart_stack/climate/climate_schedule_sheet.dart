import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/climate_settings.dart';

class ClimateScheduleSheet extends StatefulWidget {
  final ClimateSchedule schedule;
  final Function(ClimateSchedule) onScheduleChanged;

  const ClimateScheduleSheet({super.key, required this.schedule, required this.onScheduleChanged});

  @override
  State<ClimateScheduleSheet> createState() => _ClimateScheduleSheetState();
}

class _ClimateScheduleSheetState extends State<ClimateScheduleSheet> {
  late ClimateSchedule _schedule;

  @override
  void initState() {
    super.initState();
    _schedule = widget.schedule;
  }

  Future<void> _selectTime(bool isOnTime) async {
    final initialTime = isOnTime ? _schedule.onTime : _schedule.offTime;
    final picked = await showTimePicker(
      context: context,
      initialTime: initialTime,
      builder: (context, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(primary: AppColors.blue, surface: AppColors.surface),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        _schedule = isOnTime ? _schedule.copyWith(onTime: picked) : _schedule.copyWith(offTime: picked);
      });
      widget.onScheduleChanged(_schedule);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceAlt.withValues(alpha: 0.95),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: Colors.grey.shade600, borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 20),
          Text('Programare Automată',
              style: GoogleFonts.inter(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 24),
          _buildEnableToggle(),
          const SizedBox(height: 20),
          _buildTimeSelector('Pornire', _schedule.onTime, true),
          const SizedBox(height: 12),
          _buildTimeSelector('Oprire', _schedule.offTime, false),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildEnableToggle() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: [
          Icon(Icons.schedule_rounded,
              color: _schedule.isEnabled ? AppColors.blue : Colors.white.withValues(alpha: 0.5), size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Activează Programarea',
                    style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
                Text('Pornește/oprește automat',
                    style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 12)),
              ],
            ),
          ),
          Switch(
            value: _schedule.isEnabled,
            onChanged: (value) {
              setState(() => _schedule = _schedule.copyWith(isEnabled: value));
              widget.onScheduleChanged(_schedule);
            },
            activeThumbColor: AppColors.blue,
          ),
        ],
      ),
    );
  }

  Widget _buildTimeSelector(String label, TimeOfDay time, bool isOnTime) {
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 200),
      opacity: _schedule.isEnabled ? 1.0 : 0.5,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: _schedule.isEnabled ? () => _selectTime(isOnTime) : null,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
            ),
            child: Row(
              children: [
                Icon(isOnTime ? Icons.wb_sunny_rounded : Icons.nightlight_rounded,
                    color: isOnTime ? AppColors.amber : AppColors.blue, size: 22),
                const SizedBox(width: 12),
                Text(label, style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.7), fontSize: 14)),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.blue.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(_schedule.formatTime(time),
                      style: GoogleFonts.inter(color: AppColors.blue, fontSize: 16, fontWeight: FontWeight.w600)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
