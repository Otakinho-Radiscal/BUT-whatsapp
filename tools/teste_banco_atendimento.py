"""Testa o banco.py numa CÓPIA do banco. O arquivo original não é alterado.

Rodar:  python tools/teste_banco_atendimento.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
import banco  # noqa: E402

NUMERO = "+5500000000099"  # número fictício: só existe dentro da cópia

with tempfile.TemporaryDirectory() as pasta:
    copia = Path(pasta) / "teste.db"
    shutil.copy(banco.ARQUIVO_DB, copia)
    banco.ARQUIVO_DB = copia  # daqui pra baixo, tudo acontece na cópia

    banco.preparar_banco()
    banco.preparar_banco()  # rodar de novo não pode dar erro nem apagar nada
    print("tabelas: ok")

    assert banco.pegar_conversa(NUMERO) == {"etapa": "inicio", "pausado": False, "falhas": 0}
    banco.salvar_conversa(NUMERO, "menu", False, 0)
    banco.salvar_conversa(NUMERO, "instrucoes", True, 2)
    assert banco.pegar_conversa(NUMERO) == {"etapa": "instrucoes", "pausado": True, "falhas": 2}
    print("conversa: ok")

    assert banco.consentimento(NUMERO) is None
    banco.mudar_consentimento(NUMERO, "autorizado", nome="Cliente Teste")
    assert banco.consentimento(NUMERO) == "autorizado"
    banco.mudar_consentimento(NUMERO, "revogado")
    assert banco.consentimento(NUMERO) == "revogado"
    print("consentimento: ok")

    primeiro = banco.emitir_comprovante(NUMERO, "CE")
    segundo = banco.emitir_comprovante(NUMERO, "CE")
    assert primeiro == segundo, "o mesmo número ganhou dois comprovantes"
    print("comprovante: ok", primeiro["codigo"])

    assert banco.mensagem_nova("msg-teste-1", NUMERO) is True
    assert banco.mensagem_nova("msg-teste-1", NUMERO) is False
    print("mensagem repetida: ok")

    banco.registrar_evento(NUMERO, "evento de teste")
    assert banco.ultimos_eventos(NUMERO)[0][1] == "evento de teste"
    print("eventos: ok")

print("\nTudo certo. O banco original não foi alterado.")