"""
mesclar_logs.py - Linha do tempo causal do ICEIBank
Equivalente ao mesclar-logs.js (Secao 8, Sprint 2).

Sprint 1: ordenava por timestampLamport (numero).
Sprint 2: ordena por horaParede e identifica pares CONCORRENTES via relogio vetorial.

Como executar (dentro de iceibank/agencia com o venv ativo):
  python mesclar_logs.py

Relacao causal entre dois eventos (regra do relogio vetorial):
  - V1 ANTES V2:       V1[i] <= V2[i] para todo i (e ao menos um estritamente menor)
  - V2 ANTES V1:       V2[i] <= V1[i] para todo i (e ao menos um estritamente menor)
  - IGUAIS:            V1[i] == V2[i] para todo i
  - CONCORRENTES:      nenhum dos casos acima (nenhum vetor domina o outro)
"""

import json
from pathlib import Path

pasta_dados = Path(__file__).parent / "data"

if not pasta_dados.exists():
    print("Pasta data/ nao encontrada. Execute as agencias primeiro para gerar eventos.")
    raise SystemExit(1)

arquivos = list(pasta_dados.glob("*.jsonl"))
if not arquivos:
    print("Nenhum arquivo .jsonl encontrado em data/. Gere eventos nas agencias primeiro.")
    raise SystemExit(1)

todos_eventos = []
for arquivo in arquivos:
    conteudo = arquivo.read_text(encoding="utf-8").strip()
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if linha:
            evento = json.loads(linha)
            # Compatibilidade: aceita tanto timestampVetorial (Sprint 2) quanto timestampLamport (Sprint 1)
            if "timestampVetorial" not in evento and "timestampLamport" in evento:
                evento["timestampVetorial"] = [evento["timestampLamport"]]
            todos_eventos.append(evento)

# Ordenar por hora de parede (equivalente ao mesclar-logs.js do Sprint 2)
todos_eventos.sort(key=lambda e: e.get("horaParede", ""))

print("=== Linha do tempo (ordenada por hora de parede) ===")
for evento in todos_eventos:
    vetor = evento.get("timestampVetorial", "?")
    print(
        f"[{evento['agencia']}] vetor={json.dumps(vetor)} {evento['tipo']}",
        json.dumps(evento.get("detalhes", {}), ensure_ascii=False),
    )


def comparar_vetores(v1, v2):
    """
    Compara dois vetores de relogio vetorial.
    Traducao fiel do compararVetores() do mesclar-logs.js.

    Retorna:
      'ANTES'       se v1 <= v2 componente a componente (e sao diferentes)
      'DEPOIS'      se v2 <= v1 componente a componente (e sao diferentes)
      'IGUAIS'      se v1 == v2
      'CONCORRENTES' se nenhum domina o outro
    """
    if len(v1) != len(v2):
        # Vetores de tamanhos diferentes (nao deve ocorrer) - tratamos como concorrentes
        return "CONCORRENTES"
    v1_menor_ou_igual = True
    v2_menor_ou_igual = True
    for i in range(len(v1)):
        if v1[i] > v2[i]:
            v1_menor_ou_igual = False
        if v2[i] > v1[i]:
            v2_menor_ou_igual = False
    if v1_menor_ou_igual and v2_menor_ou_igual:
        return "IGUAIS"
    if v1_menor_ou_igual:
        return "ANTES"
    if v2_menor_ou_igual:
        return "DEPOIS"
    return "CONCORRENTES"


print("\n=== Pares de eventos CONCORRENTES entre agencias diferentes ===")
encontrou_concorrente = False
for i in range(len(todos_eventos)):
    for j in range(i + 1, len(todos_eventos)):
        e1 = todos_eventos[i]
        e2 = todos_eventos[j]
        if e1["agencia"] == e2["agencia"]:
            continue
        v1 = e1.get("timestampVetorial", [])
        v2 = e2.get("timestampVetorial", [])
        if not v1 or not v2:
            continue
        relacao = comparar_vetores(v1, v2)
        if relacao == "CONCORRENTES":
            encontrou_concorrente = True
            print(
                f"[{e1['agencia']}] {e1['tipo']} ({json.dumps(v1)}) "
                f"x [{e2['agencia']}] {e2['tipo']} ({json.dumps(v2)})"
            )

if not encontrou_concorrente:
    print(
        "(nenhum par concorrente encontrado nesta execucao - "
        "gere mais eventos em paralelo e rode de novo)"
    )

print(f"\nTotal: {len(todos_eventos)} eventos de {len(arquivos)} agencia(s).")
