import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from aiohttp import web

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is working.")

async def health(request):
    return web.Response(text="Bot is running")

# Build app in webhook mode
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Add handler
app.add_handler(CommandHandler("start", start))

# Add health route
if hasattr(app, "web_app"):   # <-- important check
    app.web_app.router.add_get("/", health)

# Run webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
)
