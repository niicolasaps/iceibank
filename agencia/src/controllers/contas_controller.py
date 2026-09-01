"""
contas_controller.py — Controlador de Contas do ICEIBank
Equivalente ao contasController.js do exemplo Node.js/Express do roteiro.

Parte C (Seção 7): CRUD de contas com Relógio de Lamport
Parte F (Seção 11): Rotas protegidas por JWT (via dependência get_usuario_atual)

Ordem de operações (idêntica ao Node — não alterar):
  1. Validar entrada e estado
  2. relogio.evento_local() — antes de aplicar a mudança
  3. Aplicar a mudança
  4. Registrar o evento no log
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src import config
from src.services.auth import get_usuario_atual

router = APIRouter()


class CriarContaBody(BaseModel):
    id: int
    nomeAluno: str
    saldoInicial: float = 0
    senha: str = "1234"       # senha padrão para facilitar testes; altere via /auth/registrar


class ValorBody(BaseModel):
    valor: float


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
        raise HTTPException(status_code=400, detail=f"Conta {body.id} não pertence a esta agência.")
    if body.id in contas:
        raise HTTPException(status_code=409, detail="Conta já existe.")

    ts = relogio.evento_local()
    conta = {"id": body.id, "nomeAluno": body.nomeAluno, "saldo": body.saldoInicial, "senha": body.senha}
    contas[body.id] = conta
    registro.registrar("CRIAR_CONTA", ts, {"id": body.id, "nomeAluno": body.nomeAluno, "saldoInicial": body.saldoInicial})

    # Retorna sem a senha no JSON de resposta
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.get("/contas/{id}")
def consultar_saldo(
    id: int,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    conta = request.app.state.contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/depositar")
def depositar(
    id: int,
    body: ValorBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")

    ts = relogio.evento_local()
    conta["saldo"] += body.valor
    registro.registrar("DEPOSITO", ts, {"id": id, "valor": body.valor, "novoSaldo": conta["saldo"]})
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/sacar")
def sacar(
    id: int,
    body: ValorBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
    if conta["saldo"] < body.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    ts = relogio.evento_local()
    conta["saldo"] -= body.valor
    registro.registrar("SAQUE", ts, {"id": id, "valor": body.valor, "novoSaldo": conta["saldo"]})
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}
