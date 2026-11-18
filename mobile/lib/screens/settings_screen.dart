import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/models/house.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/common/async_body.dart';
import 'package:flutter_interface/widgets/common/screen_header.dart';
import 'package:flutter_interface/widgets/common/section_header.dart';
import 'package:flutter_interface/widgets/settings/backup_reserve_card.dart';
import 'package:flutter_interface/widgets/settings/mode_card.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> with AsyncLoader<HouseSettings, SettingsScreen> {
  static const double _maxReserve = 60;

  double _backupReserve = 0;
  String _selectedMode = 'Eco';
  bool _hasBattery = false;
  bool _isSaving = false;
  bool _mpcActive = false;
  double? _reserveBeforeDrag;

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _loadController();
  }

  /// Only the rule-based controller reads the Eco/Profit mode; without an answer no note is shown.
  Future<void> _loadController() async {
    try {
      final config = await userApiService.getSimConfig();
      if (mounted) setState(() => _mpcActive = config.isMpc);
    } catch (_) {}
  }

  Future<void> _loadSettings() async {
    final settings = await load(userApiService.getSettings);
    if (settings != null) setState(() => _apply(settings));
  }

  void _apply(HouseSettings s) {
    _selectedMode = s.mode;
    _hasBattery = s.battery != null;
    _backupReserve = (s.backupReservePercent ?? 0).clamp(0, _maxReserve).toDouble();
  }

  /// Optimistic update: the mode flips immediately and rolls back on error.
  Future<void> _saveMode(String mode) async {
    final previous = _selectedMode;
    setState(() {
      _selectedMode = mode;
      _isSaving = true;
    });
    try {
      final settings = await userApiService.updateSettings(mode: mode);
      if (!mounted) return;
      setState(() => _apply(settings));
      _showSnackBar('Mod salvat: ${settings.mode}');
    } catch (e) {
      if (!mounted) return;
      setState(() => _selectedMode = previous);
      _showSnackBar('Eroare la salvare: ${ApiException.from(e).message}', isError: true);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _saveBackupReserve(double value, double previous) async {
    setState(() => _isSaving = true);
    try {
      final settings = await userApiService.updateSettings(backupReservePercent: value);
      if (!mounted) return;
      setState(() => _apply(settings));
      _showSnackBar('Rezervă backup salvată: ${_backupReserve.round()}%');
    } catch (e) {
      if (!mounted) return;
      setState(() => _backupReserve = previous);
      _showSnackBar('Eroare la salvare: ${ApiException.from(e).message}', isError: true);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Semantics(
            container: true,
            identifier: 'snackbar',
            child: Text(message, style: GoogleFonts.inter(color: Colors.white))),
        backgroundColor: isError ? AppColors.red : AppColors.green,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ScreenHeader(
              title: 'Setări',
              actions: [
                if (_isSaving)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(AppColors.green),
                    ),
                  ),
                const SizedBox(width: 16),
              ],
            ),
            Expanded(
              child: AsyncBody<HouseSettings>(value: state, onRetry: _loadSettings, builder: (_) => _buildContent()),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          const SectionHeader(
            icon: Icons.battery_charging_full_rounded,
            title: 'Invertor',
            subtitle: 'Configurare baterie',
          ),
          const SizedBox(height: 16),
          BackupReserveCard(
            value: _backupReserve,
            max: _maxReserve,
            hasBattery: _hasBattery,
            enabled: _hasBattery && !_isSaving,
            onChanged: (value) => setState(() => _backupReserve = value),
            onChangeStart: (value) => _reserveBeforeDrag = value,
            onChangeEnd: (value) => _saveBackupReserve(value, _reserveBeforeDrag ?? value),
          ),
          const SizedBox(height: 24),
          const SectionHeader(
            icon: Icons.tune_rounded,
            title: 'Mod operare',
            subtitle: 'Alege cum să fie folosită energia',
          ),
          const SizedBox(height: 16),
          if (_mpcActive) ...[
            const _MpcNote(),
            const SizedBox(height: 12),
          ],
          _modeCard(
            mode: 'Eco',
            title: 'Mod Eco',
            subtitle: 'Autoconsum',
            description: 'Prioritizează folosirea energiei solare și a bateriei pentru consum propriu. '
                'Minimizează importul din rețea și maximizează autosuficiența energetică.',
            icon: Icons.eco_rounded,
            color: AppColors.green,
          ),
          const SizedBox(height: 12),
          _modeCard(
            mode: 'Profit',
            title: 'Mod Profit',
            subtitle: 'Vinde energie',
            description: 'Vinde energia stocată în baterie când prețurile sunt mari. '
                'Cumpără energie ieftină noaptea pentru a o vinde la prețuri de vârf.',
            icon: Icons.trending_up_rounded,
            color: AppColors.amber,
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _modeCard({
    required String mode,
    required String title,
    required String subtitle,
    required String description,
    required IconData icon,
    required Color color,
  }) {
    final isSelected = _selectedMode == mode;
    return OperatingModeCard(
      semanticsId: 'settings-mode-${mode.toLowerCase()}',
      title: title,
      subtitle: subtitle,
      description: description,
      icon: icon,
      color: color,
      isSelected: isSelected,
      onTap: (!isSelected && !_isSaving) ? () => _saveMode(mode) : null,
    );
  }
}

class _MpcNote extends StatelessWidget {
  const _MpcNote();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      identifier: 'settings-mode-note',
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.blue.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.blue.withValues(alpha: 0.3)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.info_outline_rounded, color: AppColors.blue, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Acum simularea rulează cu optimizatorul MPC, care decide pentru tot cartierul. '
                'Modul ales aici se aplică doar când operatorul trece pe controlul bazat pe reguli.',
                style: GoogleFonts.inter(color: Colors.white70, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
