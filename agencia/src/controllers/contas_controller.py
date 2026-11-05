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
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import config
from src.services.auth import get_usuario_atual
from src.services.comparar_vetores import comparar_vetores
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
    # Sprint 3 (Parte E): devolve tambem o vetor atual, para o app guardar (offline-first)
    return {
        "id": conta["id"],
        "nomeAluno": conta["nomeAluno"],
        "saldo": conta["saldo"],
        "vetorAtual": request.app.state.relogio.obter_vetor_atual(),
    }


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



class SincronizarBody(BaseModel):
    # tipo e str (nao Literal) para manter o contrato do enunciado: tipo desconhecido -> 400
    # com a mensagem literal, e nao 422 do Pydantic.
    tipo: str
    valor: float
    vetorConhecido: List[int]


def _conta_publica(conta: dict) -> dict:
    """Conta sem o campo senha (mesmo formato das demais rotas)."""
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/sincronizar")
def sincronizar_operacao_pendente(
    id: int,
    body: SincronizarBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    """
    Sprint 3 (Parte E): aplica uma operacao feita offline pelo app, SE o vetor que o app
    conhecia ainda for igual ao vetor atual da agencia. Caso contrario, 409 com o estado atual.

    Contrato (identico ao sincronizarOperacaoPendente do roteiro): erros usam a chave "erro"
    e mensagens literais do enunciado.
    """
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    conta = contas.get(id)
    if conta is None:
        return JSONResponse(status_code=404, content={"erro": "Conta não encontrada nesta agência."})

    if len(body.vetorConhecido) != config.NUMERO_AGENCIAS:
        return JSONResponse(status_code=400, content={"erro": "vetorConhecido inválido."})

    # Trecho critico ATOMICO: comparar o vetor e aplicar a operacao sem que outra thread
    # (consumidor RabbitMQ, Bully, heartbeat, outras requisicoes) avance o vetor no meio.
    with relogio.travar():
        vetor_atual = relogio.obter_vetor_atual()
        relacao = comparar_vetores(body.vetorConhecido, vetor_atual)

        if relacao != "IGUAIS":
            # outras operacoes aconteceram na agencia desde a ultima sincronizacao do app:
            # nao aplica cegamente, devolve o estado atual para o app decidir
            return JSONResponse(
                status_code=409,
                content={
                    "erro": "Conflito detectado: o estado da conta mudou desde a última sincronização do app.",
                    "vetorConhecido": body.vetorConhecido,
                    "vetorAtual": vetor_atual,
                    "contaAtual": _conta_publica(conta),
                },
            )

        if body.tipo == "DEPOSITO":
            vetor = relogio.evento_local()
            conta["saldo"] += body.valor
        elif body.tipo == "SAQUE":
            if conta["saldo"] < body.valor:
                return JSONResponse(status_code=400, content={"erro": "Saldo insuficiente."})
            vetor = relogio.evento_local()
            conta["saldo"] -= body.valor
        else:
            return JSONResponse(status_code=400, content={"erro": "Tipo de operação pendente não suportado."})

        registro.registrar("SINCRONIZACAO_OFFLINE", vetor, {"id": id, "tipo": body.tipo, "valor": body.valor})
        return _conta_publica(conta)



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


class SincronizarBody(BaseModel):
    # tipo e str (nao Literal) para manter o contrato do enunciado: tipo desconhecido -> 400
    # com a mensagem literal, e nao 422 do Pydantic.
    tipo: str
    valor: float
    vetorConhecido: List[int]


def _conta_publica(conta: dict) -> dict:
    """Conta sem o campo senha (mesmo formato das demais rotas)."""
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/sincronizar")
def sincronizar_operacao_pendente(
    id: int,
    body: SincronizarBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    """
    Sprint 3 (Parte E): aplica uma operacao feita offline pelo app, SE o vetor que o app
    conhecia ainda for igual ao vetor atual da agencia. Caso contrario, 409 com o estado atual.

    Contrato (identico ao sincronizarOperacaoPendente do roteiro): erros usam a chave "erro"
    e mensagens literais do enunciado.
    """
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    conta = contas.get(id)
    if conta is None:
        return JSONResponse(status_code=404, content={"erro": "Conta nÃ£o encontrada nesta agÃªncia."})

    if len(body.vetorConhecido) != config.NUMERO_AGENCIAS:
        return JSONResponse(status_code=400, content={"erro": "vetorConhecido invÃ¡lido."})

    # Trecho critico ATOMICO: comparar o vetor e aplicar a operacao sem que outra thread
    # (consumidor RabbitMQ, Bully, heartbeat, outras requisicoes) avance o vetor no meio.
    with relogio.travar():
        vetor_atual = relogio.obter_vetor_atual()
        relacao = comparar_vetores(body.vetorConhecido, vetor_atual)

        if relacao != "IGUAIS":
            # outras operacoes aconteceram na agencia desde a ultima sincronizacao do app:
            # nao aplica cegamente, devolve o estado atual para o app decidir
            return JSONResponse(
                status_code=409,
                content={
                    "erro": "Conflito detectado: o estado da conta mudou desde a Ãºltima sincronizaÃ§Ã£o do app.",
                    "vetorConhecido": body.vetorConhecido,
                    "vetorAtual": vetor_atual,
                    "contaAtual": _conta_publica(conta),
                },
            )

        if body.tipo == "DEPOSITO":
            vetor = relogio.evento_local()
            conta["saldo"] += body.valor
        elif body.tipo == "SAQUE":
            if conta["saldo"] < body.valor:
                return JSONResponse(status_code=400, content={"erro": "Saldo insuficiente."})
            vetor = relogio.evento_local()
            conta["saldo"] -= body.valor
        else:
            return JSONResponse(status_code=400, content={"erro": "Tipo de operaÃ§Ã£o pendente nÃ£o suportado."})

        registro.registrar("SINCRONIZACAO_OFFLINE", vetor, {"id": id, "tipo": body.tipo, "valor": body.valor})
        return _conta_publica(conta)



class SincronizarBody(BaseModel):
    # tipo e str (nao Literal) para manter o contrato do enunciado: tipo desconhecido -> 400
    # com a mensagem literal, e nao 422 do Pydantic.
    tipo: str
    valor: float
    vetorConhecido: List[int]


def _conta_publica(conta: dict) -> dict:
    """Conta sem o campo senha (mesmo formato das demais rotas)."""
    return {"id": conta["id"], "nomeAluno": conta["nomeAluno"], "saldo": conta["saldo"]}


@router.post("/contas/{id}/sincronizar")
def sincronizar_operacao_pendente(
    id: int,
    body: SincronizarBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    """
    Sprint 3 (Parte E): aplica uma operacao feita offline pelo app, SE o vetor que o app
    conhecia ainda for igual ao vetor atual da agencia. Caso contrario, 409 com o estado atual.

    Contrato (identico ao sincronizarOperacaoPendente do roteiro): erros usam a chave "erro"
    e mensagens literais do enunciado.
    """
    contas = request.app.state.contas
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    conta = contas.get(id)
    if conta is None:
        return JSONResponse(status_code=404, content={"erro": "Conta não encontrada nesta agência."})

    if len(body.vetorConhecido) != config.NUMERO_AGENCIAS:
        return JSONResponse(status_code=400, content={"erro": "vetorConhecido inválido."})

    # Trecho critico ATOMICO: comparar o vetor e aplicar a operacao sem que outra thread
    # (consumidor RabbitMQ, Bully, heartbeat, outras requisicoes) avance o vetor no meio.
    with relogio.travar():
        vetor_atual = relogio.obter_vetor_atual()
        relacao = comparar_vetores(body.vetorConhecido, vetor_atual)

        if relacao != "IGUAIS":
            # outras operacoes aconteceram na agencia desde a ultima sincronizacao do app:
            # nao aplica cegamente, devolve o estado atual para o app decidir
            return JSONResponse(
                status_code=409,
                content={
                    "erro": "Conflito detectado: o estado da conta mudou desde a última sincronização do app.",
                    "vetorConhecido": body.vetorConhecido,
                    "vetorAtual": vetor_atual,
                    "contaAtual": _conta_publica(conta),
                },
            )

        if body.tipo == "DEPOSITO":
            vetor = relogio.evento_local()
            conta["saldo"] += body.valor
        elif body.tipo == "SAQUE":
            if conta["saldo"] < body.valor:
                return JSONResponse(status_code=400, content={"erro": "Saldo insuficiente."})
            vetor = relogio.evento_local()
            conta["saldo"] -= body.valor
        else:
            return JSONResponse(status_code=400, content={"erro": "Tipo de operação pendente não suportado."})

        registro.registrar("SINCRONIZACAO_OFFLINE", vetor, {"id": id, "tipo": body.tipo, "valor": body.valor})
        return _conta_publica(conta)

