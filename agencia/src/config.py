"""
config.py — Configuração global do serviço de agência ICEIBank.

Equivalente ao config.js do exemplo Node.js/Express do roteiro.

Responsabilidades:
- Ler a variável de ambiente AGENCIA_ID (identifica qual das 3 instâncias esta é).
- Definir a tabela de peers (endereços das outras agências) — usada nas Partes D em diante.
- Definir a função de particionamento: agencia_responsavel(id_conta).
"""

import os

# ---------------------------------------------------------------------------
# Constantes de particionamento
# ---------------------------------------------------------------------------

# Número total de agências no sistema (partição, não replicação).
# Todas as instâncias compartilham o mesmo valor; se alterar, altere nas 3.
NUMERO_AGENCIAS: int = 3

# Porta base. Cada agência escuta em PORTA_BASE + AGENCIA_ID.
# Se precisar de offset (ex: dois últimos dígitos da matrícula), ajuste aqui.
PORTA_BASE: int = 4000

# ---------------------------------------------------------------------------
# Identidade desta instância
# ---------------------------------------------------------------------------

# Lida da variável de ambiente AGENCIA_ID; padrão 0 para facilitar o dev.
# No PowerShell, defina com: $env:AGENCIA_ID="1"
AGENCIA_ID: int = int(os.getenv("AGENCIA_ID", "0"))

# Nome legível usado nos logs e no arquivo .jsonl
NOME_AGENCIA: str = f"agencia{AGENCIA_ID}"

# ---------------------------------------------------------------------------
# Tabela de peers
# ---------------------------------------------------------------------------
# Lista com as URLs de todas as agências, indexada pelo ID.
# Esta instância pode consultar as outras via HTTP (usado a partir da Parte D).
AGENCIAS: list[str] = [
    f"http://localhost:{PORTA_BASE + i}"
    for i in range(NUMERO_AGENCIAS)
]

# URL desta própria instância (útil para identificação em mensagens)
URL_PROPRIA: str = AGENCIAS[AGENCIA_ID]

# ---------------------------------------------------------------------------
# Regra de particionamento
# ---------------------------------------------------------------------------

def agencia_responsavel(id_conta: int) -> int:
    """
    Retorna o ID da agência responsável por uma conta.

    Regra de particionamento por módulo:
        agencia = id_conta % NUMERO_AGENCIAS

    Exemplos com 3 agências:
        conta 0 → agência 0
        conta 1 → agência 1
        conta 2 → agência 2
        conta 3 → agência 0  (cicla)
        conta 4 → agência 1
        ...

    Por que módulo? É uma função de hash simples, determinística e sem
    necessidade de tabela de lookup — qualquer agência pode calcular quem
    é o responsável por qualquer conta sem comunicação entre si.
    """
    return id_conta % NUMERO_AGENCIAS
