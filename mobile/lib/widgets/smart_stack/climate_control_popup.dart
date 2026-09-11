import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/models/climate_settings.dart';
import 'package:flutter_interface/widgets/smart_stack/arc_slider.dart';

/// Climate control popup with arc slider, mode buttons, and power toggle
class ClimateControlPopup extends StatefulWidget {
  const ClimateControlPopup({super.key});

  @override
  State<ClimateControlPopup> createState() => _ClimateControlPopupState();
}

class _ClimateControlPopupState extends State<ClimateControlPopup> {
  late double _temperature;
  late ClimateMode _mode;
  late bool _isOn;
  late ClimateRoom _selectedRoom;
  late ClimateSchedule _schedule;

  static const Color _primaryColor = Color(0xFF3B82F6);
  static const Color _successColor = Color(0xFF22C55E);
  static const Color _warningColor = Color(0xFFFBBF24);
  static const Color _errorColor = Color(0xFFEF4444);
  static const Color _surfaceColor = Color(0xFF1C1C1E);
  static const Color _glassColor = Color(0xFF1A1A1A);

  @override
  void initState() {
    super.initState();
    _temperature = appState.climateSettings.targetTemperature;
    _mode = appState.climateSettings.mode;
    _isOn = appState.climateSettings.isOn;
    _selectedRoom = appState.climateSettings.room;
    _schedule = appState.climateSettings.schedule;
  }

  void _saveAndClose() {
    appState.updateClimateSettings(ClimateSettings(
      targetTemperature: _temperature,
      mode: _mode,
      isOn: _isOn,
      room: _selectedRoom,
      schedule: _schedule,
    ));
    Navigator.pop(context);
  }

  void _showRoomSelector() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => _RoomSelectorSheet(
        selectedRoom: _selectedRoom,
        onRoomSelected: (room) {
          setState(() => _selectedRoom = room);
          Navigator.pop(context);
        },
      ),
    );
  }

  void _showScheduleSettings() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => _ScheduleSettingsSheet(
        schedule: _schedule,
        onScheduleChanged: (schedule) {
          setState(() => _schedule = schedule);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          decoration: BoxDecoration(
            color: _glassColor.withOpacity(0.92),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            border: Border(top: BorderSide(color: Colors.white.withOpacity(0.1), width: 1)),
          ),
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(width: 40, height: 5, decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.25), borderRadius: BorderRadius.circular(3))),
              const SizedBox(height: 20),
              _buildHeader(),
              const SizedBox(height: 8),
              _buildRoomSelector(),
              const SizedBox(height: 28),
              ArcSlider(minValue: 16, maxValue: 32, currentValue: _temperature, size: 200,
                onChanged: (value) => setState(() => _temperature = value)),
              const SizedBox(height: 24),
              _buildModeSection(),
              const SizedBox(height: 28),
              _buildPowerButton(),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: _saveAndClose,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.white.withOpacity(0.08), borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 18),
            ),
          ),
        ),
        Expanded(
          child: Text('Control Climă', textAlign: TextAlign.center,
            style: GoogleFonts.inter(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600, letterSpacing: -0.3)),
        ),
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: _showScheduleSettings,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: _schedule.isEnabled ? _primaryColor.withOpacity(0.2) : Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: _schedule.isEnabled ? Border.all(color: _primaryColor.withOpacity(0.5)) : null,
              ),
              child: Icon(Icons.schedule_rounded, 
                color: _schedule.isEnabled ? _primaryColor : Colors.white.withOpacity(0.6), size: 18),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRoomSelector() {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: _showRoomSelector,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: _surfaceColor, borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white.withOpacity(0.08), width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(_selectedRoom.icon, color: _primaryColor, size: 16),
              const SizedBox(width: 8),
              Text(_selectedRoom.displayName, style: GoogleFonts.inter(
                color: Colors.white.withOpacity(0.7), fontSize: 13, fontWeight: FontWeight.w500)),
              const SizedBox(width: 4),
              Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white.withOpacity(0.5), size: 18),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModeSection() {
    return Column(
      children: [
        Text('Mod', style: GoogleFonts.inter(color: Colors.white.withOpacity(0.5), fontSize: 12, fontWeight: FontWeight.w500)),
        const SizedBox(height: 4),
        Text(_getModeDisplayText(), style: GoogleFonts.inter(
          color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
        const SizedBox(height: 20),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: ClimateMode.values.map((mode) => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: _ModeButton(mode: mode, isSelected: _mode == mode, onTap: () => setState(() => _mode = mode)),
          )).toList(),
        ),
      ],
    );
  }

  Widget _buildPowerButton() {
    return GestureDetector(
      onTap: () => setState(() => _isOn = !_isOn),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: 60, height: 60,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _isOn ? _successColor : _surfaceColor,
          border: Border.all(color: _isOn ? _successColor.withOpacity(0.5) : Colors.white.withOpacity(0.1), width: 2),
          boxShadow: _isOn ? [BoxShadow(color: _successColor.withOpacity(0.4), blurRadius: 20, spreadRadius: 2)] : null,
        ),
        child: Icon(Icons.power_settings_new_rounded, color: _isOn ? Colors.white : Colors.white.withOpacity(0.5), size: 28),
      ),
    );
  }

  String _getModeDisplayText() {
    switch (_mode) {
      case ClimateMode.cold: return 'RĂCIRE';
      case ClimateMode.fan: return 'VENTILAȚIE';
      case ClimateMode.dry: return 'USCARE';
      case ClimateMode.heat: return 'ÎNCĂLZIRE';
    }
  }
}

