/// Configuracao central do app - unico arquivo a alterar para trocar de ambiente.
///
/// Emulador Android: 10.0.2.2 = localhost do PC.
/// Celular fisico: troque pelo IP do PC na rede local (ex.: http://192.168.0.10:4046)
/// e suba as agencias com `--host 0.0.0.0` (liberando o Firewall do Windows).
class Config {
  /// URLs das 3 agencias, na ordem do id (indice = id da agencia).
  /// Portas com OFFSET pessoal 46: 4046, 4047, 4048.
  static const List<String> agencias = [
    'http://10.0.2.2:4046',
    'http://10.0.2.2:4047',
    'http://10.0.2.2:4048',
  ];

  /// Timeout curto no painel de lideranca: o fallback entre agencias precisa ser rapido.
  static const Duration timeoutLider = Duration(seconds: 2);

  /// Timeout das operacoes bancarias.
  static const Duration timeoutRequisicao = Duration(seconds: 8);

  /// Intervalo do polling do painel de lideranca (igual ao heartbeat padrao do backend).
  static const Duration intervaloPolling = Duration(seconds: 3);

  /// Particionamento do backend: a conta N pertence a agencia N % 3.
  static int agenciaDaConta(int idConta) => idConta % agencias.length;
}

