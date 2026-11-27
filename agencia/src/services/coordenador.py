"""
coordenador.py - Papel de COORDENADOR no 2PC (Sprint 4, Parte C)
Equivalente ao coordenador.js do roteiro Node.js.

No ICEIBank, quem coordena cada transferencia e a agencia que o Bully elegeu como lider.

Regras criticas:
  - A decisao so vale DEPOIS de gravada em disco (estado.salvar()). Esse e o ponto sem volta.
  - COMMIT so se TODOS votaram SIM (timeout conta como NAO).
  - A decisao e entregue a todos os participantes; se algum estiver fora do ar, a reentrega
    periodica (a cada 3s) insiste ate receber confirmacao.
  - Aborto presumido:
      * No `recuperar()` (chamado UMA vez ao subir, ANTES de aceitar requisicoes), transacoes
        que ficaram em `PREPARANDO` nunca chegaram a uma decisao -> sao abortadas com seguranca.
      * Em `status_de(txId)`, transacao desconhecida responde `ABORT` (aborto presumido).
  - CONCORRENCIA: `estado.lock` nunca e mantido durante chamadas HTTP (evita deadlock quando a
    propria agencia coordenadora tambem e participante e chama `/2pc/preparar` ou `/2pc/decidir`
    em si mesma).
"""

import asyncio
import threading
import time
import uuid

from src import config
from src.services.cliente_interno import cliente_interno, criar_cliente_interno_async
from src.services.falhas import falhar

TIMEOUT_S: float = 2.0
INTERVALO_REENTREGA_S: float = 3.0


