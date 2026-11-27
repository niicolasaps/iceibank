"""
serverless/consultar-comprovante/index.py - Segunda funcao Lambda (Sprint 4, Parte F - secao 10.6 item 7)

Exposta via API Gateway do LocalStack (GET /comprovantes/{txId} ou ?txId=...).
Dado um `txId`:
  1. Consulta o indice na tabela DynamoDB `comprovantes`; se nao existir, devolve HTTP 404.
  2. Busca tambem o JSON completo no bucket S3 `s3://iceibank-comprovantes/comprovantes/{txId}.json`
     (e faz fallback para o item do DynamoDB caso necessario), devolvendo HTTP 200 com o comprovante.
"""

from decimal import Decimal
import json
import os

import boto3
from botocore.config import Config as BotoConfig

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


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def _extrair_tx_id(event: dict):
    if not isinstance(event, dict):
        return None
    path_params = event.get("pathParameters") or {}
    if isinstance(path_params, dict) and path_params.get("txId"):
        return path_params["txId"]
    query_params = event.get("queryStringParameters") or {}
    if isinstance(query_params, dict) and query_params.get("txId"):
        return query_params["txId"]
    if event.get("txId"):
        return event["txId"]
    raw_path = event.get("rawPath") or event.get("path") or ""
    if "/comprovantes/" in raw_path:
        return raw_path.split("/comprovantes/", 1)[1].strip("/")
    return None


def _resposta(status_code: int, corpo: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corpo, cls=_DecimalEncoder, ensure_ascii=False),
    }


def handler(event, context):
    tx_id = _extrair_tx_id(event)
    if not tx_id:
        return _resposta(400, {"erro": "Informe o parametro txId na URL (/comprovantes/{txId})."})

    # 1. Consulta o indice no DynamoDB
    resp_dyn = tabela.get_item(Key={"txId": tx_id})
    item = resp_dyn.get("Item")
    if not item:
        return _resposta(404, {"erro": "Comprovante não encontrado.", "txId": tx_id})

    # 2. Le o comprovante completo no S3 (e anexa metadados de origem)
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=f"comprovantes/{tx_id}.json")
        comprovante_s3 = json.loads(obj["Body"].read().decode("utf-8"))
        return _resposta(200, {**comprovante_s3, "fonte": "S3+DynamoDB"})
    except Exception:
        return _resposta(200, {**item, "fonte": "DynamoDB"})
