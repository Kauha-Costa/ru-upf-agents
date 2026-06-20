"""
Configuração central do sistema de reservas do RU/UPF.
Carrega variáveis sensíveis do .env (token do Telegram, etc.) e define
constantes de negócio (janelas de horário, URL do Forms, modelos locais).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Diretórios ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CARDAPIOS_DIR = DATA_DIR / "cardapios"          # imagens semanais já vistas (histórico p/ RAG)
VECTORSTORE_DIR = DATA_DIR / "vectorstore"       # índice Chroma

CARDAPIOS_DIR.mkdir(parents=True, exist_ok=True)
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

# --- Segredos (vêm do .env, nunca hardcoded) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# --- URL fixa do Google Forms do RU ---
# TODO: substituir pela URL real do formulário (a publicada no Instagram/RU).
FORMS_URL = os.getenv("FORMS_URL", "https://docs.google.com/forms/d/e/SEU_FORM_ID/viewform")

# --- Janelas de horário em que o Forms fica acessível ---
# (fora desses intervalos o cardápio nem aparece e a reserva não pode ser feita)
JANELAS_DISPONIVEIS = [
    (8, 0, 10, 0),   # 08:00 às 10:00
    (14, 0, 16, 0),  # 14:00 às 16:00
]

# RU funciona apenas em dias de semana (0=segunda ... 6=domingo)
DIAS_FUNCIONAMENTO = {0, 1, 2, 3, 4}  # seg a sex

DIA_SEMANA_PT = {
    0: "SEGUNDA",
    1: "TERÇA",
    2: "QUARTA",
    3: "QUINTA",
    4: "SEXTA",
    5: "SÁBADO",
    6: "DOMINGO",
}

# --- Modelos locais (Ollama) ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")          # raciocínio/roteamento
VISION_MODEL = os.getenv("VISION_MODEL", "llava:7b")        # leitura do cardápio (imagem)
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")  # embeddings p/ RAG

# --- Domínio do e-mail institucional usado no Forms ---
EMAIL_DOMAIN = "@upf.br"
