import 'package:flutter/material.dart';
import 'package:flutter_interface/services/api_client.dart';
import 'package:flutter_interface/services/user_api_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _isRegisterMode = false;
  String? _errorMessage;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final username = _usernameController.text.trim();
    final password = _passwordController.text;
    try {
      if (_isRegisterMode) {
        await userApiService.register(username, password);
      }
      // Login updates authState, which swaps this screen for the home screen.
      await userApiService.login(username, password);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _errorMessage = e.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.green.shade800,
              Colors.green.shade600,
              Colors.teal.shade400,
            ],
          ),
        ),
        child: SafeArea(
          top: false,
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Card(
                elevation: 8,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.solar_power_rounded,
                          size: 64,
                          color: Colors.green.shade700,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'VPP Simulator',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.green.shade800,
                              ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _isRegisterMode ? 'Creează un cont' : 'Bine ai revenit',
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                color: Colors.grey.shade600,
                              ),
                        ),
                        const SizedBox(height: 32),
                        TextFormField(
                          controller: _usernameController,
                          autofillHints: const [AutofillHints.username],
                          decoration: InputDecoration(
                            labelText: 'Utilizator',
                            prefixIcon: const Icon(Icons.person_outline),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Introdu numele de utilizator';
                            }
                            if (_isRegisterMode && value.trim().length < 3) {
                              return 'Minim 3 caractere';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: true,
                          autofillHints: const [AutofillHints.password],
                          onFieldSubmitted: (_) => _isLoading ? null : _submit(),
                          decoration: InputDecoration(
                            labelText: 'Parolă',
                            prefixIcon: const Icon(Icons.lock_outline),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Introdu parola';
                            }
                            if (_isRegisterMode && value.length < 6) {
                              return 'Parola trebuie să aibă cel puțin 6 caractere';
                            }
                            return null;
                          },
                        ),
                        if (_errorMessage != null) ...[
                          const SizedBox(height: 16),
                          Text(
                            _errorMessage!,
                            style: TextStyle(color: Colors.red.shade700),
                            textAlign: TextAlign.center,
                          ),
                        ],
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          height: 48,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : _submit,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green.shade700,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: _isLoading
                                ? const SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : Text(_isRegisterMode ? 'Înregistrare' : 'Autentificare'),
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextButton(
                          onPressed: () {
                            setState(() {
                              _isRegisterMode = !_isRegisterMode;
                              _errorMessage = null;
                            });
                          },
                          child: Text(
                            _isRegisterMode ? 'Ai deja cont? Autentifică-te' : 'Nu ai cont? Înregistrează-te',
                          ),
                        ),
                        if (_isRegisterMode) ...[
                          const SizedBox(height: 4),
                          Text(
                            'Contul nou nu are o casă asignată până o alocă administratorul.',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: Colors.grey.shade600,
                                ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
