"""
status_controller.py — Health-check por agência (Funcionalidade Adicional)
Seção 2.1 do roteiro: "Rota de status/health-check por agência, retornando o
relógio de Lamport atual e a quantidade de contas sob sua responsabilidade."

Endpoint: GET /status
Retorno: {"agencia": N, "relogioLamportAtual": N, "quantidadeContas": N}

Decisão de design: esta rota NÃO exige JWT.
Justificativa: health-checks são endpoints de infraestrutura, geralmente públicos
em sistemas reais (usados por load balancers, orquestradores e dashboards de
monitoramento). Expor o contador de Lamport e o total de contas não representa
risco de segurança, pois não revela dados de nenhuma conta específica.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
def status(request: Request):
    """
    Retorna o estado atual desta agência: id, relógio de Lamport e total de contas.
    Não incrementa o relógio — é uma leitura de estado, não um evento.
    """
    return {
        "agencia": request.app.state.id_agencia,
        "relogioLamportAtual": request.app.state.relogio.contador,
        "quantidadeContas": len(request.app.state.contas),
    }
