"""
Testes do fluxo de conversa do Agente 1 (Fase 6).

Mocka todas as dependências externas (Ollama, Playwright, Telegram, Chroma)
para testar apenas a máquina de estados / orquestração — não precisa de
rede, modelo local rodando, nem de estar dentro da janela do Forms.

IMPORTANTE: todo teste que alcança a etapa de dados cadastrais mocka
delegar_reserva_ao_agente2 explicitamente — isso garante que nenhum teste
acidentalmente dispara uma reserva real no Forms de verdade.
"""
from contextlib import ExitStack
from unittest.mock import patch

import agents.agent1_cardapio as agent1

CARDAPIO_OK = {
    "sucesso": True,
    "itens_principais": "arroz, feijão, coxinha da asa",
    "salada": "mix de folhas",
    "suco": "uva com jabuticaba",
    "dia": "SEGUNDA",
}


def _stack_padrao(stack: ExitStack, **overrides):
    """Aplica os mocks do "caminho feliz" (horário ok, cardápio encontrado e
    lido com sucesso, intenção sempre 'hoje'). Use overrides=... pra
    sobrescrever qualquer um deles em testes específicos."""
    padrao = {
        "checar_horario_disponivel": {"disponivel": True, "motivo": ""},
        "buscar_imagens_cardapio": {
            "sucesso": True,
            "cardapio_semanal": "fake.png",
            "legenda": "fake2.png",
            "cardapio_dia": b"fake-bytes",
        },
        "extrair_cardapio_do_dia": CARDAPIO_OK,
        "_classificar_intencao": "hoje",
        "_ingerir_no_historico": None,
    }
    padrao.update(overrides)
    for nome, valor in padrao.items():
        stack.enter_context(patch.object(agent1, nome, return_value=valor))


def test_fluxo_completo_reserva_confirmada():
    with ExitStack() as stack:
        _stack_padrao(stack, delegar_reserva_ao_agente2={"sucesso": True})
        chat_id = "teste-fluxo-completo"

        r1 = agent1.processar_mensagem(chat_id, "oi")
        assert "Cardápio de hoje" in r1
        assert "reserva" in r1.lower()

        r2 = agent1.processar_mensagem(chat_id, "sim")
        assert "refeição" in r2.lower()

        r3 = agent1.processar_mensagem(chat_id, "almoço")
        assert "nome" in r3.lower()

        r4 = agent1.processar_mensagem(chat_id, "Kauhã Costa, 203184")
        assert "✅" in r4
        assert "Kauhã Costa" in r4


def test_fluxo_reserva_recusada():
    with ExitStack() as stack:
        _stack_padrao(stack)
        chat_id = "teste-recusa"

        agent1.processar_mensagem(chat_id, "oi")
        r2 = agent1.processar_mensagem(chat_id, "não")
        assert "nenhuma reserva" in r2.lower()


def test_horario_indisponivel_bloqueia_tudo():
    with ExitStack() as stack:
        stack.enter_context(patch.object(
            agent1, "checar_horario_disponivel",
            return_value={"disponivel": False, "motivo": "Fora do horário de teste."},
        ))
        chat_id = "teste-horario-fechado"

        r1 = agent1.processar_mensagem(chat_id, "oi")
        assert r1 == "Fora do horário de teste."


def test_tipo_refeicao_invalido_reprompt():
    with ExitStack() as stack:
        _stack_padrao(stack)
        chat_id = "teste-refeicao-invalida"

        agent1.processar_mensagem(chat_id, "oi")
        agent1.processar_mensagem(chat_id, "sim")
        r3 = agent1.processar_mensagem(chat_id, "xablau")
        assert "não reconheci" in r3.lower()


def test_dados_cadastrais_formato_invalido_reprompt():
    with ExitStack() as stack:
        _stack_padrao(stack)
        chat_id = "teste-dados-invalidos"

        agent1.processar_mensagem(chat_id, "oi")
        agent1.processar_mensagem(chat_id, "sim")
        agent1.processar_mensagem(chat_id, "jantar")
        r4 = agent1.processar_mensagem(chat_id, "meu nome sem virgula")
        assert "formato inválido" in r4.lower()


def test_falha_ao_buscar_imagens_cardapio():
    with ExitStack() as stack:
        _stack_padrao(stack, buscar_imagens_cardapio={
            "sucesso": False, "erro": "Forms fora do ar.",
        })
        chat_id = "teste-falha-imagem"

        r1 = agent1.processar_mensagem(chat_id, "oi")
        assert "não consegui acessar" in r1.lower()


def test_falha_ao_ler_cardapio_com_visao():
    with ExitStack() as stack:
        _stack_padrao(stack, extrair_cardapio_do_dia={
            "sucesso": False, "erro": "Modelo de visão indisponível.",
        })
        chat_id = "teste-falha-visao"

        r1 = agent1.processar_mensagem(chat_id, "oi")
        assert "não consegui ler" in r1.lower()


def test_intencao_historico_roteia_para_rag_sem_tocar_no_fluxo_de_reserva():
    with ExitStack() as stack:
        stack.enter_context(patch.object(agent1, "_classificar_intencao", return_value="historico"))
        stack.enter_context(patch.object(agent1, "consultar_historico_cardapios", return_value={
            "sucesso": True,
            "resposta": "Na segunda passada teve arroz, feijão e coxinha da asa.",
        }))
        chat_id = "teste-historico"

        r1 = agent1.processar_mensagem(chat_id, "o que teve segunda passada?")
        assert "coxinha da asa" in r1.lower()
        # garante que ficou no estado INICIO, não avançou pro fluxo de reserva
        assert agent1._get_sessao(chat_id).estado == agent1.Estado.INICIO


def test_falha_na_reserva_agente2_nao_quebra_a_conversa():
    with ExitStack() as stack:
        _stack_padrao(stack, delegar_reserva_ao_agente2={
            "sucesso": False, "erro": "Forms fechou no meio do preenchimento.",
        })
        chat_id = "teste-falha-reserva"

        agent1.processar_mensagem(chat_id, "oi")
        agent1.processar_mensagem(chat_id, "sim")
        agent1.processar_mensagem(chat_id, "almoço")
        r4 = agent1.processar_mensagem(chat_id, "Kauhã Costa, 203184")
        assert "❌" in r4
        assert "fechou no meio" in r4
