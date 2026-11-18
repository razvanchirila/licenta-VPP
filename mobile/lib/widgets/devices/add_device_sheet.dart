import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/device.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/surface_card.dart';

/// Adds a device, or edits [device] when one is given (name, power and the critical flag).
class AddDeviceSheet extends StatefulWidget {
  final Device? device;

  const AddDeviceSheet({super.key, this.device});

  static Future<Device?> show(BuildContext context, {Device? device}) => showModalBottomSheet<Device>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => AddDeviceSheet(device: device),
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

  bool get _editing => widget.device != null;

  @override
  void initState() {
    super.initState();
    final device = widget.device;
    if (device == null) return;
    final power = device.powerW;
    _nameController.text = device.name;
    _powerController.text = power == power.roundToDouble() ? power.round().toString() : power.toString();
    _critical = device.critical;
    _startOn = device.statusOn;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _powerController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
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
      // A critical device can be neither switched off nor deleted, so it must never be saved off.
      final existing = widget.device;
      final device = existing == null
          ? await userApiService.createDevice(
              name: name,
              powerW: power,
              critical: _critical,
              statusOn: _critical || _startOn,
            )
          : await userApiService.updateDevice(
              existing.id,
              name: name,
              powerW: power,
              critical: _critical,
              statusOn: _critical ? true : null,
            );
      if (!mounted) return;
      Navigator.pop(context, device);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = ApiException.from(e).message;
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(top: MediaQuery.of(context).size.height * 0.15),
      decoration: AppTheme.sheetDecoration(radius: 24),
      child: Material(
        type: MaterialType.transparency,
        child: SingleChildScrollView(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom + MediaQuery.paddingOf(context).bottom,
          ),
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
                      child: Icon(_editing ? Icons.edit_rounded : Icons.add_rounded, color: AppColors.green, size: 24),
                    ),
                    const SizedBox(width: 14),
                    Text(
                      _title,
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
                    Semantics(
                      container: true,
                      identifier: 'device-form-critical',
                      child: SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _critical,
                        activeThumbColor: AppColors.red,
                        title: Text('Dispozitiv critic', style: GoogleFonts.inter(color: Colors.white, fontSize: 14)),
                        subtitle: Text('Nu poate fi oprit (nici de VPP la delestare)', style: AppText.hint),
                        onChanged: (v) => setState(() => _critical = v),
                      ),
                    ),
                    if (!_editing)
                      Semantics(
                        container: true,
                        identifier: 'device-form-start',
                        child: SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _critical || _startOn,
                          activeThumbColor: AppColors.green,
                          title:
                              Text('Pornit de la început', style: GoogleFonts.inter(color: Colors.white, fontSize: 14)),
                          subtitle:
                              _critical ? Text('Un dispozitiv critic este mereu pornit', style: AppText.hint) : null,
                          onChanged: _critical ? null : (v) => setState(() => _startOn = v),
                        ),
                      ),
                    if (_editing && _critical && !_startOn)
                      Text('La salvare dispozitivul va fi pornit: unul critic este mereu pornit.', style: AppText.hint),
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
                    onPressed: _saving ? null : _save,
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
                        : Text(_title, style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600)),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).padding.bottom + 10),
            ],
          ),
        ),
      ),
    );
  }

  String get _title => _editing ? 'Editează dispozitivul' : 'Adaugă dispozitiv';

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
