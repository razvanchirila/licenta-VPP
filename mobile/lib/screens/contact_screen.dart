import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/common/screen_header.dart';

class ContactScreen extends StatelessWidget {
  const ContactScreen({super.key});

  void _copyToClipboard(BuildContext context, String text, String label) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$label copiat în clipboard'),
        backgroundColor: AppColors.green,
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
                    title: 'Email',
                    subtitle: 'support@vpp-simulator.ro',
                    color: AppColors.blue,
                    onTap: () => _copyToClipboard(context, 'support@vpp-simulator.ro', 'Email'),
                  ),
                  const SizedBox(height: 12),
                  _buildContactOption(
                    context: context,
                    icon: Icons.phone_rounded,
                    title: 'Telefon',
                    subtitle: '+40 721 234 567',
                    color: AppColors.green,
                    onTap: () => _copyToClipboard(context, '+40721234567', 'Telefon'),
                  ),
                  const SizedBox(height: 12),
                  _buildContactOption(
                    context: context,
                    icon: Icons.location_on_rounded,
                    title: 'Adresă',
                    subtitle: 'Str. Energiei Nr. 10, București',
                    color: AppColors.amber,
                    onTap: () => _copyToClipboard(context, 'Str. Energiei Nr. 10, București', 'Adresa'),
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
                    question: 'Cum pot monitoriza consumul de energie?',
                    answer:
                        'Accesează secțiunea Energy din meniul principal pentru a vedea consumul în timp real și istoricul.',
                  ),
                  _buildFaqItem(
                    question: 'Ce înseamnă P2P Trading?',
                    answer:
                        'P2P Trading îți permite să vinzi sau să cumperi energie direct de la alți prosumatori din comunitate.',
                  ),
                  _buildFaqItem(
                    question: 'Cum funcționează bateria Powerwall?',
                    answer:
                        'Bateria stochează energia solară în exces și o folosește când producția solară este scăzută sau în caz de pană de curent.',
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
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: color.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
        child: Row(
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
        ),
      ),
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
