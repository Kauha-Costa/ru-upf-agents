"""
Orquestrador / Entrypoint do sistema de reservas do RU/UPF.

Uso:
    python -m orchestrator.main             # roda o bot do Telegram de verdade
    python -m orchestrator.main --demo       # simula a conversa no terminal,
                                              # sem precisar do Telegram
                                              # (cobre o requisito de interface
                                              # via linha de comando do trabalho)

Em ambos os modos, o terminal mostra o log de cada decisão/ferramenta
chamada pelos agentes, permitindo acompanhar o fluxo principal.
"""
import logging
import sys
import asyncio

import config
from agents.agent1_cardapio import processar_mensagem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("orquestrador")


def rodar_modo_demo() -> None:
    """Simula a conversa do Telegram direto no terminal — útil para
    desenvolvimento e para demonstrar o sistema sem precisar configurar
    um chat real."""
    print("=== Modo demonstração (terminal) — Sistema de Reservas RU/UPF ===")
    print("Digite 'sair' para encerrar.\n")

    chat_id = "demo-local"
    print("Bot> (digite qualquer coisa para começar, ex: 'oi')")

    while True:
        try:
            texto = input("Você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if texto.lower() in ("sair", "exit", "quit"):
            print("Encerrando.")
            break

        resposta = processar_mensagem(chat_id, texto)
        print(f"Bot> {resposta}\n")


def rodar_modo_telegram() -> None:
    """Inicia o bot real, escutando mensagens via long polling."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN não configurado. Copie .env.example para .env "
            "e preencha o token gerado pelo @BotFather."
        )
        sys.exit(1)

    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = str(update.effective_chat.id)
        texto = update.message.text or ""
        logger.info("[%s] usuário: %s", chat_id, texto)

        # processar_mensagem é síncrona e usa Playwright/Ollama internamente.
        # Para não executar código bloqueante dentro do loop async do bot,
        # rodamos o fluxo completo em uma thread separada.
        resposta = await asyncio.to_thread(processar_mensagem, chat_id, texto)
        logger.info("[%s] bot: %s", chat_id, resposta)

        await update.message.reply_text(resposta)

    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot iniciado. Aguardando mensagens no Telegram...")
    app.run_polling()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        rodar_modo_demo()
    else:
        rodar_modo_telegram()