/// Mode selection button
class _ModeButton extends StatelessWidget {
  final ClimateMode mode;
  final bool isSelected;
  final VoidCallback onTap;

  static const Color _primaryColor = Color(0xFF3B82F6);
  static const Color _surfaceColor = Color(0xFF1C1C1E);
  static const Color _successColor = Color(0xFF22C55E);
  static const Color _warningColor = Color(0xFFFBBF24);
  static const Color _errorColor = Color(0xFFEF4444);

  const _ModeButton({required this.mode, required this.isSelected, required this.onTap});

  IconData get _icon {
    switch (mode) {
      case ClimateMode.cold: return Icons.ac_unit_rounded;
      case ClimateMode.fan: return Icons.air_rounded;
      case ClimateMode.dry: return Icons.water_drop_outlined;
      case ClimateMode.heat: return Icons.whatshot_rounded;
    }
  }

  Color get _modeColor {
    switch (mode) {
      case ClimateMode.cold: return _primaryColor;
      case ClimateMode.fan: return _successColor;
      case ClimateMode.dry: return _warningColor;
      case ClimateMode.heat: return _errorColor;
    }
  }

  String get _modeLabel {
    switch (mode) {
      case ClimateMode.cold: return 'RĂCIRE';
      case ClimateMode.fan: return 'FAN';
      case ClimateMode.dry: return 'USCAT';
      case ClimateMode.heat: return 'CALD';
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 68, height: 68,
        decoration: BoxDecoration(
          color: isSelected ? _modeColor.withOpacity(0.2) : _surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: isSelected ? _modeColor.withOpacity(0.5) : Colors.white.withOpacity(0.08), width: 1.5),
          boxShadow: isSelected ? [BoxShadow(color: _modeColor.withOpacity(0.2), blurRadius: 12, spreadRadius: 1)] : null,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(_icon, color: isSelected ? _modeColor : Colors.white.withOpacity(0.5), size: 24),
            const SizedBox(height: 4),
            Text(_modeLabel, style: GoogleFonts.inter(
              color: isSelected ? _modeColor : Colors.white.withOpacity(0.5), fontSize: 9, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
          ],
        ),
      ),
    );
  }
}

