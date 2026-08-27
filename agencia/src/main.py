"""
main.py — Ponto de entrada da agência ICEIBank
Equivalente ao app.js do exemplo Node.js/Express do roteiro.

Inicializa o FastAPI, configura o estado compartilhado (app.state) e inclui as rotas.
O estado compartilhado em FastAPI usa app.state — equivalente ao app.locals do Express:

  app.locals.idAgencia  →  app.state.id_agencia
  app.locals.relogio    →  app.state.relogio
  app.locals.registro   →  app.state.registro
  app.locals.contas     →  app.state.contas  (dict Python, equivalente ao Map JS)

Como executar (PowerShell — um terminal por agência):
  $env:AGENCIA_ID="0"; uvicorn src.main:app --port 4000 --reload
  $env:AGENCIA_ID="1"; uvicorn src.main:app --port 4001 --reload
  $env:AGENCIA_ID="2"; uvicorn src.main:app --port 4002 --reload

Documentação interativa disponível em: http://localhost:{porta}/docs
"""

import os
import sys

from fastapi import FastAPI

from src import config
from src.routes import router
from src.services.event_log import RegistroEventos
from src.services.lamport_clock import RelogioLamport

# --------------------------------------------------------------------------- #
# Leitura da variável de ambiente AGENCIA_ID
# Equivalente a: const idAgencia = parseInt(process.env.AGENCIA_ID || '0', 10)
# --------------------------------------------------------------------------- #
id_agencia = int(os.environ.get("AGENCIA_ID", "0"))

# Valida se a agência está configurada — equivalente ao process.exit(1) do Node
agencia_cfg = next((a for a in config.AGENCIAS if a["id"] == id_agencia), None)
if agencia_cfg is None:
    print(f"Agência {id_agencia} não configurada em config.py", file=sys.stderr)
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Criação da aplicação FastAPI
# --------------------------------------------------------------------------- #
app = FastAPI(
    title=f"ICEIBank — Agência {id_agencia}",
    description="API REST do ICEIBank com Relógio Lógico de Lamport (Sprint 1)",
    version="1.0.0",
)

# --------------------------------------------------------------------------- #
# Estado compartilhado — equivalente ao app.locals do Express
# --------------------------------------------------------------------------- #
# app.state é o mecanismo oficial do FastAPI/Starlette para estado por processo.
# Como rodamos com um único worker (uvicorn padrão), este estado é compartilhado
# por todas as requisições dentro do mesmo processo — comportamento idêntico ao
# app.locals do Express.
app.state.id_agencia = id_agencia
app.state.relogio = RelogioLamport()
app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
app.state.contas = {}  # dict Python — equivalente ao new Map() do Node

# --------------------------------------------------------------------------- #
# Registro das rotas — equivalente ao app.use('/', routes)
# --------------------------------------------------------------------------- #
app.include_router(router)

# --------------------------------------------------------------------------- #
# Log de inicialização
# Equivalente ao app.listen(porta, () => console.log(...))
# O uvicorn imprime a porta no console; este log adiciona a identidade da agência.
# --------------------------------------------------------------------------- #
from urllib.parse import urlparse
porta = urlparse(agencia_cfg["url"]).port
print(f"[Agência {id_agencia}] configurada para ouvir na porta {porta}")
print(f"[Agência {id_agencia}] Swagger UI: http://localhost:{porta}/docs")
