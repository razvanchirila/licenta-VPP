import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/device.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';

class AddDeviceSheet extends StatefulWidget {
  const AddDeviceSheet({super.key});

  static Future<Device?> show(BuildContext context) => showModalBottomSheet<Device>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => const AddDeviceSheet(),
      );

  @override
  State<AddDeviceSheet> createState() => _AddDeviceSheetState();
}

class _AddDeviceSheetState extends State<AddDeviceSheet> {
  final _nameController = TextEditingController();
  final _powerController = TextEditingController();
  bool _critical = false;
  bool _startOn = false;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _powerController.dispose();
    super.dispose();
  }

  Future<void> _addDevice() async {
    final name = _nameController.text.trim();
    final power = double.tryParse(_powerController.text.trim().replaceAll(',', '.'));

    if (name.isEmpty) {
      setState(() => _error = 'Introdu numele dispozitivului');
      return;
    }
    if (power == null || power <= 0 || power > 50000) {
      setState(() => _error = 'Introdu un consum valid (1 - 50000 W)');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final device = await userApiService.createDevice(
        name: name,
        powerW: power,
        critical: _critical,
        statusOn: _startOn,
      );
      if (!mounted) return;
      Navigator.pop(context, device);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(top: MediaQuery.of(context).size.height * 0.15),
      decoration: AppTheme.sheetDecoration(radius: 24),
      child: SingleChildScrollView(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SheetHandle(margin: EdgeInsets.only(top: 12)),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.green.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.add_rounded, color: AppColors.green, size: 24),
                  ),
                  const SizedBox(width: 14),
                  Text(
                    'Adaugă dispozitiv',
                    style: GoogleFonts.inter(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label('Nume'),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _nameController,
                    style: GoogleFonts.inter(color: Colors.white),
                    decoration: _inputDecoration('ex: Televizor dormitor'),
                  ),
                  const SizedBox(height: 20),
                  _label('Consum (W)'),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _powerController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    style: GoogleFonts.inter(color: Colors.white),
                    decoration: _inputDecoration('ex: 150', suffix: 'W'),
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _critical,
                    activeThumbColor: AppColors.red,
                    title: Text('Dispozitiv critic', style: GoogleFonts.inter(color: Colors.white, fontSize: 14)),
                    subtitle: Text('Nu poate fi oprit (nici de VPP la delestare)', style: AppText.hint),
                    onChanged: (v) => setState(() => _critical = v),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _startOn,
                    activeThumbColor: AppColors.green,
                    title: Text('Pornit de la început', style: GoogleFonts.inter(color: Colors.white, fontSize: 14)),
                    onChanged: (v) => setState(() => _startOn = v),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 8),
                    Text(_error!, style: GoogleFonts.inter(color: AppColors.red, fontSize: 13)),
                  ],
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _saving ? null : _addDevice,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.green,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: _saving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : Text('Adaugă dispozitiv', style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600)),
                ),
              ),
            ),
            SizedBox(height: MediaQuery.of(context).padding.bottom + 10),
          ],
        ),
      ),
    );
  }

  Widget _label(String text) => Text(
        text,
        style: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 13, fontWeight: FontWeight.w500),
      );

  InputDecoration _inputDecoration(String hint, {String? suffix}) => InputDecoration(
        hintText: hint,
        hintStyle: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.3)),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.05),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        suffixText: suffix,
        suffixStyle: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5)),
      );
}
