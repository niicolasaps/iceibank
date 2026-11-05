import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/conta_provider.dart';
import '../providers/lider_provider.dart';
import '../services/api_client.dart';
import 'painel_lider.dart';

/// Tela principal: painel de lideranca + saldo + deposito/saque + transferencia.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final idConta = context.read<AuthProvider>().idConta!;
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<ContaProvider>(
          create: (_) => ContaProvider(api, idConta)..atualizar(),
        ),
        ChangeNotifierProvider<LiderProvider>(
          create: (_) => LiderProvider(api)..iniciar(),
        ),
      ],
      child: const _HomeConteudo(),
    );
  }
}

class _HomeConteudo extends StatefulWidget {
  const _HomeConteudo();

  @override
  State<_HomeConteudo> createState() => _HomeConteudoState();
}

class _HomeConteudoState extends State<_HomeConteudo> {
  final _valorCtrl = TextEditingController();
  final _destinoCtrl = TextEditingController();
  final _valorTransfCtrl = TextEditingController();

  double? _lerValor(String texto) {
    final v = double.tryParse(texto.trim().replaceAll(',', '.'));
    if (v == null || v <= 0) {
      _aviso('Informe um valor valido (maior que zero).');
      return null;
    }
    return v;
  }

  void _aviso(String texto) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(texto)));
  }

  @override
  void dispose() {
    _valorCtrl.dispose();
    _destinoCtrl.dispose();
    _valorTransfCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.read<AuthProvider>();
    final conta = context.watch<ContaProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text('Conta ${auth.idConta}'),
        actions: [
          IconButton(
            tooltip: 'Sair',
            icon: const Icon(Icons.logout),
            onPressed: () => auth.logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: conta.atualizar,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const PainelLider(),
            const SizedBox(height: 16),
            _cartaoSaldo(conta),
            if (conta.erro != null) _caixa(conta.erro!, Colors.red),
            if (conta.sucesso != null) _caixa(conta.sucesso!, Colors.green),
            const SizedBox(height: 8),
            _cartaoDepositoSaque(conta),
            const SizedBox(height: 16),
            _cartaoTransferencia(conta),
          ],
        ),
      ),
    );
  }

  Widget _cartaoSaldo(ContaProvider conta) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(conta.nomeAluno ?? '...', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              conta.saldo == null ? '--' : 'R\$ ${conta.saldo!.toStringAsFixed(2)}',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            if (conta.ocupado) const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator()),
          ],
        ),
      ),
    );
  }

  Widget _cartaoDepositoSaque(ContaProvider conta) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Deposito / Saque', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            TextField(
              controller: _valorCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Valor (R\$)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    onPressed: conta.ocupado
                        ? null
                        : () {
                            final v = _lerValor(_valorCtrl.text);
                            if (v != null) conta.depositar(v).then((_) => _valorCtrl.clear());
                          },
                    child: const Text('Depositar'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton(
                    onPressed: conta.ocupado
                        ? null
                        : () {
                            final v = _lerValor(_valorCtrl.text);
                            if (v != null) conta.sacar(v).then((_) => _valorCtrl.clear());
                          },
                    child: const Text('Sacar'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _cartaoTransferencia(ContaProvider conta) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Transferencia', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            TextField(
              controller: _destinoCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Conta de destino', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _valorTransfCtrl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Valor (R\$)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.tonal(
                onPressed: conta.ocupado
                    ? null
                    : () {
                        final destino = int.tryParse(_destinoCtrl.text.trim());
                        final v = _lerValor(_valorTransfCtrl.text);
                        if (destino == null) {
                          _aviso('Informe o numero da conta de destino.');
                          return;
                        }
                        if (v != null) {
                          conta.transferir(destino, v).then((_) {
                            if (conta.erro == null) {
                              _destinoCtrl.clear();
                              _valorTransfCtrl.clear();
                            }
                          });
                        }
                      },
                child: const Text('Transferir'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _caixa(String texto, MaterialColor cor) {
    return Container(
      margin: const EdgeInsets.only(top: 8),
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