class Coordenador:
    def __init__(self, id_agencia: int, relogio, registro, estado, eventos_nuvem=None) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self.estado = estado
        self.eventos_nuvem = eventos_nuvem
        self._reentregando = threading.Lock()

    def _url_de(self, id_ag: int) -> str:
        return next(a["url"] for a in config.AGENCIAS if a["id"] == id_ag)

    async def _pedir_voto(self, client, tx_id: str, p: dict) -> None:
        try:
            vetor_envio = self.relogio.ao_enviar()
            self.registro.registrar(
                "2PC_PREPARAR_ENVIADO",
                vetor_envio,
                {"txId": tx_id, "para": p["agencia"], "operacao": p["operacao"]},
            )
            resp = await client.post(
                f"{self._url_de(p['agencia'])}/2pc/preparar",
                json={
                    "txId": tx_id,
                    "operacao": p["operacao"],
                    "coordenador": self.id_agencia,
                    "vetorEnvio": vetor_envio,
                },
                timeout=TIMEOUT_S,
            )
            resp.raise_for_status()
            dados = resp.json()
            if dados.get("vetorEnvio"):
                self.relogio.ao_receber(dados["vetorEnvio"])
            p["voto"] = dados.get("voto")
            p["motivo"] = dados.get("motivo") or None
        except Exception:
            # sem resposta dentro do prazo conta como voto NAO
            p["voto"] = "NAO"
            p["motivo"] = "Agência não respondeu a tempo."
            self.registro.registrar(
                "2PC_VOTO_TIMEOUT",
                self.relogio.evento_local(),
                {"txId": tx_id, "agencia": p["agencia"]},
            )

    async def _entregar_decisao_async(self, client, tx_id: str, decisao: str, p: dict) -> None:
        if p.get("confirmou"):
            return
        try:
            vetor_envio = self.relogio.ao_enviar()
            self.registro.registrar(
                "2PC_DECISAO_ENVIADA",
                vetor_envio,
                {"txId": tx_id, "para": p["agencia"], "decisao": decisao},
            )
            resp = await client.post(
                f"{self._url_de(p['agencia'])}/2pc/decidir",
                json={"txId": tx_id, "decisao": decisao, "vetorEnvio": vetor_envio},
                timeout=TIMEOUT_S,
            )
            resp.raise_for_status()
            dados = resp.json()
            if dados.get("vetorEnvio"):
                self.relogio.ao_receber(dados["vetorEnvio"])
            with self.estado.lock:
                p["confirmou"] = True
        except Exception:
            # participante fora do ar: a reentrega periodica tenta de novo
            pass

    def _entregar_decisao_sync(self, tx_id: str, decisao: str, p: dict) -> None:
        if p.get("confirmou"):
            return
        try:
            vetor_envio = self.relogio.ao_enviar()
            self.registro.registrar(
                "2PC_DECISAO_ENVIADA",
                vetor_envio,
                {"txId": tx_id, "para": p["agencia"], "decisao": decisao},
            )
            resp = cliente_interno.post(
                f"{self._url_de(p['agencia'])}/2pc/decidir",
                json={"txId": tx_id, "decisao": decisao, "vetorEnvio": vetor_envio},
                timeout=TIMEOUT_S,
            )
            resp.raise_for_status()
            dados = resp.json()
            if dados.get("vetorEnvio"):
                self.relogio.ao_receber(dados["vetorEnvio"])
            with self.estado.lock:
                p["confirmou"] = True
        except Exception:
            pass

    def _concluir_se_tudo_confirmado(self, coord: dict) -> None:
        with self.estado.lock:
            if coord["estado"] == "DECIDIDA" and all(p.get("confirmou") for p in coord["participantes"]):
                coord["estado"] = "CONCLUIDA"
                self.estado.salvar()
                self.registro.registrar(
                    "2PC_CONCLUIDA",
                    self.relogio.evento_local(),
                    {"txId": coord["txId"], "decisao": coord["decisao"]},
                )

    def _resumo(self, coord: dict) -> dict:
        motivos = [p["motivo"] for p in coord["participantes"] if p.get("voto") != "SIM"]
        pendentes = [p["agencia"] for p in coord["participantes"] if not p.get("confirmou")]
        res = {
            "txId": coord["txId"],
            "resultado": coord["decisao"],
            "motivos": motivos,
            "pendentesDeConfirmacao": pendentes,
        }
        # Campos extras de continuidade para o frontend web React e o app Flutter (Sprints 1-3)
        if coord["decisao"] == "COMMIT":
            res["mensagem"] = f"Transferência concluída via 2PC (txId: {coord['txId']})."
        else:
            motivo_txt = "; ".join(m for m in motivos if m) or "Transação abortada pelo 2PC."
            res["erro"] = motivo_txt
            res["detail"] = motivo_txt
        return res

    async def coordenar(self, id_origem: int, id_destino: int, valor: float) -> dict:
        tx_id = str(uuid.uuid4())
        coord = {
            "txId": tx_id,
            "estado": "PREPARANDO",
            "decisao": None,
            "participantes": [
                {
                    "agencia": config.agencia_responsavel(id_origem),
                    "operacao": {"tipo": "DEBITO", "idConta": id_origem, "valor": valor},
                    "voto": None,
                    "motivo": None,
                    "confirmou": False,
                },
                {
                    "agencia": config.agencia_responsavel(id_destino),
                    "operacao": {"tipo": "CREDITO", "idConta": id_destino, "valor": valor},
                    "voto": None,
                    "motivo": None,
                    "confirmou": False,
                },
            ],
        }
        with self.estado.lock:
            self.estado.coordenacoes[tx_id] = coord
            self.estado.salvar()
            self.registro.registrar(
                "2PC_INICIO",
                self.relogio.evento_local(),
                {"txId": tx_id, "idOrigem": id_origem, "idDestino": id_destino, "valor": valor},
            )

        async with criar_cliente_interno_async() as client:
            # FASE 1: pergunta a todos os participantes (em paralelo) se podem se comprometer
            await asyncio.gather(*(self._pedir_voto(client, tx_id, p) for p in coord["participantes"]))
            falhar("coordenador-antes-de-decidir")

            # DECISAO: commit so se TODOS votaram SIM; qualquer outra coisa e abort.
            # Gravar a decisao em disco e o ponto sem volta da transacao.
            with self.estado.lock:
                coord["decisao"] = (
                    "COMMIT" if all(p.get("voto") == "SIM" for p in coord["participantes"]) else "ABORT"
                )
                coord["estado"] = "DECIDIDA"
                self.estado.salvar()
                self.registro.registrar(
                    f"2PC_DECISAO_{coord['decisao']}",
                    self.relogio.evento_local(),
                    {"txId": tx_id},
                )
            falhar("coordenador-apos-decidir")
            if self.eventos_nuvem is not None:
                self.eventos_nuvem.publicar_decisao(coord)

            # FASE 2: comunica a decisao a todos (em paralelo)
            await asyncio.gather(
                *(self._entregar_decisao_async(client, tx_id, coord["decisao"], p) for p in coord["participantes"])
            )

        self._concluir_se_tudo_confirmado(coord)
        return self._resumo(coord)

    # Reenvia decisoes que algum participante ainda nao confirmou.
    def reentregar_pendentes(self) -> None:
        if not self._reentregando.acquire(blocking=False):
            return
        try:
            with self.estado.lock:
                pendentes_coords = [c for c in self.estado.coordenacoes.values() if c["estado"] == "DECIDIDA"]

            for coord in pendentes_coords:
                decisao = coord["decisao"]
                for p in coord["participantes"]:
                    if not p.get("confirmou"):
                        self._entregar_decisao_sync(coord["txId"], decisao, p)
                self._concluir_se_tudo_confirmado(coord)
        finally:
            self._reentregando.release()

    # Chamado UMA vez, ao subir, antes de aceitar requisicoes. Transacoes que estavam na
    # fase 1 quando a agencia caiu nunca chegaram a uma decisao: por seguranca, sao
    # abortadas ("aborto presumido").
    def recuperar(self) -> None:
        with self.estado.lock:
            mudou = False
            for coord in self.estado.coordenacoes.values():
                if coord["estado"] == "PREPARANDO":
                    coord["decisao"] = "ABORT"
                    coord["estado"] = "DECIDIDA"
                    mudou = True
                    self.registro.registrar(
                        "2PC_ABORTO_PRESUMIDO",
                        self.relogio.evento_local(),
                        {"txId": coord["txId"]},
                    )
            if mudou:
                self.estado.salvar()

    # Resposta a pergunta de um participante em duvida: "qual foi a decisao?"
    def status_de(self, tx_id: str) -> dict:
        with self.estado.lock:
            coord = self.estado.coordenacoes.get(tx_id)
            if coord is None:
                return {"decisao": "ABORT", "observacao": "transação desconhecida (aborto presumido)"}
            if coord.get("decisao"):
                return {"decisao": coord["decisao"]}
            return {"decisao": "EM_ANDAMENTO"}

    def iniciar_reentrega(self) -> None:
        def _loop():
            while True:
                time.sleep(INTERVALO_REENTREGA_S)
                try:
                    self.reentregar_pendentes()
                except Exception as erro:
                    print(f"[2PC] Erro na reentrega de decisões: {erro}")

        threading.Thread(target=_loop, daemon=True, name="reentrega-2pc").start()
