import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/screens/login_screen.dart';
import 'package:flutter_interface/screens/powerwall_screen.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/ios_status_bar.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await authState.load();
  // When the session is cleared (logout or 401) drop any pushed screens so
  // the login screen shown by AuthGate is actually visible.
  authState.addListener(() {
    if (!authState.isLoggedIn) {
      navigatorKey.currentState?.popUntil((route) => route.isFirst);
    }
  });
  runApp(const VppSimulatorApp());
}

class VppSimulatorApp extends StatelessWidget {
  const VppSimulatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);

    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'VPP Simulator',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const AuthGate(),
      builder: (context, child) {
        return FakeIosStatusBar(
          backgroundColor: AppColors.deepBackground,
          child: MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: TextScaler.linear(
                MediaQuery.of(context).textScaler.scale(1.0).clamp(0.8, 1.2),
              ),
            ),
            child: child ?? const SizedBox.shrink(),
          ),
        );
      },
    );
  }
}

/// A 401 anywhere clears the token, which brings the user back here.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: authState,
      builder: (context, _) {
        if (authState.isLoggedIn) {
          return const PowerwallScreen();
        }
        return const LoginScreen();
      },
    );
  }
}
