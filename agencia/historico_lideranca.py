"""
historico_lideranca.py - Reconstroi o historico de liderancas a partir dos logs das agencias.
Equivalente ao historico-lideranca.js do roteiro Node.js (Sprint 3, Parte C).

Le todos os arquivos .jsonl de agencia/data/, filtra os eventos do algoritmo de Bully,
ordena por horaParede e imprime:
  1. o historico completo de eventos de eleicao;
  2. a linha do tempo de lideres (eventos TORNOU_LIDER).

Como executar (dentro de iceibank/agencia):
  python historico_lideranca.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Garante acentos corretos no console do Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

pasta_dados = Path(__file__).parent / "data"
arquivos = sorted(f for f in pasta_dados.iterdir() if f.name.endswith(".jsonl"))

eventos = []
for arquivo in arquivos:
    linhas = [l for l in arquivo.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
    eventos.extend(json.loads(l) for l in linhas)

tipos_bully = ["ELEICAO_INICIADA", "ELEICAO_RECEBIDA", "TORNOU_LIDER", "LIDER_ANUNCIADO", "LIDER_NAO_RESPONDEU"]
eventos_bully = [e for e in eventos if e["tipo"] in tipos_bully]
eventos_bully.sort(key=lambda e: datetime.fromisoformat(e["horaParede"]))

print("=== Histórico de eventos de eleição ===")
for evento in eventos_bully:
    detalhes = json.dumps(evento["detalhes"], ensure_ascii=False)
    print(f"({evento['horaParede']}) [{evento['agencia']}] {evento['tipo']}", detalhes)

tornou_lider = [e for e in eventos_bully if e["tipo"] == "TORNOU_LIDER"]
print("\n=== Linha do tempo de líderes ===")
for evento in tornou_lider:
    print(f"A partir de {evento['horaParede']}: Agência {evento['detalhes']['idAgencia']} é a líder")
