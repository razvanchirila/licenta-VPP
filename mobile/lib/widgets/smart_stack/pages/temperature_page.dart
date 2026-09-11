import 'package:flutter/material.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/temperature_card.dart';
import 'package:flutter_interface/widgets/smart_stack/climate_control_popup.dart';

/// Temperature page for SmartStack
/// Contains indoor (interactive) and outdoor (display only) temperature cards
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
          // Outdoor temperature card (display only) - LEFT
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
          // Indoor temperature card (interactive) - RIGHT
          Expanded(
            child: TemperatureCard(
              temperature: appState.indoorTemperature,
              label: 'Interior',
              icon: Icons.home_rounded,
              iconColor: const Color(0xFFFBBF24),
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
