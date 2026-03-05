from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from bot.handlers.auth import login, start, unlink
from bot.handlers.documents import (
    documents,
    documents_callback,
    my_documents,
    my_documents_callback,
    search_document,
)
from bot.handlers.reminders import reminder_doc_callback, reminders, reminders_callback
from config import settings
from containers import Container

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env file.")

    container = Container()
    container.wire(packages=["bot"])

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("unlink", unlink))
    app.add_handler(CommandHandler("documents", documents))
    app.add_handler(CommandHandler("mydocuments", my_documents))
    app.add_handler(CommandHandler("reminders", reminders))
    app.add_handler(CommandHandler("search", search_document))
    app.add_handler(CallbackQueryHandler(documents_callback, pattern=r"^d[dw]?:"))
    app.add_handler(CallbackQueryHandler(my_documents_callback, pattern=r"^md[dw]?:"))
    app.add_handler(CallbackQueryHandler(reminders_callback, pattern=r"^rd?:"))
    app.add_handler(CallbackQueryHandler(reminder_doc_callback, pattern=r"^rdd[w]?:"))

    logger.info("DRMS bot is running — press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
