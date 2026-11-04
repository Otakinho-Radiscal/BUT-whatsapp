"""Recebe as mensagens que chegam no WhatsApp e responde com o atendimento.

O WAHA avisa cada mensagem recebida com um POST em http://HOST:PORTA/webhook.
O bot responde 200 na hora, guarda a mensagem numa fila e uma thread separada
cuida de uma mensagem por vez (assim duas mensagens do mesmo cliente não se atropelam).

Rodar:  python bot/webhook.py
"""
import hashlib
import hmac
import json
import os
import queue
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

import atendimento  # noqa: E402  (depois do load_dotenv)
import banco  # noqa: E402
from envio import enviar  # noqa: E402
from waha_client import numero_do_lid  # noqa: E402

HOST = os.getenv("WEBHOOK_HOST", "127.0.0.1")
PORTA = int(os.getenv("WEBHOOK_PORTA", "5005"))
CHAVE_HMAC = os.getenv("WEBHOOK_HMAC_KEY", "")

# Mensagem mais velha que isso não recebe resposta. Acontece quando o bot fica
# fora do ar e o WAHA entrega tudo de uma vez quando ele volta.
IDADE_MAXIMA_SEGUNDOS = 10 * 60
TAMANHO_MAXIMO = 1_000_000  # bytes; webhook de texto é bem menor que isso

fila: queue.Queue = queue.Queue()


# ---------- quem mandou ----------

def mascarar(numero: str) -> str:
    """Para o log não mostrar o número inteiro: '+5511912345678' -> '...5678'."""
    return "..." + numero[-4:]


def padronizar_numero(digitos: str) -> str:
    """Põe no formato do banco: '+55' + DDD + número.

    O WhatsApp às vezes manda celular brasileiro antigo sem o 9 da frente
    (55 + DDD + 8 dígitos). O banco e o NTS guardam com o 9, então ele entra aqui.
    """
    if len(digitos) == 12 and digitos.startswith("55") and digitos[4] in "6789":
        digitos = digitos[:4] + "9" + digitos[4:]
    return "+" + digitos


def remetente(msg: dict) -> tuple[str, str] | None:
    """Devolve (numero no formato do banco, chat para responder), ou None se não der."""
    de = msg.get("from") or ""
    if de.endswith("@c.us"):
        digitos, chat = de.split("@")[0], de  # responde no mesmo chat que chegou
    else:  # @lid: apelido interno do WhatsApp, não é o telefone
        alternativo = ((msg.get("_data") or {}).get("key") or {}).get("remoteJidAlt") or ""
        if alternativo.endswith("@s.whatsapp.net"):
            telefone = alternativo
        else:
            try:
                telefone = numero_do_lid(de) or ""
            except requests.RequestException:
                telefone = ""
        digitos = telefone.split("@")[0].split(":")[0]
        chat = digitos + "@c.us"
    if not digitos.isdigit():
        return None
    return padronizar_numero(digitos), chat


# ---------- o que fazer com cada evento ----------

def processar(evento: dict) -> None:
    if evento.get("event") != "message":
        return
    msg = evento.get("payload") or {}
    if msg.get("fromMe"):
        return  # mensagem que o próprio número do bot mandou
    if not (msg.get("from") or "").endswith(("@c.us", "@lid")):
        return  # grupo, status ou canal: o bot só atende conversa individual

    quem = remetente(msg)
    if quem is None:
        print("[webhook] não consegui descobrir o número de quem mandou: ignorado")
        return
    numero, chat = quem

    id_mensagem = msg.get("id")
    if not id_mensagem or not banco.mensagem_nova(id_mensagem, numero):
        return  # o WAHA mandou a mesma mensagem de novo

    if time.time() - (msg.get("timestamp") or 0) > IDADE_MAXIMA_SEGUNDOS:
        banco.registrar_evento(numero, "Mensagem antiga (bot estava fora do ar): sem resposta")
        return

    dados = msg.get("_data") or {}
    nome = dados.get("pushName") or dados.get("notifyName")
    respostas = atendimento.responder(numero, msg.get("body") or "", nome=nome)
    for texto in respostas:
        enviar(chat, texto)
    print(f"[webhook] {mascarar(numero)}: {len(respostas)} resposta(s)")


def trabalhar() -> None:
    """Thread que esvazia a fila, uma mensagem por vez."""
    while True:
        evento = fila.get()
        try:
            processar(evento)
        except Exception:  # um evento com problema não pode derrubar o bot inteiro
            print("[webhook] erro ao processar uma mensagem:")
            traceback.print_exc()


# ---------- o servidor que o WAHA chama ----------

def assinatura_valida(corpo: bytes, assinatura: str) -> bool:
    """Confere o X-Webhook-Hmac: prova que o POST veio do WAHA com a mesma chave."""
    esperado = hmac.new(CHAVE_HMAC.encode(), corpo, hashlib.sha512).hexdigest()
    return hmac.compare_digest(esperado, assinatura)


class Webhook(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            return self._responder(404)
        tamanho = int(self.headers.get("Content-Length", 0))
        if tamanho > TAMANHO_MAXIMO:
            return self._responder(413)
        corpo = self.rfile.read(tamanho)
        if CHAVE_HMAC and not assinatura_valida(corpo, self.headers.get("X-Webhook-Hmac", "")):
            print("[webhook] assinatura inválida: ignorado")
            return self._responder(401)
        try:
            evento = json.loads(corpo)
        except json.JSONDecodeError:
            return self._responder(400)
        fila.put(evento)
        self._responder(200)

    def _responder(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass  # sem o log padrão de cada requisição


def iniciar_webhook() -> None:
    banco.preparar_banco()
    threading.Thread(target=trabalhar, daemon=True).start()
    print(f"[webhook] ouvindo em http://{HOST}:{PORTA}/webhook")
    print(f"[webhook] banco: {banco.ARQUIVO_DB.name}")
    if not CHAVE_HMAC:
        print("[webhook] AVISO: sem WEBHOOK_HMAC_KEY, qualquer um que alcance a porta pode mandar mensagens falsas")
    try:
        ThreadingHTTPServer((HOST, PORTA), Webhook).serve_forever()
    except KeyboardInterrupt:
        print("\n[webhook] Encerrado.")


if __name__ == "__main__":
    iniciar_webhook()