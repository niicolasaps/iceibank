"""
contas_controller.py — Controlador de Contas do ICEIBank
Equivalente ao contasController.js do exemplo Node.js/Express do roteiro.

Implementa os 4 endpoints da Parte C (Seção 7):
  - criar_conta      → POST /contas
  - consultar_saldo  → GET  /contas/{id}
  - depositar        → POST /contas/{id}/depositar
  - sacar            → POST /contas/{id}/sacar

ORDEM DE OPERAÇÕES (idêntica ao exemplo Node — não alterar):
  1. Validar entrada e estado (conta existe? agência correta? saldo suficiente?)
  2. Chamar relogio.evento_local()  ← incrementa o contador ANTES de aplicar a mudança
  3. Aplicar a mudança no dicionário em memória
  4. Registrar o evento no log com o timestamp obtido no passo 2

Por que incrementar o relógio ANTES de aplicar a mudança?
  O timestamp deve marcar o instante lógico em que o evento acontece, não depois.
  Se incrementarmos depois, dois eventos simultâneos em processos diferentes poderiam
  receber o mesmo timestamp, quebrando a ordenação total que o Lamport garante.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import config


# --------------------------------------------------------------------------- #
# Modelos Pydantic — validação automática do corpo das requisições
# --------------------------------------------------------------------------- #

class CriarContaBody(BaseModel):
    id: int
    nomeAluno: str
    saldoInicial: float = 0


class ValorBody(BaseModel):
    valor: float


# --------------------------------------------------------------------------- #
# Router FastAPI — equivalente ao router do Express montado em routes.js
# --------------------------------------------------------------------------- #

router = APIRouter()


# --------------------------------------------------------------------------- #
# POST /contas — criar conta
# --------------------------------------------------------------------------- #

@router.post("/contas", status_code=201)
def criar_conta(body: CriarContaBody, request: Request):
    """
    Cria uma nova conta nesta agência.
    Equivalente à função criarConta() do contasController.js.

    Regras (mesma ordem do exemplo Node):
      1. Verifica se a conta pertence a esta agência (id % 3 == id_agencia).
         → 400 se não pertencer.
      2. Verifica se a conta já existe.
         → 409 se já existir.
      3. Incrementa o relógio de Lamport.
      4. Cria a conta no dicionário em memória.
      5. Registra o evento CRIAR_CONTA no log.
    """
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    # Validação 1: conta pertence a esta agência?
    if config.agencia_responsavel(body.id) != id_agencia:
        raise HTTPException(
            status_code=400,
            detail=f"Conta {body.id} não pertence a esta agência."
        )

    # Validação 2: conta já existe?
    if body.id in contas:
        raise HTTPException(status_code=409, detail="Conta já existe.")

    # Passo 3: incrementar relógio ANTES de aplicar a mudança
    ts = relogio.evento_local()

    # Passo 4: criar conta — equivalente ao contas.set(id, {...}) do Node
    conta = {
        "id": body.id,
        "nomeAluno": body.nomeAluno,
        "saldo": body.saldoInicial,
    }
    contas[body.id] = conta

    # Passo 5: registrar evento
    registro.registrar(
        "CRIAR_CONTA",
        ts,
        {"id": body.id, "nomeAluno": body.nomeAluno, "saldoInicial": body.saldoInicial},
    )

    return conta


# --------------------------------------------------------------------------- #
# GET /contas/{id} — consultar saldo
# --------------------------------------------------------------------------- #

@router.get("/contas/{id}")
def consultar_saldo(id: int, request: Request):
    """
    Consulta o saldo de uma conta.
    Equivalente à função consultarSaldo() do contasController.js.

    Nota: consulta de saldo é uma operação de leitura — NÃO incrementa o relógio
    de Lamport (eventos de leitura não afetam a causalidade do sistema).
    """
    contas = request.app.state.contas
    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
    return conta


# --------------------------------------------------------------------------- #
# POST /contas/{id}/depositar — depositar valor
# --------------------------------------------------------------------------- #

@router.post("/contas/{id}/depositar")
def depositar(id: int, body: ValorBody, request: Request):
    """
    Deposita um valor na conta.
    Equivalente à função depositar() do contasController.js.

    Ordem (idêntica ao Node):
      1. Busca a conta → 404 se não encontrar.
      2. Incrementa o relógio de Lamport.
      3. Aplica o depósito (conta["saldo"] += valor).
      4. Registra o evento DEPOSITO no log.
    """
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    conta = contas.get(id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")

    ts = relogio.evento_local()
    conta["saldo"] += body.valor
    registro.registrar("DEPOSITO", ts, {"id": id, "valor": body.valor, "novoSaldo": conta["saldo"]})

    return conta


# --------------------------------------------------------------------------- #
# POST /contas/{id}/sacar — sacar valor
# --------------------------------------------------------------------------- #

@router.post("/contas/{id}/sacar")
def sacar(id: int, body: ValorBody, request: Request):
    """
    Saca um valor da conta.
    Equivalente à função sacar() do contasController.js.

    Ordem (idêntica ao Node):
      1. Busca a conta → 404 se não encontrar.
      2. Verifica saldo suficiente → 400 se insuficiente.
      3. Incrementa o relógio de Lamport.
      4. Aplica o saque (conta["saldo"] -= valor).
      5. Registra o evento SAQUE no log.
    """
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

    return conta
