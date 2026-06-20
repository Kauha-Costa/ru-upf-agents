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
    automação de navegador e extrai as imagens publicadas nela: a imagem do
    cardápio semanal completa (para histórico/RAG), a legenda de símbolos, e
    um recorte só da coluna do dia atual (Segunda a Sexta = 1/5 da largura
    cada, na ordem). Recortar a coluna por geometria — em vez de pedir ao
    modelo de visão para "achar" o dia certo — evita o erro mais comum dos
    modelos pequenos, que é confundir/misturar colunas.

    O cardápio semanal/legenda são salvos em disco nomeados pela SEMANA
    (segunda-feira daquela semana), não pelo dia exato — como é a mesma
    imagem de segunda a sexta, isso evita salvar 5 cópias idênticas por
    semana (útil também como acervo para o RAG da Fase 4: 1 arquivo =
    1 semana de histórico). O recorte do dia é só um artefato temporário
    para a leitura do modelo de visão, então fica em memória (bytes),
    sem ser persistido.

    Pré-condição: chamar checar_horario_disponivel() antes — se o Forms
    estiver fora da janela, a imagem não vai carregar.
    """
    from datetime import timedelta
    from playwright.sync_api import sync_playwright

    agora = datetime.now()
    dia_idx = agora.weekday()  # 0=Segunda ... 4=Sexta (bate com as colunas)
    inicio_semana = (agora - timedelta(days=dia_idx)).date().isoformat()
    caminho_semanal = config.CARDAPIOS_DIR / f"semanal_{inicio_semana}.png"
    caminho_legenda = config.CARDAPIOS_DIR / f"legenda_{inicio_semana}.png"

    # Limiar para distinguir as imagens grandes (cardápio/legenda) de ícones
    # pequenos (logo da UPF, ícone de nuvem do Google, etc.). Ajuste se
    # necessário depois de rodar o debug abaixo no formulário real.
    LARGURA_MINIMA = 300
    ALTURA_MINIMA = 150
    N_COLUNAS = 5  # Segunda a Sexta

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1600})
            page.goto(config.FORMS_URL, wait_until="networkidle", timeout=20000)

            candidatas = []
            for img in page.locator("img").all():
                try:
                    box = img.bounding_box()
                except Exception:
                    box = None
                if box and box["width"] >= LARGURA_MINIMA and box["height"] >= ALTURA_MINIMA:
                    candidatas.append((box["y"], box, img))

            candidatas.sort(key=lambda item: item[0])  # ordem visual: topo -> baixo

            if len(candidatas) < 2:
                browser.close()
                return {
                    "sucesso": False,
                    "erro": (
                        f"Esperava 2 imagens grandes na página 1 e encontrei "
                        f"{len(candidatas)}. O formulário pode estar fechado ou "
                        f"a estrutura da página mudou."
                    ),
                }

            _, box_cardapio, img_cardapio = candidatas[0]
            _, _, img_legenda = candidatas[1]
            img_cardapio.screenshot(path=str(caminho_semanal))
            img_legenda.screenshot(path=str(caminho_legenda))

            # Recorte da coluna do dia: divide a largura da imagem do
            # cardápio em N_COLUNAS partes iguais e captura só a fatia
            # correspondente ao dia atual — fica em memória (bytes),
            # não salva em disco (é descartável após a leitura).
            largura_coluna = box_cardapio["width"] / N_COLUNAS
            clip = {
                "x": box_cardapio["x"] + dia_idx * largura_coluna,
                "y": box_cardapio["y"],
                "width": largura_coluna,
                "height": box_cardapio["height"],
            }
            bytes_dia = page.screenshot(clip=clip)  # sem "path" -> retorna bytes

            browser.close()
    except Exception as exc:  # qualquer falha de navegação/timeout etc.
        return {"sucesso": False, "erro": f"Falha ao acessar o Forms: {exc}"}

    return {
        "sucesso": True,
        "cardapio_semanal": str(caminho_semanal),
        "legenda": str(caminho_legenda),
        "cardapio_dia": bytes_dia,
    }


@mcp.tool()
def extrair_cardapio_do_dia(imagem_dia: bytes) -> dict:
    """Usa o modelo de visão local (config.VISION_MODEL via Ollama) para ler
    o recorte da coluna do dia (já isolada por buscar_imagens_cardapio,
    sem outras colunas/dias misturados) e transcrever os itens do cardápio.
    """
    import json
    import ollama

    dia_semana = config.DIA_SEMANA_PT[datetime.now().weekday()]

    schema = {
        "type": "object",
        "properties": {
            "itens_principais": {"type": "string"},
            "salada": {"type": "string"},
            "suco": {"type": "string"},
        },
        "required": ["itens_principais", "salada", "suco"],
    }

    prompt = (
        "Esta imagem é o recorte de UM ÚNICO dia do cardápio de um restaurante "
        "universitário. Ela tem 3 blocos de texto, nessa ordem: "
        "(1) 'MENU DO DIA' — lista de pratos (arroz, feijão, proteína e "
        "acompanhamentos, tudo junto, sem distinção); "
        "(2) 'SALADAS' — opções de salada; "
        "(3) 'SUCO' — suco do dia.\n\n"
        "Transcreva o conteúdo de cada bloco (NÃO repita os títulos 'MENU DO "
        "DIA'/'SALADAS'/'SUCO'), em português, separando itens por vírgula, "
        "exatamente como está escrito. Ignore ícones/símbolos pequenos ao "
        "lado dos textos (só indicam informação nutricional, não fazem parte "
        "do nome do prato). Responda apenas no JSON pedido."
    )

    try:
        resposta = ollama.chat(
            model=config.VISION_MODEL,
            messages=[{"role": "user", "content": prompt, "images": [imagem_dia]}],
            format=schema,
        )
        dados = json.loads(resposta.message.content)
    except Exception as exc:
        return {"sucesso": False, "erro": f"Falha ao ler o cardápio com o modelo de visão: {exc}"}

    dados["dia"] = dia_semana  # vem do relógio do sistema, não do modelo — sempre correto
    dados["sucesso"] = True
    return dados


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
    """Envia uma mensagem de texto ao usuário, no chat_id indicado, via
    Telegram Bot API. Usada para notificações proativas (ex: Agente 2
    confirmando a reserva depois de algum tempo). Para a resposta imediata
    de cada turno da conversa, o orquestrador usa reply_text diretamente —
    ver orchestrator/main.py.
    """
    import requests

    if not config.TELEGRAM_BOT_TOKEN:
        return {"sucesso": False, "erro": "TELEGRAM_BOT_TOKEN não configurado no .env"}

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": chat_id, "text": texto}, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        return {"sucesso": False, "erro": f"Falha ao enviar mensagem: {exc}"}

    return {"sucesso": True}


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
