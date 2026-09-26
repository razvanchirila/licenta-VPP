import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/services/api_client.dart';

/// A 403 means the account has no house yet.
class HomeErrorState extends StatelessWidget {
  final ApiException? error;
  final VoidCallback onRetry;
  final VoidCallback onLogout;

  const HomeErrorState({super.key, required this.error, required this.onRetry, required this.onLogout});

  @override
  Widget build(BuildContext context) {
    final noHouse = error?.statusCode == 403;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(noHouse ? Icons.home_outlined : Icons.cloud_off_rounded, color: Colors.white38, size: 64),
            const SizedBox(height: 16),
            Text(
              noHouse
                  ? 'Contul tău nu are încă o casă asignată.\nCere administratorului să îți aloce una.'
                  : (error?.message ?? 'Nu s-au putut încărca datele'),
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 16),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Reîncearcă'),
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.green, foregroundColor: Colors.black),
            ),
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
}
