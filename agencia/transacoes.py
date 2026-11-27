r"""
transacoes.py - Mostra, para cada agencia, as transacoes 2PC que ela conhece e em que estado estao
Equivalente ao transacoes.js da secao 9.1 do roteiro Node.js.

Uso (PowerShell, dentro de iceibank/agencia):
  $env:TOKEN_INTERNO="troque-este-segredo"
  .\.venv\Scripts\python.exe transacoes.py
"""

import httpx

from src import config

for agencia in config.AGENCIAS:
    print(f"\n=== Agência {agencia['id']} ({agencia['url']}) ===")
    try:
        resp = httpx.get(
            f"{agencia['url']}/2pc/transacoes",
            headers={"x-token-interno": config.TOKEN_INTERNO},
            timeout=2.0,
        )
        if resp.status_code != 200:
            print(f"  resposta {resp.status_code} (token interno correto?)")
            continue
        dados = resp.json()
        coordenacoes = dados.get("coordenacoes", [])
        participacoes = dados.get("participacoes", [])
        for c in coordenacoes:
            print(f"  [coordenador] {c['txId'][:8]}  estado={c['estado']}  decisao={c['decisao']}")
        for p in participacoes:
            op = p["operacao"]
            print(
                f"  [participante] {p['txId'][:8]}  {op['tipo']} conta {op['idConta']} valor {op['valor']}  estado={p['estado']}"
            )
        if len(coordenacoes) + len(participacoes) == 0:
            print("  (nenhuma transação)")
    except Exception:
        print("  fora do ar")
