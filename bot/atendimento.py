"""Atendimento automático: o mesmo fluxo do simulador, agora com o banco de verdade.

responder(numero, texto) recebe a mensagem do cliente e devolve a lista de textos
que o bot deve mandar. A lista pode vir vazia (bot pausado, cliente descadastrado).
Este arquivo não envia nada: quem envia é o webhook (passo 4).

O número sempre no formato do banco: +55 + DDD + número (ex.: +5511912345678).
"""
import unicodedata
from datetime import datetime, timedelta, timezone

import banco
from templates import CONFIG, mensagens

PALAVRA = CONFIG["palavra"].upper()
PREFIXO = CONFIG["prefixo"]
FUSO_BRASILIA = timezone(timedelta(hours=-3))  # o Brasil não tem mais horário de verão

# Depois de tantas mensagens seguidas fora do fluxo, o bot para de responder até
# o cliente mandar uma palavra-chave. Evita ficar em loop com outro robô.
LIMITE_FALHAS = 3


def normalizar(texto: str) -> str:
    """'  sair. ' -> 'SAIR', 'Atendênte' -> 'ATENDENTE'."""
    sem_acento = "".join(
        letra for letra in unicodedata.normalize("NFD", texto)
        if not unicodedata.combining(letra)
    )
    return sem_acento.strip().strip(".!?,;:").strip().upper()


def _data_local(data_iso: str) -> str:
    """'2026-11-03T18:11:29.612Z' (UTC, como o banco grava) -> '03/11/2026 15:11'."""
    return datetime.fromisoformat(data_iso).astimezone(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M")


def responder(numero: str, texto_recebido: str, nome: str | None = None) -> list[str]:
    """Decide a resposta, grava o que mudou no banco e devolve os textos a enviar."""
    t = normalizar(texto_recebido)
    conversa = banco.pegar_conversa(numero)
    etapa, pausado, falhas = conversa["etapa"], conversa["pausado"], conversa["falhas"]
    consentimento = banco.consentimento(numero)
    comprovante = banco.comprovante_de(numero)

    def evento(descricao: str) -> None:
        banco.registrar_evento(numero, descricao)

    def salvar() -> None:
        banco.salvar_conversa(numero, etapa, pausado, falhas)

    # 1. Bot pausado: a equipe está respondendo. Só o SAIR ainda vale (sem resposta).
    if pausado:
        if t == "SAIR" and consentimento != "revogado":
            banco.mudar_consentimento(numero, "revogado", nome)
            evento("Consentimento revogado a pedido do cliente (bot pausado, sem resposta automática)")
        else:
            evento("Mensagem recebida com o bot pausado: sem resposta automática")
        return []

    # 2. Descadastrado: o bot fica quieto, a não ser que ele queira voltar ou falar com alguém.
    if consentimento == "revogado" and t not in (PALAVRA, "SAIR", "ATENDENTE"):
        evento("Cliente descadastrado: mensagem sem resposta automática")
        return []

    if t == "ATENDENTE":
        pausado, falhas = True, 0
        salvar()
        evento("Bot pausado: conversa passada para a equipe")
        return mensagens("atendimento", "atendente")

    if t == "SAIR":
        falhas = 0
        salvar()
        if consentimento == "revogado":
            evento("Pedido de descadastro repetido")
            return mensagens("atendimento", "ja_descadastrado")
        banco.mudar_consentimento(numero, "revogado", nome)
        evento("Consentimento revogado a pedido do cliente")
        return mensagens("atendimento", "sair_ok")

    if t == PALAVRA:
        falhas = 0
        if consentimento != "autorizado":
            banco.mudar_consentimento(numero, "autorizado", nome)
            evento("Consentimento registrado: o cliente pediu a promoção")
        if comprovante:
            salvar()
            evento("Comprovante existente lembrado ao cliente")
            return mensagens("atendimento", "ja_tem_comprovante", codigo=comprovante["codigo"])
        etapa = "menu"
        salvar()
        evento("Menu da promoção enviado")
        return mensagens("atendimento", "menu")

    if t in ("1", "2"):
        falhas = 0
        if etapa == "inicio":
            salvar()
            evento("Opção recebida antes de a promoção começar")
            return mensagens("atendimento", "comece_pela_palavra")

        if t == "2":
            if not comprovante:
                etapa = "instrucoes"
            salvar()
            evento("Instruções para salvar o contato enviadas")
            return mensagens("atendimento", "instrucoes")

        if comprovante:
            salvar()
            evento("Comprovante reenviado")
            return mensagens("atendimento", "ja_tem_comprovante", codigo=comprovante["codigo"])

        comprovante = banco.emitir_comprovante(numero, PREFIXO)
        etapa = "comprovante"
        salvar()
        evento("Declaração registrada: o cliente disse que salvou o contato")
        evento(f"Comprovante {comprovante['codigo']} emitido")
        return mensagens(
            "atendimento", "comprovante",
            codigo=comprovante["codigo"],
            emitido_em=_data_local(comprovante["emitido_em"]),
        )

    # 3. Qualquer outro texto: orienta, até o limite de tentativas.
    falhas += 1
    salvar()
    if falhas > LIMITE_FALHAS:
        evento("Texto fora das palavras-chave: limite atingido, sem resposta")
        return []
    evento("Texto fora das palavras-chave: orientação enviada")
    if etapa == "inicio":
        return mensagens("atendimento", "nao_entendi_inicio")
    if comprovante:
        return mensagens("atendimento", "nao_entendi_com_comprovante", codigo=comprovante["codigo"])
    return mensagens("atendimento", "nao_entendi_menu")


def retomar(numero: str) -> None:
    """A equipe terminou: o bot volta a responder esse cliente de onde ele parou."""
    conversa = banco.pegar_conversa(numero)
    banco.salvar_conversa(numero, conversa["etapa"], False, 0)
    banco.registrar_evento(numero, "Bot retomado pela equipe")