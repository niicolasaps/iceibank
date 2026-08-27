"""
lamport_clock.py — Relógio Lógico de Lamport (Seção 6 / Parte B).

O Relógio de Lamport é um contador inteiro por processo que garante
ordenação causal de eventos em sistemas distribuídos.

Regras fundamentais (Lamport, 1978):
  1. Antes de qualquer evento local: contador += 1
  2. Ao ENVIAR uma mensagem: contador += 1, e esse valor vai junto na mensagem
  3. Ao RECEBER uma mensagem com timestamp T:
        contador = max(contador, T) + 1

A regra 3 é o núcleo do algoritmo: garante que o receptor sempre fique
"na frente" do remetente, preservando a relação happens-before (→).

Referência: Lamport, L. (1978). Time, Clocks, and the Ordering of Events
in a Distributed System. Communications of the ACM, 21(7), 558–565.
"""


class RelogioLamport:
    """
    Implementação do Relógio Lógico de Lamport.

    NOTA SOBRE THREAD-SAFETY:
    --------------------------
    Esta implementação NÃO usa threading.Lock. Isso é intencional:
    o Uvicorn, quando executado com 1 worker (padrão para desenvolvimento),
    usa um único loop de eventos asyncio — portanto, os handlers de requisição
    correm de forma concorrente mas NÃO paralela. Não há condição de corrida.

    SE você rodar com múltiplos workers (ex: uvicorn --workers 4), cada worker
    é um PROCESSO separado com seu próprio GIL e seu próprio contador — então
    o relógio ficaria INCONSISTENTE entre workers (cada um teria seu próprio
    valor de contador). Nesse cenário, a solução correta seria:
      - Usar um store externo compartilhado (Redis, banco) para o contador, OU
      - Garantir afinidade de sessão (sticky routing) por agência.

    SE você usar threads dentro do mesmo processo (ex: ThreadPoolExecutor),
    aí sim seria necessário um threading.Lock em torno das três operações:

        import threading
        self._lock = threading.Lock()

        def evento_local(self) -> int:
            with self._lock:
                self._contador += 1
                return self._contador
    """

    def __init__(self) -> None:
        # Contador interno — começa em 0, nunca é decrementado.
        self._contador: int = 0

    # ------------------------------------------------------------------
    # Propriedade de leitura (sem incremento — apenas leitura de estado)
    # ------------------------------------------------------------------

    @property
    def valor(self) -> int:
        """Retorna o valor atual do relógio sem modificá-lo."""
        return self._contador

    # ------------------------------------------------------------------
    # Os três métodos do protocolo de Lamport
    # ------------------------------------------------------------------

    def evento_local(self) -> int:
        """
        Deve ser chamado ANTES de qualquer evento local significativo
        (ex: criar conta, depositar, sacar).

        Por que incrementar ANTES? Porque queremos que o timestamp
        registrado no log represente o momento lógico em que o evento
        OCORREU, não um instante anterior a ele. Se incrementássemos
        depois, dois eventos poderiam ser carimbados com o mesmo valor.

        Retorna o timestamp a ser associado ao evento.
        """
        self._contador += 1
        return self._contador

    def ao_enviar(self) -> int:
        """
        Deve ser chamado imediatamente ANTES de enviar uma mensagem
        a outra agência (chamada HTTP de saída).

        O valor retornado deve ser incluído na mensagem enviada
        (ex: header X-Lamport-Timestamp ou campo no corpo JSON)
        para que o receptor possa atualizar seu próprio relógio.

        Nota: ao_enviar e evento_local têm o mesmo comportamento;
        são métodos distintos por clareza semântica — deixam explícito
        NO CÓDIGO se o evento é local ou é um envio de mensagem.
        """
        self._contador += 1
        return self._contador

    def ao_receber(self, timestamp_recebido: int) -> int:
        """
        Deve ser chamado quando uma mensagem de outra agência é recebida,
        ANTES de processar a mensagem.

        Args:
            timestamp_recebido: valor do relógio do remetente no momento
                                 do envio (extraído do header/corpo da msg).

        Por que max(local, recebido) + 1?
        - O "+1" representa o próprio evento de recepção (aconteceu algo).
        - O "max" garante que o receptor nunca fique "no passado" em relação
          ao remetente: se recebi uma mensagem com timestamp 50, meu próximo
          evento DEVE ter timestamp > 50, senão pareceria que ele ocorreu
          antes de algo que o causou.

        Retorna o novo valor do relógio.
        """
        self._contador = max(self._contador, timestamp_recebido) + 1
        return self._contador
