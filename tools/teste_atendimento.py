"""Simula uma conversa inteira com o atendimento, numa CÓPIA do banco.

Rodar:  python tools/teste_atendimento.py
Mostra o chat no terminal e confere se cada resposta é a esperada.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
import atendimento  # noqa: E402
import banco  # noqa: E402

NUMERO = "+5500000000099"  # número fictício: só existe dentro da cópia


def cliente(texto: str) -> list[str]:
    """Manda uma mensagem como cliente e mostra o que o bot respondeu."""
    respostas = atendimento.responder(NUMERO, texto, nome="Cliente Teste")
    print(f"\ncliente> {texto}")
    if not respostas:
        print("    bot> (sem resposta)")
    for resposta in respostas:
        print("    bot> " + resposta.replace("\n", "\n         "))
    return respostas


with tempfile.TemporaryDirectory() as pasta:
    copia = Path(pasta) / "teste.db"
    shutil.copy(banco.ARQUIVO_DB, copia)
    banco.ARQUIVO_DB = copia  # daqui pra baixo, tudo acontece na cópia
    banco.preparar_banco()

    palavra = atendimento.PALAVRA

    r = cliente("oi")
    assert palavra in r[0], "quem chega sem a palavra deve ser orientado"

    r = cliente("1")
    assert r[0].startswith("Para começar"), "opção antes da palavra-chave"

    r = cliente(palavra.lower())  # minúsculo também vale
    assert len(r) == 2 and banco.consentimento(NUMERO) == "autorizado"

    r = cliente("2")
    assert "Para salvar" in r[0]

    r = cliente("1.")  # com ponto também vale
    assert "COMPROVANTE" in r[1]
    codigo = banco.comprovante_de(NUMERO)["codigo"]

    r = cliente("1")
    assert codigo in r[0], "mandar 1 de novo devolve o mesmo comprovante"

    r = cliente("Atendênte")  # com acento também vale
    assert banco.pegar_conversa(NUMERO)["pausado"] is True

    r = cliente("oi, tem alguém aí?")
    assert r == [], "pausado: o bot não responde"

    r = cliente("sair")
    assert r == [] and banco.consentimento(NUMERO) == "revogado", "SAIR vale mesmo pausado"

    atendimento.retomar(NUMERO)
    print("\n(equipe retomou o bot)")

    r = cliente("1")
    assert r == [], "descadastrado: o bot fica quieto"

    r = cliente(palavra)
    assert codigo in r[0] and banco.consentimento(NUMERO) == "autorizado", "voltou e lembrou o comprovante"

    for _ in range(4):
        r = cliente("blablabla")
    assert r == [], "depois de 3 tentativas fora do fluxo, o bot para de responder"

    r = cliente("2")
    assert r, "uma palavra-chave volta a ter resposta"

    print("\nHistórico gravado (mais novo primeiro):")
    for data, descricao in banco.ultimos_eventos(NUMERO, limite=5):
        print(f"  {data}  {descricao}")

print("\nTudo certo. O banco original não foi alterado.")