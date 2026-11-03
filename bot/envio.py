"""Porta única de saída das mensagens do bot.

Todo envio passa por aqui: um de cada vez e com um intervalo mínimo entre eles,
para o número não disparar mensagens em rajada (rajada é o que mais dá ban).
"""
import random
import threading
import time

from waha_client import enviar_mensagem

INTERVALO_MIN = 1.5  # segundos entre uma mensagem e a próxima
INTERVALO_MAX = 3.0

_trava = threading.Lock()
_ultimo_envio = 0.0


def enviar(chat_id: str, texto: str) -> None:
    """Espera a vez, respeita o intervalo e envia. Erro do WAHA sobe para quem chamou."""
    global _ultimo_envio
    with _trava:
        espera = _ultimo_envio + random.uniform(INTERVALO_MIN, INTERVALO_MAX) - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        try:
            enviar_mensagem(chat_id, texto)
        finally:
            _ultimo_envio = time.monotonic()