"""
Testes da regra de horário/dia de funcionamento (Fase 6).

Não precisam de Ollama, Playwright, Telegram nem de estar dentro da janela
real — a data é simulada (igual ao truque que já usamos manualmente nas
Fases 3/4), então podem rodar a qualquer momento.
"""
from datetime import datetime as real_datetime
from unittest.mock import patch

import mcp_server.server as server


def _com_data_falsa(ano, mes, dia, hora, minuto):
    class DataFalsa(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(ano, mes, dia, hora, minuto)

    return patch.object(server, "datetime", DataFalsa)


def test_segunda_dentro_da_janela_da_manha():
    with _com_data_falsa(2026, 6, 15, 9, 0):  # segunda, 09h
        resultado = server.checar_horario_disponivel()
    assert resultado["disponivel"] is True


def test_segunda_dentro_da_janela_da_tarde():
    with _com_data_falsa(2026, 6, 17, 15, 0):  # quarta, 15h
        resultado = server.checar_horario_disponivel()
    assert resultado["disponivel"] is True


def test_segunda_fora_da_janela_meio_dia():
    with _com_data_falsa(2026, 6, 15, 12, 0):  # segunda, meio-dia
        resultado = server.checar_horario_disponivel()
    assert resultado["disponivel"] is False
    assert resultado["motivo"]  # tem que vir alguma explicação


def test_sabado_bloqueado_mesmo_dentro_do_horario():
    with _com_data_falsa(2026, 6, 20, 9, 0):  # sábado, 09h
        resultado = server.checar_horario_disponivel()
    assert resultado["disponivel"] is False
    assert "segunda" in resultado["motivo"].lower() or "fim de semana" in resultado["motivo"].lower()


def test_limite_exato_do_inicio_da_janela():
    with _com_data_falsa(2026, 6, 16, 8, 0):  # terça, 08h00 em ponto
        resultado = server.checar_horario_disponivel()
    assert resultado["disponivel"] is True


def test_um_minuto_antes_da_janela_fecha():
    with _com_data_falsa(2026, 6, 16, 10, 1):  # terça, 10h01 (1 min depois do fim)
        resultado = server.checar_horario_disponivel()
    assert resultado["disponivel"] is False
