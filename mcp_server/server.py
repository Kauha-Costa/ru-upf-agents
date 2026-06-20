"""
Servidor MCP — Tools do Agente 1 (Cardápio).

Expõe, via Model Context Protocol, as ferramentas que o Agente 1 pode
chamar. Cada tool é uma função pura e testável isoladamente; o agente
(agents/agent1_cardapio.py) decide QUANDO chamar cada uma com base no
raciocínio do LLM local.

Para rodar este servidor isoladamente (modo debug, sem o agente):
    python -m mcp_server.server
"""
from __future__ import annotations

import base64
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

import config

mcp = FastMCP("ru-upf-cardapio")


def _dentro_da_janela(agora: datetime | None = None) -> tuple[bool, str]:
    """Regra de negócio central: o Forms (e o cardápio) só fica acessível
    de seg a sex, dentro das janelas configuradas em config.JANELAS_DISPONIVEIS.
    Retorna (disponivel, motivo_se_indisponivel).
    """
    agora = agora or datetime.now()

    if agora.weekday() not in config.DIAS_FUNCIONAMENTO:
        return False, "O RU não atende aos fins de semana. Volte na segunda-feira."

    minutos_atual = agora.hour * 60 + agora.minute
    for h_ini, m_ini, h_fim, m_fim in config.JANELAS_DISPONIVEIS:
        ini = h_ini * 60 + m_ini
        fim = h_fim * 60 + m_fim
        if ini <= minutos_atual <= fim:
            return True, ""

    janelas_fmt = " e ".join(
        f"{h1:02d}h{m1:02d}–{h2:02d}h{m2:02d}" for h1, m1, h2, m2 in config.JANELAS_DISPONIVEIS
    )
    return False, f"O formulário só fica disponível das {janelas_fmt}. Tente novamente nesse horário."


@mcp.tool()
def checar_horario_disponivel() -> dict:
    """Verifica se o Forms do RU está dentro da janela de horário permitida
    agora. Deve ser chamada ANTES de qualquer tentativa de buscar o cardápio
    ou fazer reserva. Se 'disponivel' for False, o agente deve informar o
    'motivo' ao usuário e parar o fluxo (sem cache — sempre live)."""
    disponivel, motivo = _dentro_da_janela()
    return {"disponivel": disponivel, "motivo": motivo}


@mcp.tool()
def buscar_imagens_cardapio() -> dict:
    """Abre a página 1 do Google Forms (URL fixa em config.FORMS_URL) via
    automação de navegador e extrai as duas imagens publicadas nela: a
    imagem do cardápio semanal e a imagem da legenda de símbolos. Salva
    localmente e retorna os caminhos dos arquivos.

    Pré-condição: chamar checar_horario_disponivel() antes — se o Forms
    estiver fora da janela, a imagem não vai carregar.
    """
    # TODO (Fase 3): implementar com Playwright real, algo como:
    #   with sync_playwright() as p:
    #       browser = p.chromium.launch()
    #       page = browser.new_page()
    #       page.goto(config.FORMS_URL)
    #       imgs = page.locator("img").all()
    #       ... salvar src/screenshot de cada <img> relevante em
    #       config.CARDAPIOS_DIR ...
    raise NotImplementedError(
        "Implementar extração das imagens do Forms via Playwright (Fase 3)."
    )


@mcp.tool()
def extrair_cardapio_do_dia(caminho_imagem_semanal: str) -> dict:
    """Usa o modelo de visão local (config.VISION_MODEL via Ollama) para ler
    a imagem do cardápio semanal e retornar APENAS os itens do dia atual
    (entrada, salada, suco), já que a imagem traz a semana inteira
    (Segunda a Sexta) em colunas.
    """
    dia_semana = config.DIA_SEMANA_PT[datetime.now().weekday()]

    # TODO (Fase 3): chamar o Ollama com o modelo de visão, algo como:
    #   import ollama
    #   with open(caminho_imagem_semanal, "rb") as f:
    #       img_b64 = base64.b64encode(f.read()).decode()
    #   resposta = ollama.chat(
    #       model=config.VISION_MODEL,
    #       messages=[{
    #           "role": "user",
    #           "content": (
    #               f"Esta imagem mostra o cardápio semanal do RU, com colunas "
    #               f"por dia da semana. Extraia APENAS a coluna de {dia_semana}. "
    #               f"Responda em JSON com as chaves: prato_principal, "
    #               f"acompanhamentos, salada, suco."
    #           ),
    #           "images": [img_b64],
    #       }],
    #   )
    raise NotImplementedError(
        f"Implementar leitura da imagem via modelo de visão para {dia_semana} (Fase 3)."
    )


@mcp.tool()
def consultar_historico_cardapios(pergunta: str) -> dict:
    """Consulta a base vetorial (RAG) com cardápios de semanas anteriores
    para responder perguntas como 'o que teve na quarta passada' ou
    'esse prato contém glúten'. Usa embeddings locais (config.EMBED_MODEL)
    e o índice Chroma em config.VECTORSTORE_DIR.
    """
    # TODO (Fase 4): implementar consulta real ao Chroma (ver rag/vectorstore.py)
    raise NotImplementedError("Implementar consulta RAG ao histórico (Fase 4).")


@mcp.tool()
def enviar_mensagem_telegram(chat_id: str, texto: str) -> dict:
    """Envia uma mensagem de texto formatada ao usuário, no chat_id indicado,
    via Telegram Bot API."""
    # TODO (Fase 3): implementar com python-telegram-bot (Bot(token).send_message)
    raise NotImplementedError("Implementar envio via Telegram Bot API (Fase 3).")


@mcp.tool()
def delegar_reserva_ao_agente2(nome: str, matricula: str, refeicao: str) -> dict:
    """Encaminha os dados coletados (nome, matrícula, refeição escolhida:
    'Almoço', 'Jantar' ou 'Almoço e jantar') ao Agente 2, que executa a
    reserva no Forms. Retorna o resultado (sucesso/erro) repassado pelo
    Agente 2.
    """
    # TODO (Fase 5): chamar agents/agent2_reserva.py::executar_reserva(...)
    raise NotImplementedError("Implementar handoff para o Agente 2 (Fase 5).")


if __name__ == "__main__":
    mcp.run()
