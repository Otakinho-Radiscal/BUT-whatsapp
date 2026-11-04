"""Cliente de mentira: você digita como cliente e vê o bot responder aqui mesmo.

Este script faz os dois lados do WAHA ao mesmo tempo:
  - manda para o bot o webhook de "mensagem recebida", como o WAHA faria;
  - recebe o /api/sendText que o bot manda de volta e mostra a resposta.

Antes de rodar: feche o fake_waha.py, porque os dois usam a porta 4000.
Rodar:  python tools/cliente_falso.py
"""
import hashlib
import hmac
import json
import os
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

URL_BOT = f"http://127.0.0.1:{os.getenv('WEBHOOK_PORTA', '5005')}/webhook"
CHAVE_HMAC = os.getenv("WEBHOOK_HMAC_KEY", "")
NUMERO = "5500000000099"  # fictício
ESPERA_RESPOSTA = 5  # segundos sem chegar nada = o bot terminou de responder

respostas: queue.Queue = queue.Queue()


class FakeWaha(BaseHTTPRequestHandler):
    """Faz o papel do WAHA recebendo o envio do bot."""

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tamanho) or b"{}")
        if self.path == "/api/sendText":
            respostas.put(dados.get("text", ""))
        corpo = b'{"fake": true}'
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass


def mandar(texto: str) -> None:
    """Manda para o bot um evento igual ao que o WAHA manda quando chega mensagem."""
    evento = {
        "event": "message",
        "session": "default",
        "payload": {
            "id": f"false_{NUMERO}@c.us_{uuid.uuid4().hex[:20].upper()}",
            "timestamp": int(time.time()),
            "from": f"{NUMERO}@c.us",
            "fromMe": False,
            "body": texto,
            "hasMedia": False,
            "_data": {"pushName": "Cliente Teste"},
        },
    }
    corpo = json.dumps(evento).encode()
    cabecalhos = {"Content-Type": "application/json"}
    if CHAVE_HMAC:
        cabecalhos["X-Webhook-Hmac"] = hmac.new(CHAVE_HMAC.encode(), corpo, hashlib.sha512).hexdigest()
        cabecalhos["X-Webhook-Hmac-Algorithm"] = "sha512"
    requests.post(URL_BOT, data=corpo, headers=cabecalhos, timeout=10).raise_for_status()


def main() -> None:
    servidor = ThreadingHTTPServer(("127.0.0.1", 4000), FakeWaha)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print("Cliente falso pronto. Digite como cliente (Ctrl+C para sair).")
    try:
        while True:
            texto = input("\nvocê> ").strip()
            if not texto:
                continue
            try:
                mandar(texto)
            except requests.RequestException as erro:
                print(f"  (o bot não respondeu: está rodando? {erro})")
                continue
            chegou = False
            while True:
                try:
                    resposta = respostas.get(timeout=ESPERA_RESPOSTA)
                except queue.Empty:
                    break
                chegou = True
                print("  bot> " + resposta.replace("\n", "\n       "))
            if not chegou:
                print("  (sem resposta)")
    except (KeyboardInterrupt, EOFError):
        print("\nTchau.")


if __name__ == "__main__":
    main()