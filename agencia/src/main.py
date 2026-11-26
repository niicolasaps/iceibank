"""
main.py - Ponto de entrada da agencia ICEIBank (Sprint 4)
Equivalente ao app.js da secao 5.8 do roteiro Node.js.

Sprint 4 (Parte A):
  - EstadoDuravel persiste contas, reservas, coordenacoes e participacoes em DATA_DIR
  - TOKEN_INTERNO e obrigatorio (protege rotas internas do Bully e 2PC)
  - RabbitMQ passa a ser opcional (nao bloqueia a subida em container sem RABBITMQ_URL)
  - `python -m src.main` sobe o uvicorn em 0.0.0.0 na porta PORTA_BASE + AGENCIA_ID
"""

import os
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import config
from src.middlewares.autenticacao_interna import TokenInternoInvalido
from src.routes import router
from src.services import bully_service
from src.services.armazenamento import EstadoDuravel
from src.services.auth import criar_token_servico
from src.services.bully_service import ServicoBully
from src.services.event_log import RegistroEventos
from src.services.eventos_nuvem import EventosNuvem
from src.services.vector_clock import RelogioVetorial

try:
    id_agencia = int(os.environ.get("AGENCIA_ID", "0"))
except ValueError:
    id_agencia = -1

if id_agencia not in (0, 1, 2):
    print("Defina AGENCIA_ID com 0, 1 ou 2.", file=sys.stderr)
    sys.exit(1)

if not config.TOKEN_INTERNO:
    print("Defina TOKEN_INTERNO (segredo compartilhado entre as agências).", file=sys.stderr)
    sys.exit(1)

estado = EstadoDuravel(id_agencia)
relogio = RelogioVetorial(id_agencia, config.NUMERO_AGENCIAS)
registro = RegistroEventos(f"agencia-{id_agencia}")
bully = ServicoBully(id_agencia, relogio, registro)
eventos_nuvem = EventosNuvem(id_agencia, relogio, registro)

app = FastAPI(
    title=f"ICEIBank - Agencia {id_agencia}",
    description="API REST do ICEIBank com Persistencia, Docker, Bully e 2PC (Sprint 4)",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TokenInternoInvalido)
async def _tratar_token_interno_invalido(_request: Request, _exc: TokenInternoInvalido):
    return JSONResponse(
        status_code=401,
        content={"erro": "Token interno ausente ou inválido."},
    )


app.state.id_agencia = id_agencia
app.state.estado = estado
# Alias para qualquer código legado que leia `app.state.contas`
app.state.contas = estado.contas
app.state.relogio = relogio
app.state.registro = registro
app.state.bully = bully
app.state.eventos_nuvem = eventos_nuvem
app.state.token_servico = criar_token_servico()

app.include_router(router)


@app.on_event("startup")
def iniciar_servicos_background():
    """
    Dispara a eleicao inicial e o heartbeat do Bully em background apos o servidor subir.
    (Nas Partes B e C tambem iniciara participante.iniciar_resolucao() e coordenador.iniciar_reentrega()).
    """
    def _eleicao_inicial():
        time.sleep(bully_service.ATRASO_INICIAL_S)
        app.state.bully.iniciar_eleicao()

    threading.Thread(target=_eleicao_inicial, daemon=True).start()
    app.state.bully.iniciar_heartbeat()


porta = int(os.environ.get("PORT", str(config.PORTA_BASE + id_agencia)))
print(f"Agência {id_agencia} no ar na porta {porta}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=porta)
