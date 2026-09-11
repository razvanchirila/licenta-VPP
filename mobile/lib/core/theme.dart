import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'constants.dart';

/// Centralized theme configuration for the VPP Simulator app
class AppTheme {
  // Private constructor to prevent instantiation
  AppTheme._();
  
  // Color scheme
  static const ColorScheme _colorScheme = ColorScheme.dark(
    primary: Color(AppConstants.primaryColorValue),
    secondary: Color(AppConstants.successColorValue),
    surface: Color(AppConstants.surfaceColorValue),
    background: Color(AppConstants.backgroundColorValue),
    error: Color(AppConstants.errorColorValue),
    onPrimary: Colors.white,
    onSecondary: Colors.white,
    onSurface: Colors.white,
    onBackground: Colors.white,
    onError: Colors.white,
  );
  
  // Custom colors
  static const Color warning = Color(AppConstants.warningColorValue);
  static const Color success = Color(AppConstants.successColorValue);
  static const Color solar = Color(0xFFFBBF24);
  static const Color battery = Color(AppConstants.primaryColorValue);
  static const Color grid = Color(AppConstants.errorColorValue);
  
  // Text theme
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
  
  // Main theme
  static ThemeData get theme => ThemeData.dark().copyWith(
    colorScheme: _colorScheme,
    scaffoldBackgroundColor: _colorScheme.background,
    textTheme: _textTheme,
    
    // AppBar theme
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.transparent,
      elevation: 0,
      titleTextStyle: _textTheme.headlineSmall?.copyWith(
        color: Colors.white,
      ),
      iconTheme: const IconThemeData(color: Colors.white),
    ),
    
    // Card theme
    cardTheme: CardThemeData(
      color: _colorScheme.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        side: BorderSide(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
    ),
    
    // Button themes
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
          color: Colors.white.withOpacity(0.2),
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
    
    // Input decoration theme
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: _colorScheme.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        borderSide: BorderSide(
          color: Colors.white.withOpacity(0.1),
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        borderSide: BorderSide(
          color: Colors.white.withOpacity(0.1),
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
        color: Colors.white.withOpacity(0.7),
      ),
      hintStyle: _textTheme.bodyMedium?.copyWith(
        color: Colors.white.withOpacity(0.5),
      ),
    ),
    
    // Divider theme
    dividerTheme: DividerThemeData(
      color: Colors.white.withOpacity(0.1),
      thickness: 1,
    ),
    
    // Icon theme
    iconTheme: const IconThemeData(
      color: Colors.white,
      size: 24,
    ),
  );
  
  // Utility methods for consistent styling
  static BoxDecoration get cardDecoration => BoxDecoration(
    color: _colorScheme.surface,
    borderRadius: BorderRadius.circular(AppConstants.borderRadius),
    border: Border.all(
      color: Colors.white.withOpacity(0.08),
      width: 1,
    ),
  );
  
  static BoxDecoration get glassDecoration => BoxDecoration(
    color: _colorScheme.surface.withOpacity(0.8),
    borderRadius: BorderRadius.circular(AppConstants.borderRadius),
    border: Border.all(
      color: Colors.white.withOpacity(0.1),
      width: 1,
    ),
  );
  
  static BoxShadow get cardShadow => BoxShadow(
    color: Colors.black.withOpacity(0.3),
    blurRadius: 10,
    offset: const Offset(0, 4),
  );
  
  static BoxShadow get glowShadow => BoxShadow(
    color: _colorScheme.primary.withOpacity(0.3),
    blurRadius: 20,
    spreadRadius: 2,
  );
  
  // Color utilities
  static Color getBatteryColor(double percentage) {
    if (percentage >= 70) return success;
    if (percentage >= 30) return warning;
    return _colorScheme.error;
  }
  
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