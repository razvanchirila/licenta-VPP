import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'constants.dart';
import 'energy_flow.dart';

class AppColors {
  AppColors._();

  static const Color background = Color(0xFF121212);
  static const Color deepBackground = Color(0xFF0A0A0A);
  static const Color surface = Color(0xFF1C1C1E);
  static const Color surfaceAlt = Color(0xFF1A1A1A);
  static const Color surfaceMenu = Color(0xFF1E1E1E);
  static const Color tooltip = Color(0xFF2C2C2E);

  static const Color blue = Color(0xFF3B82F6);
  static const Color green = Color(0xFF22C55E);
  static const Color emerald = Color(0xFF10B981);
  static const Color amber = Color(0xFFFBBF24);
  static const Color amberDark = Color(0xFFF59E0B);
  static const Color red = Color(0xFFEF4444);
  static const Color purple = Color(0xFFA855F7);
  static const Color indigo = Color(0xFF6366F1);
  static const Color orange = Color(0xFFF97316);
  static const Color slate = Color(0xFF64748B);
  static const Color teal = Color(0xFF00D4AA);

  static const Color tradingAccent = Color(0xFFB3B3B3);

  static const Color priceUp = Color(0xFFFF5252);
  static const Color priceDown = Color(0xFF00C853);

  static const Color textSecondary = Color(0x99FFFFFF);
}

class AppText {
  AppText._();

  static TextStyle get screenTitle =>
      GoogleFonts.inter(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w600, letterSpacing: -0.5);

  static TextStyle get sectionTitle =>
      GoogleFonts.inter(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600);

  static TextStyle get cardTitle => GoogleFonts.inter(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600);

  static TextStyle get subtitle => GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 13);

  static TextStyle get caption => GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 12);

  static TextStyle get small => GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 11);

  static TextStyle get muted => GoogleFonts.inter(color: Colors.white54, fontSize: 12);

  static TextStyle get hint => GoogleFonts.inter(color: Colors.white38, fontSize: 12);
}

class AppTheme {
  AppTheme._();

  static const ColorScheme _colorScheme = ColorScheme.dark(
    primary: Color(AppConstants.primaryColorValue),
    secondary: Color(AppConstants.successColorValue),
    surface: Color(AppConstants.surfaceColorValue),
    error: Color(AppConstants.errorColorValue),
    onPrimary: Colors.white,
    onSecondary: Colors.white,
    onSurface: Colors.white,
    onError: Colors.white,
  );

  static const Color warning = Color(AppConstants.warningColorValue);
  static const Color success = Color(AppConstants.successColorValue);
  static const Color solar = Color(0xFFFBBF24);
  static const Color battery = Color(AppConstants.primaryColorValue);
  static const Color grid = Color(AppConstants.errorColorValue);

