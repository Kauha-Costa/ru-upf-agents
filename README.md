RU‑UPF Agents — Reserva automatizada de refeições

Trabalho Final — Disciplina de Inteligência Artificial — UPF 2026

**Autores:** Kauhã De Costa, Tareck Alãa, Julia Laitharth

---

Visão geral
-----------

Este repositório contém uma solução multiagente para consultar o cardápio diário do Restaurante Universitário (RU) da UPF e automatizar o envio de reservas via Google Forms. O usuário interage por Telegram (ou terminal em modo demo) e o sistema cuida de extrair o cardápio (visão), consultar histórico (RAG) e, quando solicitado, preencher e submeter o formulário.

Principais capacidades
- Responder com o cardápio do dia (extraído do Forms).
- Consultar histórico de cardápios via busca semântica (RAG).
- Automatizar o preenchimento e envio de reservas no Google Forms (Playwright).

Rápido: o sistema faz tudo localmente (modelos via Ollama, índice via ChromaDB).

Requisitos
----------

- macOS / Linux / Windows
- Python 3.10+ (recomendado 3.11+)
- Ollama rodando localmente com os modelos necessários
- Playwright (Chromium)
- Dependências Python em `requirements.txt`

Instalação rápida (macOS / Linux)
--------------------------------

```bash
# 1. Instale requisitos externos (ex.: Ollama)
ollama serve &
ollama pull llama3.1:8b      # ou phi3:mini em máquinas com pouca RAM
ollama pull qwen2.5vl:3b
ollama pull nomic-embed-text

# 2. Ambiente Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Configuração de ambiente
------------------------

Copie o arquivo de exemplo e preencha as variáveis:

```bash
cp .env.example .env
# Edite .env e preencha TELEGRAM_BOT_TOKEN e FORMS_URL
```

Como rodar
----------

1) Modo Telegram (produção)

```bash
python -m orchestrator.main
```

O bot ficará disponível no Telegram e responderá ao usuário. Logs aparecem no terminal.

2) Modo demo (terminal, sem Telegram)

```bash
python -m orchestrator.main --demo
```

3) Executar a suíte de testes (mockada — roda a qualquer hora)

```bash
pip install -r requirements.txt
pytest tests/ -v
```

4) Demo simulada (interactive)

```bash
python -m scripts.demo_simulado
```

Notas sobre latência
---------------------------------------------

O sistema pode demorar na primeira resposta por causa de operações pesadas feitas nessa etapa:

- inicialização/carregamento do modelo Ollama usado para raciocínio e visão;
- inicialização do navegador Playwright e carregamento do Google Forms;
- execução da inferência de visão (extração do cardápio) e geração de embeddings.

Essas etapas explicam por que o primeiro "oi" pode demorar.

--------------------------------------

- Use `python -m orchestrator.main --demo` ou `python -m scripts.demo_simulado` para demonstrar sem depender do horário do Forms.
- Para testes que envolvam Playwright/Forms reais, faça primeiro `dry_run=True` nas chamadas à `executar_reserva` (Agente 2) para evitar envios reais.

Como consultar o histórico
-------------------------

O histórico (RAG) armazena cardápios extraídos em dias anteriores e permite perguntas do tipo "o que teve na segunda passada?". A função pública é `consultar_historico_cardapios(pergunta: str) -> dict` em `mcp_server/server.py`.

Exemplos práticos:

- Via Python (ambiente configurado):

```bash
source .venv/bin/activate
python -c "from mcp_server import server; print(server.consultar_historico_cardapios('o que teve na segunda passada?'))"
```

- Via bot (modo normal ou `--demo`): envie como primeira mensagem do chat uma pergunta de histórico, por exemplo:

	"o que teve na segunda passada?"

O retorno esperado é um dicionário JSON com `sucesso` e `resposta` (texto sintetizado). Se o índice estiver vazio, a resposta será uma mensagem informando que não há histórico suficiente.

Para inspecionar os documentos brutos recuperados (debug):

```python
from rag.vectorstore import buscar_cardapios_similares
print(buscar_cardapios_similares('o que teve na segunda passada?', n_resultados=3))
```

Requisitos para consultas reais:

- Ollama disponível (para gerar embeddings e sintetizar a resposta);
- ChromaDB disponível em `data/vectorstore/` com entradas indexadas.

Se preferir, use `python -m scripts.demo_simulado` para ver o fluxo de histórico sem depender de serviços externos (útil para apresentação).

