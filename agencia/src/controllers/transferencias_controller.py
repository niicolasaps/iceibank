"""
transferencias_controller.py - Controlador de Transferencias via 2PC (Sprint 4, Parte C)
Equivalente ao transferenciasController.js da secao 7.2 do roteiro Node.js.

Qualquer agencia recebe o pedido do cliente (POST /transferencias, protegido por JWT),
mas quem COORDENA o 2PC e sempre o lider eleito pelo Bully. Se esta agencia nao for o
lider, encaminha o pedido ao lider pela rota interna POST /2pc/coordenar (protegida por
`x-token-interno`).

Codigos HTTP (identicos ao roteiro):
  - 200: resultado == 'COMMIT'
  - 422: resultado == 'ABORT' (com `motivos`)
  - 400: dados invalidos / origem == destino
  - 503: sem lider eleito ou coordenador indisponivel
  - 409: POST /2pc/coordenar chamado em uma agencia que nao e a lider
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import config
from src.middlewares.autenticacao_interna import autenticacao_interna
from src.services.auth import get_usuario_atual
from src.services.cliente_interno import criar_cliente_interno_async

router = APIRouter()


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


def _erro(status_code: int, msg: str) -> JSONResponse:
    """Inclui tanto `erro` (contrato Sprint 4) quanto `detail` (frontend web React / app Flutter)."""
    return JSONResponse(status_code=status_code, content={"erro": msg, "detail": msg})


@router.post("/transferencias")
async def transferir(
    body: TransferenciaBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    if body.valor <= 0:
        return _erro(400, "Informe idOrigem, idDestino (inteiros) e valor (> 0).")
    if body.idOrigem == body.idDestino:
        return _erro(400, "Origem e destino devem ser diferentes.")

    bully = request.app.state.bully
    coordenador = request.app.state.coordenador
    id_agencia = request.app.state.id_agencia

    lider = bully.obter_lider_atual()
    if lider is None:
        return _erro(503, "Sem líder eleito no momento. Tente novamente.")

    try:
        if lider == id_agencia:
            r = await coordenador.coordenar(body.idOrigem, body.idDestino, body.valor)
            return JSONResponse(status_code=200 if r["resultado"] == "COMMIT" else 422, content=r)

        url = next(a["url"] for a in config.AGENCIAS if a["id"] == lider)
        async with criar_cliente_interno_async() as client:
            resp = await client.post(
                f"{url}/2pc/coordenar",
                json={"idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor},
                timeout=15.0,
            )
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception:
        return _erro(503, "Coordenador indisponível. Nada foi aplicado; tente novamente.")


# Rota interna: outra agencia pede para este lider coordenar.
@router.post("/2pc/coordenar", dependencies=[Depends(autenticacao_interna)])
async def coordenar_a_requisicao(body: TransferenciaBody, request: Request):
    bully = request.app.state.bully
    coordenador = request.app.state.coordenador
    id_agencia = request.app.state.id_agencia

    if bully.obter_lider_atual() != id_agencia:
        return _erro(409, "Esta agência não é a líder.")

    r = await coordenador.coordenar(body.idOrigem, body.idDestino, body.valor)
    return JSONResponse(status_code=200 if r["resultado"] == "COMMIT" else 422, content=r)
