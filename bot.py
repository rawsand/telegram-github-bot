import os
import requests
from flask import Flask, request

app = Flask(__name__)

# ================= ENVIRONMENT VARIABLES =================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PCLOUD_TOKEN = os.environ.get("PCLOUD_TOKEN")

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

    # ================= START COMMAND =================
    if text.lower() == "/start":
        send_message(chat_id, "Send a direct link.")

    # ================= URL RECEIVED =================
    elif text.startswith("http"):

        send_message(chat_id, "⬆ Starting upload to pCloud...")

        success, error = upload_to_pcloud(text)

        if success:
            send_message(chat_id, "✅ Upload complete!")
        else:
            send_message(chat_id, f"❌ Upload failed: {error}")

    return "OK"


# ================= TELEGRAM =================

def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        }
    )


# ================= PCLOUD REMOTE UPLOAD =================

def upload_to_pcloud(file_url):

    try:

        response = requests.get(
            "https://api.pcloud.com/uploadfilefromurl",
            params={
                "auth": PCLOUD_TOKEN,
                "folderid": 0,
                "url": file_url
            }
        )

        data = response.json()

        if data.get("result") != 0:
            return False, data.get("error", "Unknown pCloud error")

        return True, None

    except Exception as e:
        return False, str(e)


# ================= MAIN =================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
