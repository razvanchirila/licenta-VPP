/// Model for solar production forecast data from forecast.solar API
class SolarForecastData {
  /// Hourly power production in watts (DateTime -> watts)
  final Map<DateTime, double> hourlyWatts;

  /// Daily energy production in watt-hours (date string -> watt-hours)
  final Map<String, double> dailyWattHours;

  SolarForecastData({
    required this.hourlyWatts,
    required this.dailyWattHours,
  });

  /// Parse from forecast.solar API JSON response
  factory SolarForecastData.fromJson(Map<String, dynamic> json) {
    final result = json['result'] as Map<String, dynamic>?;
    if (result == null) {
      return SolarForecastData(hourlyWatts: {}, dailyWattHours: {});
    }

    // Parse hourly watts
    final wattsMap = result['watts'] as Map<String, dynamic>? ?? {};
    final hourlyWatts = <DateTime, double>{};
    wattsMap.forEach((key, value) {
      final dateTime = DateTime.tryParse(key);
      if (dateTime != null) {
        hourlyWatts[dateTime] = (value as num).toDouble();
      }
    });

    // Parse daily watt-hours
    final dailyMap = result['watt_hours_day'] as Map<String, dynamic>? ?? {};
    final dailyWattHours = <String, double>{};
    dailyMap.forEach((key, value) {
      dailyWattHours[key] = (value as num).toDouble();
    });

    return SolarForecastData(
      hourlyWatts: hourlyWatts,
      dailyWattHours: dailyWattHours,
    );
  }

  /// Get today's date string (YYYY-MM-DD)
  String get _todayString {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }

  /// Total estimated production for today in kWh
  double get todayTotalKwh {
    final todayWh = dailyWattHours[_todayString] ?? 0;
    return todayWh / 1000;
  }

  /// Get hourly data for today only
  Map<int, double> get todayHourlyWatts {
    return getHourlyWattsForDate(_todayString);
  }

  /// Get hourly data for a specific date (YYYY-MM-DD format)
  Map<int, double> getHourlyWattsForDate(String dateStr) {
    final result = <int, double>{};
    
    hourlyWatts.forEach((dateTime, watts) {
      final dtStr = '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')}';
      if (dtStr == dateStr) {
        result[dateTime.hour] = watts;
      }
    });
    
    return result;
  }

  /// Get hourly data in kW for a specific date
  Map<int, double> getHourlyKwForDate(String dateStr) {
    return getHourlyWattsForDate(dateStr).map((hour, watts) => MapEntry(hour, watts / 1000));
  }

  /// Get hourly data in kW for today
  Map<int, double> get todayHourlyKw {
    return todayHourlyWatts.map((hour, watts) => MapEntry(hour, watts / 1000));
  }

  /// Get total kWh for a specific date
  double getTotalKwhForDate(String dateStr) {
    return (dailyWattHours[dateStr] ?? 0) / 1000;
  }

  /// Peak production hours for a specific date (top 3 hours)
  List<int> getPeakHoursForDate(String dateStr) {
    final hourlyData = getHourlyWattsForDate(dateStr);
    if (hourlyData.isEmpty) return [];

    final sortedEntries = hourlyData.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return sortedEntries
        .take(3)
        .map((e) => e.key)
        .toList()
      ..sort();
  }

  /// Peak production hours (top 3 hours with highest production)
  List<int> get peakHours {
    return getPeakHoursForDate(_todayString);
  }

  /// Get list of available dates
  List<String> get availableDates {
    return dailyWattHours.keys.toList()..sort();
  }

  /// Maximum hourly production in kW (for chart scaling)
  double get maxHourlyKw {
    if (hourlyWatts.isEmpty) return 0;
    final maxWatts = hourlyWatts.values.reduce((a, b) => a > b ? a : b);
    return maxWatts / 1000;
  }

  /// Get daily totals sorted by date
  List<DailyForecast> get dailyForecasts {
    final forecasts = dailyWattHours.entries
        .map((e) => DailyForecast(
              date: e.key,
              wattHours: e.value,
            ))
        .toList()
      ..sort((a, b) => a.date.compareTo(b.date));
    return forecasts;
  }

  /// Check if we have data
  bool get hasData => hourlyWatts.isNotEmpty || dailyWattHours.isNotEmpty;
}

/// Daily forecast summary
class DailyForecast {
  final String date;
  final double wattHours;

  DailyForecast({
    required this.date,
    required this.wattHours,
  });

  /// Energy in kWh
  double get kWh => wattHours / 1000;

  /// Formatted date (e.g., "Luni, 15 Ian")
  String get formattedDate {
    final parts = date.split('-');
    if (parts.length != 3) return date;
    
    final dateTime = DateTime.tryParse(date);
    if (dateTime == null) return date;

    final weekdays = ['Lun', 'Mar', 'Mie', 'Joi', 'Vin', 'Sâm', 'Dum'];
    final months = ['Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    final weekday = weekdays[dateTime.weekday - 1];
    final day = dateTime.day;
    final month = months[dateTime.month - 1];
    
    return '$weekday, $day $month';
  }

  /// Check if this is today
  bool get isToday {
    final now = DateTime.now();
    final todayStr = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    return date == todayStr;
  }
}
