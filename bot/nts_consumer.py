import os
import random
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

from templates import tem_template, texto  # noqa: E402
from waha_client import enviar_mensagem  # noqa: E402  (depois do load_dotenv)

NTS_URL = os.getenv("NTS_URL", "http://127.0.0.1:8000").rstrip("/")
NTS_TOKEN = os.getenv("NTS_TOKEN", "")
DRY_RUN = os.getenv("NTS_DRY_RUN", "1") != "0"
ARQUIVO_DB = RAIZ / "database" / "contatos_whatsapp.db"

INTERVALO_SEGUNDOS = 30
MAX_POR_CICLO = 10
PAUSA_MIN = 5   # segundos entre mensagens
PAUSA_MAX = 15
TENTATIVAS_ACK = 3

# Promoções ficam de fora até existir o tratamento de "SAIR" (opt-out).
TIPOS_SUPORTADOS = {
    "reservation.pending",
    "reservation.confirmed",
    "reservation.cancelled",
    "karaoke.called",
}
# Cada tipo daqui precisa de um template no grupo "nts" do templates.json.

_ja_avisados: set[int] = set()       # ids ignorados que já foram registrados no log
_enviadas_sem_ack: set[int] = set()  # WAHA aceitou, mas o NTS ainda não recebeu o ack


def _headers() -> dict:
    if not NTS_TOKEN:
        raise RuntimeError("Defina NTS_TOKEN no .env")
    return {"Authorization": f"Bearer {NTS_TOKEN}"}


def numero_autorizado(telefone: str) -> bool:
    """True só se o número está em contatos_autorizados. Sem banco, nega."""
    if not ARQUIVO_DB.exists():
        return False
    with closing(sqlite3.connect(ARQUIVO_DB)) as conn:
        linha = conn.execute(
            "SELECT 1 FROM contatos_autorizados WHERE numero = ?", (telefone,)
        ).fetchone()
    return linha is not None


def motivo_bloqueio(evento: dict) -> str | None:
    if evento["type"] not in TIPOS_SUPORTADOS:
        return f"tipo não suportado ({evento['type']})"
    if not numero_autorizado(evento["recipient"]["phone"]):
        return "número fora de contatos_autorizados"
    return None


def montar_mensagem(evento: dict) -> str:
    """Texto do template com o nome do tipo do evento (ex.: "karaoke.called")."""
    campos = {**evento["data"], "nome": evento["recipient"]["name"]}
    return texto("nts", evento["type"], **campos)


def listar_pendentes() -> list[dict]:
    resposta = requests.get(
        f"{NTS_URL}/v1/notifications/pending", headers=_headers(), timeout=10
    )
    resposta.raise_for_status()
    return resposta.json()


def reservar(item_id: int) -> str | None:
    """Reserva a notificação por 5 min. None se ela não está mais disponível."""
    resposta = requests.post(
        f"{NTS_URL}/v1/notifications/{item_id}/claim",
        headers=_headers(), json={}, timeout=10,
    )
    if resposta.status_code in (400, 404):
        return None
    resposta.raise_for_status()
    return resposta.json()["claim_token"]


def confirmar(item_id: int, token: str) -> bool:
    """Confirma o envio ao NTS, com algumas tentativas."""
    for tentativa in range(1, TENTATIVAS_ACK + 1):
        try:
            resposta = requests.post(
                f"{NTS_URL}/v1/notifications/{item_id}/ack",
                headers=_headers(), json={"claim_token": token}, timeout=10,
            )
            resposta.raise_for_status()
            return True
        except requests.RequestException as erro:
            print(f"[NTS] ack #{item_id} falhou ({tentativa}/{TENTATIVAS_ACK}): {erro}")
            if tentativa < TENTATIVAS_ACK:
                time.sleep(1)
    return False


def processar_fila() -> int:
    """Roda um ciclo e devolve quantas mensagens novas foram enviadas."""
    enviadas = 0
    for item in listar_pendentes():
        if enviadas >= MAX_POR_CICLO:
            break
        item_id, evento = item["id"], item["event"]

        try:
            motivo = motivo_bloqueio(evento)
            if motivo:
                if item_id not in _ja_avisados:
                    _ja_avisados.add(item_id)
                    print(f"[NTS] #{item_id} ignorada: {motivo}")
                continue
            chat_id = evento["recipient"]["phone"].lstrip("+") + "@c.us"
            texto = montar_mensagem(evento)
        except (KeyError, ValueError) as erro:
            print(f"[NTS] #{item_id} com formato inesperado: {erro!r}")
            continue

        if DRY_RUN:
            print(f"[DRY RUN] #{item_id}: {chat_id} -> {texto}")
            continue

        token = reservar(item_id)
        if token is None:
            continue

        enviou = False
        if item_id not in _enviadas_sem_ack:
            if enviadas:
                time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))
            try:
                enviar_mensagem(chat_id, texto)
            except requests.RequestException as erro:
                print(f"[NTS] WAHA falhou na #{item_id}: {erro}. Encerrando o ciclo.")
                break
            _enviadas_sem_ack.add(item_id)
            enviou = True

        # Se já enviamos antes e só faltou o ack, aqui só confirmamos (sem reenviar).
        if confirmar(item_id, token):
            _enviadas_sem_ack.discard(item_id)
            print(f"[NTS] #{item_id} enviada e confirmada: {chat_id}")
        else:
            print(f"[NTS] #{item_id} enviada, mas sem ack. Será confirmada no próximo ciclo.")
        if enviou:
            enviadas += 1
    return enviadas


def main() -> None:
    if not NTS_TOKEN:
        raise SystemExit("NTS_TOKEN não definido no .env")
    if DRY_RUN:
        print("[NTS] Modo demonstração: nada será reservado nem enviado.")
    else:
        print("[NTS] ENVIO REAL ativado (NTS_DRY_RUN=0).")
    try:
        while True:
            try:
                processar_fila()
            except requests.RequestException as erro:
                print(f"[NTS] API indisponível: {erro}")
            time.sleep(INTERVALO_SEGUNDOS)
    except KeyboardInterrupt:
        print("\n[NTS] Encerrado.")


if __name__ == "__main__":
    main()