import os
import re
import requests
import threading
from datetime import datetime
from flask import Flask, request
from pcloud_handler import PCloudHandler

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
PCLOUD_TOKEN = os.environ.get("PCLOUD_TOKEN")

PCLOUD = PCloudHandler(PCLOUD_TOKEN)
pending_links = {}

# ================= ROUTES =================

@app.route("/")
def home():
    return "Bot running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "callback_query" in data:
        query = data["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        choice = query["data"]

        if choice.startswith("delete_one::"):
            fileid = int(choice.split("::")[1])
            PCLOUD.delete_file(fileid)
            send_message(chat_id, "🗑 File deleted")
            retry_upload(chat_id)
            return "OK"

        return "OK"

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if text.startswith("http"):
            pending_links[chat_id] = text
            threading.Thread(target=upload_file, args=(chat_id, text)).start()

    return "OK"

# ================= TELEGRAM =================

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})

def show_delete_menu(chat_id):
    entries = PCLOUD.list_files()
    if not entries:
        send_message(chat_id, "⚠ No files found in pCloud root.")
        return

    keyboard = []
    for e in entries:
        keyboard.append([{"text": f"Delete {e['name']}", "callback_data": f"delete_one::{e['fileid']}"}])

    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": "Select files to delete:",
        "reply_markup": {"inline_keyboard": keyboard}
    })

# ================= UPLOAD =================

def extract_filename(headers, url):
    cd = headers.get("Content-Disposition") if headers else None
    if cd:
        match = re.findall(r'filename\*?=(?:UTF-8\'\')?"?([^\";]+)"?', cd)
        if match:
            filename = match[0].strip()
            base, ext = os.path.splitext(filename)
            return (base[:50-len(ext)] + ext)[:50]
    if url:
        clean_url = url.split("?")[0]
        filename_from_url = clean_url.rstrip("/").split("/")[-1]
        if "." in filename_from_url and len(filename_from_url) > 3:
            base, ext = os.path.splitext(filename_from_url.strip())
            return (base[:50-len(ext)] + ext)[:50]
    fallback = f"DirectUpload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    base, ext = os.path.splitext(fallback)
    return (base[:50-len(ext)] + ext)[:50]

def upload_file(chat_id, url):
    try:
        send_message(chat_id, "🔍 Checking file...")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            filename = extract_filename(r.headers, url)
            total_size = int(r.headers.get("Content-Length", 0))

            total_space, used_space = PCLOUD.get_space_info()
            free_space = total_space - used_space
            if total_size > free_space:
                send_message(chat_id, "❌ pCloud Full. Delete files below.")
                show_delete_menu(chat_id)
                return

            send_message(chat_id, f"⬆ Uploading {filename}...")
            PCLOUD.upload_file(r.raw, filename)
            send_message(chat_id, f"✅ Upload successful!\nRoot Folder\nFile: {filename}")

    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")

def retry_upload(chat_id):
    url = pending_links.get(chat_id)
    if url:
        threading.Thread(target=upload_file, args=(chat_id, url)).start()

# ================= MAIN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
