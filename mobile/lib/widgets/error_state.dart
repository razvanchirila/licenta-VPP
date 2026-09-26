import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

class ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  final Color accent;

  const ErrorState({
    super.key,
    required this.message,
    required this.onRetry,
    this.accent = AppColors.green,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off_rounded, color: Colors.white38, size: 56),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: Colors.white70, fontSize: 15),
            ),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Reîncearcă'),
              style: ElevatedButton.styleFrom(
                backgroundColor: accent,
                foregroundColor: Colors.black,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class InlineError extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const InlineError({super.key, required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.red.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.red.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: AppColors.red, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(message, style: GoogleFonts.inter(color: Colors.white70, fontSize: 12)),
          ),
          TextButton(
            onPressed: onRetry,
            child: Text('Reîncearcă', style: GoogleFonts.inter(color: Colors.white, fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
