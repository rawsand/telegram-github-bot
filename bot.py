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

    success, error_msg = upload_to_pcloud(text)
    if success:
          send_message(chat_id, "✅ Upload complete!")
    else:
          send_message(chat_id, f"❌ Upload failed: {error_msg}")
    
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
        upload_json = resp.json()
        if upload_json.get("result") != 0:
            return False, upload_json.get("error", "Unknown error")
        upload_url = upload_json["hosts"][0]

        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            files = {"file": ("uploaded_file", r.raw)}
            upload_resp = requests.post(f"https://{upload_url}/uploadfile?auth={PCLOUD_TOKEN}", files=files)
            upload_json = upload_resp.json()
            if upload_json.get("result") != 0:
                return False, upload_json.get("error", "Unknown error")

        return True, None

    except Exception as e:
        return False, str(e)

# ================= MAIN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
