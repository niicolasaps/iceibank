"""
contas_controller.py - Controlador de Contas do ICEIBank (Sprint 4: persistencia atomica em disco)
Equivalente ao contasController.js do roteiro Node.js.

Sprint 4 (Parte A):
  - As contas vivem em `estado.contas` (EstadoDuravel) e todo endpoint que muda saldo chama `estado.salvar()`.
  - Toda secao critica "ler -> mudar -> salvar()" roda sob `with estado.lock:`.
  - O saque respeita `saldo_disponivel(conta)` (saldo - reservado) e devolve 422 quando insuficiente.
  - Compatibilidade com Sprints 1-3:
      * POST /contas aceita `titular` (Sprint 4) OU `nomeAluno` (Sprints 1-3) e `id` opcional
        (se ausente, gera com `_proximo_id()`; se presente, valida particao 400 e duplicidade 409).
      * As respostas incluem tanto `titular` quanto `nomeAluno`, alem de `saldo`, `reservado` e `disponivel`.
      * GET /contas/{id} continua devolvendo `vetorAtual` (Sprint 3 - offline-first).
      * POST /contas/{id}/sincronizar (Sprint 3 - Parte E) continua ativo e usa `estado.contas` + `estado.salvar()`.
"""

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import config
from src.services.auth import get_usuario_atual
from src.services.comparar_vetores import comparar_vetores
from src.services.mensageria import publicar
from src.services.saldo import saldo_disponivel

router = APIRouter()

# Limite para notificacao de saldo baixo (Sprint 2 - publicada se RABBITMQ_URL estiver ativa)
LIMITE_SALDO_BAIXO: float = 50.0


class CriarContaBody(BaseModel):
    id: Optional[int] = None
    titular: Optional[str] = None
    nomeAluno: Optional[str] = None
    saldoInicial: float = 0.0
    senha: str = "1234"


class ValorBody(BaseModel):
    valor: float


class SincronizarBody(BaseModel):
    tipo: str
    valor: float
    vetorConhecido: List[int]


def _proximo_id(id_agencia: int, contas: dict) -> int:
    """ids das contas desta agencia: idAgencia, idAgencia+3, idAgencia+6..."""
    existentes = list(contas.keys())
    if not existentes:
        return id_agencia
    return max(existentes) + config.NUMERO_AGENCIAS


def _visao(conta: dict, vetor_atual: Optional[List[int]] = None) -> dict:
    """Visao publica da conta: compativel com o contrato do Sprint 4 e dos Sprints 1-3."""
    nome = conta.get("titular") or conta.get("nomeAluno") or f"Usuario {conta['id']}"
    reservado = conta.get("reservado") or 0
    resp = {
        "id": conta["id"],
        "titular": nome,
        "nomeAluno": nome,
        "saldo": conta["saldo"],
        "reservado": reservado,
        "disponivel": saldo_disponivel(conta),
    }
    if vetor_atual is not None:
        resp["vetorAtual"] = vetor_atual
    return resp


async def _verificar_saldo_baixo(id_conta: int, saldo_atual: float, id_agencia: int) -> None:
    """Publica alerta de saldo baixo se saldo < LIMITE_SALDO_BAIXO (apenas se RabbitMQ estiver ativo)."""
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
    estado = request.app.state.estado
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    nome = (body.titular or body.nomeAluno or "").strip()
    if not nome or body.saldoInicial < 0:
        raise HTTPException(
            status_code=400,
            detail="Informe titular e saldoInicial (número >= 0).",
        )

    with estado.lock:
        if body.id is not None:
            if config.agencia_responsavel(body.id) != id_agencia:
                raise HTTPException(status_code=400, detail=f"Conta {body.id} nao pertence a esta agencia.")
            if body.id in estado.contas:
                raise HTTPException(status_code=409, detail="Conta ja existe.")
            novo_id = body.id
        else:
            novo_id = _proximo_id(id_agencia, estado.contas)

        conta = {
            "id": novo_id,
            "titular": nome,
            "nomeAluno": nome,
            "saldo": float(body.saldoInicial),
            "reservado": 0.0,
            "senha": body.senha,
        }
        estado.contas[novo_id] = conta
        estado.salvar()
        ts = relogio.evento_local()
        registro.registrar("CONTA_CRIADA", ts, {"id": conta["id"]})
        return _visao(conta)


