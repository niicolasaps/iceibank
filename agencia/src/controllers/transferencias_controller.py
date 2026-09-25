"""
transferencias_controller.py - Controlador de Transferencias do ICEIBank
Equivalente ao transferenciasController.js do roteiro.

Sprint 2: a chamada REST direta (creditar-remoto) foi substituida por
mensageria assincrona via RabbitMQ. A rota /contas/{id}/creditar-remoto
foi REMOVIDA - o credito remoto agora chega pela fila, consumido em main.py.

Mudanca de semantica:
  Sprint 1: HTTP 200 = credito JA aplicado na outra agencia.
  Sprint 2: HTTP 200 = mensagem PUBLICADA na fila (credito sera aplicado de forma assincrona).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src import config
from src.services.auth import get_usuario_atual
from src.services.mensageria import publicar

router = APIRouter()


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


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
        raise HTTPException(status_code=404, detail="Conta de origem nao encontrada nesta agencia.")
    if conta_origem["saldo"] < body.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    agencia_destino = config.agencia_responsavel(body.idDestino)

    # Debito com evento local (vetor vetorial)
    vetor_debito = relogio.evento_local()
    conta_origem["saldo"] -= body.valor
    registro.registrar("TRANSFERENCIA_DEBITO", vetor_debito, {
        "idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor
    })

    # Transferencia local (mesma agencia)
    if agencia_destino == id_agencia:
        conta_destino = contas.get(body.idDestino)
        if conta_destino is None:
            conta_origem["saldo"] += body.valor  # rollback local
            raise HTTPException(status_code=404, detail="Conta de destino nao encontrada.")
        vetor_credito = relogio.evento_local()
        conta_destino["saldo"] += body.valor
        registro.registrar("TRANSFERENCIA_CREDITO", vetor_credito, {
            "idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor
        })
        return {"mensagem": "Transferencia concluida (mesma agencia)."}

    # Transferencia entre agencias - publica na fila via RabbitMQ
    # (Sprint 1 fazia chamada REST direta aqui - agora e assincrono)
    vetor_envio = relogio.ao_enviar()
    await _publicar_async(f"agencia.{agencia_destino}.creditar", {
        "idConta": body.idDestino,
        "valor": body.valor,
        "vetorEnvio": vetor_envio,
        "origemAgencia": id_agencia,
    })

    return {"mensagem": "Transferencia publicada para a agencia de destino (entrega assincrona)."}


async def _publicar_async(routing_key: str, mensagem: dict) -> None:
    """Chama publicar() de forma compativel com o event loop do FastAPI."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, publicar, routing_key, mensagem)
