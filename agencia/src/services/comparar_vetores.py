"""
comparar_vetores.py - Comparacao de dois vetores do relogio vetorial (Sprint 3, Parte E)
Equivalente ao compararVetores.js do roteiro Node.js.

Mesma logica do mesclar_logs.py (Sprint 2), agora usada em tempo real pelo backend.
Funcao pura: sem efeitos colaterais e sem chamadas de rede.

Retorna:
  'IGUAIS'       - todos os componentes iguais
  'ANTES'        - v1 <= v2 em todos os componentes (v1 aconteceu antes de v2)
  'DEPOIS'       - v2 <= v1 em todos os componentes
  'CONCORRENTES' - nenhum domina o outro
"""

from typing import List


def comparar_vetores(v1: List[int], v2: List[int]) -> str:
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

