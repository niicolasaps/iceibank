import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import '../config.dart';
import '../services/api_client.dart';
import '../services/banco_local.dart';

/// Estado da conta logada - Parte F: offline-first.
///
/// - Cache local (sqflite) do saldo e do vetorAtual: a tela funciona sem conexao.
/// - Deposito/saque sem conexao vao para a fila de pendentes, com o vetor que o app conhecia.
/// - UI otimista: saldoProvisorio = saldo confirmado +/- operacoes pendentes.
/// - Sincronizacao automatica: ao reconectar (connectivity_plus) e periodicamente enquanto
///   houver pendentes. A fila e processada EM ORDEM e UMA POR VEZ.
/// - 409: a operacao fica marcada como CONFLITO (nao e descartada) e a fila para ate a
///   pessoa usuaria decidir: "Aplicar mesmo assim" ou "Descartar".
/// - Transferencias exigem conexao (nao entram na fila).
class ContaProvider extends ChangeNotifier {
  final ApiClient api;
  final int idConta;
  final BancoLocal _db = BancoLocal();

  ContaProvider(this.api, this.idConta) {
    _iniciar();
  }

  String? nomeAluno;
  double? saldoConfirmado; // ultimo saldo confirmado pela agencia
  List<int>? vetorConhecido; // ultimo vetorAtual recebido da agencia
  DateTime? atualizadoEm; // quando o dado acima foi obtido
  List<OperacaoPendente> pendentes = [];

  bool offline = false;
  bool ocupado = false;
  bool sincronizando = false;
  String? erro; // ultimo erro, mostrado na tela
  String? sucesso; // ultima mensagem de sucesso

  StreamSubscription<List<ConnectivityResult>>? _conectividade;
  Timer? _timerSincronizacao;
  bool _encerrado = false;

  /// true depois que o PROPRIO app aplicou uma pendente: o vetor da agencia avancou por
  /// causa do app, entao e preciso reler GET /contas/{id} antes de enviar a proxima.
  bool _renovarVetorAntesDaProxima = false;

  // --- Valores derivados para a UI ---

  List<OperacaoPendente> get _naFila =>
      pendentes.where((op) => op.status == StatusPendente.pendente).toList();

  int get quantidadePendentes => _naFila.length;

  /// Ha alguma operacao esperando decisao (conflito ou recusada)? A fila fica parada.
  bool get filaBloqueada => pendentes.any((op) => op.status != StatusPendente.pendente);

  /// UI otimista: so as operacoes ainda na fila entram no saldo provisorio.
  /// As que deram conflito/recusa NAO entram - a tela mostra o saldo real.
  double? get saldoProvisorio {
    if (saldoConfirmado == null) return null;
    return _naFila.fold<double>(saldoConfirmado!, (soma, op) => soma + op.efeito);
  }

  // --- Ciclo de vida ---

  Future<void> _iniciar() async {
    await _carregarDoBancoLocal();
    _conectividade = Connectivity().onConnectivityChanged.listen(_aoMudarConectividade);
    _timerSincronizacao = Timer.periodic(Config.intervaloSincronizacao, (_) {
      if (quantidadePendentes > 0 && !filaBloqueada) sincronizar();
    });
    await atualizar();
  }

  Future<void> _carregarDoBancoLocal() async {
    final cache = await _db.lerConta(idConta);
    if (cache != null) {
      nomeAluno = cache.nomeAluno;
      saldoConfirmado = cache.saldo;
      vetorConhecido = cache.vetor;
      atualizadoEm = cache.atualizadoEm;
    }
    pendentes = await _db.listarPendentes(idConta);
    _notificar();
  }

  void _aoMudarConectividade(List<ConnectivityResult> resultado) {
    final semRede = resultado.isEmpty || resultado.every((r) => r == ConnectivityResult.none);
    if (semRede) {
      offline = true;
      _notificar();
    } else {
      // a rede voltou: atualiza e, se a agencia responder, sincroniza a fila sozinho
      atualizar();
    }
  }

  // --- Leitura ---

  /// GET /contas/{id}. Sem conexao: mantem o ultimo dado conhecido (cache) e marca offline.
  /// Importante: NAO altera o vetor guardado nas pendentes (isso esconderia um conflito).
  Future<void> atualizar() async {
    try {
      await _aplicarContaDoServidor(await api.consultarConta(idConta));
      offline = false;
    } on ApiException catch (e) {
      if (e.semConexao) {
        offline = true;
      } else {
        erro = e.mensagem;
      }
    }
    _notificar();
    if (!offline) await sincronizar();
  }

