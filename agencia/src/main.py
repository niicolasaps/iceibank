"""
main.py — Ponto de entrada da agencia ICEIBank
Equivalente ao app.js do exemplo Node.js/Express do roteiro.

Novidade (Parte F): gera token de servico no startup e armazena em app.state.
Esse token e usado pela logica de transferencia entre agencias para autenticar
as chamadas maquina-a-maquina ao endpoint /contas/{id}/creditar-remoto.

Como executar (PowerShell, um terminal por agencia):
  $env:AGENCIA_ID="0"; uvicorn src.main:app --port 4046 --reload
  $env:AGENCIA_ID="1"; uvicorn src.main:app --port 4047 --reload
  $env:AGENCIA_ID="2"; uvicorn src.main:app --port 4048 --reload
"""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.routes import router
from src.services.auth import criar_token_servico
from src.services.event_log import RegistroEventos
from src.services.lamport_clock import RelogioLamport

id_agencia = int(os.environ.get("AGENCIA_ID", "0"))

agencia_cfg = next((a for a in config.AGENCIAS if a["id"] == id_agencia), None)
if agencia_cfg is None:
    print(f"Agência {id_agencia} não configurada em config.py", file=sys.stderr)
    sys.exit(1)

app = FastAPI(
    title=f"ICEIBank — Agência {id_agencia}",
    description="API REST do ICEIBank com Relógio Lógico de Lamport (Sprint 1)",
    version="1.0.0",
)

# CORS — necessario para o frontend React em desenvolvimento (porta 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado compartilhado — equivalente ao app.locals do Express
app.state.id_agencia = id_agencia
app.state.relogio = RelogioLamport()
app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
app.state.contas = {}
app.state.token_servico = criar_token_servico()  # token maquina-a-maquina

app.include_router(router)

from urllib.parse import urlparse
porta = urlparse(agencia_cfg["url"]).port
print(f"[Agência {id_agencia}] ouvindo na porta {porta}")
print(f"[Agência {id_agencia}] Swagger UI: http://localhost:{porta}/docs")
