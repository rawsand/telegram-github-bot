import os
import requests
from flask import Flask, request

app = Flask(__name__)

# Environment variables
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

    if text.lower() == "/start":
        send_message(chat_id, "Send a direct link.")

    # If text looks like a URL, start pCloud upload
    elif text.startswith("http"):
        send_message(chat_id, "⬆ Starting upload...")  # Step 2

        success = upload_to_pcloud(text)  # Streaming upload

        if success:
            send_message(chat_id, "✅ Upload complete!")  # Step 3
        else:
            send_message(chat_id, "❌ Upload failed.")

    return "OK"

# ================= TELEGRAM =================

def send_message(chat_id, text):
    """Send message via Telegram bot."""
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

# ================= PCLOUD UPLOAD =================

def upload_to_pcloud(file_url):
    try:
        resp = requests.get(f"https://api.pcloud.com/getuploadserver?auth={PCLOUD_TOKEN}")
        print("getuploadserver:", resp.json())
        upload_url = resp.json()["hosts"][0]

        with requests.get(file_url, stream=True) as r:
            print("file URL status:", r.status_code)
            r.raise_for_status()
            files = {"file": ("uploaded_file", r.raw)}
            upload_resp = requests.post(f"https://{upload_url}/uploadfile?auth={PCLOUD_TOKEN}", files=files)
            print("upload_resp:", upload_resp.json())

        result = upload_resp.json()
        return result.get("result") == 0

    except Exception as e:
        print("pCloud upload error:", e)
        return False

# ================= MAIN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
