"""
bully_service.py - Algoritmo de Bully (eleicao de lider) - Sprint 3
Equivalente ao bullyService.js do roteiro Node.js.

Parte A: mensagens de eleicao e coordenador.

Regras (identicas ao bullyService.js):
  1. iniciar_eleicao(): envia /bully/eleicao a todas as agencias de ID MAIOR.
     Se nenhuma responder, eu venco (tornar_me_lider).
  2. tornar_me_lider(): anuncia /bully/coordenador a todas as outras agencias.
  3. receber_eleicao(): ao receber eleicao de ID menor, inicio minha propria eleicao.
  4. receber_coordenador(): guarda o lider anunciado.

NOTA DE THREAD-SAFETY:
  Em Node ha uma unica thread; aqui as rotas HTTP, a eleicao e (na Parte B) o heartbeat
  rodam em threads diferentes. Por isso lider_atual e eleicao_em_andamento sao protegidos
  por threading.Lock. O lock NUNCA e mantido durante chamadas HTTP (evita travar a agencia).

Constantes ficam no topo do modulo (facilita torna-las configuraveis por env var depois).
"""

import threading
import time
from typing import List, Optional

import httpx

from src import config
from src.services.event_log import RegistroEventos
from src.services.vector_clock import RelogioVetorial

# --- Constantes (equivalente a TIMEOUT_MS = 1000 do Node) ---
TIMEOUT_S: float = 1.0
# Pequena espera antes da eleicao inicial: o startup do FastAPI roda ANTES do socket
# ser aberto, entao damos tempo ao servidor para comecar a ouvir (ver main.py).
ATRASO_INICIAL_S: float = 1.0
# Parte B: intervalo padrao do heartbeat (equivalente a intervaloMs = 3000 do Node).
INTERVALO_HEARTBEAT_S: float = 3.0


class ServicoBully:
    """Equivalente a criarServicoBully(idAgencia, relogio, registro) do Node."""

    def __init__(self, id_agencia: int, relogio: RelogioVetorial, registro: RegistroEventos) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self._lider_atual: Optional[int] = None
        self._eleicao_em_andamento: bool = False
        self._lock = threading.Lock()

    def _agencias_com_id_maior(self) -> List[dict]:
        return [a for a in config.AGENCIAS if a["id"] > self.id_agencia]

    def iniciar_eleicao(self) -> None:
        # check-and-set atomico (em Node isso era atomico de graca, aqui precisa de lock)
        with self._lock:
            if self._eleicao_em_andamento:
                return
            self._eleicao_em_andamento = True

        vetor = self.relogio.evento_local()
        self.registro.registrar("ELEICAO_INICIADA", vetor, {"idAgencia": self.id_agencia})

        maiores = self._agencias_com_id_maior()
        alguem_respondeu = False

        for agencia in maiores:
            try:
                vetor_envio = self.relogio.ao_enviar()
                httpx.post(
                    f"{agencia['url']}/bully/eleicao",
                    json={"origemId": self.id_agencia, "vetorEnvio": vetor_envio},
                    timeout=TIMEOUT_S,
                )
                alguem_respondeu = True
            except Exception:
                # agencia fora do ar ou nao respondeu a tempo - ignora e segue
                pass

        with self._lock:
            self._eleicao_em_andamento = False

        if not alguem_respondeu:
            self.tornar_me_lider()
        # se alguem maior respondeu, e essa agencia quem vai conduzir a propria
        # eleicao e eventualmente anunciar o resultado via /bully/coordenador

    def tornar_me_lider(self) -> None:
        with self._lock:
            self._lider_atual = self.id_agencia
        vetor = self.relogio.evento_local()
        self.registro.registrar("TORNOU_LIDER", vetor, {"idAgencia": self.id_agencia})
        for agencia in config.AGENCIAS:
            if agencia["id"] == self.id_agencia:
                continue
            try:
                vetor_envio = self.relogio.ao_enviar()
                httpx.post(
                    f"{agencia['url']}/bully/coordenador",
                    json={"liderId": self.id_agencia, "vetorEnvio": vetor_envio},
                    timeout=TIMEOUT_S,
                )
            except Exception:
                # agencia fora do ar - vai descobrir o lider quando voltar
                pass

    def receber_eleicao(self, origem_id: int, vetor_recebido: List[int]) -> None:
        vetor = self.relogio.ao_receber(vetor_recebido)
        self.registro.registrar("ELEICAO_RECEBIDA", vetor, {"de": origem_id, "minhaId": self.id_agencia})
        # o 200 da rota ja serve como "OK" implicito - e inicio minha propria eleicao,
        # pois posso ser o novo lider. Roda em thread: a rota NAO pode esperar
        # (dispara e esquece, como o iniciarEleicao() sem await do Node).
        threading.Thread(target=self.iniciar_eleicao, daemon=True).start()

    def receber_coordenador(self, lider_id: int, vetor_recebido: List[int]) -> None:
        with self._lock:
            self._lider_atual = lider_id
        vetor = self.relogio.ao_receber(vetor_recebido)
        self.registro.registrar("LIDER_ANUNCIADO", vetor, {"liderId": lider_id, "agencia": self.id_agencia})

    def obter_lider_atual(self) -> Optional[int]:
        with self._lock:
            return self._lider_atual

    # --- Parte B: heartbeat e failover ---

    def verificar_lider(self) -> None:
        with self._lock:
            lider_atual = self._lider_atual

        if lider_atual is None:
            self.iniciar_eleicao()
            return
        if lider_atual == self.id_agencia:
            return  # eu sou o lider, nada a verificar

        lider_info = next(a for a in config.AGENCIAS if a["id"] == lider_atual)
        try:
            httpx.get(f"{lider_info['url']}/bully/lider", timeout=TIMEOUT_S)
        except Exception:
            vetor = self.relogio.evento_local()
            self.registro.registrar(
                "LIDER_NAO_RESPONDEU", vetor, {"liderAtual": lider_atual, "agencia": self.id_agencia}
            )
            with self._lock:
                self._lider_atual = None
            self.iniciar_eleicao()

    def iniciar_heartbeat(self, intervalo_s: float = INTERVALO_HEARTBEAT_S) -> None:
        """Equivalente ao setInterval(verificarLider, intervaloMs) - roda em thread daemon."""
        def _loop():
            while True:
                time.sleep(intervalo_s)
                try:
                    self.verificar_lider()
                except Exception as erro:
                    # uma falha pontual nao pode matar o heartbeat
                    print(f"[Bully] Erro no heartbeat: {erro}")

        threading.Thread(target=_loop, daemon=True).start()
