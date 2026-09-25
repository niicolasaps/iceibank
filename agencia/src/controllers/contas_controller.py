"""
contas_controller.py - Controlador de Contas do ICEIBank
Equivalente ao contasController.js do roteiro.

Sprint 2 - Funcionalidade adicional: notificacao de saldo baixo.
  Apos depositar ou sacar, se o saldo ficar abaixo de LIMITE_SALDO_BAIXO,
  publica um evento na routing key "agencia.{id}.alerta-saldo-baixo".
  Nao ha consumidor dedicado para este topico - o objetivo e demonstrar
  a publicacao. Documente isso no RESPOSTAS.md.

Ordem de operacoes (identica ao Node - nao alterar):
  1. Validar entrada e estado
  2. relogio.evento_local() - antes de aplicar a mudanca
  3. Aplicar a mudanca
  4. Registrar o evento no log
  5. (Sprint 2) Verificar saldo baixo e publicar alerta se necessario
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src import config
from src.services.auth import get_usuario_atual
from src.services.mensageria import publicar

router = APIRouter()

# Limite para notificacao de saldo baixo (ajustavel)
LIMITE_SALDO_BAIXO: float = 50.0


class CriarContaBody(BaseModel):
    id: int
    nomeAluno: str
    saldoInicial: float = 0
    senha: str = "1234"


class ValorBody(BaseModel):
    valor: float


async def _verificar_saldo_baixo(id_conta: int, saldo_atual: float, id_agencia: int) -> None:
    """Publica alerta de saldo baixo se saldo < LIMITE_SALDO_BAIXO."""
    if saldo_atual < LIMITE_SALDO_BAIXO:
        routing_key = f"agencia.{id_agencia}.alerta-saldo-baixo"
        mensagem = {
            "idConta": id_conta,
            "saldoAtual": saldo_atual,
            "limite": LIMITE_SALDO_BAIXO,
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, publicar, routing_key, mensagem)
        print(f"[Alerta] Saldo baixo na conta {id_conta}: R$ {saldo_atual:.2f} (limite: R$ {LIMITE_SALDO_BAIXO:.2f})")


@router.post("/contas", status_code=201)
def criar_conta(
    body: CriarContaBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    if config.agencia_responsavel(body.id) != id_agencia:
        raise HTTPException(status_code=400, detail=f"Conta {body.id} nao pertence a esta agencia.")
    if body.id in contas:
        raise HTTPException(status_code=409, detail="Conta ja existe.")

    ts = relogio.evento_local()
    conta = {"id": body.id, "nomeAluno": body.nomeAluno, "saldo": body.saldoInicial, "senha": body.senha}
    contas[body.id] = conta
    registro.registrar("CRIAR_CONTA", ts, {"id": body.id, "nomeAluno": body.nomeAluno, "saldoInicial": body.saldoInicial})

    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.get("/contas/{id}")
def consultar_saldo(
    id: int,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    conta = request.app.state.contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/depositar")
async def depositar(
    id: int,
    body: ValorBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")

    ts = relogio.evento_local()
    conta["saldo"] += body.valor
    registro.registrar("DEPOSITO", ts, {"id": id, "valor": body.valor, "novoSaldo": conta["saldo"]})

    # Funcionalidade adicional: alerta de saldo baixo
    await _verificar_saldo_baixo(id, conta["saldo"], id_agencia)

    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/sacar")
async def sacar(
    id: int,
    body: ValorBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")
    if conta["saldo"] < body.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    ts = relogio.evento_local()
    conta["saldo"] -= body.valor
    registro.registrar("SAQUE", ts, {"id": id, "valor": body.valor, "novoSaldo": conta["saldo"]})

    # Funcionalidade adicional: alerta de saldo baixo
    await _verificar_saldo_baixo(id, conta["saldo"], id_agencia)

    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}
