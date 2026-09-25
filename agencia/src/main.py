"""
main.py - Ponto de entrada da agencia ICEIBank

Sprint 2:
  - RelogioVetorial substitui RelogioLamport
  - Consumidor RabbitMQ (pika) iniciado em thread separada no startup
  - RABBITMQ_URL deve estar definida como variavel de ambiente

Como executar localmente:
  $env:RABBITMQ_URL="amqps://usuario:senha@host.cloudamqp.com/vhost"
  $env:AGENCIA_ID="0"; python -m uvicorn src.main:app --port 4046 --reload
  $env:AGENCIA_ID="1"; python -m uvicorn src.main:app --port 4047 --reload
  $env:AGENCIA_ID="2"; python -m uvicorn src.main:app --port 4048 --reload
"""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.routes import router
from src.services.auth import criar_token_servico
from src.services.event_log import RegistroEventos
from src.services.mensageria import assinar
from src.services.vector_clock import RelogioVetorial

id_agencia = int(os.environ.get("AGENCIA_ID", "0"))

agencia_cfg = next((a for a in config.AGENCIAS if a["id"] == id_agencia), None)
if agencia_cfg is None:
    print(f"Agencia {id_agencia} nao configurada em config.py", file=sys.stderr)
    sys.exit(1)

app = FastAPI(
    title=f"ICEIBank - Agencia {id_agencia}",
    description="API REST do ICEIBank com Relogio Vetorial e RabbitMQ (Sprint 2)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.id_agencia = id_agencia
app.state.relogio = RelogioVetorial(id_agencia, config.NUMERO_AGENCIAS)
app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
app.state.contas = {}
app.state.token_servico = criar_token_servico()

app.include_router(router)


@app.on_event("startup")
def iniciar_consumidor():
    """
    Inicia o consumidor RabbitMQ em thread separada ao subir o servidor.
    Thread daemon=True: termina automaticamente quando o processo para.
    """
    relogio = app.state.relogio
    registro = app.state.registro
    contas = app.state.contas

    def processar_credito(mensagem):
        id_conta = mensagem.get("idConta")
        valor = mensagem.get("valor")
        vetor_envio = mensagem.get("vetorEnvio")
        origem_agencia = mensagem.get("origemAgencia")

        vetor = relogio.ao_receber(vetor_envio)

        conta = contas.get(id_conta)
        if conta is None:
            registro.registrar("CREDITO_REMOTO_FALHOU", vetor, {
                "idConta": id_conta,
                "valor": valor,
                "origemAgencia": origem_agencia,
                "motivo": "conta nao encontrada",
            })
            print(f"[Consumidor] ATENCAO: conta {id_conta} nao encontrada - credito de R${valor} nao aplicado!")
            return

        conta["saldo"] += valor
        saldo_fmt = f"{conta['saldo']:.2f}"
        registro.registrar("TRANSFERENCIA_CREDITO_REMOTO", vetor, {
            "idConta": id_conta,
            "valor": valor,
            "origemAgencia": origem_agencia,
        })
        print(f"[Consumidor] Credito de R${valor} aplicado na conta {id_conta}. Novo saldo: R${saldo_fmt}")

    assinar(id_agencia, processar_credito)


porta = os.environ.get("PORT", str(config.PORTA_BASE + id_agencia))
print(f"[Agencia {id_agencia}] ouvindo na porta {porta}")
print(f"[Agencia {id_agencia}] Documentacao: http://localhost:{porta}/docs")