  Future<void> _aplicarContaDoServidor(Map<String, dynamic> conta) async {
    nomeAluno = conta['nomeAluno'] as String?;
    saldoConfirmado = (conta['saldo'] as num?)?.toDouble();
    final vetor = conta['vetorAtual'];
    if (vetor is List) vetorConhecido = vetor.cast<int>();
    atualizadoEm = DateTime.now();
    if (saldoConfirmado != null) {
      await _db.salvarConta(idConta, nomeAluno, saldoConfirmado!, vetorConhecido);
    }
  }

  // --- Escrita ---

  Future<void> depositar(double valor) => _operacaoDeEscrita('DEPOSITO', valor);

  Future<void> sacar(double valor) => _operacaoDeEscrita('SAQUE', valor);

  Future<void> _operacaoDeEscrita(String tipo, double valor) async {
    _limparMensagens();
    ocupado = true;
    _notificar();
    try {
      // Se ja ha fila, a nova operacao entra no fim dela (preserva a ordem). Mandar direto
      // furaria a fila e avancaria o vetor, fazendo as pendentes antigas darem 409.
      if (offline || pendentes.isNotEmpty) {
        await _enfileirar(tipo, valor);
        if (!offline) unawaited(sincronizar());
        return;
      }
      try {
        if (tipo == 'DEPOSITO') {
          await api.depositar(idConta, valor);
          sucesso = 'Deposito realizado.';
        } else {
          await api.sacar(idConta, valor);
          sucesso = 'Saque realizado.';
        }
        await _releituraSilenciosa(); // depositar/sacar nao devolvem vetorAtual
      } on ApiException catch (e) {
        if (e.semConexao) {
          offline = true;
          await _enfileirar(tipo, valor);
        } else {
          erro = e.mensagem;
        }
      }
    } finally {
      ocupado = false;
      _notificar();
    }
  }

  Future<void> _enfileirar(String tipo, double valor) async {
    if (vetorConhecido == null || saldoConfirmado == null) {
      erro = 'Sem dados salvos desta conta. Conecte-se a agencia ao menos uma vez antes de operar offline.';
      return;
    }
    // reduz o risco da UI otimista: nao aceita saque maior que o saldo provisorio
    if (tipo == 'SAQUE' && valor > (saldoProvisorio ?? 0)) {
      erro = 'Saldo provisorio insuficiente para este saque.';
      return;
    }
    await _db.inserirPendente(idConta, tipo, valor, vetorConhecido!);
    pendentes = await _db.listarPendentes(idConta);
    sucesso = offline
        ? 'Sem conexao com a agencia: operacao salva como PENDENTE e sera sincronizada automaticamente.'
        : 'Operacao adicionada a fila de sincronizacao.';
  }

  Future<void> transferir(int idDestino, double valor) async {
    _limparMensagens();
    if (offline) {
      erro = 'Transferencias exigem conexao com a agencia e nao ficam pendentes. Tente novamente quando estiver online.';
      _notificar();
      return;
    }
    if (pendentes.isNotEmpty) {
      erro = 'Ha operacoes pendentes de sincronizacao. Aguarde a sincronizacao (ou resolva o conflito) antes de transferir.';
      _notificar();
      return;
    }
    ocupado = true;
    _notificar();
    try {
      sucesso = await api.transferir(idConta, idDestino, valor);
      await _releituraSilenciosa();
    } on ApiException catch (e) {
      if (e.semConexao) {
        offline = true;
        erro = 'Sem conexao com a agencia: a transferencia NAO foi realizada (transferencias nao ficam pendentes).';
      } else {
        erro = e.mensagem;
      }
    } finally {
      ocupado = false;
      _notificar();
    }
  }

  Future<void> _releituraSilenciosa() async {
    try {
      await _aplicarContaDoServidor(await api.consultarConta(idConta));
    } on ApiException catch (e) {
      if (e.semConexao) offline = true;
    }
  }

  // --- Sincronizacao da fila ---

