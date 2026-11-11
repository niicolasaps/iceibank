import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../config.dart';
import '../providers/auth_provider.dart';
import '../providers/conta_provider.dart';
import '../providers/lider_provider.dart';
import '../services/api_client.dart';
import '../services/banco_local.dart';
import '../theme.dart';
import 'painel_lider.dart';

/// Tela principal com o mesmo visual Dark Navy & Gold do frontend web (`App.jsx` + `App.css`).
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final idConta = context.read<AuthProvider>().idConta!;
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<ContaProvider>(
          create: (_) => ContaProvider(api, idConta),
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
      _aviso('Informe um valor válido (maior que zero).');
      return null;
    }
    return v;
  }

  void _aviso(String texto) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          backgroundColor: IceiTheme.heroStart,
          content: Text(texto, style: const TextStyle(color: IceiTheme.textPrimary)),
        ),
      );
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
    final agConta = auth.agenciaAtiva ?? Config.agenciaDaConta(auth.idConta!);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: IceiTheme.pageBgGradient),
        child: SafeArea(
          child: Column(
            children: [
              _topbar(auth, conta, agConta),
              Expanded(
                child: RefreshIndicator(
                  color: IceiTheme.gold,
                  backgroundColor: IceiTheme.heroStart,
                  onRefresh: conta.atualizar,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
                    children: [
                      const PainelLider(),
                      const SizedBox(height: 14),
                      if (conta.offline) _bannerOffline(conta),
                      _balanceHero(conta, auth.idConta!, agConta),
                      if (conta.erro != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: IceiAlert(texto: conta.erro!, erro: true),
                        ),
                      if (conta.sucesso != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: IceiAlert(texto: conta.sucesso!, erro: false),
                        ),
                      if (conta.pendentes.isNotEmpty) ...[
                        _cartaoPendentes(conta),
                        const SizedBox(height: 14),
                      ],
                      _cartaoDepositoSaque(conta),
                      const SizedBox(height: 14),
                      _cartaoTransferencia(conta, auth.idConta!),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Topbar identica ao `.topbar` + `.sidebar-brand` do frontend web.
  Widget _topbar(AuthProvider auth, ContaProvider conta, int agConta) {
    final online = !conta.offline;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Color(0xCC080F1A),
        border: Border(bottom: BorderSide(color: IceiTheme.cardBorder, width: 1)),
      ),
      child: Row(
        children: [
          const Text('🏦', style: TextStyle(fontSize: 24)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const GoldGradientText(
                      'ICEIBank',
                      style: TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: IceiTheme.gold.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: IceiTheme.gold.withValues(alpha: 0.25)),
                      ),
                      child: Text(
                        'Conta #${auth.idConta}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: IceiTheme.gold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: online ? IceiTheme.emerald : IceiTheme.amber,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        online
                            ? 'Agência $agConta online (:${4046 + agConta})'
                            : 'Modo Offline · cache local ativo',
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 11.5,
                          color: online ? IceiTheme.textMuted : IceiTheme.amberLight,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Atualizar',
            onPressed: conta.ocupado || conta.sincronizando ? null : conta.atualizar,
            icon: const Icon(Icons.refresh_rounded, color: IceiTheme.gold, size: 21),
          ),
          InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: auth.logout,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(
                color: IceiTheme.danger.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: IceiTheme.danger.withValues(alpha: 0.28)),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('🚪', style: TextStyle(fontSize: 12)),
                  SizedBox(width: 4),
                  Text(
                    'Sair',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: IceiTheme.dangerLight,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Cartao Hero do saldo identico ao `.balance-hero` do ConsultaSaldo.jsx.
  Widget _balanceHero(ContaProvider conta, int idConta, int agConta) {
    final provisorio = conta.saldoProvisorio;
    final qtd = conta.quantidadePendentes;
    final temPendente = qtd > 0;
    final partes = provisorio == null ? ['--', '00'] : _formatarPartes(provisorio);
    final vetorStr =
        conta.vetorConhecido == null ? '[?, ?, ?]' : '[${conta.vetorConhecido!.join(', ')}]';

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        gradient: IceiTheme.heroGradient,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: temPendente
              ? IceiTheme.amber.withValues(alpha: 0.55)
              : IceiTheme.gold.withValues(alpha: 0.25),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Stack(
        children: [
          // Brilho dourado radial no canto superior direito (como .balance-hero::after)
          Positioned(
            top: -50,
            right: -40,
            child: IgnorePointer(
              child: Container(
                width: 190,
                height: 190,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [IceiTheme.gold.withValues(alpha: 0.14), Colors.transparent],
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(temPendente ? '⏳' : '💰', style: const TextStyle(fontSize: 14)),
                    const SizedBox(width: 6),
                    Text(
                      temPendente ? 'SALDO PROVISÓRIO (UI OTIMISTA)' : 'SALDO DISPONÍVEL',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.5,
                        color: temPendente ? IceiTheme.amberLight : IceiTheme.gold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                RichText(
                  text: TextSpan(
                    children: [
                      TextSpan(
                        text: 'R\$ ',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                          color: IceiTheme.textPrimary.withValues(alpha: 0.65),
                        ),
                      ),
                      TextSpan(
                        text: '${partes[0]},${partes[1]}',
                        style: TextStyle(
                          fontSize: 38,
                          fontWeight: FontWeight.w900,
                          letterSpacing: -1.5,
                          color: temPendente ? IceiTheme.amberLight : IceiTheme.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 6),
                RichText(
                  text: TextSpan(
                    style: const TextStyle(fontSize: 13, color: IceiTheme.textSubtle),
                    children: [
                      TextSpan(
                        text: conta.nomeAluno ?? 'Titular #$idConta',
                        style: const TextStyle(
                          color: Color(0xCCF1F5F9),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const TextSpan(text: '  ·  Conta '),
                      TextSpan(
                        text: '#$idConta',
                        style: const TextStyle(
                          color: Color(0xCCF1F5F9),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      TextSpan(text: '  ·  Ag. $agConta'),
                    ],
                  ),
                ),

                if (temPendente) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                    decoration: BoxDecoration(
                      color: IceiTheme.amber.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: IceiTheme.amber.withValues(alpha: 0.4)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.schedule_rounded, size: 16, color: IceiTheme.amberLight),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                '$qtd operação(ões) pendente(s) de sincronização',
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w700,
                                  color: IceiTheme.amberLight,
                                ),
                              ),
                            ),
                          ],
                        ),
                        if (conta.saldoConfirmado != null) ...[
                          const SizedBox(height: 3),
                          Text(
                            'Saldo confirmado pela agência: ${_reais(conta.saldoConfirmado!)}',
                            style: const TextStyle(fontSize: 12, color: IceiTheme.textPrimary),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 16),
                Row(
                  children: [
                    _metaCol(
                      label: 'STATUS',
                      value: conta.offline ? '● Offline (Cache)' : '● Ativa',
                      valueColor: conta.offline ? IceiTheme.amberLight : IceiTheme.emerald,
                    ),
                    const SizedBox(width: 22),
                    _metaCol(
                      label: 'VETOR CONHECIDO',
                      value: vetorStr,
                      valueColor: IceiTheme.gold,
                    ),
                    if (conta.atualizadoEm != null) ...[
                      const SizedBox(width: 22),
                      _metaCol(
                        label: 'ATUALIZADO',
                        value: _hora(conta.atualizadoEm!),
                        valueColor: const Color(0xCCF1F5F9),
                      ),
                    ],
                  ],
                ),

                if (conta.ocupado || conta.sincronizando)
                  const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: LinearProgressIndicator(
                      color: IceiTheme.gold,
                      backgroundColor: Color(0x22FFFFFF),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _metaCol({required String label, required String value, required Color valueColor}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.0,
            color: IceiTheme.textSubtle,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: valueColor,
          ),
        ),
      ],
    );
  }

  Widget _bannerOffline(ContaProvider conta) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: IceiTheme.amber.withValues(alpha: 0.12),
        border: Border.all(color: IceiTheme.amber.withValues(alpha: 0.45)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.cloud_off_rounded, color: IceiTheme.amberLight, size: 22),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Modo Offline-First Ativo',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 13.5,
                    color: IceiTheme.amberLight,
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  'Sem conexão com a agência. Exibindo o último dado salvo no SQLite. '
                  'Depósitos e saques entram na fila local e sincronizam sozinhos ao reconectar.',
                  style: TextStyle(fontSize: 12, color: IceiTheme.textPrimary, height: 1.35),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _cartaoPendentes(ContaProvider conta) {
    return GlassCard(
      borderColor: conta.filaBloqueada
          ? IceiTheme.danger.withValues(alpha: 0.45)
          : IceiTheme.amber.withValues(alpha: 0.35),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(conta.filaBloqueada ? '⚠️' : '📥', style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Fila de Operações Offline',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    color: IceiTheme.textPrimary,
                  ),
                ),
              ),
              if (conta.sincronizando)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: IceiTheme.gold),
                ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Sincronizadas em ordem FIFO com verificação do Relógio Vetorial.',
            style: TextStyle(fontSize: 12.5, color: IceiTheme.textSubtle),
          ),
          const SizedBox(height: 12),
          for (final op in conta.pendentes) _itemPendente(conta, op),
        ],
      ),
    );
  }

  Widget _itemPendente(ContaProvider conta, OperacaoPendente op) {
    final nome = op.tipo == 'DEPOSITO' ? 'Depósito' : 'Saque';
    final emoji = op.tipo == 'DEPOSITO' ? '💰' : '💸';
    final descricao = '$emoji $nome de ${_reais(op.valor)}';

    if (op.status == StatusPendente.pendente) {
      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
        decoration: BoxDecoration(
          color: IceiTheme.amber.withValues(alpha: 0.09),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: IceiTheme.amber.withValues(alpha: 0.32)),
        ),
        child: Row(
          children: [
            const Icon(Icons.schedule_rounded, color: IceiTheme.amberLight, size: 22),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    descricao,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                      color: IceiTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Pendente · vetor [${op.vetorConhecido.join(', ')}] · ${_hora(op.criadoEm)}',
                    style: const TextStyle(fontSize: 11.5, color: IceiTheme.amberLight),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final conflito = op.status == StatusPendente.conflito;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: IceiTheme.danger.withValues(alpha: 0.11),
        border: Border.all(color: IceiTheme.danger.withValues(alpha: 0.5)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                conflito ? Icons.sync_problem_rounded : Icons.block_rounded,
                color: IceiTheme.dangerLight,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${conflito ? 'CONFLITO (HTTP 409)' : 'RECUSADA'}: $descricao',
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                    color: IceiTheme.dangerLight,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          if (op.mensagem != null)
            Text(
              op.mensagem!,
              style: const TextStyle(fontSize: 12.5, color: IceiTheme.textPrimary, height: 1.35),
            ),
          if (op.saldoReal != null) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Saldo real atual na agência: ${_reais(op.saldoReal!)}',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 12.5,
                  color: IceiTheme.goldBright,
                ),
              ),
            ),
          ],
          const SizedBox(height: 6),
          Text(
            conflito
                ? 'A operação não foi aplicada. As demais pendentes aguardam sua decisão:'
                : 'A agência recusou a operação. As demais pendentes aguardam sua decisão:',
            style: const TextStyle(fontSize: 11.5, color: IceiTheme.textMuted),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              if (conflito) ...[
                Expanded(
                  child: GradientButton(
                    label: 'Aplicar mesmo assim',
                    emoji: '✅',
                    gradient: IceiTheme.goldBtnGradient,
                    textColor: const Color(0xFF0A1628),
                    glowColor: IceiTheme.gold,
                    verticalPadding: 11,
                    onPressed: conta.ocupado || conta.sincronizando
                        ? null
                        : () => conta.aplicarMesmoAssim(op),
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: IceiTheme.dangerLight,
                    side: BorderSide(color: IceiTheme.danger.withValues(alpha: 0.45)),
                    padding: const EdgeInsets.symmetric(vertical: 11),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed:
                      conta.ocupado || conta.sincronizando ? null : () => conta.descartar(op),
                  child: const Text(
                    'Descartar',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// Card de Deposito e Saque com os botoes `.btn-green` e `.btn-red` identicos ao web.
  Widget _cartaoDepositoSaque(ContaProvider conta) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Text('💰', style: TextStyle(fontSize: 19)),
              SizedBox(width: 8),
              Text(
                'Depositar ou Sacar',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: IceiTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Operações funcionam online e também em modo offline (entram na fila local).',
            style: TextStyle(fontSize: 12.5, color: IceiTheme.textSubtle),
          ),
          const SizedBox(height: 16),
          const FormLabel('Valor da Operação (R\$)'),
          TextField(
            controller: _valorCtrl,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(color: IceiTheme.textPrimary, fontSize: 15),
            decoration: const InputDecoration(hintText: '0,00'),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: GradientButton(
                  label: 'Depositar',
                  emoji: '💰',
                  gradient: IceiTheme.greenBtnGradient,
                  glowColor: IceiTheme.greenStart,
                  onPressed: conta.ocupado
                      ? null
                      : () {
                          final v = _lerValor(_valorCtrl.text);
                          if (v != null) conta.depositar(v).then((_) => _valorCtrl.clear());
                        },
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: GradientButton(
                  label: 'Sacar',
                  emoji: '💸',
                  gradient: IceiTheme.redBtnGradient,
                  glowColor: IceiTheme.redStart,
                  onPressed: conta.ocupado
                      ? null
                      : () {
                          final v = _lerValor(_valorCtrl.text);
                          if (v != null) conta.sacar(v).then((_) => _valorCtrl.clear());
                        },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// Card de Transferencia com `.info-box` e `.btn-purple` identicos ao Transferencia.jsx.
  Widget _cartaoTransferencia(ContaProvider conta, int idOrigem) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Text('🔄', style: TextStyle(fontSize: 19)),
              SizedBox(width: 8),
              Text(
                'Transferência',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: IceiTheme.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Transfira entre contas da mesma agência ou de agências diferentes (via RabbitMQ).',
            style: TextStyle(fontSize: 12.5, color: IceiTheme.textSubtle),
          ),
          const SizedBox(height: 14),
          // Info box roxa identica ao .info-box do Transferencia.jsx
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
            decoration: BoxDecoration(
              color: IceiTheme.purpleStart.withValues(alpha: 0.09),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: IceiTheme.purpleStart.withValues(alpha: 0.25)),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('ℹ️', style: TextStyle(fontSize: 14)),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Particionamento automático por ID: Conta 0, 3, 6 → Ag. 0  ·  '
                    'Conta 1, 4, 7 → Ag. 1  ·  Conta 2, 5, 8 → Ag. 2',
                    style: TextStyle(
                      fontSize: 12,
                      color: IceiTheme.purpleLight,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const FormLabel('Conta Destino'),
                    TextField(
                      controller: _destinoCtrl,
                      keyboardType: TextInputType.number,
                      style: const TextStyle(color: IceiTheme.textPrimary, fontSize: 15),
                      decoration: const InputDecoration(hintText: 'Ex: 1'),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const FormLabel('Valor (R\$)'),
                    TextField(
                      controller: _valorTransfCtrl,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: IceiTheme.textPrimary, fontSize: 15),
                      decoration: const InputDecoration(hintText: '0,00'),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          GradientButton(
            label: 'Confirmar Transferência',
            emoji: '🔄',
            gradient: IceiTheme.purpleBtnGradient,
            glowColor: IceiTheme.purpleStart,
            onPressed: conta.ocupado
                ? null
                : () {
                    final destino = int.tryParse(_destinoCtrl.text.trim());
                    final v = _lerValor(_valorTransfCtrl.text);
                    if (destino == null) {
                      _aviso('Informe o ID da conta de destino.');
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
          ),
        ],
      ),
    );
  }

  List<String> _formatarPartes(double v) {
    final s = v.toStringAsFixed(2);
    final idx = s.indexOf('.');
    final intPart = s.substring(0, idx);
    final decPart = s.substring(idx + 1);
    final buf = StringBuffer();
    final neg = intPart.startsWith('-');
    final digits = neg ? intPart.substring(1) : intPart;
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && (digits.length - i) % 3 == 0) buf.write('.');
      buf.write(digits[i]);
    }
    return [neg ? '-$buf' : buf.toString(), decPart];
  }

  String _reais(double v) {
    final p = _formatarPartes(v);
    return 'R\$ ${p[0]},${p[1]}';
  }

  String _dois(int n) => n.toString().padLeft(2, '0');

  String _hora(DateTime d) => '${_dois(d.hour)}:${_dois(d.minute)}:${_dois(d.second)}';
}
