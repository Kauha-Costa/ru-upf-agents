# Sistema de Reservas no RU/UPF — Agentes IA

> Trabalho Final de Inteligência Artificial — UPF 2026
> Status: 🚧 em desenvolvimento (Fase 2 concluída — ver seção "Status do projeto")

## O que é

Sistema multiagente que automatiza a reserva de refeição no Restaurante
Universitário da UPF via Telegram: o usuário conversa com o bot, recebe o
cardápio do dia (extraído automaticamente do Google Forms do RU) e, se
confirmar, tem a reserva preenchida e enviada automaticamente — sem precisar
acessar o formulário manualmente.

Dois agentes cooperam:
- **Agente 1 (Cardápio)** — interface com o usuário, leitura do cardápio
  (visão computacional local), histórico via RAG.
- **Agente 2 (Reserva)** — automação do Google Forms (preenchimento e envio).

## Setup do ambiente

### 1. Pré-requisitos

**macOS**
```bash
brew install python@3.11 git ollama
ollama serve &
```

**Windows**
- Instale o Python 3.11+ em [python.org](https://python.org) (marque "Add to PATH").
- Instale o Git em [git-scm.com](https://git-scm.com).
- Instale o Ollama em [ollama.com/download/windows](https://ollama.com/download/windows)
  (roda como serviço em background automaticamente — não precisa do `ollama serve &`).

### 2. Modelos locais

```bash
ollama pull llama3.1:8b      # ou phi3:mini se sua máquina tiver pouca RAM
ollama pull llava:7b         # ou moondream
ollama pull nomic-embed-text
```

### 3. Ambiente Python

**macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 4. Variáveis de ambiente

```bash
cp .env.example .env
```
Preencha `TELEGRAM_BOT_TOKEN` (gerado pelo @BotFather) e `FORMS_URL` (link
fixo do Google Forms do RU).

## Como executar

```bash
# Modo terminal (simula a conversa do Telegram, sem precisar de bot real)
python -m orchestrator.main --demo

# Modo real (bot do Telegram)
python -m orchestrator.main
```

## Status do projeto

| Fase | Item | Status |
|---|---|---|
| 1 | Setup de ambiente | ✅ |
| 2 | Estrutura do repositório + servidor MCP + esqueleto Agente 1 | ✅ |
| 3 | Integração Telegram real + Playwright (busca cardápio) + modelo de visão | ✅ testado no Forms real |
| 4 | Base de conhecimento + embeddings (RAG histórico) | ⏳ |
| 5 | Agente 2 (preenchimento/envio do Forms) + handoff entre agentes | ⏳ |
| 6 | Testes ponta a ponta | ⏳ |
| 7 | README final completo (todos os itens exigidos no PDF) | ⏳ |

> As funções ainda não implementadas levantam `NotImplementedError` de
> propósito, com um comentário `TODO (Fase X)` indicando onde e como serão
> completadas — isso mantém o sistema executável (modo demo já funciona,
> só avisa o que falta) durante todo o desenvolvimento.

## Estrutura

```
ru-upf-agents/
├── config.py                  # constantes, janelas de horário, modelos
├── mcp_server/server.py       # tools do Agente 1 expostas via MCP
├── agents/agent1_cardapio.py  # fluxo de conversa do Agente 1
├── orchestrator/main.py       # entrypoint (Telegram / --demo)
├── rag/                       # ingestão e consulta da base vetorial (Fase 4)
└── data/
    ├── cardapios/             # histórico de imagens do cardápio
    └── vectorstore/           # índice Chroma
```
