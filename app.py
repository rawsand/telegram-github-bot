import os
import re
import requests
import threading
from datetime import datetime
from flask import Flask, request
from pcloud import PyCloud  # pip install pcloud

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

PCLOUD_EMAIL = os.environ.get("PCLOUD_EMAIL")
PCLOUD_PASSWORD = os.environ.get("PCLOUD_PASSWORD")
PCLOUD = PyCloud(PCLOUD_EMAIL, PCLOUD_PASSWORD)

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

        url = pending_links.get(chat_id)

        if choice.startswith("delete_one::"):
            filename = choice.split("::")[1]
            delete_single_file(chat_id, filename)
            return "OK"

        if choice == "delete_all":
            delete_all_files(chat_id)
            return "OK"

        return "OK"

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]

        if "text" in data["message"]:
            text = data["message"]["text"]

            if text == "/start":
                send_message(chat_id, "Send a direct link.")
            elif text.startswith("http"):
                pending_links[chat_id] = text
                threading.Thread(target=upload_file, args=(chat_id, text)).start()

    return "OK"

# ================= TELEGRAM =================
def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})

# ================= FILENAME =================
def extract_filename(headers, url):
    # Try Content-Disposition
    cd = headers.get("Content-Disposition")
    if cd:
        match = re.findall(r'filename\*?=(?:UTF-8\'\')?"?([^\";]+)"?', cd)
        if match:
            filename = match[0].strip()
            base, ext = os.path.splitext(filename)
            return (base[:50-len(ext)] + ext)[:50]

    # Try URL path
    if url:
        clean_url = url.split("?")[0]
        filename_from_url = clean_url.rstrip("/").split("/")[-1]
        if "." in filename_from_url and len(filename_from_url) > 3:
            base, ext = os.path.splitext(filename_from_url.strip())
            return (base[:50-len(ext)] + ext)[:50]

    # Fallback
    fallback = f"DirectUpload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    base, ext = os.path.splitext(fallback)
    return (base[:50-len(ext)] + ext)[:50]

# ================= UPLOAD ENGINE =================
def upload_file(chat_id, url):
    try:
        status_msg = send_message(chat_id, "🔍 Checking file...")

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            filename = extract_filename(r.headers, url)
            total_size = int(r.headers.get("Content-Length", 0))

            # Check pCloud space
            account_info = PCLOUD.getfolderinfo(folderid=0)
            free_space = account_info['folderidquota'] - account_info['folderidused']
            if total_size > free_space:
                send_message(chat_id, "❌ pCloud Full. Delete files below.")
                show_delete_menu(chat_id)
                return

            send_message(chat_id, f"⬆ Uploading {filename}...")

            uploaded_bytes = 0
            gap_percent = 10
            next_percent = gap_percent
            chunk_size = 1024*1024  # 1 MB

            def progress_chunk(chunk_len):
                nonlocal uploaded_bytes, next_percent
                uploaded_bytes += chunk_len
                if total_size == 0:
                    return
                percent = int((uploaded_bytes / total_size) * 100)
                if percent >= next_percent:
                    send_message(chat_id, f"⬆ Uploading: {percent}%")
                    next_percent += gap_percent

            def chunked_stream(stream):
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    progress_chunk(len(chunk))
                    yield chunk

            PCLOUD.uploadfile(filename, chunked_stream(r.raw), folderid=0)

            send_message(chat_id, f"✅ Upload successful!\nRoot Folder\nFile: {filename}")

    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")

# ================= DELETE =================
def show_delete_menu(chat_id):
    try:
        files = PCLOUD.listfolder(folderid=0)['metadata']
        if not files:
            send_message(chat_id, "⚠ No files found in pCloud root.")
            return

        keyboard = []
        for entry in files[:5]:  # show only first 5
            keyboard.append([{
                "text": f"Delete {entry['name']}",
                "callback_data": f"delete_one::{entry['name']}"
            }])

        keyboard.append([{
            "text": "Delete ALL Files",
            "callback_data": "delete_all"
        }])

        requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": "Select files to delete:",
            "reply_markup": {"inline_keyboard": keyboard}
        })

    except Exception as e:
        send_message(chat_id, f"❌ Could not fetch file list.\n{str(e)}")

def delete_single_file(chat_id, filename):
    try:
        files = PCLOUD.listfolder(folderid=0)['metadata']
        for f in files:
            if f['name'] == filename:
                PCLOUD.deletefile(f['path'])
                break
        send_message(chat_id, f"🗑 Deleted {filename}")
    except Exception as e:
        send_message(chat_id, f"❌ Delete error: {str(e)}")

def delete_all_files(chat_id):
    try:
        files = PCLOUD.listfolder(folderid=0)['metadata']
        for f in files[:5]:  # delete only first 5
            PCLOUD.deletefile(f['path'])
        send_message(chat_id, "🗑 All first 5 files deleted.")
    except Exception as e:
        send_message(chat_id, f"❌ Delete error: {str(e)}")

# ================= MAIN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
