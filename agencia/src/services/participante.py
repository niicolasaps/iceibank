"""
participante.py - Papel de PARTICIPANTE no 2PC (Sprint 4, Parte B)
Equivalente ao participante.js do roteiro Node.js.

Cada agencia envolvida na transferencia (a do debito e a do credito) responde a
`preparar` (fase 1: votacao) e `decidir` (fase 2: decisao).

CONCORRENCIA: toda secao critica "ler -> mudar -> salvar()" roda sob `estado.lock`
(RLock). O lock NUNCA e mantido durante uma chamada HTTP (resolver_em_duvida faz a
consulta ao coordenador FORA do lock e so depois chama decidir(), que toma o lock).
Ordem de locks: estado.lock sempre antes do lock do relogio.
"""

import threading
import time
from typing import Optional

from src import config
from src.services.cliente_interno import cliente_interno
from src.services.falhas import falhar
from src.services.saldo import saldo_disponivel

# --- Constantes (facilitam a futura funcionalidade "timeouts configuraveis") ---
TIMEOUT_S: float = 2.0
INTERVALO_RESOLUCAO_S: float = 3.0


class Participante:
    def __init__(self, id_agencia: int, relogio, registro, estado) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self.estado = estado
        self._avisou_bloqueio: set = set()
        self._resolvendo = threading.Lock()  # evita duas rodadas de resolucao ao mesmo tempo

    # FASE 1: o participante vota. So vota SIM se tem certeza de que conseguira aplicar a
    # operacao quando o coordenador mandar. E, ao votar SIM, ele se COMPROMETE: grava a
    # promessa em disco ANTES de responder.
    def preparar(self, dados: dict) -> dict:
        tx_id = dados["txId"]
        operacao = dados["operacao"]
        coordenador = dados.get("coordenador")
        vetor_envio_recebido = dados.get("vetorEnvio")

        if vetor_envio_recebido:
            self.relogio.ao_receber(vetor_envio_recebido)

        # A chave inclui o tipo porque, numa transferencia entre contas da MESMA agencia, ela
        # participa duas vezes da mesma transacao (debito e credito).
        chave = f"{tx_id}:{operacao['tipo']}"

        with self.estado.lock:
            existente = self.estado.participacoes.get(chave)
            if existente:
                # idempotencia: o coordenador pode repetir a pergunta
                voto = "NAO" if existente["estado"] == "ABORTADO" else "SIM"
                return {"voto": voto, "vetorEnvio": self.relogio.ao_enviar()}

            conta = self.estado.contas.get(operacao["idConta"])
            motivo: Optional[str] = None
            if conta is None:
                motivo = "Conta não encontrada nesta agência."
            elif operacao["tipo"] == "DEBITO" and saldo_disponivel(conta) < operacao["valor"]:
                motivo = "Saldo insuficiente."

            if motivo:
                self.estado.participacoes[chave] = {
                    "txId": tx_id,
                    "coordenador": coordenador,
                    "operacao": operacao,
                    "estado": "ABORTADO",
                    "motivo": motivo,
                }
                self.estado.salvar()
                self.registro.registrar("2PC_VOTO_NAO", self.relogio.evento_local(), {"txId": tx_id, "motivo": motivo})
                return {"voto": "NAO", "motivo": motivo, "vetorEnvio": self.relogio.ao_enviar()}

            if operacao["tipo"] == "DEBITO":
                # o dinheiro fica "travado": continua em saldo, mas nao em disponivel
                conta["reservado"] = (conta.get("reservado") or 0) + operacao["valor"]
            self.estado.participacoes[chave] = {
                "txId": tx_id,
                "coordenador": coordenador,
                "operacao": operacao,
                "estado": "PREPARADO",
            }
            self.estado.salvar()  # promessa duravel ANTES de responder SIM
            self.registro.registrar("2PC_VOTO_SIM", self.relogio.evento_local(), {"txId": tx_id, "operacao": operacao})
            falhar("participante-apos-votar")  # caiu depois de se comprometer, antes de responder
            return {"voto": "SIM", "vetorEnvio": self.relogio.ao_enviar()}

    # FASE 2: o coordenador comunica a decisao final. Aplica (ou descarta) a operacao
    # preparada. Idempotente: receber a mesma decisao duas vezes e seguro.
    def decidir(self, dados: dict) -> dict:
        tx_id = dados["txId"]
        decisao = dados["decisao"]
        vetor_envio_recebido = dados.get("vetorEnvio")

        if vetor_envio_recebido:
            self.relogio.ao_receber(vetor_envio_recebido)

        with self.estado.lock:
            minhas = [p for p in self.estado.participacoes.values() if p["txId"] == tx_id]
            if not minhas:
                if decisao == "ABORT":
                    return {"ok": True, "vetorEnvio": self.relogio.ao_enviar()}
                return {"erro": "Transação desconhecida por este participante."}

            falhar("participante-antes-de-aplicar")  # caiu com a decisao em maos, sem aplica-la
            for p in minhas:
                if p["estado"] != "PREPARADO":
                    continue
                conta = self.estado.contas[p["operacao"]["idConta"]]
                tipo = p["operacao"]["tipo"]
                valor = p["operacao"]["valor"]
                if decisao == "COMMIT":
                    if tipo == "DEBITO":
                        conta["saldo"] -= valor
                        conta["reservado"] -= valor
                    else:
                        conta["saldo"] += valor
                    p["estado"] = "COMMITADO"
                else:
                    if tipo == "DEBITO":
                        conta["reservado"] -= valor
                    p["estado"] = "ABORTADO"
                self.registro.registrar(
                    f"2PC_{decisao}_APLICADO", self.relogio.evento_local(), {"txId": tx_id, "tipo": tipo, "valor": valor}
                )
            self.estado.salvar()  # saldo, reserva e estado da transacao mudam juntos, de forma atomica
            return {"ok": True, "vetorEnvio": self.relogio.ao_enviar()}

    # Se este participante votou SIM e nunca recebeu a decisao (o coordenador caiu, a rede
    # falhou...), ele esta "em duvida": nao pode decidir sozinho. So resta perguntar ao
    # coordenador, repetidamente, ate conseguir resposta.
    def resolver_em_duvida(self) -> None:
        if not self._resolvendo.acquire(blocking=False):
            return
        try:
            # copia sob o lock; a consulta HTTP acontece FORA do lock
            with self.estado.lock:
                em_duvida = [dict(p) for p in self.estado.participacoes.values() if p["estado"] == "PREPARADO"]

            for p in em_duvida:
                coord = next(a for a in config.AGENCIAS if a["id"] == p["coordenador"])
                decisao = None
                try:
                    resp = cliente_interno.get(f"{coord['url']}/2pc/status/{p['txId']}", timeout=TIMEOUT_S)
                    resp.raise_for_status()  # httpx nao levanta em 4xx/5xx (o axios do Node levanta)
                    decisao = resp.json().get("decisao")
                except Exception:
                    if p["txId"] not in self._avisou_bloqueio:
                        self._avisou_bloqueio.add(p["txId"])
                        self.registro.registrar(
                            "2PC_BLOQUEADA_AGUARDANDO_COORDENADOR",
                            self.relogio.evento_local(),
                            {"txId": p["txId"], "coordenador": p["coordenador"]},
                        )
                    continue

                if decisao in ("COMMIT", "ABORT"):
                    self.registro.registrar(
                        "2PC_RESOLVIDA_POR_CONSULTA", self.relogio.evento_local(), {"txId": p["txId"], "decisao": decisao}
                    )
                    self.decidir({"txId": p["txId"], "decisao": decisao})
                    self._avisou_bloqueio.discard(p["txId"])
        finally:
            self._resolvendo.release()

    def iniciar_resolucao(self) -> None:
        """Roda uma vez agora e depois periodicamente, em thread daemon (nao bloqueia a subida)."""

        def _loop():
            while True:
                try:
                    self.resolver_em_duvida()
                except Exception as erro:
                    print(f"[2PC] Erro na resolução de dúvida: {erro}")
                time.sleep(INTERVALO_RESOLUCAO_S)

        threading.Thread(target=_loop, daemon=True, name="resolucao-2pc").start()
