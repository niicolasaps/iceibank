"""
eventos_nuvem.py - Publicacao "melhor esforco" no topico SNS da nuvem local (LocalStack) - Sprint 4, Parte F
Equivalente ao eventosNuvem.js da secao 10.3 do roteiro Node.js.

Decisoes importantes:
  - Fora do caminho critico do 2PC: como `boto3` e sincrono/bloqueante, a chamada `sns.publish`
    roda em uma thread daemon em background (`threading.Thread`), com timeout curto (1s de conexao,
    2s de leitura e 0 retries). Se o LocalStack estiver parado, o coordenador responde ao cliente
    normalmente e a thread apenas registra `NUVEM_PUBLICACAO_FALHOU` no log.
  - So fica ativo se `SNS_TOPIC_ARN` estiver definido no ambiente.
"""

from datetime import datetime, timezone
import json
import os
import threading

import boto3
from botocore.config import Config as BotoConfig


class EventosNuvem:
    def __init__(self, id_agencia: int, relogio, registro) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self.topico = os.environ.get("SNS_TOPIC_ARN", "").strip()
        self.endpoint_url = os.environ.get("AWS_ENDPOINT_URL") or None
        self.regiao = os.environ.get("AWS_REGION", "us-east-1")
        self._cliente = None
        if self.topico:
            self._cliente = boto3.client(
                "sns",
                region_name=self.regiao,
                endpoint_url=self.endpoint_url,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
                config=BotoConfig(
                    connect_timeout=1,
                    read_timeout=2,
                    retries={"max_attempts": 0},
                ),
            )

    def publicar_decisao(self, coord: dict) -> None:
        if not self._cliente:
            return
        debito = next(p["operacao"] for p in coord["participantes"] if p["operacao"]["tipo"] == "DEBITO")
        credito = next(p["operacao"] for p in coord["participantes"] if p["operacao"]["tipo"] == "CREDITO")
        evento = {
            "txId": coord["txId"],
            "resultado": coord["decisao"],  # COMMIT ou ABORT
            "idOrigem": debito["idConta"],
            "idDestino": credito["idConta"],
            "valor": debito["valor"],
            "coordenador": self.id_agencia,
            "decididaEm": datetime.now(timezone.utc).isoformat(),
        }
        tx_id = coord["txId"]

        def _enviar():
            try:
                self._cliente.publish(
                    TopicArn=self.topico,
                    Message=json.dumps(evento),
                )
                self.registro.registrar(
                    "NUVEM_EVENTO_PUBLICADO",
                    self.relogio.evento_local(),
                    {"txId": tx_id},
                )
            except Exception as erro:
                self.registro.registrar(
                    "NUVEM_PUBLICACAO_FALHOU",
                    self.relogio.evento_local(),
                    {"txId": tx_id, "erro": type(erro).__name__},
                )

        threading.Thread(target=_enviar, daemon=True, name=f"sns-{tx_id[:8]}").start()
