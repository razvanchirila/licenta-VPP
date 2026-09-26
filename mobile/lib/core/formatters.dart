import 'package:intl/intl.dart';

/// `1.5 kW` above 1000 W, otherwise `150 W`.
String formatPowerW(double watts) {
  if (watts >= 1000) {
    return '${(watts / 1000).toStringAsFixed(1)} kW';
  }
  return '${watts.round()} W';
}

/// `1.2 kWh` above one kWh, otherwise `350 Wh`.
String formatEnergyKwh(double kWh) {
  if (kWh >= 1) {
    return '${kWh.toStringAsFixed(1)} kWh';
  }
  return '${(kWh * 1000).toStringAsFixed(0)} Wh';
}

String formatKwh(double kWh, {int decimals = 1}) => '${kWh.toStringAsFixed(decimals)} kWh';

String formatLei(double lei, {int decimals = 2, bool signed = false}) {
  final sign = signed && lei >= 0 ? '+' : '';
  return '$sign${lei.toStringAsFixed(decimals)} lei';
}

String twoDigits(int n) => n.toString().padLeft(2, '0');

String formatSimTime(DateTime? t) => t == null ? '-' : DateFormat('dd/MM HH:mm').format(t);

String formatClock(DateTime t) => '${twoDigits(t.hour)}:${twoDigits(t.minute)}';

String formatDayMonth(DateTime t) => '${twoDigits(t.day)}/${twoDigits(t.month)}';

/// `yyyy-MM-dd`, the date format of the backend query parameters.
String formatApiDate(DateTime d) => DateFormat('yyyy-MM-dd').format(d);
