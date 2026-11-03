import os
import random
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

WAHA_URL = os.getenv("WAHA_URL", "http://localhost:3000")
WAHA_SESSION = os.getenv("WAHA_SESSION", "default")
HEADERS = {"X-Api-Key": os.getenv("WAHA_API_KEY", "")}
ARQUIVO_DB = RAIZ / "database" / "contatos_whatsapp.db"

LIMITE_TOTAL = 100  # teto fixo de mensagens por execução
PAUSA_MIN = 5       # segundos
PAUSA_MAX = 15


def buscar_contatos() -> list[tuple[str, str]]:
    conn = sqlite3.connect(ARQUIVO_DB)
    try:
        return conn.execute(
            "SELECT COALESCE(nome, '(sem nome)'), numero FROM contatos_autorizados"
        ).fetchall()
    finally:
        conn.close()
        
def para_chat_id(numero: str) -> str:
    # converte o número para o formato de chat id do waha
    return numero.lstrip("+") + "@c.us"

def checar_sessao() -> None:
    resposta = requests.get(
        f"{WAHA_URL}/api/sessions/{WAHA_SESSION}", headers=HEADERS, timeout=10
    )
    resposta.raise_for_status()
    dados = resposta.json()
    status = dados.get("status")
    me = ((dados.get("me") or {}).get("id") or "").split("@")[0]
    print(f"sessão: {status} | número enviando: final {me[-4:] or '?????' }")
    if status != "WORKING":
       sys.exit("A sessão não está WORKING. Corrija isso antes de enviar.")
       

def enviar(chat_id: str, texto: str) -> None:
    resposta = requests.post(
        f"{WAHA_URL}/api/sendText",
        headers=HEADERS,
        json={"session": WAHA_SESSION, "chatId": chat_id, "text": texto},
        timeout=10,
    )
    resposta.raise_for_status()
    


def main() -> None:
    rodadas = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    if not ARQUIVO_DB.exists():
        sys.exit("Banco não encontrado em database/.")
    contatos = buscar_contatos()
    if not contatos:
        sys.exit("nenhum contato autorizado no banco.")
            
    total = len(contatos) * rodadas
    if total > LIMITE_TOTAL:
        sys.exit(f"{total} mensagens passam do limite do bot reduza a quantidade de rodadas")
        
    checar_sessao()
    print(f"\nDestinatários autorizados: ({len(contatos)}):")
    for nome, numero in contatos:
        print(f" {nome}: final {numero[-4:]}")
        print(f"\n{rodadas} rodada(s) x {len(contatos)}")
        print(f"Pausa aleatoria de {PAUSA_MIN} a {PAUSA_MAX}s entre os envios")
        if input("digite 'sim' pra continuar: ").strip().lower() != "sim":
            sys.exit("cancelado.")
            
        enviadas = 0
        for _ in range(rodadas):
            ordem = contatos[:]
            random.shuffle(ordem)
            for nome, numero in ordem:
                enviadas += 1
                texto = f"Teste {enviadas}/{total} às {datetime.now():%H:%M:%S}"
                try:
                    enviar(para_chat_id(numero), texto)
                except requests.RequestException as erro:
                    sys.exit(f"falhou na mensagem {enviadas} ({nome}): {erro}. parando.")
                    print(f"[{enviadas}/{total}] enviada para {nome}")
                    if enviadas < total:
                        time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))
                        
        print("concluido.")
        
if __name__ == "__main__":
    main()
