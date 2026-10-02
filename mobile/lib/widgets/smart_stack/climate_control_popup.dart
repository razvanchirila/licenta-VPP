import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/models/climate_settings.dart';
import 'package:flutter_interface/widgets/smart_stack/arc_slider.dart';
import 'package:flutter_interface/widgets/smart_stack/climate/climate_room_sheet.dart';
import 'package:flutter_interface/widgets/smart_stack/climate/climate_schedule_sheet.dart';
import 'package:flutter_interface/core/theme.dart';

/// Demo-only: the settings live in [AppState], nothing is sent to the backend.
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

  static const Color _primaryColor = AppColors.blue;
  static const Color _successColor = AppColors.green;
  static const Color _surfaceColor = AppColors.surface;
  static const Color _glassColor = AppColors.surfaceAlt;

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
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ClimateRoomSheet(
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
      builder: (context) => ClimateScheduleSheet(
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
            color: _glassColor.withValues(alpha: 0.92),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            border: Border(top: BorderSide(color: Colors.white.withValues(alpha: 0.1), width: 1)),
          ),
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
              child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                  width: 40,
                  height: 5,
                  decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.25), borderRadius: BorderRadius.circular(3))),
              const SizedBox(height: 20),
              _buildHeader(),
              const SizedBox(height: 8),
              _buildRoomSelector(),
              const SizedBox(height: 28),
              ArcSlider(
                  minValue: 16,
                  maxValue: 32,
                  currentValue: _temperature,
                  size: 200,
                  onChanged: (value) => setState(() => _temperature = value)),
              const SizedBox(height: 24),
              _buildModeSection(),
              const SizedBox(height: 28),
              _buildPowerButton(),
              const SizedBox(height: 20),
            ],
          )),
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
              padding: const EdgeInsets.all(13),
              decoration:
                  BoxDecoration(color: Colors.white.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 18),
            ),
          ),
        ),
        Expanded(
          child: Text('Control Climă',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                  color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600, letterSpacing: -0.3)),
        ),
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: _showScheduleSettings,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(
                color:
                    _schedule.isEnabled ? _primaryColor.withValues(alpha: 0.2) : Colors.white.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: _schedule.isEnabled ? Border.all(color: _primaryColor.withValues(alpha: 0.5)) : null,
              ),
              child: Icon(Icons.schedule_rounded,
                  color: _schedule.isEnabled ? _primaryColor : Colors.white.withValues(alpha: 0.6), size: 18),
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
            color: _surfaceColor,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white.withValues(alpha: 0.08), width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(_selectedRoom.icon, color: _primaryColor, size: 16),
              const SizedBox(width: 8),
              Text(_selectedRoom.displayName,
                  style: GoogleFonts.inter(
                      color: Colors.white.withValues(alpha: 0.7), fontSize: 13, fontWeight: FontWeight.w500)),
              const SizedBox(width: 4),
              Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white.withValues(alpha: 0.5), size: 18),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildModeSection() {
    return Column(
      children: [
        Text('Mod',
            style: GoogleFonts.inter(
                color: Colors.white.withValues(alpha: 0.5), fontSize: 12, fontWeight: FontWeight.w500)),
        const SizedBox(height: 4),
        Text(_getModeDisplayText(),
            style:
                GoogleFonts.inter(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
        const SizedBox(height: 20),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: ClimateMode.values
              .map((mode) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    child:
                        _ModeButton(mode: mode, isSelected: _mode == mode, onTap: () => setState(() => _mode = mode)),
                  ))
              .toList(),
        ),
      ],
    );
  }

  Widget _buildPowerButton() {
    return GestureDetector(
      onTap: () => setState(() => _isOn = !_isOn),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: 60,
        height: 60,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _isOn ? _successColor : _surfaceColor,
          border: Border.all(
              color: _isOn ? _successColor.withValues(alpha: 0.5) : Colors.white.withValues(alpha: 0.1), width: 2),
          boxShadow:
              _isOn ? [BoxShadow(color: _successColor.withValues(alpha: 0.4), blurRadius: 20, spreadRadius: 2)] : null,
        ),
        child: Icon(Icons.power_settings_new_rounded,
            color: _isOn ? Colors.white : Colors.white.withValues(alpha: 0.5), size: 28),
      ),
    );
  }

  String _getModeDisplayText() {
    switch (_mode) {
      case ClimateMode.cold:
        return 'RĂCIRE';
      case ClimateMode.fan:
        return 'VENTILAȚIE';
      case ClimateMode.dry:
        return 'USCARE';
      case ClimateMode.heat:
        return 'ÎNCĂLZIRE';
    }
  }
}

class _ModeButton extends StatelessWidget {
  final ClimateMode mode;
  final bool isSelected;
  final VoidCallback onTap;

  static const Color _primaryColor = AppColors.blue;
  static const Color _surfaceColor = AppColors.surface;
  static const Color _successColor = AppColors.green;
  static const Color _warningColor = AppColors.amber;
  static const Color _errorColor = AppColors.red;

  const _ModeButton({required this.mode, required this.isSelected, required this.onTap});

  IconData get _icon {
    switch (mode) {
      case ClimateMode.cold:
        return Icons.ac_unit_rounded;
      case ClimateMode.fan:
        return Icons.air_rounded;
      case ClimateMode.dry:
        return Icons.water_drop_outlined;
      case ClimateMode.heat:
        return Icons.whatshot_rounded;
    }
  }

  Color get _modeColor {
    switch (mode) {
      case ClimateMode.cold:
        return _primaryColor;
      case ClimateMode.fan:
        return _successColor;
      case ClimateMode.dry:
        return _warningColor;
      case ClimateMode.heat:
        return _errorColor;
    }
  }

  String get _modeLabel {
    switch (mode) {
      case ClimateMode.cold:
        return 'RĂCIRE';
      case ClimateMode.fan:
        return 'FAN';
      case ClimateMode.dry:
        return 'USCAT';
      case ClimateMode.heat:
        return 'CALD';
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 68,
        height: 68,
        decoration: BoxDecoration(
          color: isSelected ? _modeColor.withValues(alpha: 0.2) : _surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
              color: isSelected ? _modeColor.withValues(alpha: 0.5) : Colors.white.withValues(alpha: 0.08), width: 1.5),
          boxShadow: isSelected
              ? [BoxShadow(color: _modeColor.withValues(alpha: 0.2), blurRadius: 12, spreadRadius: 1)]
              : null,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(_icon, color: isSelected ? _modeColor : Colors.white.withValues(alpha: 0.5), size: 24),
            const SizedBox(height: 4),
            Text(_modeLabel,
                style: GoogleFonts.inter(
                    color: isSelected ? _modeColor : Colors.white.withValues(alpha: 0.5),
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5)),
          ],
        ),
      ),
    );
  }
}
