import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from aiohttp import web

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
PCLOUD_TOKEN = os.environ["PCLOUD_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a file link, and I will upload it to pCloud.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("Please send a valid link.")
        return
    msg = await update.message.reply_text("Upload started...")
    try:
        resp = requests.get(f"https://api.pcloud.com/getuploadserver?auth={PCLOUD_TOKEN}")
        upload_url = resp.json()["hosts"][0]
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            files = {"file": ("uploaded_file", r.raw)}
            upload_resp = requests.post(f"https://{upload_url}/uploadfile?auth={PCLOUD_TOKEN}", files=files)
        result = upload_resp.json()
        if result.get("result") == 0:
            await msg.edit_text("✅ Upload successful!")
        else:
            await msg.edit_text(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

# Health route for Render
async def health(request):
    return web.Response(text="Bot is running")

# Build app
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

# Add health route
app.web_app.router.add_get("/", health)

# Correct webhook URL path: /<TOKEN>
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
)
