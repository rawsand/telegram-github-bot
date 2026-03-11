import os
import requests
from flask import Flask, request
from requests_toolbelt.multipart.encoder import MultipartEncoder

app = Flask(__name__)

# ================= ENVIRONMENT VARIABLES =================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
PCLOUD_TOKEN = os.environ["PCLOUD_TOKEN"]  # Your pCloud auth token
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ================= ROUTES =================
@app.route("/")
def home():
    return "Bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return "OK"

    message = data.get("message")
    if not message:
        return "OK"

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # /start command
    if text.lower() == "/start":
        send_message(chat_id, "Send a direct link.")

    # If the message is a URL, start pCloud upload
    elif text.startswith("http"):
        send_message(chat_id, "⬆ Starting upload...")  # Step 2

        success, error_msg = upload_to_pcloud(text)  # Streaming upload

        if success:
            send_message(chat_id, "✅ Upload complete!")  # Step 3
        else:
            send_message(chat_id, f"❌ Upload failed: {error_msg}")  # Step 3 fail

    return "OK"

# ================= TELEGRAM FUNCTIONS =================
def send_message(chat_id, text):
    """Send a message via Telegram bot."""
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

# ================= PCLOUD UPLOAD WITH MULTIPART =================
def upload_to_pcloud(file_url):
    try:

        # Ask pCloud to download the file directly
        resp = requests.get(
            "https://api.pcloud.com/uploadfilefromurl",
            params={
                "auth": PCLOUD_TOKEN,
                "folderid": 0,
                "url": file_url
            }
        )

        data = resp.json()

        if data.get("result") != 0:
            return False, data.get("error", "Unknown pCloud error")

        return True, None

    except Exception as e:
        return False, str(e)

# ================= MAIN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
