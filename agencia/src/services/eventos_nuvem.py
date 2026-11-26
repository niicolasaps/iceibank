"""
eventos_nuvem.py - Publicacao opcional de eventos de decisao no SNS/LocalStack (Sprint 4, Parte F)
Equivalente ao eventosNuvem.js do roteiro Node.js.

Nesta sessao (Partes A-C), funciona como um stub seguro sem efeito quando SNS_TOPIC_ARN
esta vazio (exatamente como o `eventosNuvem?.publicarDecisao(coord)` do app.js da secao 5.8).
A implementacao real com boto3/LocalStack entra na Parte F.
"""


class EventosNuvem:
    def __init__(self, id_agencia: int, relogio, registro) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro

    def publicar_decisao(self, coord: dict) -> None:
        # Parte F implementara a publicacao no topico SNS quando SNS_TOPIC_ARN estiver definido.
        return
