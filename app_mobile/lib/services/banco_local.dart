import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// Status de uma operacao na fila local.
class StatusPendente {
  static const pendente = 'PENDENTE'; // aguardando sincronizacao
  static const conflito = 'CONFLITO'; // backend devolveu 409 - aguarda decisao da pessoa usuaria
  static const recusada = 'RECUSADA'; // backend recusou por regra de negocio (ex.: saldo insuficiente)
}

/// Operacao de escrita (deposito/saque) feita sem conexao, guardada para sincronizar depois.
class OperacaoPendente {
  final int id;
  final int idConta;
  final String tipo; // 'DEPOSITO' ou 'SAQUE' (mesmos valores do contrato do backend)
  final double valor;
  final List<int> vetorConhecido; // vetorAtual que o app tinha quando a operacao foi feita
  final String status;
  final DateTime criadoEm;
  final String? mensagem; // motivo do conflito/recusa
  final double? saldoReal; // saldo da conta devolvido no 409 (contaAtual.saldo)

  OperacaoPendente({
    required this.id,
    required this.idConta,
    required this.tipo,
    required this.valor,
    required this.vetorConhecido,
    required this.status,
    required this.criadoEm,
    this.mensagem,
    this.saldoReal,
  });

  factory OperacaoPendente.fromMap(Map<String, Object?> m) => OperacaoPendente(
        id: m['id'] as int,
        idConta: m['idConta'] as int,
        tipo: m['tipo'] as String,
        valor: (m['valor'] as num).toDouble(),
        vetorConhecido: (jsonDecode(m['vetorConhecido'] as String) as List).cast<int>(),
        status: m['status'] as String,
        criadoEm: DateTime.parse(m['criadoEm'] as String),
        mensagem: m['mensagem'] as String?,
        saldoReal: (m['saldoReal'] as num?)?.toDouble(),
      );

  /// Efeito esperado no saldo (usado na UI otimista).
  double get efeito => tipo == 'DEPOSITO' ? valor : -valor;
}

/// Ultima copia conhecida de uma conta (para a tela funcionar offline).
class ContaCache {
  final int id;
  final String? nomeAluno;
  final double saldo;
  final List<int>? vetor;
  final DateTime atualizadoEm;

  ContaCache(this.id, this.nomeAluno, this.saldo, this.vetor, this.atualizadoEm);
}

/// Armazenamento local (sqflite): cache das contas consultadas + fila de operacoes pendentes.
class BancoLocal {
  static Database? _db;

  Future<Database> _abrir() async {
    if (_db != null) return _db!;
    final caminho = p.join(await getDatabasesPath(), 'iceibank.db');
    _db = await openDatabase(
      caminho,
      version: 1,
      onCreate: (db, versao) async {
        await db.execute('''
          CREATE TABLE contas (
            id INTEGER PRIMARY KEY,
            nomeAluno TEXT,
            saldo REAL NOT NULL,
            vetor TEXT,
            atualizadoEm TEXT NOT NULL
          )''');
        await db.execute('''
          CREATE TABLE pendentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idConta INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            vetorConhecido TEXT NOT NULL,
            status TEXT NOT NULL,
            criadoEm TEXT NOT NULL,
            mensagem TEXT,
            saldoReal REAL
          )''');
      },
    );
    return _db!;
  }

  // --- Cache de contas ---

  Future<void> salvarConta(int id, String? nomeAluno, double saldo, List<int>? vetor) async {
    final db = await _abrir();
    await db.insert(
      'contas',
      {
        'id': id,
        'nomeAluno': nomeAluno,
        'saldo': saldo,
        'vetor': vetor == null ? null : jsonEncode(vetor),
        'atualizadoEm': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<ContaCache?> lerConta(int id) async {
    final db = await _abrir();
    final linhas = await db.query('contas', where: 'id = ?', whereArgs: [id]);
    if (linhas.isEmpty) return null;
    final m = linhas.first;
    final vetor = m['vetor'] as String?;
    return ContaCache(
      id,
      m['nomeAluno'] as String?,
      (m['saldo'] as num).toDouble(),
      vetor == null ? null : (jsonDecode(vetor) as List).cast<int>(),
      DateTime.parse(m['atualizadoEm'] as String),
    );
  }

  // --- Fila de pendentes (sempre em ordem de criacao) ---

  Future<List<OperacaoPendente>> listarPendentes(int idConta) async {
    final db = await _abrir();
    final linhas = await db.query('pendentes', where: 'idConta = ?', whereArgs: [idConta], orderBy: 'id ASC');
    return linhas.map(OperacaoPendente.fromMap).toList();
  }

  Future<void> inserirPendente(int idConta, String tipo, double valor, List<int> vetorConhecido) async {
    final db = await _abrir();
    await db.insert('pendentes', {
      'idConta': idConta,
      'tipo': tipo,
      'valor': valor,
      'vetorConhecido': jsonEncode(vetorConhecido),
      'status': StatusPendente.pendente,
      'criadoEm': DateTime.now().toIso8601String(),
    });
  }

  Future<void> removerPendente(int id) async {
    final db = await _abrir();
    await db.delete('pendentes', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> marcarPendente(int id, String status, String? mensagem, double? saldoReal) async {
    final db = await _abrir();
    await db.update('pendentes', {'status': status, 'mensagem': mensagem, 'saldoReal': saldoReal},
        where: 'id = ?', whereArgs: [id]);
  }

  /// Volta uma operacao em conflito para a fila, com o vetor atual (opcao "Aplicar mesmo assim").
  Future<void> reabrirPendente(int id, List<int> vetor) async {
    final db = await _abrir();
    await db.update(
      'pendentes',
      {'status': StatusPendente.pendente, 'vetorConhecido': jsonEncode(vetor), 'mensagem': null, 'saldoReal': null},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  /// Apos uma sincronizacao bem-sucedida DO PROPRIO APP, as demais pendentes passam a
  /// conhecer o vetor novo (a mudanca no vetor foi causada pelo app, nao e conflito).
  Future<void> atualizarVetorPendentes(int idConta, List<int> vetor) async {
    final db = await _abrir();
    await db.update('pendentes', {'vetorConhecido': jsonEncode(vetor)},
        where: 'idConta = ? AND status = ?', whereArgs: [idConta, StatusPendente.pendente]);
  }
}

