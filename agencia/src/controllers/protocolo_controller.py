"""
protocolo_controller.py - Rotas internas do Bully e do 2PC (Sprint 4, Parte B)
Equivalente ao protocoloController.js do roteiro Node.js.

Chamadas apenas por outras agencias. Exigem `x-token-interno` (sem JWT).
Unica excecao: GET /bully/lider continua PUBLICO (o app Flutter consulta essa rota).

Os handlers sao `def` (rodam no pool de threads do FastAPI): participante.preparar/decidir
fazem E/S de disco sob lock e nao devem bloquear o event loop.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.middlewares.autenticacao_interna import autenticacao_interna

router = APIRouter()


class EleicaoBody(BaseModel):
    origemId: int
    vetorEnvio: List[int]


class CoordenadorBody(BaseModel):
    liderId: int
    vetorEnvio: List[int]


class OperacaoBody(BaseModel):
    tipo: str  # 'DEBITO' ou 'CREDITO'
    idConta: int
    valor: float


class PrepararBody(BaseModel):
    txId: str
    operacao: OperacaoBody
    coordenador: int
    vetorEnvio: Optional[List[int]] = None


class DecidirBody(BaseModel):
    txId: str
    decisao: str  # 'COMMIT' ou 'ABORT'
    vetorEnvio: Optional[List[int]] = None


# --- Bully ---

# GET /bully/lider continua PUBLICO. Devolve os dois formatos: {idAgencia, liderAtual} (Sprint 3,
# lido pelo app Flutter) e {lider} (Sprint 4).
@router.get("/bully/lider")
def lider(request: Request):
    lider_atual = request.app.state.bully.obter_lider_atual()
    return {
        "idAgencia": request.app.state.id_agencia,
        "liderAtual": lider_atual,
        "lider": lider_atual,
    }


@router.post("/bully/eleicao", dependencies=[Depends(autenticacao_interna)])
def eleicao(body: EleicaoBody, request: Request):
    request.app.state.bully.receber_eleicao(body.origemId, body.vetorEnvio)
    return {"ok": True, "vetorEnvio": request.app.state.relogio.ao_enviar()}


@router.post("/bully/coordenador", dependencies=[Depends(autenticacao_interna)])
def coordenador_anunciado(body: CoordenadorBody, request: Request):
    request.app.state.bully.receber_coordenador(body.liderId, body.vetorEnvio)
    return {"ok": True}


# --- 2PC ---

@router.post("/2pc/preparar", dependencies=[Depends(autenticacao_interna)])
def preparar(body: PrepararBody, request: Request):
    return request.app.state.participante.preparar(body.model_dump())


@router.post("/2pc/decidir", dependencies=[Depends(autenticacao_interna)])
def decidir(body: DecidirBody, request: Request):
    r = request.app.state.participante.decidir(body.model_dump())
    return JSONResponse(status_code=409 if "erro" in r else 200, content=r)


@router.get("/2pc/status/{tx_id}", dependencies=[Depends(autenticacao_interna)])
def status(tx_id: str, request: Request):
    coordenador = getattr(request.app.state, "coordenador", None)
    if coordenador is None:
        # O coordenador entra na Parte C. Ate la, o participante em duvida fica "bloqueado" nos logs.
        return JSONResponse(status_code=501, content={"erro": "Coordenador ainda não implementado nesta agência."})
    return coordenador.status_de(tx_id)


@router.get("/2pc/transacoes", dependencies=[Depends(autenticacao_interna)])
def transacoes(request: Request):
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
