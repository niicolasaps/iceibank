"""
event_log.py — Registro de Eventos com carimbos de Lamport (Seção 6 / Parte B).

Equivalente ao módulo eventLog.js do exemplo Node.js/Express do roteiro.

Cada operação significativa da agência (criar conta, depositar, sacar, etc.)
é registrada em dois destinos simultaneamente:
  1. Console (stdout) — para acompanhamento em tempo real durante o desenvolvimento.
  2. Arquivo .jsonl  — para persistência e futura mesclagem dos logs das 3 agências
                       em uma linha do tempo única ordenada por Lamport (Parte E).

Formato .jsonl: cada linha é um JSON independente e válido. Essa escolha facilita
o streaming e processamento linha a linha sem carregar o arquivo inteiro em memória.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class RegistroEventos:
    """
    Grava eventos no log .jsonl e no console, com timestamp de Lamport
    e hora de parede (wall clock) em UTC.

    Campos de cada evento:
        agencia          (str)  — nome desta instância, ex: "agencia0"
        tipo             (str)  — nome do evento, ex: "CONTA_CRIADA"
        timestampLamport (int)  — valor do relógio de Lamport no momento do evento
        horaParede       (str)  — ISO 8601 em UTC, ex: "2024-08-27T04:00:00.123456Z"
        detalhes         (dict) — payload específico de cada tipo de evento

    ATENÇÃO: horaParede é registrada APENAS para fins de análise posterior
    (Seção 11 do roteiro — comparação entre relógio lógico e físico). Ela NÃO
    é usada em nenhuma decisão de negócio; toda ordenação causal usa só Lamport.
    """

    def __init__(self, nome_agencia: str) -> None:
        """
        Args:
            nome_agencia: identificador desta instância, ex: "agencia0".
                          Usado no nome do arquivo e no campo "agencia" de cada evento.
        """
        self._nome_agencia = nome_agencia
        self._arquivo = self._preparar_arquivo(nome_agencia)

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def registrar(
        self,
        tipo: str,
        timestamp_lamport: int,
        detalhes: dict,
    ) -> None:
        """
        Registra um evento no console e no arquivo .jsonl.

        Args:
            tipo:               Nome do evento em SNAKE_UPPER_CASE, ex: "CONTA_CRIADA".
            timestamp_lamport:  Valor atual do relógio de Lamport (já incrementado).
            detalhes:           Dicionário com dados específicos do evento.
        """
        hora_parede = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

        evento = {
            "agencia": self._nome_agencia,
            "tipo": tipo,
            "timestampLamport": timestamp_lamport,
            "horaParede": hora_parede,
            "detalhes": detalhes,
        }

        self._imprimir_console(tipo, timestamp_lamport, detalhes)
        self._gravar_arquivo(evento)

    # ------------------------------------------------------------------
    # Métodos auxiliares privados
    # ------------------------------------------------------------------

    @staticmethod
    def _preparar_arquivo(nome_agencia: str) -> Path:
        """
        Garante que o diretório data/ exista e retorna o Path do arquivo .jsonl.

        O diretório é relativo ao diretório de trabalho atual — por isso,
        execute o uvicorn a partir de agencia/ (ou configure adequadamente).
        """
        # Caminho: agencia/data/eventos-agenciaN.jsonl
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / f"eventos-{nome_agencia}.jsonl"

    def _imprimir_console(
        self,
        tipo: str,
        timestamp_lamport: int,
        detalhes: dict,
    ) -> None:
        """Imprime evento no console no formato do roteiro."""
        print(f"[Lamport {timestamp_lamport}] {tipo} {detalhes}")

    def _gravar_arquivo(self, evento: dict) -> None:
        """
        Acrescenta o evento como uma nova linha JSON no arquivo .jsonl.

        O modo 'a' (append) garante que:
          - Reiniciar a agência NÃO apaga o histórico anterior.
          - Múltiplas operações não se sobrescrevem.
        """
        with open(self._arquivo, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")
