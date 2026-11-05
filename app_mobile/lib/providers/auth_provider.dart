import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../services/api_client.dart';

/// Estado de autenticacao: guarda o JWT (armazenamento seguro) e o id da conta logada.
class AuthProvider extends ChangeNotifier {
  final ApiClient api;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  int? idConta;
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
      if (token != null && id != null) {
        api.token = token;
        idConta = int.tryParse(id);
      }
    } catch (_) {
      // storage indisponivel: segue deslogado
    }
    carregando = false;
    notifyListeners();
  }

  Future<void> login(int id, String senha) async {
    mensagemSessao = null;
    final token = await api.login(id, senha); // lanca ApiException em caso de erro
    api.token = token;
    idConta = id;
    await _storage.write(key: 'token', value: token);
    await _storage.write(key: 'idConta', value: id.toString());
    notifyListeners();
  }

  Future<void> logout() async {
    api.token = null;
    idConta = null;
    await _storage.delete(key: 'token');
    await _storage.delete(key: 'idConta');
    notifyListeners();
  }

  /// 401 numa rota protegida: avisa de forma visivel e leva a tela de login.
  void _sessaoExpirada() {
    mensagemSessao = 'Sessao expirada ou invalida. Faca login novamente.';
    logout();
  }
}

