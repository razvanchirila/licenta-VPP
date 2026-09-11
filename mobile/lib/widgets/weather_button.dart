import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_interface/models/weather_data.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/core/utils.dart';

/// Weather button widget displaying current weather conditions
class WeatherButton extends StatelessWidget {
  final WeatherData weatherData;
  final VoidCallback? onTap;
  final bool isCompact;

  const WeatherButton({
    super.key,
    required this.weatherData,
    this.onTap,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactButton(context);
    }
    return _buildFullButton(context);
  }

  Widget _buildFullButton(BuildContext context) {
    return Semantics(
      label: 'Vremea curentă: ${weatherData.description}, ${weatherData.temperature.celsius}',
      hint: 'Apasă pentru detalii despre vreme',
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: AppConstants.shortAnimation,
          padding: EdgeInsets.symmetric(
            horizontal: AppConstants.spacingM,
            vertical: AppConstants.spacingS,
          ),
          decoration: AppTheme.glassDecoration.copyWith(
            boxShadow: [AppTheme.cardShadow],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Weather icon with animation
              AnimatedSwitcher(
                duration: AppConstants.mediumAnimation,
                child: Icon(
                  weatherData.icon,
                  key: ValueKey(weatherData.condition),
                  color: _getWeatherColor(),
                  size: 24,
                ),
              ),
              SizedBox(width: AppConstants.spacingS),
              // Temperature and description
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    weatherData.temperature.celsius,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.white,
                    ),
                  ),
                  Text(
                    weatherData.description,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.white70,
                    ),
                  ),
                ],
              ),

            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCompactButton(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: AppConstants.spacingS,
          vertical: AppConstants.spacingXS,
        ),
        decoration: AppTheme.cardDecoration,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              weatherData.icon,
              color: _getWeatherColor(),
              size: 16,
            ),
            SizedBox(width: AppConstants.spacingXS),
            Text(
              weatherData.temperature.celsius,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getWeatherColor() {
    switch (weatherData.condition) {
      case WeatherCondition.sunny:
        return const Color(0xFFFFA500); // Orange
      case WeatherCondition.partlyCloudy:
        return const Color(0xFFFFD700); // Gold
      case WeatherCondition.cloudy:
        return const Color(0xFF87CEEB); // Sky blue
      case WeatherCondition.rainy:
        return const Color(0xFF4682B4); // Steel blue
      case WeatherCondition.stormy:
        return const Color(0xFF483D8B); // Dark slate blue
      case WeatherCondition.foggy:
        return const Color(0xFF708090); // Slate gray
      case WeatherCondition.snow:
        return const Color(0xFFE0E0E0); // Light gray
      case WeatherCondition.unknown:
        return Colors.white70;
    }
  }
}