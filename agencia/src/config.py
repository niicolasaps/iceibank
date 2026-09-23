"""
config.py - Configuracao de particionamento do ICEIBank

Regra de particionamento:
  A conta de id N pertence a agencia N % NUMERO_AGENCIAS.

Portas locais (OFFSET = 46):
  Agencia 0 -> http://localhost:4046
  Agencia 1 -> http://localhost:4047
  Agencia 2 -> http://localhost:4048

Em producao (Render), as URLs sao configuradas via variaveis de ambiente:
  AGENCIA_0_URL, AGENCIA_1_URL, AGENCIA_2_URL
"""

import os

OFFSET: int = 46
NUMERO_AGENCIAS: int = 3
PORTA_BASE: int = 4000 + OFFSET


def _url_agencia(i: int) -> str:
    """Retorna a URL da agencia i, priorizando variavel de ambiente."""
    env_key = f"AGENCIA_{i}_URL"
    return os.environ.get(env_key, f"http://localhost:{PORTA_BASE + i}")


# Lista de agencias com id e URL - usada para comunicacao entre agencias
AGENCIAS: list[dict] = [
    {"id": i, "url": _url_agencia(i)}
    for i in range(NUMERO_AGENCIAS)
]


def agencia_responsavel(id_conta: int) -> int:
    """Retorna o id da agencia responsavel por uma conta."""
    return id_conta % NUMERO_AGENCIAS
