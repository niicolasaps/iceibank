"""
config.py - Configuracao do ICEIBank (Sprint 4: tudo configuravel por variavel de ambiente)

Regra de particionamento:
  A conta de id N pertence a agencia N % NUMERO_AGENCIAS.

Portas (OFFSET pessoal = 46):
  Agencia 0 -> 4046 | Agencia 1 -> 4047 | Agencia 2 -> 4048

Em CONTAINERS (docker compose), as agencias se enxergam pelo nome do servico
(AGENCIAS_HOSTS=agencia-0,agencia-1,agencia-2) na porta PORTA_BASE + id.
Fora de containers, tudo e localhost.

Variaveis de ambiente:
  PORTA_BASE        porta da agencia 0 (padrao 4000 + OFFSET = 4046)
  AGENCIAS_HOSTS    hosts das 3 agencias, separados por virgula (padrao: localhost,localhost,localhost)
  AGENCIA_URL_<id>  sobrescreve a URL completa de uma agencia (nuvem). O nome legado
                    AGENCIA_<id>_URL (Sprint 1, Render) continua aceito.
  DATA_DIR          onde ficam estado e logs (em container: /dados, um volume)
  TOKEN_INTERNO     segredo compartilhado entre as agencias nas rotas internas (Bully e 2PC)
"""

import os
from pathlib import Path

# Meu OFFSET pessoal (portas 4046, 4047, 4048).
OFFSET: int = 46
NUMERO_AGENCIAS: int = 3
PORTA_BASE: int = int(os.environ.get("PORTA_BASE", str(4000 + OFFSET)))

# Em containers, as agencias se enxergam pelo nome do servico (ex.: agencia-1).
# Fora de containers, tudo e localhost.
HOSTS = os.environ.get("AGENCIAS_HOSTS", "localhost,localhost,localhost").split(",")

# Onde ficam os arquivos que precisam sobreviver a um reinicio (estado e logs).
# Padrao: agencia/data (o mesmo lugar dos Sprints 1-3, que mesclar_logs.py e
# historico_lideranca.py leem). Em containers, aponte para um volume (ex.: /dados).
DATA_DIR: str = os.environ.get("DATA_DIR") or str(Path(__file__).resolve().parent.parent / "data")

# Segredo compartilhado entre as agencias para as rotas internas (Bully e 2PC).
TOKEN_INTERNO: str = os.environ.get("TOKEN_INTERNO", "")


def _url_agencia(i: int) -> str:
    """URL da agencia i: AGENCIA_URL_<i> > AGENCIA_<i>_URL (legado) > http://<host>:<porta>."""
    return (
        os.environ.get(f"AGENCIA_URL_{i}")
        or os.environ.get(f"AGENCIA_{i}_URL")
        or f"http://{HOSTS[i].strip()}:{PORTA_BASE + i}"
    )


# Lista de agencias com id e URL - usada na comunicacao entre agencias
AGENCIAS: list[dict] = [{"id": i, "url": _url_agencia(i)} for i in range(NUMERO_AGENCIAS)]


def agencia_responsavel(id_conta: int) -> int:
    """Retorna o id da agencia responsavel por uma conta."""
    return id_conta % NUMERO_AGENCIAS
