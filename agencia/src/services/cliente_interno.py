"""
cliente_interno.py - Cliente HTTP para falar com as OUTRAS agencias nas rotas internas (Sprint 4)
Equivalente ao clienteInterno.js do roteiro Node.js.

Ja anexa o token compartilhado (`x-token-interno`) em todas as requisicoes.

Dois clientes, ambos httpx (o mesmo cliente HTTP dos sprints anteriores):
  - cliente_interno           : sincrono e thread-safe. Usado pelo Bully (heartbeat e eleicao
                                rodam em threads).
  - criar_cliente_interno_async(): httpx.AsyncClient para o 2PC (asyncio.gather nas rotas async).
                                Crie dentro do event loop que vai usa-lo (use `async with`).
"""

import httpx

from src import config

_HEADERS = {"x-token-interno": config.TOKEN_INTERNO}

cliente_interno = httpx.Client(headers=_HEADERS)


def criar_cliente_interno_async() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=_HEADERS)
