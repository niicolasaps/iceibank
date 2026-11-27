"""
serverless/gerar-comprovante/index.py - Funcao Lambda acionada pela fila SQS `comprovantes`
Equivalente ao index.mjs da secao 10.4 do roteiro Node.js (adaptado para runtime Python 3.12,
conforme a secao 11).

Para cada mensagem do lote SQS:
  1. Grava o comprovante completo (JSON) no bucket S3 `iceibank-comprovantes` em `comprovantes/{txId}.json`;
  2. Registra um indice na tabela DynamoDB `comprovantes` (chave primaria `txId`) com
     `ConditionExpression="attribute_not_exists(txId)"` para garantir IDEMPOTENCIA;
  3. Devolve `{"batchItemFailures": [{"itemIdentifier": messageId}, ...]}` apenas para as
     mensagens que falharem (falha parcial).
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import os

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

BUCKET = os.environ.get("BUCKET", "iceibank-comprovantes")
TABELA = os.environ.get("TABELA", "comprovantes")
REGIAO = os.environ.get("AWS_REGION", "us-east-1")


def _descobrir_endpoint():
    ep = os.environ.get("AWS_ENDPOINT_URL")
    if ep:
        return ep
    host = os.environ.get("LOCALSTACK_HOSTNAME")
    if host:
        return f"http://{host}:4566"
    return None


ENDPOINT = _descobrir_endpoint()

s3 = boto3.client(
    "s3",
    region_name=REGIAO,
    endpoint_url=ENDPOINT,
    config=BotoConfig(s3={"addressing_style": "path"}) if ENDPOINT else None,
)
dynamodb = boto3.resource("dynamodb", region_name=REGIAO, endpoint_url=ENDPOINT)
tabela = dynamodb.Table(TABELA)


def _ler_evento(corpo: str) -> dict:
    externo = json.loads(corpo)
    # Sem "raw message delivery", o SNS embrulha o evento em um envelope com o campo Message.
    if isinstance(externo, dict) and "Message" in externo:
        return json.loads(externo["Message"])
    return externo


def handler(event, context):
    falhas = []
    for registro in event.get("Records", []):
        msg_id = registro.get("messageId")
        try:
            ev = _ler_evento(registro["body"])
            emitido_em = datetime.now(timezone.utc).isoformat()
            comprovante = {
                **ev,
                "emitidoEm": emitido_em,
                "mensagem": "Transferencia concluida."
                if ev.get("resultado") == "COMMIT"
                else "Transferencia nao realizada.",
            }
            s3.put_object(
                Bucket=BUCKET,
                Key=f"comprovantes/{ev['txId']}.json",
                Body=json.dumps(comprovante).encode("utf-8"),
                ContentType="application/json",
            )
            try:
                tabela.put_item(
                    Item={
                        "txId": ev["txId"],
                        "resultado": ev["resultado"],
                        "valor": Decimal(str(ev["valor"])),
                        "idOrigem": int(ev["idOrigem"]),
                        "idDestino": int(ev["idDestino"]),
                        "emitidoEm": emitido_em,
                    },
                    ConditionExpression="attribute_not_exists(txId)",
                )
            except ClientError as erro:
                codigo = erro.response.get("Error", {}).get("Code")
                if codigo != "ConditionalCheckFailedException":
                    raise
        except Exception as erro:
            print(f"falha ao processar {msg_id}: {erro}")
            falhas.append({"itemIdentifier": msg_id})
    return {"batchItemFailures": falhas}