/// Room selector bottom sheet
class _RoomSelectorSheet extends StatelessWidget {
  final ClimateRoom selectedRoom;
  final Function(ClimateRoom) onRoomSelected;

  const _RoomSelectorSheet({required this.selectedRoom, required this.onRoomSelected});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A1A).withOpacity(0.95),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 40, height: 4, decoration: BoxDecoration(
            color: Colors.grey.shade600, borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 20),
          Text('Selectează Camera', style: GoogleFonts.inter(
            color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 20),
          ...ClimateRoom.values.map((room) => _RoomTile(
            room: room, isSelected: room == selectedRoom, onTap: () => onRoomSelected(room))),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _RoomTile extends StatelessWidget {
  final ClimateRoom room;
  final bool isSelected;
  final VoidCallback onTap;

  const _RoomTile({required this.room, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: isSelected ? const Color(0xFF3B82F6).withOpacity(0.2) : const Color(0xFF1C1C1E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: isSelected ? const Color(0xFF3B82F6).withOpacity(0.5) : Colors.white.withOpacity(0.08)),
            ),
            child: Row(
              children: [
                Icon(room.icon, color: isSelected ? const Color(0xFF3B82F6) : Colors.white.withOpacity(0.6), size: 22),
                const SizedBox(width: 12),
                Text(room.displayName, style: GoogleFonts.inter(
                  color: isSelected ? Colors.white : Colors.white.withOpacity(0.8), fontSize: 15, fontWeight: FontWeight.w500)),
                const Spacer(),
                if (isSelected) const Icon(Icons.check_circle_rounded, color: Color(0xFF3B82F6), size: 22),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Schedule settings bottom sheet
class _ScheduleSettingsSheet extends StatefulWidget {
  final ClimateSchedule schedule;
  final Function(ClimateSchedule) onScheduleChanged;

  const _ScheduleSettingsSheet({required this.schedule, required this.onScheduleChanged});

  @override
  State<_ScheduleSettingsSheet> createState() => _ScheduleSettingsSheetState();
}

class _ScheduleSettingsSheetState extends State<_ScheduleSettingsSheet> {
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
          colorScheme: const ColorScheme.dark(primary: Color(0xFF3B82F6), surface: Color(0xFF1C1C1E)),
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
        color: const Color(0xFF1A1A1A).withOpacity(0.95),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 40, height: 4, decoration: BoxDecoration(
            color: Colors.grey.shade600, borderRadius: BorderRadius.circular(2))),
          const SizedBox(height: 20),
          Text('Programare Automată', style: GoogleFonts.inter(
            color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
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
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Row(
        children: [
          Icon(Icons.schedule_rounded, color: _schedule.isEnabled ? const Color(0xFF3B82F6) : Colors.white.withOpacity(0.5), size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Activează Programarea', style: GoogleFonts.inter(
                  color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
                Text('Pornește/oprește automat', style: GoogleFonts.inter(
                  color: Colors.white.withOpacity(0.5), fontSize: 12)),
              ],
            ),
          ),
          Switch(
            value: _schedule.isEnabled,
            onChanged: (value) {
              setState(() => _schedule = _schedule.copyWith(isEnabled: value));
              widget.onScheduleChanged(_schedule);
            },
            activeColor: const Color(0xFF3B82F6),
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
              color: const Color(0xFF1C1C1E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.08)),
            ),
            child: Row(
              children: [
                Icon(isOnTime ? Icons.wb_sunny_rounded : Icons.nightlight_rounded,
                  color: isOnTime ? const Color(0xFFFBBF24) : const Color(0xFF3B82F6), size: 22),
                const SizedBox(width: 12),
                Text(label, style: GoogleFonts.inter(color: Colors.white.withOpacity(0.7), fontSize: 14)),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF3B82F6).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(_schedule.formatTime(time), style: GoogleFonts.inter(
                    color: const Color(0xFF3B82F6), fontSize: 16, fontWeight: FontWeight.w600)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
