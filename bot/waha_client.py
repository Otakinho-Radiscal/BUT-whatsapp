import os

import requests
from dotenv import load_dotenv

load_dotenv()

WAHA_URL = os.getenv("WAHA_URL", "http://localhost:3000")
WAHA_SESSION = os.getenv("WAHA_SESSION", "default")
WAHA_API_KEY = os.getenv("WAHA_API_KEY")


def enviar_mensagem(chat_id: str, texto: str) -> None:
    #envia mensagem pelo waha usando o chat id que vai ser informado
    resposta = requests.post(
        f"{WAHA_URL}/api/sendText",
        headers={"X-Api-Key": WAHA_API_KEY},
        json={
            "session": WAHA_SESSION,
            "chatId": chat_id,
            "text": texto,
        },
        timeout=10, #se não receber uma resposta em 10 segundo desiste de tntar e sobe um erro
    )
    resposta.raise_for_status()
def numero_do_lid(lid: str) -> str | None:
    """'123456@lid' -> '5511912345678@c.us'. None se o WAHA não souber o número.

    O @lid é um apelido interno do WhatsApp, que às vezes chega no lugar do telefone.
    No engine NOWEB, essa consulta só funciona com o Store ativado no WAHA.
    """
    resposta = requests.get(
        f"{WAHA_URL}/api/{WAHA_SESSION}/lids/{lid.split('@')[0]}",
        headers={"X-Api-Key": WAHA_API_KEY},
        timeout=10,
    )
    if resposta.status_code == 404:
        return None
    resposta.raise_for_status()
    return resposta.json().get("pn")