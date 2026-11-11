import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/conta_provider.dart';
import '../providers/lider_provider.dart';
import '../services/api_client.dart';
import '../services/banco_local.dart';
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
          create: (_) => ContaProvider(api, idConta), // carrega cache, atualiza e sincroniza sozinho
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
            if (conta.offline) _bannerOffline(conta),
            _cartaoSaldo(conta),
            if (conta.erro != null) _caixa(conta.erro!, Colors.red),
            if (conta.sucesso != null) _caixa(conta.sucesso!, Colors.green),
            if (conta.pendentes.isNotEmpty) ...[
              const SizedBox(height: 8),
              _cartaoPendentes(conta),
            ],
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
    final provisorio = conta.saldoProvisorio;
    final qtd = conta.quantidadePendentes;
    final temPendente = qtd > 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(conta.nomeAluno ?? '...', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              provisorio == null ? '--' : _reais(provisorio),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: temPendente ? Colors.orange.shade800 : null,
                  ),
            ),
            if (temPendente) ...[
              const SizedBox(height: 6),
              Row(
                children: [
                  Icon(Icons.schedule, size: 18, color: Colors.orange.shade800),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Saldo provisorio: $qtd operacao(oes) pendente(s) de sincronizacao',
                      style: TextStyle(color: Colors.orange.shade800, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
              if (conta.saldoConfirmado != null)
                Text('Saldo confirmado pela agencia: ${_reais(conta.saldoConfirmado!)}'),
            ],
            if (conta.offline && conta.atualizadoEm != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text('Ultimo dado conhecido: ${_dataHora(conta.atualizadoEm!)}',
                    style: Theme.of(context).textTheme.bodySmall),
              ),
            if (conta.ocupado || conta.sincronizando)
              const Padding(padding: EdgeInsets.only(top: 8), child: LinearProgressIndicator()),
          ],
        ),
      ),
    );
  }

  Widget _bannerOffline(ContaProvider conta) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blueGrey.withValues(alpha: 0.15),
        border: Border.all(color: Colors.blueGrey),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Row(
        children: [
          Icon(Icons.cloud_off, color: Colors.blueGrey),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Sem conexao com a agencia. Mostrando o ultimo saldo salvo. Depositos e saques ficam '
              'PENDENTES e serao sincronizados automaticamente quando a conexao voltar.',
            ),
          ),
        ],
      ),
    );
  }

  Widget _cartaoPendentes(ContaProvider conta) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Operacoes feitas offline', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            for (final op in conta.pendentes) _itemPendente(conta, op),
          ],
        ),
      ),
    );
  }

  Widget _itemPendente(ContaProvider conta, OperacaoPendente op) {
    final nome = op.tipo == 'DEPOSITO' ? 'Deposito' : 'Saque';
    final descricao = '$nome de ${_reais(op.valor)}';

    if (op.status == StatusPendente.pendente) {
      return ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(Icons.schedule, color: Colors.orange.shade800),
        title: Text(descricao),
        subtitle: Text('Pendente de sincronizacao - feita as ${_hora(op.criadoEm)}'),
      );
    }

    final conflito = op.status == StatusPendente.conflito;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.withValues(alpha: 0.08),
        border: Border.all(color: Colors.red),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(conflito ? Icons.sync_problem : Icons.block, color: Colors.red),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${conflito ? 'CONFLITO' : 'RECUSADA'}: $descricao',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.red),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (op.mensagem != null) Text(op.mensagem!),
          if (op.saldoReal != null) ...[
            const SizedBox(height: 4),
            Text('Saldo real atual na agencia: ${_reais(op.saldoReal!)}',
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 4),
          Text(
            conflito
                ? 'A operacao nao foi aplicada. As demais pendentes aguardam sua decisao.'
                : 'A agencia recusou a operacao. As demais pendentes aguardam sua decisao.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              if (conflito)
                Expanded(
                  child: FilledButton(
                    onPressed: conta.ocupado || conta.sincronizando ? null : () => conta.aplicarMesmoAssim(op),
                    child: const Text('Aplicar mesmo assim'),
                  ),
                ),
              if (conflito) const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: conta.ocupado || conta.sincronizando ? null : () => conta.descartar(op),
                  child: const Text('Descartar'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _reais(double v) => 'R\$ ${v.toStringAsFixed(2)}';

  String _dois(int n) => n.toString().padLeft(2, '0');

  String _hora(DateTime d) => '${_dois(d.hour)}:${_dois(d.minute)}:${_dois(d.second)}';

  String _dataHora(DateTime d) => '${_dois(d.day)}/${_dois(d.month)} ${_hora(d)}';

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

