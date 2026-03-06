import os
import asyncio
from flask import Flask, request

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

app = Flask(__name__)

# -----------------------------
# TELEGRAM APPLICATION
# -----------------------------

application = ApplicationBuilder().token(BOT_TOKEN).build()


# -----------------------------
# HANDLERS
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Working")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    text = update.message.text

    await update.message.reply_text(f"Received link:\n{text}")


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))


# -----------------------------
# INITIALIZE BOT
# -----------------------------

async def init_bot():

    await application.initialize()
    await application.start()

    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"

    await application.bot.set_webhook(webhook_url)


asyncio.run(init_bot())


# -----------------------------
# WEBHOOK
# -----------------------------

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json(force=True)

    update = Update.de_json(data, application.bot)

    asyncio.run(application.process_update(update))

    return "ok"


# -----------------------------
# HEALTH CHECK
# -----------------------------

@app.route("/")
def home():
    return "Bot Running"