  static TextTheme get _textTheme => GoogleFonts.interTextTheme(
        ThemeData.dark().textTheme.copyWith(
              displayLarge: GoogleFonts.inter(
                fontSize: 32,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
              displayMedium: GoogleFonts.inter(
                fontSize: 28,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.5,
              ),
              displaySmall: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeXXL,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.5,
              ),
              headlineLarge: GoogleFonts.inter(
                fontSize: 22,
                fontWeight: FontWeight.w600,
              ),
              headlineMedium: GoogleFonts.inter(
                fontSize: 20,
                fontWeight: FontWeight.w600,
              ),
              headlineSmall: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeXL,
                fontWeight: FontWeight.w600,
              ),
              titleLarge: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeL,
                fontWeight: FontWeight.w600,
              ),
              titleMedium: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeM,
                fontWeight: FontWeight.w500,
              ),
              titleSmall: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeS,
                fontWeight: FontWeight.w500,
              ),
              bodyLarge: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeL,
                fontWeight: FontWeight.w400,
              ),
              bodyMedium: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeM,
                fontWeight: FontWeight.w400,
              ),
              bodySmall: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeS,
                fontWeight: FontWeight.w400,
              ),
              labelLarge: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeM,
                fontWeight: FontWeight.w500,
              ),
              labelMedium: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeS,
                fontWeight: FontWeight.w500,
                letterSpacing: 0.5,
              ),
              labelSmall: GoogleFonts.inter(
                fontSize: AppConstants.fontSizeXS,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
              ),
            ),
      );

  static ThemeData get theme => ThemeData.dark().copyWith(
        colorScheme: _colorScheme,
        scaffoldBackgroundColor: _colorScheme.surface,
        textTheme: _textTheme,
        appBarTheme: AppBarTheme(
          backgroundColor: Colors.transparent,
          elevation: 0,
          titleTextStyle: _textTheme.headlineSmall?.copyWith(
            color: Colors.white,
          ),
          iconTheme: const IconThemeData(color: Colors.white),
        ),
        cardTheme: CardThemeData(
          color: _colorScheme.surface,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            side: BorderSide(
              color: Colors.white.withValues(alpha: 0.08),
              width: 1,
            ),
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: _colorScheme.primary,
            foregroundColor: _colorScheme.onPrimary,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            ),
            textStyle: _textTheme.labelLarge,
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white,
            side: BorderSide(
              color: Colors.white.withValues(alpha: 0.2),
              width: 1,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            ),
            textStyle: _textTheme.labelLarge,
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: _colorScheme.primary,
            textStyle: _textTheme.labelLarge,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _colorScheme.surface,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            borderSide: BorderSide(
              color: Colors.white.withValues(alpha: 0.1),
            ),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            borderSide: BorderSide(
              color: Colors.white.withValues(alpha: 0.1),
            ),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            borderSide: BorderSide(
              color: _colorScheme.primary,
              width: 2,
            ),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppConstants.borderRadius),
            borderSide: BorderSide(
              color: _colorScheme.error,
            ),
          ),
          labelStyle: _textTheme.bodyMedium?.copyWith(
            color: Colors.white.withValues(alpha: 0.7),
          ),
          hintStyle: _textTheme.bodyMedium?.copyWith(
            color: Colors.white.withValues(alpha: 0.5),
          ),
        ),
        dividerTheme: DividerThemeData(
          color: Colors.white.withValues(alpha: 0.1),
          thickness: 1,
        ),
        iconTheme: const IconThemeData(
          color: Colors.white,
          size: 24,
        ),
      );

  static BoxDecoration get cardDecoration => BoxDecoration(
        color: _colorScheme.surface,
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.08),
          width: 1,
        ),
      );

  static BoxDecoration surfaceDecoration({double radius = 12}) => BoxDecoration(
        color: _colorScheme.surface,
        borderRadius: BorderRadius.circular(radius),
      );

  static BoxDecoration sheetDecoration({Color color = AppColors.surface, double radius = 20}) => BoxDecoration(
        color: color,
        borderRadius: BorderRadius.vertical(top: Radius.circular(radius)),
      );

  static BoxDecoration get glassDecoration => BoxDecoration(
        color: _colorScheme.surface.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.1),
          width: 1,
        ),
      );

  static BoxShadow get cardShadow => BoxShadow(
        color: Colors.black.withValues(alpha: 0.3),
        blurRadius: 10,
        offset: const Offset(0, 4),
      );

  static BoxShadow get glowShadow => BoxShadow(
        color: _colorScheme.primary.withValues(alpha: 0.3),
        blurRadius: 20,
        spreadRadius: 2,
      );

  static Color getBatteryColor(double percentage) => batteryLevelColor(percentage);

  static Color getGridStatusColor(bool isImporting) {
    return isImporting ? _colorScheme.error : success;
  }

  static Color getPowerColor(String type) {
    switch (type.toLowerCase()) {
      case 'solar':
        return solar;
      case 'battery':
        return battery;
      case 'grid':
        return grid;
      case 'home':
      case 'consumption':
        return Colors.white;
      default:
        return Colors.white;
    }
  }
}
