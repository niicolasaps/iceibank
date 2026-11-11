import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config.dart';
import '../providers/auth_provider.dart';
import '../services/api_client.dart';
import '../theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  final _idCtrl = TextEditingController();
  final _senhaCtrl = TextEditingController();
  int _agenciaSelecionada = 0;
  bool _escolheuManualmente = false;
  bool _entrando = false;
  String? _erro;
  late final AnimationController _floatCtrl;

  @override
  void initState() {
    super.initState();
    _floatCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat(reverse: true);
    _idCtrl.addListener(_atualizarAgenciaPeloId);
  }

  void _atualizarAgenciaPeloId() {
    if (_escolheuManualmente) return;
    final id = int.tryParse(_idCtrl.text.trim());
    if (id != null && id >= 0) {
      final ag = Config.agenciaDaConta(id);
      if (ag != _agenciaSelecionada) setState(() => _agenciaSelecionada = ag);
    }
  }

  Future<void> _entrar() async {
    final id = int.tryParse(_idCtrl.text.trim());
    if (id == null || _senhaCtrl.text.isEmpty) {
      setState(() => _erro = 'Informe o ID da conta e a senha.');
      return;
    }
    setState(() {
      _entrando = true;
      _erro = null;
    });
    try {
      await context.read<AuthProvider>().login(
            id,
            _senhaCtrl.text,
            agenciaIdx: _agenciaSelecionada,
          );
    } on ApiException catch (e) {
      setState(() => _erro = e.mensagem);
    } finally {
      if (mounted) setState(() => _entrando = false);
    }
  }

  @override
  void dispose() {
    _floatCtrl.dispose();
    _idCtrl.dispose();
    _senhaCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final aviso = context.watch<AuthProvider>().mensagemSessao;
    final msgErro = _erro ?? aviso;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: IceiTheme.pageBgGradient),
        child: Stack(
          children: [
            // Brilhos radiais sutis de fundo (como no .login-bg do App.css)
            Positioned(
              top: -80,
              left: -60,
              child: Container(
                width: 260,
                height: 260,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [IceiTheme.gold.withValues(alpha: 0.09), Colors.transparent],
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -100,
              right: -60,
              child: Container(
                width: 280,
                height: 280,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [const Color(0xFF3B82F6).withValues(alpha: 0.08), Colors.transparent],
                  ),
                ),
              ),
            ),
            SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 32),
                      decoration: BoxDecoration(
                        color: const Color(0x09FFFFFF),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: IceiTheme.cardBorder, width: 1),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.6),
                            blurRadius: 60,
                            offset: const Offset(0, 28),
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Logo flutuante + Titulo dourado + Subtitulo + Divisor
                          AnimatedBuilder(
                            animation: _floatCtrl,
                            builder: (context, child) => Transform.translate(
                              offset: Offset(0, -5 * _floatCtrl.value),
                              child: child,
                            ),
                            child: const Text(
                              '🏦',
                              textAlign: TextAlign.center,
                              style: TextStyle(fontSize: 48),
                            ),
                          ),
                          const SizedBox(height: 10),
                          const Center(
                            child: GoldGradientText(
                              'ICEIBank',
                              style: TextStyle(
                                fontSize: 32,
                                fontWeight: FontWeight.w900,
                                letterSpacing: -1,
                                height: 1.05,
                              ),
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'SISTEMA BANCÁRIO DISTRIBUÍDO',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 11,
                              color: Color(0x59F1F5F9),
                              letterSpacing: 1.8,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 14),
                          Center(
                            child: Container(
                              width: 44,
                              height: 2,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(2),
                                gradient: const LinearGradient(
                                  colors: [Colors.transparent, IceiTheme.gold, Colors.transparent],
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 26),

                          // Seletor clicavel de Agencia (igual ao <select> do Login.jsx da web)
                          const FormLabel('Agência'),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
                            decoration: BoxDecoration(
                              color: IceiTheme.inputFill,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: IceiTheme.gold.withValues(alpha: 0.35)),
                            ),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<int>(
                                value: _agenciaSelecionada,
                                isExpanded: true,
                                dropdownColor: const Color(0xFF111F35),
                                borderRadius: BorderRadius.circular(12),
                                icon: const Icon(
                                  Icons.keyboard_arrow_down_rounded,
                                  color: IceiTheme.gold,
                                ),
                                items: List.generate(Config.agencias.length, (i) {
                                  final host = Config.agencias[i].replaceFirst('http://', '');
                                  return DropdownMenuItem<int>(
                                    value: i,
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 7,
                                          height: 7,
                                          decoration: const BoxDecoration(
                                            color: IceiTheme.gold,
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Text(
                                            'Agência $i — :${4046 + i} ($host)',
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              color: IceiTheme.textPrimary,
                                              fontSize: 13.5,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                }),
                                onChanged: (novo) {
                                  if (novo == null) return;
                                  setState(() {
                                    _agenciaSelecionada = novo;
                                    _escolheuManualmente = true;
                                  });
                                },
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // Linha com ID da Conta e Senha (igual ao .form-row da web)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                flex: 5,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const FormLabel('ID da Conta'),
                                    TextField(
                                      controller: _idCtrl,
                                      keyboardType: TextInputType.number,
                                      style: const TextStyle(color: IceiTheme.textPrimary, fontSize: 15),
                                      decoration: const InputDecoration(hintText: 'Ex: 0'),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                flex: 6,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const FormLabel('Senha'),
                                    TextField(
                                      controller: _senhaCtrl,
                                      obscureText: true,
                                      style: const TextStyle(color: IceiTheme.textPrimary, fontSize: 15),
                                      decoration: const InputDecoration(hintText: '••••••••'),
                                      onSubmitted: (_) => _entrar(),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),

                          if (msgErro != null)
                            IceiAlert(
                              texto: msgErro,
                              erro: true,
                              onClose: () => setState(() => _erro = null),
                            ),

                          const SizedBox(height: 20),
                          GradientButton(
                            label: _entrando ? 'Autenticando...' : 'Acessar Conta',
                            emoji: _entrando ? null : '🔐',
                            gradient: IceiTheme.goldBtnGradient,
                            textColor: const Color(0xFF0A1628),
                            glowColor: IceiTheme.gold,
                            loading: _entrando,
                            onPressed: _entrar,
                            verticalPadding: 15,
                          ),

                          const SizedBox(height: 22),
                          RichText(
                            textAlign: TextAlign.center,
                            text: TextSpan(
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: Color(0x45F1F5F9),
                                height: 1.55,
                              ),
                              children: [
                                const TextSpan(text: 'Primeiro acesso? Use '),
                                TextSpan(
                                  text: 'POST /auth/bootstrap',
                                  style: TextStyle(
                                    color: IceiTheme.gold.withValues(alpha: 0.8),
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const TextSpan(text: '\npara criar credenciais via terminal.'),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
