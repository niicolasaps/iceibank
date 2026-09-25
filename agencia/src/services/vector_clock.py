"""
vector_clock.py - Relogio Vetorial (substitui lamport_clock.py do Sprint 1)
Equivalente ao vectorClock.js do roteiro Node.js.

O Relogio Vetorial resolve a limitacao do Lamport:
  - Lamport: timestamps diferentes podem OU NAO ser causalmente relacionados (nao da pra saber).
  - Vetorial: dado V1 e V2, conseguimos determinar com CERTEZA se V1 < V2 (causal) ou sao concorrentes.

Regras (identicas ao vectorClock.js):
  1. evento_local():  incrementa apenas a propria posicao no vetor.
  2. ao_enviar():     incrementa a propria posicao e retorna copia do vetor inteiro.
  3. ao_receber(V):   para cada posicao i, vetor[i] = max(vetor[i], V[i]); depois incrementa propria posicao.

NOTA DE THREAD-SAFETY:
  O consumidor pika roda em thread separada (ver main.py) e chama ao_receber().
  Adicionamos threading.Lock para proteger as tres operacoes de atualizacao concorrente.
"""

import threading
from typing import List


class RelogioVetorial:
    """
    Implementa o Relogio Vetorial.
    Equivalente a classe RelogioVetorial do vectorClock.js.
    """

    def __init__(self, id_agencia: int, numero_agencias: int) -> None:
        self.id_agencia = id_agencia
        self.numero_agencias = numero_agencias
        self.vetor: List[int] = [0] * numero_agencias
        self._lock = threading.Lock()

    def evento_local(self) -> List[int]:
        """
        Chamado antes de qualquer evento interno (depositar, sacar, criar conta).
        Incrementa apenas a propria posicao e retorna copia do vetor.
        """
        with self._lock:
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    def ao_enviar(self) -> List[int]:
        """
        Chamado antes de publicar uma mensagem para outra agencia.
        Incrementa a propria posicao e retorna copia do vetor para anexar a mensagem.
        """
        with self._lock:
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    def ao_receber(self, vetor_recebido: List[int]) -> List[int]:
        """
        Chamado ao consumir uma mensagem de outra agencia.
        Para cada posicao i: vetor[i] = max(vetor[i], vetor_recebido[i]).
        Depois incrementa a propria posicao (o recebimento e um evento local).
        """
        with self._lock:
            for i in range(self.numero_agencias):
                self.vetor[i] = max(self.vetor[i], vetor_recebido[i])
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    def vetor_atual(self) -> List[int]:
        """Retorna copia do vetor atual sem modificar (para o GET /status)."""
        with self._lock:
            return list(self.vetor)
