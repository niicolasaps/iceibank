"""
autenticacao_interna.py - Protege as rotas que so outras agencias deveriam chamar (Sprint 4)
Equivalente ao autenticacaoInterna.js do roteiro Node.js.

Segredo compartilhado enviado no cabecalho `x-token-interno`. Usado como dependencia
do FastAPI nas rotas /bully/eleicao, /bully/coordenador e /2pc/*. Estas rotas NAO usam JWT.
GET /bully/lider continua publico (o app Flutter consulta essa rota).

O erro e uma excecao propria para que o handler registrado em main.py responda
exatamente {"erro": "Token interno ausente ou inválido."} com HTTP 401, como no enunciado.
"""

import hmac
from typing import Optional

from fastapi import Header

from src import config


class TokenInternoInvalido(Exception):
    pass


def autenticacao_interna(x_token_interno: Optional[str] = Header(default=None)) -> None:
    esperado = config.TOKEN_INTERNO
    # compare_digest: comparacao em tempo constante. Sem token configurado, recusa tudo.
    if not esperado or x_token_interno is None or not hmac.compare_digest(
        x_token_interno.encode("utf-8"), esperado.encode("utf-8")
    ):
        raise TokenInternoInvalido()