  Future<void> sincronizar() async {
    if (sincronizando || _encerrado) return;
    sincronizando = true;
    _notificar();
    var aplicadas = 0;
    try {
      while (!_encerrado) {
        pendentes = await _db.listarPendentes(idConta);
        if (pendentes.isEmpty) break;
        final op = pendentes.first;
        if (op.status != StatusPendente.pendente) break; // espera decisao sobre conflito/recusa

        try {
          if (_renovarVetorAntesDaProxima) {
            // o vetor avancou por causa da pendente que o PROPRIO app acabou de aplicar
            await _aplicarContaDoServidor(await api.consultarConta(idConta));
            await _db.atualizarVetorPendentes(idConta, vetorConhecido!);
            _renovarVetorAntesDaProxima = false;
            continue; // relê a fila com o vetor novo
          }

          await api.sincronizar(idConta, op.tipo, op.valor, op.vetorConhecido);
          await _db.removerPendente(op.id);
          aplicadas++;
          offline = false;
          _renovarVetorAntesDaProxima = true;
        } on ApiException catch (e) {
          if (e.semConexao) {
            offline = true;
            break;
          }
          if (e.status == 401) break; // AuthProvider ja leva ao login; a fila fica salva
          if (e.status == 409 && e.dados is Map) {
            await _registrarConflito(op, e.dados as Map);
            break;
          }
          // 400/404: recusa por regra de negocio (ex.: saldo insuficiente na agencia)
          await _db.marcarPendente(op.id, StatusPendente.recusada, e.mensagem, null);
          erro = 'Uma operacao pendente foi recusada pela agencia: ${e.mensagem}';
          break;
        }
      }
      if (_renovarVetorAntesDaProxima && !offline) {
        // fila esvaziou: atualiza saldo/vetor confirmados depois da ultima aplicada
        await _releituraSilenciosa();
        _renovarVetorAntesDaProxima = false;
      }
    } finally {
      pendentes = await _db.listarPendentes(idConta);
      if (aplicadas > 0) {
        sucesso = aplicadas == 1
            ? '1 operacao pendente foi sincronizada automaticamente.'
            : '$aplicadas operacoes pendentes foram sincronizadas automaticamente.';
      }
      sincronizando = false;
      _notificar();
    }
  }

  Future<void> _registrarConflito(OperacaoPendente op, Map dados) async {
    final contaAtual = dados['contaAtual'];
    final saldoReal = contaAtual is Map ? (contaAtual['saldo'] as num?)?.toDouble() : null;
    final mensagem = dados['erro'] as String? ?? 'Conflito detectado.';
    await _db.marcarPendente(op.id, StatusPendente.conflito, mensagem, saldoReal);

    // mostra o estado ATUAL e REAL da conta devolvido pela agencia
    if (saldoReal != null) saldoConfirmado = saldoReal;
    final vetorAtual = dados['vetorAtual'];
    if (vetorAtual is List) vetorConhecido = vetorAtual.cast<int>();
    atualizadoEm = DateTime.now();
    if (saldoConfirmado != null) {
      await _db.salvarConta(idConta, nomeAluno, saldoConfirmado!, vetorConhecido);
    }
    erro = 'Uma operacao feita offline NAO foi aplicada automaticamente: a conta mudou na agencia '
        'enquanto o app estava desconectado. Revise abaixo e decida o que fazer.';
  }

  /// "Aplicar mesmo assim": relê a conta (vetor atual) e reenvia a operacao com esse vetor.
  Future<void> aplicarMesmoAssim(OperacaoPendente op) async {
    _limparMensagens();
    ocupado = true;
    _notificar();
    try {
      await _aplicarContaDoServidor(await api.consultarConta(idConta));
      await _db.reabrirPendente(op.id, vetorConhecido!);
      await _db.atualizarVetorPendentes(idConta, vetorConhecido!);
      _renovarVetorAntesDaProxima = false;
      pendentes = await _db.listarPendentes(idConta);
    } on ApiException catch (e) {
      erro = e.semConexao ? 'Sem conexao com a agencia: tente novamente quando estiver online.' : e.mensagem;
      ocupado = false;
      _notificar();
      return;
    }
    ocupado = false;
    await sincronizar();
  }

  /// "Descartar": remove a operacao da fila; as proximas voltam a ser sincronizadas.
  Future<void> descartar(OperacaoPendente op) async {
    _limparMensagens();
    await _db.removerPendente(op.id);
    pendentes = await _db.listarPendentes(idConta);
    sucesso = 'Operacao descartada.';
    _notificar();
    if (!offline && quantidadePendentes > 0) await sincronizar();
  }

  // --- Utilitarios ---

  void _limparMensagens() {
    erro = null;
    sucesso = null;
  }

  void _notificar() {
    if (!_encerrado) notifyListeners();
  }

  @override
  void dispose() {
    _encerrado = true;
    _conectividade?.cancel();
    _timerSincronizacao?.cancel();
    super.dispose();
  }
}
