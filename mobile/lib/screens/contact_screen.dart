import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/screen_header.dart';

class ContactScreen extends StatelessWidget {
  const ContactScreen({super.key});

  /// The browser can refuse clipboard access (no permission, page not focused).
  Future<void> _copyToClipboard(BuildContext context, String text) async {
    final messenger = ScaffoldMessenger.of(context);
    var copied = true;
    try {
      await Clipboard.setData(ClipboardData(text: text));
    } catch (_) {
      copied = false;
    }
    messenger.showSnackBar(
      SnackBar(
        content: Text(copied ? 'Copiat în clipboard: $text' : 'Textul nu a putut fi copiat în clipboard'),
        backgroundColor: copied ? AppColors.green : AppColors.red,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.deepBackground,
      appBar: AppBar(
        backgroundColor: AppColors.deepBackground,
        elevation: 0,
        leading: const BackNavButton(icon: Icons.arrow_back_ios_new_rounded),
        title: Text(
          'Contact',
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHeaderCard(),
                  const SizedBox(height: 24),
                  Text(
                    'Contactează-ne',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildContactOption(
                    context: context,
                    icon: Icons.email_rounded,
                    title: 'E-mail',
                    subtitle: 'support@vpp-simulator.ro',
                    color: AppColors.blue,
                    onTap: () => _copyToClipboard(context, 'support@vpp-simulator.ro'),
                  ),
                  const SizedBox(height: 12),
                  _buildContactOption(
                    context: context,
                    icon: Icons.phone_rounded,
                    title: 'Telefon',
                    subtitle: '+40 700 000 000',
                    color: AppColors.green,
                    onTap: () => _copyToClipboard(context, '+40700000000'),
                  ),
                  const SizedBox(height: 12),
                  _buildContactOption(
                    context: context,
                    icon: Icons.location_on_rounded,
                    title: 'Adresă',
                    subtitle: 'Str. Energiei Nr. 10, București',
                    color: AppColors.amber,
                    onTap: () => _copyToClipboard(context, 'Str. Energiei Nr. 10, București'),
                  ),
                  const SizedBox(height: 32),
                  Text(
                    'Program suport',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildScheduleCard(),
                  const SizedBox(height: 32),
                  Text(
                    'Întrebări frecvente',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildFaqItem(
                    question: 'Unde văd consumul și producția casei?',
                    answer: 'Ecranul principal arată puterile din ultimul pas al simulării. Graficele pe zi, '
                        'săptămână și lună sunt în meniu, la Energie, iar consumul pe dispozitive la Statistici.',
                  ),
                  _buildFaqItem(
                    question: 'Ce înseamnă Trading P2P?',
                    answer: 'Surplusul unei case este vândut vecinilor din comunitate la un preț mai mic decât cel '
                        'din rețea. În meniu, la Trading P2P, găsești prețul curent, portofelul, istoricul '
                        'tranzacțiilor și opțiunile de vânzare și cumpărare.',
                  ),
                  _buildFaqItem(
                    question: 'Cum este folosită bateria casei?',
                    answer: 'Bateria se încarcă din surplusul solar și se descarcă atunci când consumul depășește '
                        'producția. Rezerva de backup, sub care bateria nu se descarcă, se alege din meniu, la Setări.',
                  ),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          )),
    );
  }

  Widget _buildHeaderCard() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppColors.surfaceAlt.withValues(alpha: 0.8),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.1),
            width: 1,
          ),
        ),
        child: Column(
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: AppColors.blue.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.support_agent_rounded,
                color: AppColors.blue,
                size: 40,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Suntem aici să te ajutăm',
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Echipa noastră de suport este disponibilă pentru orice întrebare despre sistemul tău de energie.',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContactOption({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    final radius = BorderRadius.circular(16);
    return Semantics(
      container: true,
      button: true,
      label: '$title: $subtitle',
      hint: 'Copiază',
      onTap: onTap,
      excludeSemantics: true,
      child: Material(
        color: color.withValues(alpha: 0.1),
        shape: RoundedRectangleBorder(
          borderRadius: radius,
          side: BorderSide(color: color.withValues(alpha: 0.3), width: 1),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: radius,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: _contactRow(icon: icon, title: title, subtitle: subtitle, color: color),
          ),
        ),
      ),
    );
  }

  Widget _contactRow({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
  }) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: color, size: 24),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: GoogleFonts.inter(
                  color: Colors.white.withValues(alpha: 0.6),
                  fontSize: 14,
                ),
              ),
            ],
          ),
        ),
        Icon(
          Icons.copy_rounded,
          color: Colors.white.withValues(alpha: 0.4),
          size: 20,
        ),
      ],
    );
  }

  Widget _buildScheduleCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceAlt,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.1),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          _buildScheduleRow('Luni - Vineri', '09:00 - 18:00', true),
          const SizedBox(height: 12),
          _buildScheduleRow('Sâmbătă', '10:00 - 14:00', true),
          const SizedBox(height: 12),
          _buildScheduleRow('Duminică', 'Închis', false),
        ],
      ),
    );
  }

  Widget _buildScheduleRow(String day, String hours, bool isOpen) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          day,
          style: GoogleFonts.inter(
            color: Colors.white.withValues(alpha: 0.8),
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
        Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: isOpen ? AppColors.green : AppColors.red,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              hours,
              style: GoogleFonts.inter(
                color: isOpen ? Colors.white : Colors.white.withValues(alpha: 0.5),
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildFaqItem({required String question, required String answer}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceAlt,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.1),
          width: 1,
        ),
      ),
      child: Material(
        type: MaterialType.transparency,
        child: ExpansionTile(
          shape: const Border(),
          collapsedShape: const Border(),
          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          iconColor: Colors.white.withValues(alpha: 0.5),
          collapsedIconColor: Colors.white.withValues(alpha: 0.5),
          title: Text(
            question,
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          children: [
            Text(
              answer,
              style: GoogleFonts.inter(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
