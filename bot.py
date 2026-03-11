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
    """
    Stream a file from the given URL to pCloud.
    Returns: (True, None) if successful, (False, error_message) if failed.
    """
    try:
        # Step 1: Get pCloud upload server
        resp = requests.get(f"https://api.pcloud.com/getuploadserver?auth={PCLOUD_TOKEN}")
        upload_json = resp.json()
        if upload_json.get("result") != 0:
            return False, upload_json.get("error", "Unknown error from pCloud")
        upload_url = upload_json["hosts"][0]

        # Step 2: Stream file using MultipartEncoder
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            m = MultipartEncoder(
                fields={
                    "file": ("uploaded_file", r.raw, "application/octet-stream")
                }
            )
            upload_resp = requests.post(
                f"https://{upload_url}/uploadfile?auth={PCLOUD_TOKEN}&folderid=0",
                data=m,
                headers={'Content-Type': m.content_type},
                timeout=600
            )

        # Step 3: Safely parse JSON response
        try:
            result = upload_resp.json()
        except ValueError:
            return False, f"Non-JSON response: {upload_resp.text[:200]}"

        if result.get("result") != 0:
            return False, result.get("error", "Unknown error from pCloud upload")

        return True, None

    except Exception as e:
        return False, str(e)

# ================= MAIN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
