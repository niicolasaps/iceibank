"""
config.py — Configuração de particionamento do ICEIBank
Equivalente ao config.js do exemplo Node.js/Express do roteiro.

Regra de particionamento:
  A conta de id N pertence à agência N % NUMERO_AGENCIAS.
  Com 3 agências: conta 0 → agência 0, conta 1 → agência 1, conta 2 → agência 2,
                  conta 3 → agência 0, conta 4 → agência 1, etc.

Portas (OFFSET = 46, dois últimos dígitos da matrícula):
  Agência 0 → http://localhost:4046
  Agência 1 → http://localhost:4047
  Agência 2 → http://localhost:4048
"""

# OFFSET pessoal = dois últimos dígitos da matrícula/RA.
# Necessário para evitar colisão de portas em laboratório compartilhado.
# Meu OFFSET = 46 → PORTA_BASE = 4046 → agências em 4046, 4047, 4048.
OFFSET: int = 46

NUMERO_AGENCIAS: int = 3

PORTA_BASE: int = 4000 + OFFSET

# Lista de agências com id e URL — espelha o array AGENCIAS do config.js.
AGENCIAS: list[dict] = [
    {"id": i, "url": f"http://localhost:{PORTA_BASE + i}"}
    for i in range(NUMERO_AGENCIAS)
]


def agencia_responsavel(id_conta: int) -> int:
    """
    Retorna o id da agência responsável por uma conta.
    Equivalente à função agenciaResponsavel(idConta) do config.js.
    """
    return id_conta % NUMERO_AGENCIAS
