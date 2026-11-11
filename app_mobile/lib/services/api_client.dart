import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';

/// Erro de API ja traduzido para uma mensagem que pode ser mostrada na tela.
class ApiException implements Exception {
  final String mensagem;
  final int? status;

  /// true quando nao foi possivel falar com a agencia (timeout / conexao recusada).
  final bool semConexao;

  /// Corpo JSON da resposta de erro (ex.: o 409 do /sincronizar traz contaAtual e vetorAtual).
  final dynamic dados;

  ApiException(this.mensagem, {this.status, this.semConexao = false, this.dados});

  @override
  String toString() => mensagem;
}

/// Cliente REST do ICEIBank. Cada agencia so responde pelas contas da sua particao
/// (id % 3), entao as chamadas de conta vao para a agencia da propria conta.
class ApiClient {
  final http.Client _http = http.Client();

  String? token;

  /// Chamado quando uma rota protegida devolve 401 (token ausente/expirado).
  void Function()? onNaoAutorizado;

  Future<dynamic> _requisitar(
    String metodo,
    String base,
    String caminho, {
    Map<String, dynamic>? corpo,
    bool autenticado = true,
    Duration timeout = Config.timeoutRequisicao,
  }) async {
    final uri = Uri.parse('$base$caminho');
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (autenticado && token != null) {
      headers['Authorization'] = 'Bearer $token';
    }

    http.Response resposta;
    try {
      final futuro = metodo == 'GET'
          ? _http.get(uri, headers: headers)
          : _http.post(uri, headers: headers, body: jsonEncode(corpo ?? {}));
      resposta = await futuro.timeout(timeout);
    } on TimeoutException {
      throw ApiException('A agencia nao respondeu a tempo.', semConexao: true);
    } on SocketException {
      throw ApiException('Sem conexao com a agencia.', semConexao: true);
    } on http.ClientException {
      throw ApiException('Sem conexao com a agencia.', semConexao: true);
    }

    final texto = utf8.decode(resposta.bodyBytes);
    dynamic dados;
    if (texto.isNotEmpty) {
      try {
        dados = jsonDecode(texto);
      } catch (_) {
        dados = texto;
      }
    }

    if (resposta.statusCode >= 200 && resposta.statusCode < 300) return dados;

    if (resposta.statusCode == 401 && autenticado) {
      token = null;
      onNaoAutorizado?.call();
      throw ApiException('Nao autorizado. Faca login novamente.', status: 401);
    }
    throw ApiException(_extrairMensagem(dados, resposta.statusCode),
        status: resposta.statusCode, dados: dados);
  }

  /// O backend devolve erros como {"detail": "..."} (FastAPI) ou {"erro": "..."}.
  String _extrairMensagem(dynamic dados, int status) {
    if (dados is Map) {
      final detail = dados['detail'];
      if (detail is String) return detail;
      if (detail is List) return 'Dados invalidos na requisicao.';
      final erro = dados['erro'];
      if (erro is String) return erro;
    }
    return 'Erro $status ao falar com a agencia.';
  }

  String _baseDaConta(int idConta) => Config.agencias[Config.agenciaDaConta(idConta)];

  // --- Autenticacao (contrato do Sprint 1: POST /auth/login {idConta, senha}) ---

  Future<String> login(int idConta, String senha) async {
    final dados = await _requisitar(
      'POST',
      _baseDaConta(idConta),
      '/auth/login',
      corpo: {'idConta': idConta, 'senha': senha},
      autenticado: false,
    );
    return (dados as Map)['token'] as String;
  }

  // --- Contas ---

  Future<Map<String, dynamic>> consultarConta(int idConta) async {
    final dados = await _requisitar('GET', _baseDaConta(idConta), '/contas/$idConta');
    return Map<String, dynamic>.from(dados as Map);
  }

  Future<Map<String, dynamic>> depositar(int idConta, double valor) async {
    final dados = await _requisitar('POST', _baseDaConta(idConta), '/contas/$idConta/depositar',
        corpo: {'valor': valor});
    return Map<String, dynamic>.from(dados as Map);
  }

  Future<Map<String, dynamic>> sacar(int idConta, double valor) async {
    final dados = await _requisitar('POST', _baseDaConta(idConta), '/contas/$idConta/sacar',
        corpo: {'valor': valor});
    return Map<String, dynamic>.from(dados as Map);
  }

  /// Transferencia local ou entre agencias: sempre enviada a agencia da conta de origem.
  Future<String> transferir(int idOrigem, int idDestino, double valor) async {
    final dados = await _requisitar('POST', _baseDaConta(idOrigem), '/transferencias',
        corpo: {'idOrigem': idOrigem, 'idDestino': idDestino, 'valor': valor});
    return (dados as Map)['mensagem'] as String? ?? 'Transferencia realizada.';
  }

  /// Parte E/F: POST /contas/{id}/sincronizar {tipo, valor, vetorConhecido}.
  /// 200 -> conta atualizada; 409 -> ApiException com dados = {erro, vetorConhecido, vetorAtual, contaAtual}.
  Future<Map<String, dynamic>> sincronizar(
      int idConta, String tipo, double valor, List<int> vetorConhecido) async {
    final dados = await _requisitar('POST', _baseDaConta(idConta), '/contas/$idConta/sincronizar',
        corpo: {'tipo': tipo, 'valor': valor, 'vetorConhecido': vetorConhecido});
    return Map<String, dynamic>.from(dados as Map);
  }

  // --- Bully (sem JWT, como no backend) ---

  /// Consulta GET /bully/lider em UMA agencia. Devolve o JSON {idAgencia, liderAtual}.
  Future<Map<String, dynamic>> consultarLider(String baseUrl) async {
    final dados = await _requisitar('GET', baseUrl, '/bully/lider',
        autenticado: false, timeout: Config.timeoutLider);
    return Map<String, dynamic>.from(dados as Map);
  }
}

