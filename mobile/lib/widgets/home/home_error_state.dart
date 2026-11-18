import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/browser_viewport.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/services/api_client.dart';

/// A 403 means the account has no house yet; for an operator account that is the normal case.
class HomeErrorState extends StatelessWidget {
  final ApiException? error;
  final bool isAdmin;
  final String? operatorPanelUrl;
  final VoidCallback onRetry;
  final VoidCallback onLogout;

  const HomeErrorState({
    super.key,
    required this.error,
    required this.onRetry,
    required this.onLogout,
    this.isAdmin = false,
    this.operatorPanelUrl,
  });

  @override
  Widget build(BuildContext context) {
    final noHouse = error?.statusCode == 403;
    final operator = noHouse && isAdmin;
    final panelUrl = operatorPanelUrl;
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(_icon(noHouse, operator), color: Colors.white38, size: 64),
            const SizedBox(height: 16),
            Semantics(
              container: true,
              identifier: 'home-error',
              child: Text(
                _message(noHouse, operator),
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(color: Colors.white70, fontSize: 16),
              ),
            ),
            const SizedBox(height: 24),
            if (!operator)
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Reîncearcă'),
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.green, foregroundColor: Colors.black),
              ),
            if (operator && panelUrl != null) ...[
              ElevatedButton.icon(
                onPressed: () => openBrowserPage(panelUrl),
                icon: const Icon(Icons.open_in_new_rounded),
                label: const Text('Deschide panoul de operator'),
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.green, foregroundColor: Colors.black),
              ),
              const SizedBox(height: 12),
              SelectableText(
                panelUrl,
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(color: Colors.white54, fontSize: 13),
              ),
            ],
            const SizedBox(height: 8),
            TextButton(
              onPressed: onLogout,
              child: Text('Deconectare', style: GoogleFonts.inter(color: Colors.white54)),
            ),
          ],
        ),
      ),
    );
  }

  IconData _icon(bool noHouse, bool operator) {
    if (operator) return Icons.admin_panel_settings_outlined;
    return noHouse ? Icons.home_outlined : Icons.cloud_off_rounded;
  }

  String _message(bool noHouse, bool operator) {
    if (operator) {
      return 'Acesta este un cont de operator, fără casă asignată.\n'
          'Comunitatea se administrează din panoul de operator; aplicația arată casa unui utilizator.';
    }
    if (noHouse) return 'Contul tău nu are încă o casă asignată.\nCere administratorului să îți aloce una.';
    return error?.message ?? 'Nu s-au putut încărca datele';
  }
}
