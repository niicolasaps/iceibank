import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../services/api_client.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _idCtrl = TextEditingController();
  final _senhaCtrl = TextEditingController();
  bool _entrando = false;
  String? _erro;

  Future<void> _entrar() async {
    final id = int.tryParse(_idCtrl.text.trim());
    if (id == null || _senhaCtrl.text.isEmpty) {
      setState(() => _erro = 'Informe o numero da conta e a senha.');
      return;
    }
    setState(() {
      _entrando = true;
      _erro = null;
    });
    try {
      await context.read<AuthProvider>().login(id, _senhaCtrl.text);
    } on ApiException catch (e) {
      setState(() => _erro = e.mensagem);
    } finally {
      if (mounted) setState(() => _entrando = false);
    }
  }

  @override
  void dispose() {
    _idCtrl.dispose();
    _senhaCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final aviso = context.watch<AuthProvider>().mensagemSessao;
    return Scaffold(
      appBar: AppBar(title: const Text('ICEIBank')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: ListView(
          children: [
            const SizedBox(height: 24),
            const Text('Entrar', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
            const SizedBox(height: 24),
            if (aviso != null) _Mensagem(texto: aviso, erro: true),
            TextField(
              controller: _idCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Numero da conta', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _senhaCtrl,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Senha', border: OutlineInputBorder()),
              onSubmitted: (_) => _entrar(),
            ),
            const SizedBox(height: 16),
            if (_erro != null) _Mensagem(texto: _erro!, erro: true),
            FilledButton(
              onPressed: _entrando ? null : _entrar,
              child: _entrando
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Entrar'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Mensagem extends StatelessWidget {
  final String texto;
  final bool erro;
  const _Mensagem({required this.texto, required this.erro});

  @override
  Widget build(BuildContext context) {
    final cor = erro ? Colors.red : Colors.green;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: cor.withValues(alpha: 0.1),
        border: Border.all(color: cor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(texto, style: TextStyle(color: cor.shade800)),
    );
  }
}

