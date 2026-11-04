"""Banco do atendimento: conversas, comprovantes, consentimento e mensagens já recebidas.

Usa o mesmo arquivo do resto do bot (database/contatos_whatsapp.db).
As tabelas novas são criadas por preparar_banco(), que pode rodar quantas vezes
quiser: o que já existe não é mexido.
"""
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# BOT_DB (opcional) troca o arquivo, por exemplo por uma cópia para testes.
ARQUIVO_DB = RAIZ / os.getenv("BOT_DB", "database/contatos_whatsapp.db")

AGORA = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"  # mesmo formato de data do contatos_whatsapp

TABELAS = f"""
CREATE TABLE IF NOT EXISTS conversas (
    numero        TEXT PRIMARY KEY,
    etapa         TEXT NOT NULL DEFAULT 'inicio'
                  CHECK (etapa IN ('inicio', 'menu', 'instrucoes', 'comprovante')),
    pausado       INTEGER NOT NULL DEFAULT 0 CHECK (pausado IN (0, 1)),
    falhas        INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT NOT NULL DEFAULT ({AGORA})
);

CREATE TABLE IF NOT EXISTS comprovantes (
    codigo     TEXT PRIMARY KEY,
    numero     TEXT NOT NULL UNIQUE,
    emitido_em TEXT NOT NULL DEFAULT ({AGORA})
);

CREATE TABLE IF NOT EXISTS mensagens_recebidas (
    id          TEXT PRIMARY KEY,
    numero      TEXT NOT NULL,
    recebida_em TEXT NOT NULL DEFAULT ({AGORA})
);

CREATE TABLE IF NOT EXISTS eventos_atendimento (
    id        INTEGER PRIMARY KEY,
    numero    TEXT NOT NULL,
    descricao TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT ({AGORA})
);
"""

# Letras e números sem os que se confundem na leitura (0 e O, 1 e I).
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ---------- ajudantes ----------

def _conectar() -> sqlite3.Connection:
    # timeout: se outra parte do bot estiver gravando, espera até 10 s em vez de dar erro
    return sqlite3.connect(ARQUIVO_DB, timeout=10)


def _alterar(sql: str, parametros: tuple = ()) -> int:
    """Roda um comando que muda o banco e confirma. Devolve quantas linhas mudaram."""
    with closing(_conectar()) as conn:
        with conn:  # confirma no final, ou desfaz tudo se der erro
            return conn.execute(sql, parametros).rowcount


def _buscar_um(sql: str, parametros: tuple = ()):
    with closing(_conectar()) as conn:
        return conn.execute(sql, parametros).fetchone()


def preparar_banco() -> None:
    """Cria as tabelas do atendimento, se ainda não existirem."""
    if not ARQUIVO_DB.exists():
        raise FileNotFoundError(f"Banco não encontrado: {ARQUIVO_DB}")
    with closing(_conectar()) as conn:
        conn.executescript(TABELAS)


# ---------- conversa ----------

def pegar_conversa(numero: str) -> dict:
    """Estado da conversa. Quem nunca falou com o bot começa na etapa 'inicio'."""
    linha = _buscar_um(
        "SELECT etapa, pausado, falhas FROM conversas WHERE numero = ?", (numero,)
    )
    if linha is None:
        return {"etapa": "inicio", "pausado": False, "falhas": 0}
    return {"etapa": linha[0], "pausado": bool(linha[1]), "falhas": linha[2]}


def salvar_conversa(numero: str, etapa: str, pausado: bool, falhas: int) -> None:
    _alterar(
        f"""INSERT INTO conversas (numero, etapa, pausado, falhas) VALUES (?, ?, ?, ?)
            ON CONFLICT(numero) DO UPDATE SET
                etapa = excluded.etapa,
                pausado = excluded.pausado,
                falhas = excluded.falhas,
                atualizado_em = {AGORA}""",
        (numero, etapa, int(pausado), falhas),
    )


# ---------- consentimento (fica no contatos_whatsapp) ----------

def consentimento(numero: str) -> str | None:
    """'autorizado', 'pendente' ou 'revogado'. None se o número não está cadastrado."""
    linha = _buscar_um(
        "SELECT consentimento FROM contatos_whatsapp WHERE numero = ?", (numero,)
    )
    return linha[0] if linha else None


def mudar_consentimento(numero: str, novo: str, nome: str | None = None) -> None:
    """Grava 'autorizado' ou 'revogado' com a hora do pedido.

    Número que ainda não está no banco é cadastrado com origem 'whatsapp'.
    O SAIR de quem não estava cadastrado também fica gravado, para ninguém
    importar esse número depois como autorizado sem perceber.
    """
    if novo not in ("autorizado", "revogado"):
        raise ValueError(f"consentimento inválido: {novo}")
    _alterar(
        f"""INSERT INTO contatos_whatsapp (numero, nome, origem, consentimento, consentimento_em)
            VALUES (?, ?, 'whatsapp', ?, {AGORA})
            ON CONFLICT(numero) DO UPDATE SET
                consentimento = excluded.consentimento,
                consentimento_em = excluded.consentimento_em""",
        (numero, nome, novo),
    )


# ---------- comprovante ----------

def comprovante_de(numero: str) -> dict | None:
    linha = _buscar_um(
        "SELECT codigo, emitido_em FROM comprovantes WHERE numero = ?", (numero,)
    )
    return {"codigo": linha[0], "emitido_em": linha[1]} if linha else None


def _gerar_codigo(prefixo: str) -> str:
    def bloco() -> str:
        return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(4))
    return f"{prefixo}-{bloco()}-{bloco()}"


def emitir_comprovante(numero: str, prefixo: str) -> dict:
    """Um comprovante por número. Se já existe, devolve o mesmo em vez de criar outro."""
    for _ in range(5):
        existente = comprovante_de(numero)
        if existente:
            return existente
        try:
            _alterar(
                "INSERT INTO comprovantes (codigo, numero) VALUES (?, ?)",
                (_gerar_codigo(prefixo), numero),
            )
        except sqlite3.IntegrityError:
            continue  # código repetido (muito raro): tenta de novo
    resultado = comprovante_de(numero)
    if resultado is None:
        raise RuntimeError("não foi possível gerar um código de comprovante")
    return resultado


# ---------- mensagens recebidas (para não responder a mesma duas vezes) ----------

def mensagem_nova(id_mensagem: str, numero: str) -> bool:
    """Anota a mensagem. True se é a primeira vez; False se o WAHA já tinha mandado ela."""
    return _alterar(
        "INSERT OR IGNORE INTO mensagens_recebidas (id, numero) VALUES (?, ?)",
        (id_mensagem, numero),
    ) == 1


# ---------- histórico do que o bot fez ----------

def registrar_evento(numero: str, descricao: str) -> None:
    _alterar(
        "INSERT INTO eventos_atendimento (numero, descricao) VALUES (?, ?)",
        (numero, descricao),
    )


def ultimos_eventos(numero: str, limite: int = 20) -> list[tuple[str, str]]:
    """(data, descrição) dos eventos mais recentes do número, do mais novo pro mais velho."""
    with closing(_conectar()) as conn:
        return conn.execute(
            """SELECT criado_em, descricao FROM eventos_atendimento
               WHERE numero = ? ORDER BY id DESC LIMIT ?""",
            (numero, limite),
        ).fetchall()