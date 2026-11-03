"""Textos do bot: lê o templates.json e preenche os campos entre chaves.

Exemplos:
    mensagens("atendimento", "menu")           -> lista com as 2 mensagens do menu
    texto("nts", "karaoke.called", nome="Ana", song="Música", artist="Artista")

Os campos do bloco "config" (casa, palavra, beneficio, contato) entram sozinhos.
"""
import json
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent / "templates.json"

with open(ARQUIVO, encoding="utf-8-sig") as arquivo:  # -sig: aceita arquivo salvo com BOM
    _DADOS = json.load(arquivo)

CONFIG = _DADOS["config"]


def chaves(grupo: str) -> list[str]:
    """Nomes dos templates de um grupo ("atendimento" ou "nts")."""
    return list(_DADOS[grupo])


def tem_template(grupo: str, chave: str) -> bool:
    return chave in _DADOS.get(grupo, {})


def mensagens(grupo: str, chave: str, /, **campos) -> list[str]:
    """Devolve as mensagens do template, já preenchidas (uma por balão).

    Se faltar um campo, dá KeyError aqui, em vez de mandar "{nome}" para o cliente.
    O config vem por último: o nome da casa e a palavra-chave não mudam por mensagem.
    """
    modelo = _DADOS[grupo][chave]
    if isinstance(modelo, str):
        modelo = [modelo]
    valores = {**campos, **CONFIG}
    return [linha.format_map(valores) for linha in modelo]


def texto(grupo: str, chave: str, /, **campos) -> str:
    """Igual a mensagens(), mas junta tudo numa mensagem só."""
    return "\n\n".join(mensagens(grupo, chave, **campos))