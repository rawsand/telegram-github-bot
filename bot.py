import os
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, filters

# Environment variables set on Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Send me a file link, and I will upload it to pCloud.")

def handle_link(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    
    if not url.startswith("http"):
        update.message.reply_text("Please send a valid link.")
        return

    msg = update.message.reply_text("Upload started...")
    
    try:
        # Get pCloud upload server
        resp = requests.get(f"https://api.pcloud.com/getuploadserver?auth={PCLOUD_TOKEN}")
        upload_url = resp.json()["hosts"][0]

        # Stream file from URL to pCloud
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            files = {'file': ('uploaded_file', r.raw)}
            upload_resp = requests.post(f"https://{upload_url}/uploadfile?auth={PCLOUD_TOKEN}", files=files)
        
        result = upload_resp.json()
        if result.get("result") == 0:
            msg.edit_text("✅ Upload successful!")
        else:
            msg.edit_text(f"❌ Upload failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        msg.edit_text(f"❌ Error: {e}")

def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
