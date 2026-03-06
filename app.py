import os
import re
import threading
import requests
from datetime import datetime
from flask import Flask, request
from pcloud_handler import PcloudHandler  # You will create this similar to dropbox_handler

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

PCLOUD = PcloudHandler(PCLOUD_TOKEN)
pending_links = {}

# ================= TELEGRAM =================

def send_message(chat_id, text):
    r = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )
    return r.json()

def edit_message(chat_id, message_id, text):
    requests.post(
        f"{TELEGRAM_API}/editMessageText",
        json={"chat_id": chat_id, "message_id": message_id, "text": text}
    )

# ================= FILENAME =================

def extract_filename(headers, url):
    cd = headers.get("Content-Disposition")
    if cd:
        match = re.findall(r'filename="?([^";]+)"?', cd)
        if match:
            name = match[0]
            base, ext = os.path.splitext(name)
            return (base[:50-len(ext)] + ext)[:50]

    name = url.split("?")[0].split("/")[-1]
    if "." in name:
        base, ext = os.path.splitext(name)
        return (base[:50-len(ext)] + ext)[:50]

    return f"Upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

# ================= DELETE MENU =================

def show_delete_menu(chat_id):
    files = PCLOUD.list_files()
    if not files:
        send_message(chat_id, "⚠ No files to delete")
        return

    keyboard = []
    for name, fid in files[:5]:
        keyboard.append([{"text": f"Delete {name}", "callback_data": f"delete::{fid}"}])

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "Delete files:",
            "reply_markup": {"inline_keyboard": keyboard}
        }
    )

# ================= UPLOAD ENGINE =================

def upload_file(chat_id, url):
    try:
        msg = send_message(chat_id, "🔍 Checking file...")
        message_id = msg["result"]["message_id"]

        r = requests.get(url, stream=True)
        total_size = int(r.headers.get("Content-Length", 0))
        filename = extract_filename(r.headers, url)
        free = PCLOUD.get_space()

        if total_size > free:
            edit_message(chat_id, message_id, "❌ pCloud full.")
            show_delete_menu(chat_id)
            return

        edit_message(chat_id, message_id, f"⬆ Uploading\n{filename}")

        uploaded = 0
        next_percent = 10

        def progress_callback(chunk_bytes):
            nonlocal uploaded, next_percent
            uploaded += len(chunk_bytes)
            percent = int(uploaded * 100 / total_size)
            if percent >= next_percent:
                edit_message(chat_id, message_id, f"⬆ Uploading: {percent}%")
                next_percent += 10

        # Streaming upload directly to pCloud
        PCLOUD.upload_stream(r, filename, progress_callback)

        edit_message(chat_id, message_id, f"✅ Upload complete: {filename}")

    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")

# ================= WEBHOOK =================

@app.route("/")
def home():
    return "Bot Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        data_val = query["data"]

        if data_val.startswith("delete::"):
            fileid = data_val.split("::")[1]
            PCLOUD.delete_file(fileid)
            send_message(chat_id, "🗑 File deleted")
        return "OK"

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        if "text" in data["message"]:
            text = data["message"]["text"]
            if text.startswith("http"):
                threading.Thread(target=upload_file, args=(chat_id, text)).start()
            else:
                send_message(chat_id, "Send a direct download link")
    return "OK"

# ================= MAIN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
