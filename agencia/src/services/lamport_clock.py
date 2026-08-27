"""
lamport_clock.py — Relógio Lógico de Lamport
Equivalente ao lamportClock.js do exemplo Node.js/Express do roteiro.

O Relógio de Lamport garante ordenação causal de eventos em sistemas distribuídos.
Cada processo mantém um contador inteiro local. As três operações abaixo implementam
as regras descritas por Leslie Lamport (1978):

  1. evento_local(): antes de qualquer evento interno, o processo incrementa seu contador.
  2. ao_enviar(): antes de enviar uma mensagem, o processo incrementa e anexa o timestamp.
  3. ao_receber(ts): ao receber uma mensagem com timestamp ts, o processo atualiza seu
     contador para max(local, ts) + 1 — o "+1" marca que o recebimento em si é um evento
     posterior a tudo que o remetente já havia visto.

NOTA DE THREAD-SAFETY:
  Esta implementação pressupõe um único worker/processo (padrão do uvicorn sem --workers N).
  Se você rodar com múltiplos workers (uvicorn src.main:app --workers 4), cada processo
  teria sua própria instância de RelogioLamport na memória, sem sincronização entre eles.
  Nesse cenário seria necessário:
    - Um threading.Lock envolvendo as três operações (para múltiplas threads no mesmo processo), OU
    - Um contador compartilhado externo (Redis, banco, etc.) para múltiplos processos.
  Para o Sprint 1, um único worker é suficiente e nenhum lock é necessário.
"""


class RelogioLamport:
    """
    Implementa o Relógio Lógico de Lamport.
    Equivalente à classe RelogioLamport do lamportClock.js.
    """

    def __init__(self) -> None:
        self.contador: int = 0

    def evento_local(self) -> int:
        """
        Deve ser chamado antes de qualquer evento interno (criar conta, depositar, sacar).
        Incrementa o contador e retorna o novo valor — esse valor vira o timestampLamport
        do evento registrado no log.

        Por que incrementar ANTES de aplicar a mudança?
        O timestamp marca o instante lógico em que o evento ocorre. Incrementar antes
        garante que eventos posteriores no mesmo processo terão timestamps maiores,
        preservando a ordem causal: se A causa B, então ts(A) < ts(B).
        """
        self.contador += 1
        return self.contador

    def ao_enviar(self) -> int:
        """
        Deve ser chamado imediatamente antes de enviar uma mensagem a outra agência.
        Incrementa o contador (o envio é um evento) e retorna o valor para ser
        anexado à mensagem — a agência destinatária usará esse valor em ao_receber().
        """
        self.contador += 1
        return self.contador

    def ao_receber(self, timestamp_recebido: int) -> int:
        """
        Deve ser chamado ao receber uma mensagem de outra agência que carregue um timestamp.
        Atualiza o contador para max(local, recebido) + 1.

        O "+1" é obrigatório: o recebimento em si é um evento que deve ser posterior
        a qualquer coisa que o remetente já tenha visto (timestamp_recebido) E a qualquer
        coisa que este processo já tenha visto (self.contador).
        """
        self.contador = max(self.contador, timestamp_recebido) + 1
        return self.contador
