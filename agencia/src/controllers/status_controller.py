"""
status_controller.py - Funcionalidade adicional do Sprint 1 (GET /status)
Atualizado no Sprint 4 para ler a quantidade de contas do EstadoDuravel.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
def status(request: Request):
    """
    Health-check publico (sem JWT).
    Retorna o estado atual da agencia: id, vetor de relogio e quantidade de contas.
    """
    relogio = request.app.state.relogio
    estado = request.app.state.estado
    with estado.lock:
        qtd = len(estado.contas)
    return {
        "agencia": request.app.state.id_agencia,
        "relogioVetorialAtual": relogio.vetor_atual(),
        "quantidadeContas": qtd,
    }


@router.get("/saude")
def saude(request: Request):
    """
    Funcionalidade adicional do Sprint 4 (Secao 2.1):
    Endpoint publico GET /saude (sem JWT e sem x-token-interno) usado pelo `healthcheck`
    do docker-compose.yml para monitorar a saude dos containers das 3 agencias.
    """
    return {
        "status": "ok",
        "idAgencia": request.app.state.id_agencia,
        "liderAtual": request.app.state.bully.obter_lider_atual(),
    }
