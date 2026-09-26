/// Tolerant JSON accessors: missing or null keys become defaults instead of
/// throwing, so a partial backend response never crashes a screen.
double asDouble(dynamic v, [double fallback = 0.0]) {
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v) ?? fallback;
  return fallback;
}

double? asDoubleOrNull(dynamic v) => v is num ? v.toDouble() : null;

int asInt(dynamic v, [int fallback = 0]) {
  if (v is int) return v;
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v) ?? fallback;
  return fallback;
}

int? asIntOrNull(dynamic v) => v is num ? v.toInt() : null;

bool asBool(dynamic v, [bool fallback = false]) => v is bool ? v : fallback;

String asString(dynamic v, [String fallback = '']) => v?.toString() ?? fallback;

DateTime? asDateTime(dynamic v) => v is String ? DateTime.tryParse(v) : null;

Map<String, dynamic> asMap(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};

List<Map<String, dynamic>> asMapList(dynamic v) =>
    v is List ? v.whereType<Map>().map((m) => Map<String, dynamic>.from(m)).toList() : const [];
