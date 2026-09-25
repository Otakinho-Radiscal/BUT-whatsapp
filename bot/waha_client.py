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