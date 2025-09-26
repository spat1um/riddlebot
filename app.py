# app.py
import os
import unicodedata
import threading
import logging
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from waitress import serve

# ===================== НАСТРОЙКИ =====================
CORRECT_ANSWER = "Я бывал здесь, я бывал там и бывал где-то посередине"
SECRET_FILE = "prize_secret.jpg"
SUCCESS_CAPTION = "Прочти хорошенько. Одна знаменитая история показывает, что бывает полезно ЧИТАТЬ картинки внимательно"
PORT = int(os.environ.get("PORT", "10000"))
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "")).casefold().strip()

# ====== Telegram handlers ======
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я собако. Я жду ответ./help для очень глупых")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Тебе нужно отправить ответ одним сообщением и без точки в конце.Собако ждет.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if normalize(text) == normalize(CORRECT_ANSWER):
        try:
            with open(SECRET_FILE, "rb") as f:
                await update.message.reply_document(document=f, caption=SUCCESS_CAPTION)
        except FileNotFoundError:
            logging.error("SECRET_FILE not found: %s", SECRET_FILE)
            await update.message.reply_text("йок")
    else:
        await update.message.reply_text("По пустякам Собако не разговаривает")

def build_bot_app() -> Application:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Переменная TELEGRAM_TOKEN не задана в среде Render.")
    logging.info("Starting Telegram bot with token prefix: %s***", token[:10])
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app

def run_bot():
    # создаём event loop для побочного потока (обязательно!)
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    logging.info("BOT: building application…")
    application = build_bot_app()

    async def _before_start(app: Application):
        try:
            await app.bot.delete_webhook(drop_pending_updates=True)
            me = await app.bot.get_me()
            logging.info("Bot authorized as @%s (id=%s)", me.username, me.id)
        except Exception as e:
            logging.exception("Pre-start bot setup failed: %s", e)

    # хук выполнится перед запуском polling
    application.post_init = _before_start

    logging.info("BOT: starting polling…")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        stop_signals=None,       # мы в отдельном потоке — сигналы ловить нельзя
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=10,
    )
    logging.info("BOT: polling stopped.")

# ====== Flask (пинги от аптайм-монитора) ======
web = Flask(__name__)

@web.get("/")
def root():
    return "ok", 200

@web.get("/ping")
def ping():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    t = threading.Thread(target=run_bot, daemon=True, name="run_bot")
    t.start()
    logging.info("WEB: starting waitress on port %s", PORT)
    serve(web, host="0.0.0.0", port=PORT)
