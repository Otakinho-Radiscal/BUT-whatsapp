"""Mostra todos os textos do templates.json preenchidos com dados de exemplo.

Rodar:  python tools/teste_templates.py
Se algum template pedir um campo que não existe, aparece ERRO na linha dele.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
from templates import chaves, mensagens  # noqa: E402

EXEMPLO = {
    "nome": "Cliente Teste",
    "codigo": "CE-AB12-CD34",
    "emitido_em": "03/11/2026 14:30",
    "event_name": "Festa Teste",
    "song": "Música Teste",
    "artist": "Artista Teste",
}

erros = 0
for grupo in ("atendimento", "nts"):
    print(f"\n===== {grupo} =====")
    for chave in chaves(grupo):
        try:
            linhas = mensagens(grupo, chave, **EXEMPLO)
        except KeyError as erro:
            erros += 1
            print(f"\n[{chave}] ERRO: falta o campo {erro}")
            continue
        print(f"\n[{chave}]")
        for linha in linhas:
            print("  > " + linha.replace("\n", "\n    "))

print(f"\n{erros} erro(s).")