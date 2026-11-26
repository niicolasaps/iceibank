"""
saldo.py - Saldo disponivel (Sprint 4, Parte A)
Equivalente ao saldo.js do roteiro Node.js.
"""


def saldo_disponivel(conta: dict) -> float:
    """
    Saldo que realmente pode ser gasto agora: o saldo menos o que esta reservado
    por transacoes distribuidas (2PC) que ainda nao terminaram.
    """
    return conta["saldo"] - (conta.get("reservado") or 0)
