import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/lider_provider.dart';

/// Painel de lideranca: mostra a lider atual e atualiza sozinho (polling no LiderProvider).
class PainelLider extends StatelessWidget {
  const PainelLider({super.key});

  @override
  Widget build(BuildContext context) {
    final lider = context.watch<LiderProvider>();

    late final Color cor;
    late final IconData icone;
    late final String titulo;
    String? detalhe;

    switch (lider.status) {
      case StatusLider.carregando:
        cor = Colors.grey;
        icone = Icons.hourglass_empty;
        titulo = 'Consultando lider...';
      case StatusLider.definido:
        cor = Colors.green;
        icone = Icons.star;
        titulo = 'Lider atual: Agencia ${lider.liderAtual}';
        detalhe = 'Consultada via agencia ${lider.agenciaConsultada}';
      case StatusLider.eleicaoEmAndamento:
        cor = Colors.orange;
        icone = Icons.how_to_vote;
        titulo = 'Eleicao em andamento...';
        detalhe = 'Agencia ${lider.agenciaConsultada} ainda nao conhece a lider';
      case StatusLider.indisponivel:
        cor = Colors.red;
        icone = Icons.cloud_off;
        titulo = 'Nenhuma agencia respondeu';
        detalhe = 'Tentando novamente automaticamente';
    }

    return Card(
      color: cor.withValues(alpha: 0.12),
      child: ListTile(
        leading: Icon(icone, color: cor, size: 36),
        title: Text(titulo, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: detalhe == null ? null : Text(detalhe),
      ),
    );
  }
}

