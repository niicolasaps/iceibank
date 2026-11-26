"""
routes.py — Roteador central do ICEIBank (Sprint 4)
Equivalente ao routes.js do exemplo Node.js/Express do roteiro.

- Rotas publicas de contas/transferencias: protegidas por JWT (como nos Sprints 1-3).
- GET /bully/lider e GET /status: publicos (o app Flutter consulta /bully/lider).
- Rotas internas (/bully/eleicao, /bully/coordenador, /2pc/*): protegidas pelo segredo
  compartilhado `x-token-interno` via dependencia `autenticacao_interna` (sem JWT).
"""

from typing import List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.controllers.auth_controller import router as auth_router
from src.controllers.contas_controller import router as contas_router
from src.controllers.status_controller import router as status_router
from src.controllers.transferencias_controller import router as transferencias_router
from src.middlewares.autenticacao_interna import autenticacao_interna

router = APIRouter()

# Auth — login e registro de senha (sem JWT obrigatorio)
router.include_router(auth_router)

# Contas — CRUD + sincronizar offline-first (protegido por JWT)
router.include_router(contas_router)

# Transferencias (protegido por JWT)
router.include_router(transferencias_router)

# Health-check publico (/status)
router.include_router(status_router)


class EleicaoBody(BaseModel):
    origemId: int
    vetorEnvio: List[int]


class CoordenadorBody(BaseModel):
    liderId: int
    vetorEnvio: List[int]


# GET /bully/lider continua PUBLICO (o app Flutter consulta essa rota sem segredo interno).
# Devolve os dois formatos juntos: {idAgencia, liderAtual} (Sprint 3) e {lider} (Sprint 4).
@router.get("/bully/lider")
def bully_lider(request: Request):
    lider_atual = request.app.state.bully.obter_lider_atual()
    return {
        "idAgencia": request.app.state.id_agencia,
        "liderAtual": lider_atual,
        "lider": lider_atual,
    }


# Rotas internas: exigem `x-token-interno` (401 {"erro": "Token interno ausente ou inválido."})
@router.post("/bully/eleicao", dependencies=[Depends(autenticacao_interna)])
def bully_eleicao(body: EleicaoBody, request: Request):
    request.app.state.bully.receber_eleicao(body.origemId, body.vetorEnvio)
    return {"ok": True, "vetorEnvio": request.app.state.relogio.ao_enviar()}


@router.post("/bully/coordenador", dependencies=[Depends(autenticacao_interna)])
def bully_coordenador(body: CoordenadorBody, request: Request):
    request.app.state.bully.receber_coordenador(body.liderId, body.vetorEnvio)
    return {"ok": True}


@router.get("/2pc/transacoes", dependencies=[Depends(autenticacao_interna)])
def listar_transacoes_2pc(request: Request):
    estado = request.app.state.estado
    relogio = request.app.state.relogio
    with estado.lock:
        coordenacoes = list(estado.coordenacoes.values())
        participacoes = list(estado.participacoes.values())
    return {
        "coordenacoes": coordenacoes,
        "participacoes": participacoes,
        "vetor": relogio.obter_vetor_atual(),
    }
