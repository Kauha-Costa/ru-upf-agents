"""
Agente 1 — Agente de Cardápio.

Responsável por toda a interação com o usuário: checar se o Forms está
disponível, buscar e interpretar o cardápio do dia, perguntar sobre a
reserva e, em caso positivo, delegar ao Agente 2.

Este módulo implementa o FLUXO determinístico da conversa (máquina de
estados simples) e usa o LLM local apenas nos pontos em que decisão ou
geração de linguagem natural são realmente necessárias — não é preciso
(nem desejável) deixar TUDO a cargo do LLM quando o fluxo de negócio já
é bem definido pelo enunciado do projeto.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

import config
from mcp_server.server import (
    checar_horario_disponivel,
    buscar_imagens_cardapio,
    extrair_cardapio_do_dia,
    consultar_historico_cardapios,
    delegar_reserva_ao_agente2,
)

logger = logging.getLogger("agente1.cardapio")


class Estado(Enum):
    INICIO = auto()
    AGUARDANDO_CONFIRMACAO_RESERVA = auto()
    AGUARDANDO_TIPO_REFEICAO = auto()
    AGUARDANDO_DADOS_CADASTRAIS = auto()
    FINALIZADO = auto()


@dataclass
class SessaoUsuario:
    """Estado de conversa de um usuário específico (1 por chat_id)."""
    chat_id: str
    estado: Estado = Estado.INICIO
    nome: str | None = None
    matricula: str | None = None
    refeicao: str | None = None
    cardapio_hoje: dict | None = None


# Sessões em memória — simples e suficiente para o escopo do trabalho.
# (Em produção trocaríamos por algo persistente; aqui o processo do bot
# roda continuamente, então memória é aceitável.)
_sessoes: dict[str, SessaoUsuario] = {}


def _get_sessao(chat_id: str) -> SessaoUsuario:
    if chat_id not in _sessoes:
        _sessoes[chat_id] = SessaoUsuario(chat_id=chat_id)
    return _sessoes[chat_id]


def processar_mensagem(chat_id: str, texto_usuario: str) -> str:
    """Ponto de entrada chamado pelo orquestrador (Telegram ou modo --demo)
    para cada mensagem recebida. Retorna o texto de resposta do bot.
    """
    sessao = _get_sessao(chat_id)
    texto_usuario = texto_usuario.strip().lower()

    if sessao.estado == Estado.INICIO:
        return _iniciar_consulta_cardapio(sessao)

    if sessao.estado == Estado.AGUARDANDO_CONFIRMACAO_RESERVA:
        return _tratar_confirmacao_reserva(sessao, texto_usuario)

    if sessao.estado == Estado.AGUARDANDO_TIPO_REFEICAO:
        return _tratar_tipo_refeicao(sessao, texto_usuario)

    if sessao.estado == Estado.AGUARDANDO_DADOS_CADASTRAIS:
        return _tratar_dados_cadastrais(sessao, texto_usuario)

    # Conversa já finalizada — reinicia o ciclo para uma nova consulta.
    sessao.estado = Estado.INICIO
    return _iniciar_consulta_cardapio(sessao)


def _iniciar_consulta_cardapio(sessao: SessaoUsuario) -> str:
    disponibilidade = checar_horario_disponivel()
    if not disponibilidade["disponivel"]:
        # Regra escolhida: SEM cache — se o Forms não está acessível agora,
        # avisamos o usuário e não tentamos nada além disso.
        return disponibilidade["motivo"]

    imagens = buscar_imagens_cardapio()
    if not imagens["sucesso"]:
        logger.warning("Falha ao buscar imagens do cardápio: %s", imagens["erro"])
        return f"⚠️ Não consegui acessar o cardápio agora. {imagens['erro']}"

    cardapio_hoje = extrair_cardapio_do_dia(imagens["cardapio_dia"])
    if not cardapio_hoje["sucesso"]:
        logger.warning("Falha ao extrair cardápio do dia: %s", cardapio_hoje["erro"])
        return f"⚠️ Não consegui ler o cardápio da imagem. {cardapio_hoje['erro']}"

    sessao.cardapio_hoje = cardapio_hoje
    sessao.estado = Estado.AGUARDANDO_CONFIRMACAO_RESERVA

    texto_cardapio = _formatar_cardapio(cardapio_hoje)
    return (
        f"{texto_cardapio}\n\n"
        "Deseja fazer a reserva para hoje? (sim/não)"
    )


def _tratar_confirmacao_reserva(sessao: SessaoUsuario, resposta: str) -> str:
    if resposta in ("sim", "s", "yes"):
        sessao.estado = Estado.AGUARDANDO_TIPO_REFEICAO
        return "Qual refeição você deseja reservar? (Almoço / Jantar / Almoço e jantar)"

    if resposta in ("não", "nao", "n", "no"):
        sessao.estado = Estado.FINALIZADO
        return "Tudo bem, nenhuma reserva foi feita. Se mudar de ideia, é só me chamar de novo!"

    return "Não entendi. Pode responder apenas 'sim' ou 'não'?"


def _tratar_tipo_refeicao(sessao: SessaoUsuario, resposta: str) -> str:
    mapa = {
        "almoço": "Almoço", "almoco": "Almoço", "1": "Almoço",
        "jantar": "Jantar", "2": "Jantar",
        "almoço e jantar": "Almoço e jantar", "almoco e jantar": "Almoço e jantar",
        "ambos": "Almoço e jantar", "3": "Almoço e jantar",
    }
    refeicao = mapa.get(resposta)
    if refeicao is None:
        return "Não reconheci a opção. Digite: Almoço, Jantar ou Almoço e jantar."

    sessao.refeicao = refeicao
    sessao.estado = Estado.AGUARDANDO_DADOS_CADASTRAIS
    return "Perfeito. Agora me informe seu nome completo e matrícula, separados por vírgula. Ex: Kauhã Costa, 203184"


def _tratar_dados_cadastrais(sessao: SessaoUsuario, resposta: str) -> str:
    partes = [p.strip() for p in resposta.split(",")]
    if len(partes) != 2:
        return "Formato inválido. Envie: Nome completo, matrícula (ex: Kauhã Costa, 203184)"

    sessao.nome, sessao.matricula = partes

    try:
        resultado = delegar_reserva_ao_agente2(
            nome=sessao.nome, matricula=sessao.matricula, refeicao=sessao.refeicao
        )
    except NotImplementedError:
        logger.warning("Handoff para o Agente 2 ainda não implementado (Fase 5).")
        sessao.estado = Estado.FINALIZADO
        return "⚠️ A etapa de reserva automática ainda será implementada na próxima fase."

    sessao.estado = Estado.FINALIZADO
    if resultado.get("sucesso"):
        return f"✅ Reserva confirmada para {sessao.refeicao.lower()}, {sessao.nome}!"
    return f"❌ Não consegui concluir a reserva: {resultado.get('erro', 'erro desconhecido')}"


def _formatar_cardapio(cardapio: dict) -> str:
    dia = config.DIA_SEMANA_PT[datetime.now().weekday()]
    return (
        f"🍽️ Cardápio de hoje ({dia.title()}):\n"
        f"- {cardapio.get('itens_principais', '—')}\n"
        f"- Salada: {cardapio.get('salada', '—')}\n"
        f"- Suco: {cardapio.get('suco', '—')}"
    )
