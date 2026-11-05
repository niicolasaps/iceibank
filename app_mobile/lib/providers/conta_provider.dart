import 'package:flutter/foundation.dart';

import '../services/api_client.dart';

/// Estado da conta logada e das operacoes bancarias (Parte D: tudo online).
class ContaProvider extends ChangeNotifier {
  final ApiClient api;
  final int idConta;

  ContaProvider(this.api, this.idConta);

  String? nomeAluno;
  double? saldo;
  bool ocupado = false;
  String? erro; // ultimo erro, mostrado na tela
  String? sucesso; // ultima mensagem de sucesso

  void _limparMensagens() {
    erro = null;
    sucesso = null;
  }

  Future<void> atualizar() => _executar(() async {
        _aplicar(await api.consultarConta(idConta));
      });

  Future<void> depositar(double valor) => _executar(() async {
        _aplicar(await api.depositar(idConta, valor));
        sucesso = 'Deposito realizado.';
      });

  Future<void> sacar(double valor) => _executar(() async {
        _aplicar(await api.sacar(idConta, valor));
        sucesso = 'Saque realizado.';
      });

  Future<void> transferir(int idDestino, double valor) => _executar(() async {
        sucesso = await api.transferir(idConta, idDestino, valor);
        // a transferencia entre agencias e assincrona; o debito ja vale na origem
        _aplicar(await api.consultarConta(idConta));
      });

  void _aplicar(Map<String, dynamic> conta) {
    nomeAluno = conta['nomeAluno'] as String?;
    saldo = (conta['saldo'] as num?)?.toDouble();
  }

  Future<void> _executar(Future<void> Function() acao) async {
    ocupado = true;
    _limparMensagens();
    notifyListeners();
    try {
      await acao();
    } on ApiException catch (e) {
      erro = e.mensagem;
    } catch (e) {
      erro = 'Erro inesperado: $e';
    }
    ocupado = false;
    notifyListeners();
  }
}

