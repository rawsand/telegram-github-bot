import os
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Environment variables on Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")  # Your pCloud OAuth token

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Send me a file link, and I will upload it to pCloud.")

def handle_link(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    
    # Basic URL validation
    if not url.startswith("http"):
        update.message.reply_text("Please send a valid link.")
        return

    msg = update.message.reply_text("Upload started...")
    
    try:
        # Streaming upload to pCloud
        # First, get a pCloud upload URL
        resp = requests.get(f"https://api.pcloud.com/getuploadserver?auth={PCLOUD_TOKEN}")
        upload_url = resp.json()["hosts"][0]
        
        # Stream file directly from link
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
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
