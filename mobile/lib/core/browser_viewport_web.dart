import 'dart:js_interop';
import 'dart:js_interop_unsafe';

JSAny? _call(String name) {
  final fn = globalContext.getProperty<JSAny?>(name.toJS);
  if (fn == null || !fn.isA<JSFunction>()) return null;
  return (fn as JSFunction).callAsFunction();
}

/// [top, right, bottom, left] in CSS pixels, from env(safe-area-inset-*) measured in index.html.
List<double> safeAreaInsets() {
  final result = _call('vppSafeArea');
  if (result == null || !result.isA<JSArray>()) return const [0, 0, 0, 0];
  final values = (result as JSArray<JSNumber>).toDart.map((n) => n.toDartDouble).toList();
  return values.length == 4 ? values : const [0, 0, 0, 0];
}

bool isStandalone() {
  final result = _call('vppStandalone');
  return result != null && result.isA<JSBoolean>() && (result as JSBoolean).toDart;
}
