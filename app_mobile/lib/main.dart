import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';

void main() {
  runApp(const IceiBankApp());
}

class IceiBankApp extends StatelessWidget {
  const IceiBankApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiClient>(create: (_) => ApiClient()),
        ChangeNotifierProvider<AuthProvider>(
          create: (ctx) => AuthProvider(ctx.read<ApiClient>()),
        ),
      ],
      child: MaterialApp(
        title: 'ICEIBank',
        theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
        home: const _Raiz(),
      ),
    );
  }
}

/// Decide entre login e tela principal conforme o estado de autenticacao.
class _Raiz extends StatelessWidget {
  const _Raiz();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    if (auth.carregando) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return auth.estaLogado ? const HomeScreen() : const LoginScreen();
  }
}
