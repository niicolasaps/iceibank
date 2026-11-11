import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: IceiTheme.bgDeep,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
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
        debugShowCheckedModeBanner: false,
        theme: IceiTheme.buildTheme(),
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
      return const Scaffold(
        backgroundColor: IceiTheme.bgDeep,
        body: Center(
          child: CircularProgressIndicator(color: IceiTheme.gold),
        ),
      );
    }
    return auth.estaLogado ? const HomeScreen() : const LoginScreen();
  }
}
