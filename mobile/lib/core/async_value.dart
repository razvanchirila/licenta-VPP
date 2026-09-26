import 'package:flutter/widgets.dart';
import 'package:flutter_interface/services/api_client.dart';

/// `data` may be kept while reloading (`AsyncValue.loading(previous: ...)`)
/// so the screen can show stale values instead of a blank page.
class AsyncValue<T> {
  final T? data;
  final String? error;
  final bool isLoading;

  const AsyncValue.loading({T? previous})
      : data = previous,
        error = null,
        isLoading = true;

  const AsyncValue.data(T this.data)
      : error = null,
        isLoading = false;

  const AsyncValue.error(String this.error, {T? previous})
      : data = previous,
        isLoading = false;

  bool get hasError => error != null;
  bool get hasData => data != null;

  /// Picks one of the three branches; the error branch wins over stale data.
  R when<R>({
    required R Function() loading,
    required R Function(String message) error,
    required R Function(T data) data,
  }) {
    if (isLoading) return loading();
    if (this.error != null) return error(this.error!);
    return data(this.data as T);
  }
}

/// Ignores results of superseded requests: a slow older response must not overwrite a newer one.
mixin AsyncLoader<T, W extends StatefulWidget> on State<W> {
  AsyncValue<T> state = const AsyncValue.loading();
  int _requestId = 0;

  Future<T?> load(Future<T> Function() fetch, {bool keepPrevious = false}) async {
    final id = ++_requestId;
    setState(() => state = AsyncValue.loading(previous: keepPrevious ? state.data : null));
    try {
      final data = await fetch();
      if (!mounted || id != _requestId) return null;
      setState(() => state = AsyncValue.data(data));
      return data;
    } on ApiException catch (e) {
      if (!mounted || id != _requestId) return null;
      setState(() => state = AsyncValue.error(e.message, previous: keepPrevious ? state.data : null));
      return null;
    }
  }

  void updateData(T data) => setState(() => state = AsyncValue.data(data));
}