@router.get("/contas/{id}")
def consultar_saldo(
    id: int,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    estado = request.app.state.estado
    relogio = request.app.state.relogio
    with estado.lock:
        conta = estado.contas.get(id)
        if conta is None:
            raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
        return _visao(conta, vetor_atual=relogio.obter_vetor_atual())


@router.post("/contas/{id}/depositar")
async def depositar(
    id: int,
    body: ValorBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    estado = request.app.state.estado
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    if body.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido.")

    with estado.lock:
        conta = estado.contas.get(id)
        if conta is None:
            raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
        conta["saldo"] += body.valor
        estado.salvar()
        ts = relogio.evento_local()
        registro.registrar("DEPOSITO", ts, {"id": conta["id"], "valor": body.valor})
        visao_atual = _visao(conta)

    await _verificar_saldo_baixo(id, visao_atual["saldo"], id_agencia)
    return visao_atual


@router.post("/contas/{id}/sacar")
async def sacar(
    id: int,
    body: ValorBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    estado = request.app.state.estado
    relogio = request.app.state.relogio
    registro = request.app.state.registro
    id_agencia = request.app.state.id_agencia

    if body.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido.")

    with estado.lock:
        conta = estado.contas.get(id)
        if conta is None:
            raise HTTPException(status_code=404, detail="Conta não encontrada nesta agência.")
        if saldo_disponivel(conta) < body.valor:
            raise HTTPException(status_code=422, detail="Saldo insuficiente.")
        conta["saldo"] -= body.valor
        estado.salvar()
        ts = relogio.evento_local()
        registro.registrar("SAQUE", ts, {"id": conta["id"], "valor": body.valor})
        visao_atual = _visao(conta)

    await _verificar_saldo_baixo(id, visao_atual["saldo"], id_agencia)
    return visao_atual


@router.post("/contas/{id}/sincronizar")
def sincronizar_operacao_pendente(
    id: int,
    body: SincronizarBody,
    request: Request,
    _usuario=Depends(get_usuario_atual),
):
    """
    Sprint 3 (Parte E) integrado com o EstadoDuravel do Sprint 4:
    compara vetorConhecido com vetorAtual e aplica sobre estado.contas, salvando em disco.
    """
    estado = request.app.state.estado
    relogio = request.app.state.relogio
    registro = request.app.state.registro

    with estado.lock:
        conta = estado.contas.get(id)
        if conta is None:
            return JSONResponse(status_code=404, content={"erro": "Conta não encontrada nesta agência."})

        if len(body.vetorConhecido) != config.NUMERO_AGENCIAS:
            return JSONResponse(status_code=400, content={"erro": "vetorConhecido inválido."})

        with relogio.travar():
            vetor_atual = relogio.obter_vetor_atual()
            relacao = comparar_vetores(body.vetorConhecido, vetor_atual)

            if relacao != "IGUAIS":
                return JSONResponse(
                    status_code=409,
                    content={
                        "erro": "Conflito detectado: o estado da conta mudou desde a última sincronização do app.",
                        "vetorConhecido": body.vetorConhecido,
                        "vetorAtual": vetor_atual,
                        "contaAtual": _visao(conta),
                    },
                )

            if body.tipo == "DEPOSITO":
                vetor = relogio.evento_local()
                conta["saldo"] += body.valor
            elif body.tipo == "SAQUE":
                if saldo_disponivel(conta) < body.valor:
                    return JSONResponse(status_code=400, content={"erro": "Saldo insuficiente."})
                vetor = relogio.evento_local()
                conta["saldo"] -= body.valor
            else:
                return JSONResponse(status_code=400, content={"erro": "Tipo de operação pendente não suportado."})

            estado.salvar()
            registro.registrar("SINCRONIZACAO_OFFLINE", vetor, {"id": id, "tipo": body.tipo, "valor": body.valor})
            return _visao(conta)
