class ForecastLabels {
  ForecastLabels._();

  static const List<String> _weekdays = ['Lun', 'Mar', 'Mie', 'Joi', 'Vin', 'Sâm', 'Dum'];

  static String ymd(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  static String dayLabel(String dateStr, DateTime now) {
    if (dateStr == ymd(now)) return 'Azi';
    if (dateStr == ymd(now.add(const Duration(days: 1)))) return 'Mâine';

    final dt = DateTime.tryParse(dateStr);
    if (dt == null) return dateStr;
    return '${_weekdays[dt.weekday - 1]} ${dt.day}';
  }

  static String timeSinceUpdate(DateTime? timestamp, DateTime now) {
    if (timestamp == null) return '';
    final diff = now.difference(timestamp);
    if (diff.inMinutes < 1) return 'Actualizat acum';
    if (diff.inMinutes < 60) return 'Actualizat acum ${diff.inMinutes} min';
    if (diff.inHours < 24) return 'Actualizat acum ${diff.inHours} ore';
    return 'Actualizat acum ${diff.inDays} zile';
  }

  static String peakHoursText(List<int> hours) => hours.map((h) => '${h.toString().padLeft(2, '0')}:00').join(', ');
}
