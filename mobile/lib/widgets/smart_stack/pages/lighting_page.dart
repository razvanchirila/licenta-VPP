import 'package:flutter/material.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/widgets/smart_stack/cards/lighting_card.dart';

class LightingPage extends StatefulWidget {
  const LightingPage({super.key});

  @override
  State<LightingPage> createState() => _LightingPageState();
}

class _LightingPageState extends State<LightingPage> {
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

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          LightingCard(
            allLightsOn: appState.allLightsOn,
            onToggle: () => appState.toggleAllLights(),
          ),
          const Spacer(),
        ],
      ),
    );
  }
}
