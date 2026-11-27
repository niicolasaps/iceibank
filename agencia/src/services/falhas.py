"""
falhas.py - Injecao de falhas para os testes do 2PC (Sprint 4, Parte B)
Equivalente ao falhas.js do roteiro Node.js.

Derruba o PROCESSO INTEIRO em um ponto exato do protocolo, UMA unica vez: um arquivo
marcador (falha-<id>-<ponto>.consumida, em DATA_DIR) impede que a agencia caia de novo toda
vez que o Docker a reiniciar (o que causaria um loop de quedas).

Uso (PowerShell, fora de container): $env:FALHA_2PC="participante-apos-votar"
Uso (compose): FALHA_2PC_0 / FALHA_2PC_1 / FALHA_2PC_2 no .env.
Para repetir um cenario, apague o arquivo falha-*.consumida de DATA_DIR.

Por que os._exit(1) e nao sys.exit(1)? sys.exit() levanta SystemExit, e dentro de uma thread
(handlers `def` do FastAPI e tarefas em background rodam em threads) isso so encerraria a
thread - o processo continuaria vivo. os._exit(1) derruba o processo imediatamente, como o
process.exit(1) do Node, sem rodar finalizadores: e exatamente o que uma queda real faz.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from src import config


def falhar(ponto: str) -> None:
    if os.environ.get("FALHA_2PC") != ponto:
        return
    id_agencia = os.environ.get("AGENCIA_ID", "0")
    marcador = Path(config.DATA_DIR) / f"falha-{id_agencia}-{ponto}.consumida"
    if marcador.exists():
        return
    marcador.write_text(datetime.now().isoformat(), encoding="utf-8")
    print(f"[FALHA INJETADA] {ponto}: derrubando a agência {id_agencia} agora", file=sys.stderr, flush=True)
    os._exit(1)
