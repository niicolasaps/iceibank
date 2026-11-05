import 'dart:async';

import 'package:flutter/widgets.dart';

import '../config.dart';
import '../services/api_client.dart';

enum StatusLider { carregando, definido, eleicaoEmAndamento, indisponivel }

/// Painel de lideranca: consulta GET /bully/lider periodicamente.
///
/// - Se a agencia consultada nao responde, tenta as outras antes de desistir (fallback).
/// - liderAtual == null (durante uma eleicao) NAO e erro: vira "eleicao em andamento".
/// - O Timer e cancelado ao sair da tela e pausado quando o app vai para segundo plano.
class LiderProvider extends ChangeNotifier with WidgetsBindingObserver {
  final ApiClient api;
  LiderProvider(this.api);

  StatusLider status = StatusLider.carregando;
  int? liderAtual;
  int? agenciaConsultada; // quem respondeu a ultima consulta
  DateTime? ultimaAtualizacao;

  Timer? _timer;
  bool _consultando = false;
  bool _ativo = false;
  int _ultimaAgenciaOk = 0; // comeca a proxima rodada por quem respondeu por ultimo

  void iniciar() {
    if (_ativo) return;
    _ativo = true;
    WidgetsBinding.instance.addObserver(this);
    _ligarTimer();
  }

  void parar() {
    _ativo = false;
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _timer = null;
  }

  void _ligarTimer() {
    _timer?.cancel();
    _consultar(); // primeira consulta imediata
    _timer = Timer.periodic(Config.intervaloPolling, (_) => _consultar());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!_ativo) return;
    if (state == AppLifecycleState.resumed) {
      _ligarTimer();
    } else if (state == AppLifecycleState.paused) {
      _timer?.cancel();
      _timer = null;
    }
  }

  Future<void> _consultar() async {
    if (_consultando) return; // evita consultas sobrepostas
    _consultando = true;
    try {
      final total = Config.agencias.length;
      for (var i = 0; i < total; i++) {
        final indice = (_ultimaAgenciaOk + i) % total;
        try {
          final resposta = await api.consultarLider(Config.agencias[indice]);
          _ultimaAgenciaOk = indice;
          agenciaConsultada = indice;
          final lider = resposta['liderAtual'];
          liderAtual = lider is int ? lider : null;
          status = liderAtual == null ? StatusLider.eleicaoEmAndamento : StatusLider.definido;
          ultimaAtualizacao = DateTime.now();
          return;
        } on ApiException {
          continue; // esta agencia nao respondeu: tenta a proxima
        }
      }
      // nenhuma das 3 respondeu
      status = StatusLider.indisponivel;
      agenciaConsultada = null;
    } finally {
      _consultando = false;
      if (_ativo) notifyListeners();
    }
  }

  @override
  void dispose() {
    parar();
    super.dispose();
  }
}

