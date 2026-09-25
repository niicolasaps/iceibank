"""
status_controller.py - Funcionalidade adicional do Sprint 1 (GET /status)
Atualizado no Sprint 2 para exibir o relogio vetorial no lugar do Lamport.
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
    return {
        "agencia": request.app.state.id_agencia,
        "relogioVetorialAtual": relogio.vetor_atual(),
        "quantidadeContas": len(request.app.state.contas),
    }