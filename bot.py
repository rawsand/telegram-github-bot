import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]  # Fail fast if not set
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

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

    if text.lower() == "/start":  # case-insensitive match
        send_message(chat_id, "Send a direct link.")

    return "OK"

# ================= TELEGRAM =================

def send_message(chat_id, text):
    """Send message via Telegram bot."""
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

# ================= MAIN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
