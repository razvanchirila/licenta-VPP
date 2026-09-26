import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';

Future<double?> showVppTransferDialog(BuildContext context, {required double? rateLeiKwh}) async {
  final controller = TextEditingController(text: '1.0');
  final value = await showDialog<double>(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: AppColors.surface,
      title: Text('Transferă energie în rezerva VPP', style: GoogleFonts.inter(color: Colors.white, fontSize: 18)),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Energia se mută din bateria ta în rezerva VPP și operatorul te plătește cu '
            '${rateLeiKwh?.toStringAsFixed(2) ?? '-'} lei/kWh.',
            style: GoogleFonts.inter(color: Colors.white70, fontSize: 13),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: controller,
            autofocus: true,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: GoogleFonts.inter(color: Colors.white),
            decoration: InputDecoration(
              suffixText: 'kWh',
              suffixStyle: GoogleFonts.inter(color: Colors.white54),
              filled: true,
              fillColor: Colors.white.withValues(alpha: 0.05),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Anulează', style: GoogleFonts.inter(color: Colors.white54)),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, double.tryParse(controller.text.replaceAll(',', '.'))),
          child: Text('Transferă', style: GoogleFonts.inter(color: AppColors.tradingAccent)),
        ),
      ],
    ),
  );
  controller.dispose();
  return value;
}
