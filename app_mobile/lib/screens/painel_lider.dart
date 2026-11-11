import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/lider_provider.dart';
import '../theme.dart';

/// Painel de lideranca estilo Dark Glassmorphism (mostra a lider Bully em tempo real).
class PainelLider extends StatelessWidget {
  const PainelLider({super.key});

  @override
  Widget build(BuildContext context) {
    final lider = context.watch<LiderProvider>();

    late final Color accent;
    late final String emoji;
    late final String badge;
    late final String titulo;
    late final String subtitulo;

    switch (lider.status) {
      case StatusLider.carregando:
        accent = IceiTheme.gold;
        emoji = '⏳';
        badge = 'CONSENSO BULLY';
        titulo = 'Consultando líder...';
        subtitulo = 'Verificando agências ativas do cluster';
      case StatusLider.definido:
        accent = IceiTheme.emerald;
        emoji = '👑';
        badge = 'COORDENADOR ATIVO · BULLY';
        titulo = 'Líder atual: Agência #${lider.liderAtual}';
        subtitulo =
            'Porta :${4046 + (lider.liderAtual ?? 0)} · respondido via Ag. #${lider.agenciaConsultada}';
      case StatusLider.eleicaoEmAndamento:
        accent = IceiTheme.amber;
        emoji = '🗳️';
        badge = 'ELEIÇÃO EM ANDAMENTO';
        titulo = 'Elegendo nova líder...';
        subtitulo = 'Agência #${lider.agenciaConsultada} aguardando anúncio de coordenador';
      case StatusLider.indisponivel:
        accent = IceiTheme.danger;
        emoji = '📡';
        badge = 'CLUSTER INACESSÍVEL';
        titulo = 'Nenhuma agência respondeu';
        subtitulo = 'Tentando reconectar automaticamente a cada 3s';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            accent.withValues(alpha: 0.14),
            const Color(0xFF111F35).withValues(alpha: 0.65),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: accent.withValues(alpha: 0.35), width: 1),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: accent.withValues(alpha: 0.35)),
            ),
            child: Text(emoji, style: const TextStyle(fontSize: 21)),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(color: accent, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        badge,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.2,
                          color: accent,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  titulo,
                  style: const TextStyle(
                    fontSize: 15.5,
                    fontWeight: FontWeight.w800,
                    color: IceiTheme.textPrimary,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitulo,
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: IceiTheme.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
