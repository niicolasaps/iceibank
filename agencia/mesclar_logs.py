"""
mesclar_logs.py — Script de linha do tempo unificada do ICEIBank
Equivalente ao mesclar-logs.js do exemplo Node.js/Express do roteiro. (Parte E, Seção 10)

Lê todos os arquivos .jsonl de agencia/data/, junta os eventos de todas as
agências em uma lista única, ordena por timestampLamport (relógio lógico) e
imprime no console uma linha do tempo unificada.

Como executar (dentro de iceibank/agencia com o venv ativo):
  python mesclar_logs.py

Nota sobre empates de timestamp:
  Dois eventos com o mesmo timestampLamport vindos de agências diferentes são
  genuinamente CONCORRENTES — não há relação causal entre eles. O Lamport
  garante que se A causou B então ts(A) < ts(B), mas NÃO garante a volta:
  ts(A) < ts(B) não implica que A causou B. Por isso o Sprint 2 introduz o
  relógio vetorial, que permite detectar concorrência com certeza.
"""

import json
from pathlib import Path

pasta_dados = Path(__file__).parent / "data"

if not pasta_dados.exists():
    print("Pasta data/ não encontrada. Execute as agências primeiro para gerar eventos.")
    raise SystemExit(1)

arquivos = list(pasta_dados.glob("*.jsonl"))
if not arquivos:
    print("Nenhum arquivo .jsonl encontrado em data/. Gere eventos nas agências primeiro.")
    raise SystemExit(1)

todos_eventos = []
for arquivo in arquivos:
    conteudo = arquivo.read_text(encoding="utf-8").strip()
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if linha:
            todos_eventos.append(json.loads(linha))

todos_eventos.sort(key=lambda e: e["timestampLamport"])

print("=== Linha do tempo unificada (ordenada por relogio de Lamport) ===")
for evento in todos_eventos:
    print(
        f"[Lamport {evento['timestampLamport']}] "
        f"({evento['horaParede']}) "
        f"{evento['agencia']} - {evento['tipo']} "
        f"{json.dumps(evento['detalhes'], ensure_ascii=False)}"
    )

print(f"\nTotal: {len(todos_eventos)} eventos de {len(arquivos)} agência(s).")
