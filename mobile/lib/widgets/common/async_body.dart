import 'package:flutter/material.dart';
import 'package:flutter_interface/core/async_value.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/widgets/error_state.dart';

class AsyncBody<T> extends StatelessWidget {
  final AsyncValue<T> value;
  final VoidCallback onRetry;
  final Widget Function(T data) builder;
  final Color accent;

  const AsyncBody({
    super.key,
    required this.value,
    required this.onRetry,
    required this.builder,
    this.accent = AppColors.green,
  });

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => Center(child: CircularProgressIndicator(color: accent)),
      error: (message) => ErrorState(message: message, onRetry: onRetry, accent: accent),
      data: builder,
    );
  }
}
