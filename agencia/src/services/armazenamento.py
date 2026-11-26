"""
armazenamento.py - Estado duravel da agencia (Sprint 4, Parte A)
Equivalente ao armazenamento.js do roteiro Node.js.

Tudo que precisa sobreviver a uma queda (contas, reservas e o estado das transacoes
distribuidas) vive em UM unico arquivo por agencia, gravado de forma ATOMICA:
escreve num arquivo temporario, forca a gravacao em disco (fsync) e so entao troca o
nome para o arquivo definitivo (os.replace e atomico).

Formato (identico ao do Node): Maps viram listas de pares [chave, valor]. Isso preserva
chaves NUMERICAS (ids de conta); um dict com chaves int viraria chaves str no JSON e,
ao recarregar, estado.contas.get(0) falharia.

CONCORRENCIA (diferenca crucial Node -> Python):
  No Node, cada requisicao roda numa unica thread. Aqui, handlers `def` rodam num pool
  de threads e o Bully/heartbeat tambem usam threads, entao ha corrida real. Por isso o
  estado tem um RLock (`estado.lock`): toda secao critica "ler -> mudar -> salvar()" deve
  ser feita com `with estado.lock:`. NUNCA segure esse lock durante uma chamada HTTP.
  Ordem de locks (evita deadlock): estado.lock SEMPRE antes do lock do relogio.
"""

import json
import os
import threading
from pathlib import Path

from src import config


class EstadoDuravel:
    def __init__(self, id_agencia: int) -> None:
        Path(config.DATA_DIR).mkdir(parents=True, exist_ok=True)
        self.caminho = Path(config.DATA_DIR) / f"estado-agencia-{id_agencia}.json"
        self.lock = threading.RLock()
        self.contas: dict = {}  # id (int) -> dict da conta
        self.coordenacoes: dict = {}  # txId (str) -> dict
        self.participacoes: dict = {}  # "txId:TIPO" (str) -> dict
        self.carregar()

    def carregar(self) -> None:
        if not self.caminho.exists():
            return
        with open(self.caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        # chaves de contas voltam a ser int (lista de pares preserva o tipo; int() garante)
        self.contas = {int(k): v for k, v in dados.get("contas", [])}
        self.coordenacoes = {k: v for k, v in dados.get("coordenacoes", [])}
        self.participacoes = {k: v for k, v in dados.get("participacoes", [])}

    def salvar(self) -> None:
        with self.lock:
            dados = {
                "contas": [[k, v] for k, v in self.contas.items()],
                "coordenacoes": [[k, v] for k, v in self.coordenacoes.items()],
                "participacoes": [[k, v] for k, v in self.participacoes.items()],
            }
            temporario = str(self.caminho) + ".tmp"
            # 1) escreve tudo num arquivo temporario  2) flush + fsync (forca ir para o disco)
            with open(temporario, "w", encoding="utf-8") as f:
                f.write(json.dumps(dados))
                f.flush()
                os.fsync(f.fileno())
            # 3) troca o nome: atomico - o arquivo definitivo nunca fica pela metade
            os.replace(temporario, self.caminho)
