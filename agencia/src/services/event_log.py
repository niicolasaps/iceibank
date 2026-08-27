"""
event_log.py — Registro de Eventos (log JSONL)
Equivalente ao eventLog.js do exemplo Node.js/Express do roteiro.

Cada evento é uma linha JSON gravada em:
  agencia/data/eventos-{nome_agencia}.jsonl

Campos do evento (mesmos nomes do exemplo Node — não alterar):
  - agencia          : nome da agência (ex.: "agencia-0")
  - tipo             : tipo do evento em maiúsculas (ex.: "CRIAR_CONTA")
  - timestampLamport : valor do relógio lógico no momento do evento
  - horaParede       : hora real UTC em ISO 8601 (apenas para comparação — não usada em lógica)
  - detalhes         : dict com dados específicos do evento

horaParede NÃO é usada em nenhuma decisão de negócio. Ela existe apenas para a análise
da Seção 11 do roteiro (comparar ordenação por Lamport vs. por hora real).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class RegistroEventos:
    """
    Grava eventos em arquivo JSONL e imprime no console.
    Equivalente à classe RegistroEventos do eventLog.js.
    """

    def __init__(self, nome_agencia: str) -> None:
        self.nome_agencia = nome_agencia

        # Equivalente ao path.join(__dirname, '..', '..', 'data', `eventos-${nomeAgencia}.jsonl`)
        # __file__ = agencia/src/services/event_log.py
        # data/   = agencia/data/
        base_dir = Path(__file__).parent.parent.parent / "data"
        base_dir.mkdir(parents=True, exist_ok=True)
        self.caminho_arquivo = base_dir / f"eventos-{nome_agencia}.jsonl"

    def registrar(self, tipo: str, timestamp_lamport: int, detalhes: dict) -> dict:
        """
        Registra um evento no log JSONL e imprime no console.
        Equivalente ao método registrar() do eventLog.js.

        Parâmetros:
          tipo              : tipo do evento (ex.: "CRIAR_CONTA", "DEPOSITO", "SAQUE")
          timestamp_lamport : valor do relógio de Lamport no momento do evento
          detalhes          : informações específicas do evento

        Retorna o dict do evento gravado (útil para testes).
        """
        evento = {
            "agencia": self.nome_agencia,
            "tipo": tipo,
            "timestampLamport": timestamp_lamport,
            # horaParede é apenas referência — não usada em lógica de negócio
            "horaParede": datetime.now(timezone.utc).isoformat(),
            "detalhes": detalhes,
        }

        # Appenda uma linha JSON ao arquivo (não carrega tudo na memória)
        with open(self.caminho_arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

        # Saída no console — equivalente ao console.log do eventLog.js
        print(f"[Lamport {timestamp_lamport}] {tipo}", detalhes)

        return evento
