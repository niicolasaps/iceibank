"""
routes.py — Roteador central do ICEIBank
Equivalente ao routes.js do exemplo Node.js/Express do roteiro.
"""

from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.controllers.auth_controller import router as auth_router
from src.controllers.contas_controller import router as contas_router
from src.controllers.status_controller import router as status_router
from src.controllers.transferencias_controller import router as transferencias_router

router = APIRouter()

# Auth — login e registro de senha (sem JWT obrigatorio)
router.include_router(auth_router)

# Parte C — CRUD de contas (protegido por JWT)
router.include_router(contas_router)

# Parte D — Transferencias (protegido por JWT)
router.include_router(transferencias_router)

# Funcionalidade adicional — Health-check (publico)
router.include_router(status_router)


# Sprint 3 - Parte A: rotas do Bully (SEM JWT, como no enunciado - ver pergunta 5.5.3)
class EleicaoBody(BaseModel):
    origemId: int
    vetorEnvio: List[int]


class CoordenadorBody(BaseModel):
    liderId: int
    vetorEnvio: List[int]


@router.post("/bully/eleicao")
def bully_eleicao(body: EleicaoBody, request: Request):
    request.app.state.bully.receber_eleicao(body.origemId, body.vetorEnvio)
    return PlainTextResponse("OK", status_code=200)  # equivalente a res.sendStatus(200)


@router.post("/bully/coordenador")
def bully_coordenador(body: CoordenadorBody, request: Request):
    request.app.state.bully.receber_coordenador(body.liderId, body.vetorEnvio)
    return PlainTextResponse("OK", status_code=200)


@router.get("/bully/lider")
def bully_lider(request: Request):
    lider_atual = request.app.state.bully.obter_lider_atual()
    return {"idAgencia": request.app.state.id_agencia, "liderAtual": lider_atual}
