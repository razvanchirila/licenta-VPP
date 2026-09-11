import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/state/app_state.dart';
import 'package:flutter_interface/services/user_api_service.dart';

/// Settings screen for battery/powerwall configuration
/// 
/// Allows users to:
/// - Set backup reserve (SOC min) via a draggable slider
/// - Choose between Eco and Profit operating modes
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Battery backup reserve (0-100%)
  late double _backupReserve;

  // Operating mode: "Eco" or "Profit"
  late String _selectedMode;

  // Saving indicator (for UI feedback)
  bool _isSaving = false;

  // Loading settings from API
  bool _isLoading = true;

  // Track if user is currently dragging the slider
  bool _isDragging = false;

  @override
  void initState() {
    super.initState();
    _backupReserve = appState.backupReserve.clamp(0, 60);
    _selectedMode = appState.mode;
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final data = await userApiService.getSettings();
    if (!mounted) return;
    setState(() {
      if (data != null) {
        _selectedMode = (data['mode'] as String?) ?? appState.mode;
        _backupReserve = ((data['backup_reserve_percent'] as num?)?.toDouble() ?? appState.backupReserve).clamp(0, 60);
        appState.mode = _selectedMode;
        appState.backupReserve = _backupReserve;
      }
      _isLoading = false;
    });
  }

  Future<void> _saveMode(String mode) async {
    setState(() {
      _selectedMode = mode;
      _isSaving = true;
    });
    appState.mode = mode;

    final result = await userApiService.updateSettings(mode: mode);
    if (!mounted) return;
    setState(() => _isSaving = false);
    if (result != null && result['error'] == null) {
      _showSnackBar('Mod salvat cu succes');
    } else {
      _showSnackBar('Eroare la salvare', isError: true);
    }
  }

  Future<void> _saveBackupReserve() async {
    appState.backupReserve = _backupReserve;
    setState(() => _isSaving = true);

    final result = await userApiService.updateSettings(backupReservePercent: _backupReserve);
    if (!mounted) return;
    setState(() => _isSaving = false);
    if (result != null && result['error'] == null) {
      _showSnackBar('Rezervă backup salvată');
    } else {
      _showSnackBar('Eroare la salvare', isError: true);
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: GoogleFonts.inter(color: Colors.white),
        ),
        backgroundColor: isError ? const Color(0xFFEF4444) : const Color(0xFF22C55E),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: Color(0xFF22C55E),
                      ),
                    )
                  : _buildContent(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          // Back button
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: const Icon(
              Icons.arrow_back_ios_rounded,
              color: Colors.white,
              size: 22,
            ),
          ),
          const SizedBox(width: 8),
          // Title
          Text(
            'Settings',
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.5,
            ),
          ),
          const Spacer(),
          // Saving indicator
          if (_isSaving)
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF22C55E)),
              ),
            ),
          const SizedBox(width: 16),
        ],
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
          
          // Battery section header
          _buildSectionHeader(
            icon: Icons.battery_charging_full_rounded,
            title: 'Invertor',
            subtitle: 'Configurare baterie',
          ),
          const SizedBox(height: 16),
          
          // Backup Reserve Slider
          _buildBackupReserveCard(),
          const SizedBox(height: 24),
          
          // Operating Mode section header
          _buildSectionHeader(
            icon: Icons.tune_rounded,
            title: 'Mod operare',
            subtitle: 'Alege cum să fie folosită energia',
          ),
          const SizedBox(height: 16),
          
          // Eco Mode Card
          _buildModeCard(
            mode: "Eco",
            title: "Eco Mode",
            subtitle: "Self-Powered",
            description: "Prioritizează folosirea energiei solare și a bateriei pentru consum propriu. Minimizează importul din rețea și maximizează autosuficiența energetică.",
            icon: Icons.eco_rounded,
            color: const Color(0xFF22C55E),
          ),
          const SizedBox(height: 12),
          
          // Profit Mode Card
          _buildModeCard(
            mode: "Profit",
            title: "Profit Mode",
            subtitle: "Sell Energy",
            description: "Vinde energia stocată în baterie când prețurile sunt mari. Cumpără energie ieftină noaptea pentru a o vinde la prețuri de vârf.",
            icon: Icons.trending_up_rounded,
            color: const Color(0xFFFBBF24),
          ),
          
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: const Color(0xFF1C1C1E),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(
            icon,
            color: Colors.white.withOpacity(0.8),
            size: 22,
          ),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              subtitle,
              style: GoogleFonts.inter(
                color: Colors.white.withOpacity(0.5),
                fontSize: 13,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildBackupReserveCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1C1C1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Title row with value
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Rezervă Backup',
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Procentul minim de baterie păstrat ca rezervă',
                      style: GoogleFonts.inter(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              // Value display
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFF22C55E).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: const Color(0xFF22C55E).withOpacity(0.3),
                    width: 1,
                  ),
                ),
                child: Text(
                  '${_backupReserve.toInt()}%',
                  style: GoogleFonts.inter(
                    color: const Color(0xFF22C55E),
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          // Slider
          SliderTheme(
            data: SliderThemeData(
              activeTrackColor: const Color(0xFF22C55E),
              inactiveTrackColor: Colors.white.withOpacity(0.1),
              thumbColor: const Color(0xFF22C55E),
              overlayColor: const Color(0xFF22C55E).withOpacity(0.2),
              trackHeight: 6,
              thumbShape: const RoundSliderThumbShape(
                enabledThumbRadius: 12,
                elevation: 4,
              ),
              overlayShape: const RoundSliderOverlayShape(overlayRadius: 24),
            ),
            child: Slider(
              value: _backupReserve.clamp(0, 60),
              min: 0,
              max: 60,
              divisions: 12,
              onChangeStart: (value) {
                _isDragging = true;
              },
              onChanged: (value) {
                setState(() {
                  _backupReserve = value;
                });
              },
              onChangeEnd: (value) {
                _isDragging = false;
                // Only save and show notification when user releases the slider
                _saveBackupReserve();
              },
            ),
          ),
          
          // Labels - visual representation showing 0-100% but only 0-60% usable
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              children: [
                Text(
                  '0%',
                  style: GoogleFonts.inter(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 11,
                  ),
                ),
                const Spacer(),
                Text(
                  '30%',
                  style: GoogleFonts.inter(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 11,
                  ),
                ),
                const Spacer(),
                Text(
                  '60%',
                  style: GoogleFonts.inter(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Info box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF3B82F6).withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: const Color(0xFF3B82F6).withOpacity(0.2),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.info_outline_rounded,
                  color: const Color(0xFF3B82F6).withOpacity(0.8),
                  size: 18,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Această rezervă va fi păstrată pentru situații de urgență (pană de curent).',
                    style: GoogleFonts.inter(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeCard({
    required String mode,
    required String title,
    required String subtitle,
    required String description,
    required IconData icon,
    required Color color,
  }) {
    final isSelected = _selectedMode == mode;
    
    return GestureDetector(
      onTap: () {
        if (!isSelected && !_isSaving) {
          _saveMode(mode); // ignore: discarded_futures
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected
              ? color.withOpacity(0.12)
              : const Color(0xFF1C1C1E),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected
                ? color.withOpacity(0.5)
                : Colors.white.withOpacity(0.08),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icon container
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: isSelected
                    ? color.withOpacity(0.2)
                    : Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                icon,
                color: isSelected ? color : Colors.white.withOpacity(0.6),
                size: 26,
              ),
            ),
            const SizedBox(width: 14),
            
            // Text content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        title,
                        style: GoogleFonts.inter(
                          color: isSelected ? color : Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? color.withOpacity(0.2)
                              : Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          subtitle,
                          style: GoogleFonts.inter(
                            color: isSelected
                                ? color
                                : Colors.white.withOpacity(0.6),
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    description,
                    style: GoogleFonts.inter(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 13,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            
            // Checkmark
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                color: isSelected
                    ? color
                    : Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: isSelected
                    ? null
                    : Border.all(
                        color: Colors.white.withOpacity(0.2),
                        width: 2,
                      ),
              ),
              child: isSelected
                  ? const Icon(
                      Icons.check_rounded,
                      color: Colors.black,
                      size: 16,
                    )
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}
