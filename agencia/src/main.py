"""
main.py - Ponto de entrada da agencia ICEIBank

Como executar localmente:
  $env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload
  $env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload
  $env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload

Em producao (Render), o PORT e fornecido automaticamente pelo ambiente.
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
    print(f"Agencia {id_agencia} nao configurada em config.py", file=sys.stderr)
    sys.exit(1)

app = FastAPI(
    title=f"ICEIBank - Agencia {id_agencia}",
    description="API REST do ICEIBank com Relogio Logico de Lamport (Sprint 1)",
    version="1.0.0",
)

# CORS - aceita qualquer origem para funcionar no Vercel e em laboratorios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado compartilhado
app.state.id_agencia = id_agencia
app.state.relogio = RelogioLamport()
app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
app.state.contas = {}
app.state.token_servico = criar_token_servico()

app.include_router(router)

porta = os.environ.get("PORT", str(config.PORTA_BASE + id_agencia))
print(f"[Agencia {id_agencia}] ouvindo na porta {porta}")
print(f"[Agencia {id_agencia}] Documentacao interativa: http://localhost:{porta}/docs")
