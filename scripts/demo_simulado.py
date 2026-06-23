"""
Demonstração simulada (não depende de Ollama, Playwright, Telegram nem da
janela real de horário do Forms). Pensada pra apresentar/corrigir o
trabalho a qualquer momento, sem risco de fazer uma reserva real.

Uso:
    python -m scripts.demo_simulado
"""
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parent.parent))

import agents.agent1_cardapio as agent1

CARDAPIO_FALSO = {
    "sucesso": True,
    "itens_principais": "arroz branco, feijão preto, coxinha da asa ao molho branco, farofa de couve",
    "salada": "mix de folhas, repolho, cenoura",
    "suco": "uva com jabuticaba",
    "dia": "SEGUNDA",
}

HISTORICO_FALSO = {
    "sucesso": True,
    "resposta": "Na segunda passada (dado simulado) teve arroz, feijão, coxinha da asa e farofa de couve.",
}


def main() -> None:
    print("=== DEMO SIMULADA — dados e ferramentas externas são fictícios ===")
    print("Nenhuma reserva real é feita. Não precisa de Ollama/Playwright/Telegram rodando.")
    print("Digite 'sair' para encerrar.\n")

    with ExitStack() as stack:
        stack.enter_context(patch.object(
            agent1, "checar_horario_disponivel", return_value={"disponivel": True, "motivo": ""}
        ))
        stack.enter_context(patch.object(agent1, "buscar_imagens_cardapio", return_value={
            "sucesso": True, "cardapio_semanal": "fake.png", "legenda": "fake2.png", "cardapio_dia": b"fake",
        }))
        stack.enter_context(patch.object(agent1, "extrair_cardapio_do_dia", return_value=CARDAPIO_FALSO))
        stack.enter_context(patch.object(agent1, "_ingerir_no_historico", return_value=None))
        stack.enter_context(patch.object(
            agent1, "delegar_reserva_ao_agente2", return_value={"sucesso": True}
        ))
        stack.enter_context(patch.object(
            agent1, "consultar_historico_cardapios", return_value=HISTORICO_FALSO
        ))
        # _classificar_intencao NÃO é mockada aqui de propósito: se você
        # tiver o Ollama rodando, a demo ainda mostra o roteamento por LLM
        # de verdade. Sem Ollama, ela cai no fallback "hoje" (ver
        # agents/agent1_cardapio.py) e a conversa segue normalmente.

        chat_id = "demo-simulada"
        print("Bot> (digite qualquer coisa pra começar, ex: 'oi')\n")
        while True:
            try:
                texto = input("Você> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando.")
                break
            if texto.lower() in ("sair", "exit", "quit"):
                print("Encerrando.")
                break
            resposta = agent1.processar_mensagem(chat_id, texto)
            print(f"Bot> {resposta}\n")


if __name__ == "__main__":
    main()
