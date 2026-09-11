import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_interface/screens/powerwall_screen.dart';
import 'package:flutter_interface/screens/login_screen.dart';
import 'package:flutter_interface/core/theme.dart';
import 'package:flutter_interface/core/constants.dart';
import 'package:flutter_interface/core/utils.dart';
import 'package:flutter_interface/services/service_manager.dart';
import 'package:flutter_interface/services/user_api_service.dart';
import 'package:flutter_interface/widgets/ios_status_bar.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize app in production-ready way
  await _initializeApp();
  
  runApp(const VppSimulatorApp());
}

/// Initialize app services and configuration
Future<void> _initializeApp() async {
  try {
    AppUtils.debugLog('Starting app initialization...', tag: 'Main');
    
    // Initialize service manager
    await serviceManager.initialize();
    
    // Initialize user API service (load saved token)
    await userApiService.init();
    
    AppUtils.debugLog('App initialization completed', tag: 'Main');
  } catch (e, stackTrace) {
    AppUtils.debugLogError('App initialization failed', error: e, stackTrace: stackTrace);
    
    // In production, you might want to show an error screen or retry
    if (EnvironmentConfig.isProduction) {
      // Handle initialization failure gracefully
      rethrow;
    }
  }
}

/// Main application widget
class VppSimulatorApp extends StatelessWidget {
  const VppSimulatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Ascunde status bar-ul real al sistemului
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    
    return MaterialApp(
      title: 'VPP Simulator',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const AuthWrapper(),
      
      // Production-ready configuration
      builder: (context, child) {
        // Înfășoară cu iOS Status Bar simulat
        return IosStatusBar(
          backgroundColor: const Color(0xFF0A0A0A),
          child: _AppWrapper(child: child),
        );
      },
    );
  }
}

/// Wrapper that handles authentication state
class AuthWrapper extends StatefulWidget {
  const AuthWrapper({super.key});

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  bool _isLoggedIn = false;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  void _checkAuth() {
    setState(() {
      _isLoggedIn = userApiService.isLoggedIn;
    });
  }

  void _onLoginSuccess() {
    setState(() {
      _isLoggedIn = true;
    });
  }

  void _onLogout() {
    userApiService.logout();
    setState(() {
      _isLoggedIn = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoggedIn) {
      return PowerwallScreen(onLogout: _onLogout);
    }
    return LoginScreen(onLoginSuccess: _onLoginSuccess);
  }
}

/// App wrapper for error handling and global features
class _AppWrapper extends StatelessWidget {
  final Widget? child;

  const _AppWrapper({this.child});

  @override
  Widget build(BuildContext context) {
    return MediaQuery(
      // Ensure text scaling doesn't break the UI
      data: MediaQuery.of(context).copyWith(
        textScaleFactor: MediaQuery.of(context).textScaleFactor.clamp(0.8, 1.2),
      ),
      child: child ?? const SizedBox.shrink(),
    );
  }
}