import 'dart:math' as math;

import 'package:intl/intl.dart';

class EnergyPeriod {
  EnergyPeriod._();

  static const String day = 'day';
  static const String week = 'week';
  static const String month = 'month';

  /// For months the day of month is clamped so 31 Jan -> 28 Feb instead of overflowing.
  static DateTime shift(DateTime base, String period, int direction) {
    switch (period) {
      case day:
        return base.add(Duration(days: direction));
      case week:
        return base.add(Duration(days: direction * 7));
      case month:
        final firstOfTarget = DateTime(base.year, base.month + direction, 1);
        final lastDay = DateTime(firstOfTarget.year, firstOfTarget.month + 1, 0).day;
        return DateTime(firstOfTarget.year, firstOfTarget.month, math.min(base.day, lastDay));
      default:
        return base;
    }
  }

  static String label(DateTime? date, String period) {
    if (date == null) return 'Ziua simulată';
    switch (period) {
      case week:
        final weekStart = date.subtract(Duration(days: date.weekday - 1));
        final weekEnd = weekStart.add(const Duration(days: 6));
        return '${DateFormat('dd/MM').format(weekStart)} - ${DateFormat('dd/MM').format(weekEnd)}';
      case month:
        return DateFormat('MM/yyyy').format(date);
      default:
        return DateFormat('dd/MM/yyyy').format(date);
    }
  }

  static String axisLabel(DateTime time, String period) {
    switch (period) {
      case week:
        return DateFormat('E').format(time);
      case month:
        return DateFormat('dd').format(time);
      default:
        return DateFormat('HH:mm').format(time);
    }
  }

  static String adjective(String period) {
    switch (period) {
      case week:
        return 'săptămânală';
      case month:
        return 'lunară';
      default:
        return 'zilnică';
    }
  }
}
