"""
event_log.py - Registro de Eventos (log JSONL)
Equivalente ao eventLog.js do roteiro.

Sprint 2: o campo mudou de "timestampLamport" (int) para "timestampVetorial" (lista de ints).
O nome "timestampVetorial" e exatamente o mesmo usado no mesclar-logs.py (Sprint 2, Secao 8).

Campos do evento:
  - agencia           : nome da agencia (ex.: "agencia-0")
  - tipo              : tipo do evento em maiusculas (ex.: "CRIAR_CONTA")
  - timestampVetorial : vetor completo no momento do evento [v0, v1, v2]
  - horaParede        : hora real UTC em ISO 8601 (apenas para comparacao - nao usada em logica)
  - detalhes          : dict com dados especificos do evento
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List


class RegistroEventos:
    """
    Grava eventos em arquivo JSONL e imprime no console.
    Equivalente a classe RegistroEventos do eventLog.js.
    """

    def __init__(self, nome_agencia: str) -> None:
        self.nome_agencia = nome_agencia
        base_dir = Path(__file__).parent.parent.parent / "data"
        base_dir.mkdir(parents=True, exist_ok=True)
        self.caminho_arquivo = base_dir / f"eventos-{nome_agencia}.jsonl"

    def registrar(self, tipo: str, timestamp_vetorial: List[int], detalhes: dict) -> dict:
        """
        Registra um evento no log JSONL e imprime no console.

        Parametros:
          tipo               : tipo do evento (ex.: "CRIAR_CONTA", "DEPOSITO")
          timestamp_vetorial : vetor de Lamport completo no momento do evento
          detalhes           : informacoes especificas do evento
        """
        evento = {
            "agencia": self.nome_agencia,
            "tipo": tipo,
            "timestampVetorial": timestamp_vetorial,
            "horaParede": datetime.now(timezone.utc).isoformat(),
            "detalhes": detalhes,
        }

        with open(self.caminho_arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

        # Console - equivalente ao console.log do eventLog.js
        print(f"[Vetor {timestamp_vetorial}] {tipo}", detalhes)

        return evento
