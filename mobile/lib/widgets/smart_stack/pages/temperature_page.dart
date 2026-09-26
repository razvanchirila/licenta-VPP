import 'package:flutter/material.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/temperature_card.dart';
import 'package:flutter_interface/widgets/smart_stack/climate_control_popup.dart';
import 'package:flutter_interface/core/theme.dart';

class TemperaturePage extends StatefulWidget {
  const TemperaturePage({super.key});

  @override
  State<TemperaturePage> createState() => _TemperaturePageState();
}

class _TemperaturePageState extends State<TemperaturePage> {
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

  void _openClimateControl() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => const ClimateControlPopup(),
    );
  }

  void _toggleUnit() {
    appState.useCelsius = !appState.useCelsius;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: TemperatureCard(
              temperature: appState.outdoorTemperature,
              label: appState.weatherDescription,
              icon: appState.weatherIcon,
              iconColor: const Color(0xFF60A5FA),
              isInteractive: false,
              useCelsius: appState.useCelsius,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: TemperatureCard(
              temperature: appState.indoorTemperature,
              label: 'Interior (țintă)',
              icon: Icons.home_rounded,
              iconColor: AppColors.amber,
              isInteractive: true,
              onTap: _openClimateControl,
              useCelsius: appState.useCelsius,
              showUnitToggle: true,
              onUnitToggle: _toggleUnit,
            ),
          ),
        ],
      ),
    );
  }
}
