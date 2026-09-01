"""
transferencias_controller.py — Controlador de Transferencias do ICEIBank
Equivalente ao transferenciasController.js do roteiro. (Parte D, Seção 8)

Parte F: transferir exige JWT de usuario; creditar-remoto aceita token de servico.

LIMITACAO CONHECIDA (intencional): sem rollback em falha entre agencias.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src import config
from src.services.auth import get_token_qualquer, get_usuario_atual

router = APIRouter()


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


class CreditarRemotoBody(BaseModel):
    valor: float
    timestampLamport: int
    origemAgencia: int


@router.post("/transferencias")
async def transferir(
    body: TransferenciaBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    conta_origem = contas.get(body.idOrigem)
    if conta_origem is None:
        raise HTTPException(status_code=404, detail="Conta de origem não encontrada nesta agência.")
    if conta_origem["saldo"] < body.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    agencia_destino = config.agencia_responsavel(body.idDestino)

    ts_debito = relogio.evento_local()
    conta_origem["saldo"] -= body.valor
    registro.registrar("TRANSFERENCIA_DEBITO", ts_debito, {
        "idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor
    })

    if agencia_destino == id_agencia:
        conta_destino = contas.get(body.idDestino)
        if conta_destino is None:
            conta_origem["saldo"] += body.valor
            raise HTTPException(status_code=404, detail="Conta de destino não encontrada.")
        ts_credito = relogio.evento_local()
        conta_destino["saldo"] += body.valor
        registro.registrar("TRANSFERENCIA_CREDITO", ts_credito, {
            "idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor
        })
        return {"mensagem": "Transferência concluída (mesma agência)."}

    ts_envio = relogio.ao_enviar()
    url_destino = next(a["url"] for a in config.AGENCIAS if a["id"] == agencia_destino)
    token_servico = request.app.state.token_servico
    headers = {"Authorization": f"Bearer {token_servico}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{url_destino}/contas/{body.idDestino}/creditar-remoto",
                json={"valor": body.valor, "timestampLamport": ts_envio, "origemAgencia": id_agencia},
                headers=headers,
                timeout=5.0,
            )
            resp.raise_for_status()
        return {"mensagem": "Transferência concluída (entre agências)."}

    except Exception as e:
        registro.registrar("TRANSFERENCIA_FALHOU", relogio.evento_local(), {
            "idOrigem": body.idOrigem, "idDestino": body.idDestino,
            "valor": body.valor, "erro": str(e),
        })
        raise HTTPException(
            status_code=502,
            detail="Falha ao contatar agência de destino. Débito já aplicado - inconsistência conhecida (ver Sprint 4).",
        )


@router.post("/contas/{id}/creditar-remoto")
async def creditar_remoto(
    id: int,
    body: CreditarRemotoBody,
    request: Request,
    _token=Depends(get_token_qualquer),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    ts = relogio.ao_receber(body.timestampLamport)

    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")

    conta["saldo"] += body.valor
    registro.registrar("TRANSFERENCIA_CREDITO_REMOTO", ts, {
        "idConta": id, "valor": body.valor, "origemAgencia": body.origemAgencia
    })
    return {"mensagem": "Crédito remoto aplicado.", "saldoAtual": conta["saldo"]}
