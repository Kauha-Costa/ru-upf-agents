"""
Agente 2 — Agente de Reserva.

Executa a reserva de forma autônoma: abre o Google Forms do RU, preenche os
campos com os dados recebidos do Agente 1 e submete. Usa Playwright pra
interagir com a página REAL renderizada (clica, digita) em vez de montar o
POST manualmente — assim os tokens internos do Forms (fbzx, dlut,
partialResponse etc., que mudam a cada carregamento) são gerados pelo
próprio navegador, sem precisar ser replicados à mão.

IDs dos campos (capturados de uma submissão real do formulário — ver
definicao_e_arquitetura): ajustar as constantes abaixo se o Forms for
republicado com IDs diferentes.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import config

# --- Seletores dos campos (página 2) ---
CAMPO_ANO = 'input[name="entry.438994047_year"]'
CAMPO_MES = 'input[name="entry.438994047_month"]'
CAMPO_DIA = 'input[name="entry.438994047_day"]'
CAMPO_NOME = 'input[name="entry.1773563523"]'
CAMPO_MATRICULA = 'input[name="entry.1642444040"]'
CAMPO_REFEICAO = "entry.24359638"
CAMPO_VINCULO = "entry.919059448"

# Todo usuário do bot é estudante da UPF (o fluxo de conversa só coleta
# nome + matrícula) — então o vínculo é fixo. Ajustar aqui se o escopo
# crescer para outros públicos (funcionário/professor/comunidade).
VINCULO_PADRAO = "Aluno graduação UPF"


def executar_reserva(
    nome: str, matricula: str, refeicao: str, dry_run: bool = False, headless: bool = True
) -> dict:
    """Abre o Forms, preenche os campos e submete a reserva.

    dry_run=True preenche tudo mas NÃO clica em "Enviar" — em vez disso tira
    um screenshot da página 2 preenchida e devolve o caminho, pra inspeção
    visual sem registrar uma reserva real. Use isso pra testar/depurar os
    seletores antes de rodar de verdade.

    Retorna {"sucesso": True} ou {"sucesso": False, "erro": "..."}.
    """
    from playwright.sync_api import sync_playwright

    email = f"{matricula}{config.EMAIL_DOMAIN}"
    hoje = datetime.now()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page(viewport={"width": 1280, "height": 1600})
            page.goto(config.FORMS_URL, wait_until="networkidle", timeout=20000)

            # --- Página 1: e-mail institucional ---
            page.get_by_role("textbox").first.fill(email)
            page.get_by_role("button", name="Avançar").click()
            page.wait_for_timeout(1000)  # tempo da página 2 renderizar

            # --- Página 2: dados da reserva ---
            page.wait_for_selector('input[type="date"]', timeout=20000)
            campos = page.get_by_role("textbox")
            if campos.count() < 3:
                raise Exception("Não encontrei os campos visíveis da página 2 do Forms")

            # A página 2 atual exibe: data, nome e matrícula em inputs visíveis.
            data_iso = hoje.date().isoformat()
            campos.nth(0).fill(data_iso)
            campos.nth(1).fill(nome)
            campos.nth(2).fill(matricula)

            _selecionar_opcao_radio(page, refeicao)
            _selecionar_opcao_radio(page, VINCULO_PADRAO)

            if dry_run:
                caminho_print = str(config.CARDAPIOS_DIR / "dry_run_pagina2.png")
                page.screenshot(path=caminho_print, full_page=True)
                browser.close()
                return {"sucesso": True, "dry_run": True, "screenshot": caminho_print}

            page.get_by_role("button", name="Enviar").click()
            page.wait_for_timeout(1500)
            confirmado = _confirmar_envio(page)
            browser.close()
    except Exception as exc:
        return {"sucesso": False, "erro": f"Falha ao preencher/enviar o Forms: {exc}"}

    if not confirmado:
        return {
            "sucesso": False,
            "erro": (
                "O Forms não mostrou a confirmação de envio esperada — "
                "verifique se os seletores/IDs ainda batem com a versão "
                "atual do formulário."
            ),
        }
    return {"sucesso": True}


def _selecionar_opcao(page, nome_campo: str, valor: str) -> None:
    """Marca o radio/checkbox cujo name=nome_campo e value=valor."""
    page.check(f'input[name="{nome_campo}"][value="{valor}"]')


def _selecionar_opcao_radio(page, valor: str) -> None:
    """Clica no botão de opção correspondente ao texto visível."""
    # O formulário atual usa radio buttons estilizados sem name/values visíveis.
    # Seleciona pelo atributo aria-label exato para evitar correspondências parciais
    # como 'Almoço' e 'Almoço e jantar'.
    page.get_by_role("radio", name=valor, exact=True).click()


def _confirmar_envio(page) -> bool:
    """Verifica se o Forms mostrou a mensagem de confirmação de envio."""
    try:
        page.wait_for_selector("text=registrada", timeout=5000)
        return True
    except Exception:
        return False
