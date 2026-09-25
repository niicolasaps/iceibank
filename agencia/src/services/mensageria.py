"""
mensageria.py - Publish/Subscribe via RabbitMQ com pika
Equivalente ao mensageria.js do roteiro Node.js.

Arquitetura:
  - Exchange: "iceibank.eventos" (topic, durable)
  - Fila por agencia: "fila-agencia-{id}" (durable)
  - Routing key para creditos: "agencia.{id}.creditar"
  - Routing key para alertas: "agencia.{id}.alerta-saldo-baixo"

DECISAO DE PROJETO (documentada):
  pika em modo simples e bloqueante - nao compativel com o event loop do FastAPI.
  Solucao: o consumidor (assinar) roda em uma thread separada (daemon=True),
  iniciada no evento de startup do FastAPI (ver main.py). Isso evita travar
  o loop de eventos do uvicorn enquanto o pika espera mensagens.
"""

import json
import os
import sys
import threading
import time
from typing import Callable, List

import pika
import pika.exceptions

RABBITMQ_URL = os.environ.get("RABBITMQ_URL")
EXCHANGE = "iceibank.eventos"

if not RABBITMQ_URL:
    print(
        "[ERRO] Defina a variavel de ambiente RABBITMQ_URL com a URL AMQP da sua instancia CloudAMQP "
        "antes de iniciar.\n"
        "Exemplo: $env:RABBITMQ_URL=\"amqps://usuario:senha@host.cloudamqp.com/vhost\"",
        file=sys.stderr,
    )
    sys.exit(1)


def _criar_conexao() -> pika.BlockingConnection:
    """Cria e retorna uma conexao bloqueante ao RabbitMQ."""
    params = pika.URLParameters(RABBITMQ_URL)
    params.heartbeat = 60
    params.blocked_connection_timeout = 300
    return pika.BlockingConnection(params)


def publicar(routing_key: str, mensagem: dict) -> None:
    """
    Publica uma mensagem na exchange iceibank.eventos com a routing_key fornecida.
    Abre uma conexao dedicada por publicacao (simples e seguro para chamadas ocasionais).
    Equivalente a publicar() do mensageria.js.

    durable=True + delivery_mode=2 garantem que a mensagem nao se perde se a
    agencia de destino estiver fora do ar no momento da publicacao.
    """
    conexao = _criar_conexao()
    canal = conexao.channel()
    canal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    canal.basic_publish(
        exchange=EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(mensagem).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=2),  # persistent=True
    )
    conexao.close()
    print(f"[Mensageria] Publicado em {routing_key}: {mensagem}")


def assinar(id_agencia: int, ao_receber_mensagem: Callable[[dict], None]) -> threading.Thread:
    """
    Inicia um consumidor em thread separada que escuta a fila desta agencia.
    Retorna a Thread para que main.py possa armazena-la (nao e necessario fazer join).

    A thread e daemon=True: termina automaticamente quando o processo principal termina.
    Equivalente a assinar() do mensageria.js.
    """
    nome_fila = f"fila-agencia-{id_agencia}"
    routing_key = f"agencia.{id_agencia}.creditar"

    def _consumir():
        while True:
            try:
                conexao = _criar_conexao()
                canal = conexao.channel()

                canal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
                canal.queue_declare(queue=nome_fila, durable=True)
                canal.queue_bind(queue=nome_fila, exchange=EXCHANGE, routing_key=routing_key)

                # prefetch_count=1: processa uma mensagem por vez (garante ordem)
                canal.basic_qos(prefetch_count=1)

                def _callback(ch, method, properties, body):
                    try:
                        conteudo = json.loads(body.decode("utf-8"))
                        ao_receber_mensagem(conteudo)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        print(f"[Mensageria] Erro ao processar mensagem: {e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                canal.basic_consume(queue=nome_fila, on_message_callback=_callback)
                print(f"[Mensageria] Agencia {id_agencia} ouvindo fila: {nome_fila}")
                canal.start_consuming()

            except pika.exceptions.AMQPConnectionError as e:
                print(f"[Mensageria] Conexao perdida ({e}). Reconectando em 5s...")
                time.sleep(5)
            except Exception as e:
                print(f"[Mensageria] Erro inesperado no consumidor: {e}. Reiniciando em 5s...")
                time.sleep(5)

    thread = threading.Thread(target=_consumir, daemon=True, name=f"consumer-agencia-{id_agencia}")
    thread.start()
    return thread
