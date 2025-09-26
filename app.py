import os, unicodedata, threading, asyncio, logging
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ====== НАСТРОЙКИ БОТА ======
CORRECT_ANSWER = "Я бывал здесь, я бывал там и бывал где-то посередине"
SECRET_FILE = "prize_secret.jpg"
SUCCESS_CAPTION = "Прочти хорошенько. Одна знаменитая история показывает, что бывает полезно ЧИТАТЬ картинки внимательно"

def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", (text or "")).casefold().strip()

# === Telegram bot ===
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я собако. Я жду ответ.help для очень глупых")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Тебе нужно отправить ответ одним сообщением и без точки в конце.Собако ждет.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if normalize(text) == normalize(CORRECT_ANSWER):
        try:
            with open(SECRET_FILE, "rb") as f:
                await update.message.reply_document(document=f, caption=SUCCESS_CAPTION)
        except FileNotFoundError:
            await update.message.reply_text("Файл приза не найден на сервере 😕")
    else:
        await update.message.reply_text("По пустякам Собако не разговаривает")

def build_bot_app() -> Application:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("Переменная TELEGRAM_TOKEN не задана.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app

def run_bot():
    # отдельный поток для asyncio-бота
    logging.basicConfig(level=logging.INFO)
    application = build_bot_app()
    asyncio.run(application.run_polling(allowed_updates=Update.ALL_TYPES))

# === Flask web (для пингов) ===
web = Flask(__name__)

@web.get("/")
def root():
    return "ok", 200

@web.get("/ping")
def ping():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    # локальный запуск: сначала бот, затем Flask
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
