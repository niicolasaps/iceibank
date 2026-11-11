import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../services/api_client.dart';

/// Estado de autenticacao: guarda o JWT (armazenamento seguro) e o id da conta logada.
class AuthProvider extends ChangeNotifier {
  final ApiClient api;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  int? idConta;
  int? agenciaAtiva;
  bool carregando = true; // true enquanto le o token salvo no startup
  String? mensagemSessao; // ex.: "Sessao expirada" - mostrada na tela de login

  AuthProvider(this.api) {
    api.onNaoAutorizado = _sessaoExpirada;
    _restaurar();
  }

  bool get estaLogado => api.token != null && idConta != null;

  Future<void> _restaurar() async {
    try {
      final token = await _storage.read(key: 'token');
      final id = await _storage.read(key: 'idConta');
      final ag = await _storage.read(key: 'agenciaAtiva');
      if (token != null && id != null) {
        api.token = token;
        idConta = int.tryParse(id);
        agenciaAtiva = ag != null ? int.tryParse(ag) : null;
        api.agenciaSelecionada = agenciaAtiva;
      }
    } catch (_) {
      // storage indisponivel: segue deslogado
    }
    carregando = false;
    notifyListeners();
  }

  Future<void> login(int id, String senha, {int? agenciaIdx}) async {
    mensagemSessao = null;
    api.agenciaSelecionada = agenciaIdx;
    final token = await api.login(id, senha); // lanca ApiException em caso de erro
    api.token = token;
    idConta = id;
    agenciaAtiva = agenciaIdx;
    await _storage.write(key: 'token', value: token);
    await _storage.write(key: 'idConta', value: id.toString());
    if (agenciaIdx != null) {
      await _storage.write(key: 'agenciaAtiva', value: agenciaIdx.toString());
    }
    notifyListeners();
  }

  Future<void> logout() async {
    api.token = null;
    api.agenciaSelecionada = null;
    idConta = null;
    agenciaAtiva = null;
    await _storage.delete(key: 'token');
    await _storage.delete(key: 'idConta');
    await _storage.delete(key: 'agenciaAtiva');
    notifyListeners();
  }

  /// 401 numa rota protegida: avisa de forma visivel e leva a tela de login.
  void _sessaoExpirada() {
    mensagemSessao = 'Sessao expirada ou invalida. Faca login novamente.';
    logout();
  }
}

