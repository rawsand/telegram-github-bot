import os
import re
import requests
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)


# -----------------------------
# TELEGRAM SEND MESSAGE
# -----------------------------

def send_message(chat_id, text, reply_markup=None):

    url = f"{TELEGRAM_API}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    requests.post(url, json=data)


def edit_message(chat_id, message_id, text):

    url = f"{TELEGRAM_API}/editMessageText"

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    requests.post(url, json=data)


# -----------------------------
# UTIL FUNCTIONS
# -----------------------------

def get_filename(url):

    name = url.split("/")[-1]
    name = name.split("?")[0]

    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)

    if len(name) > 60:
        name = name[:60]

    return name


def format_size(size):

    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024


def get_pcloud_space():

    url = "https://api.pcloud.com/userinfo"

    r = requests.get(url, params={"auth": PCLOUD_TOKEN}).json()

    quota = r["quota"]
    used = r["usedquota"]

    return quota - used


def list_files():

    url = "https://api.pcloud.com/listfolder"

    r = requests.get(url, params={
        "auth": PCLOUD_TOKEN,
        "folderid": 0
    }).json()

    files = []

    if "metadata" in r:
        for f in r["metadata"]["contents"]:
            if not f["isfolder"]:
                files.append((f["name"], f["fileid"]))

    return files


def delete_file(fileid):

    url = "https://api.pcloud.com/deletefile"

    requests.get(url, params={
        "auth": PCLOUD_TOKEN,
        "fileid": fileid
    })


# -----------------------------
# DOWNLOAD + UPLOAD
# -----------------------------

def download_upload(url, chat_id, message_id):

    filename = get_filename(url)

    r = requests.head(url)
    size = int(r.headers.get("content-length", 0))

    free = get_pcloud_space()

    edit_message(
        chat_id,
        message_id,
        f"📄 {filename}\n📦 {format_size(size)}\n💾 Free {format_size(free)}"
    )

    if free < size:

        files = list_files()

        if not files:
            send_message(chat_id, "❌ Disk Full")
            return

        keyboard = {
            "inline_keyboard": []
        }

        for name, fid in files[:10]:
            keyboard["inline_keyboard"].append(
                [{"text": f"Delete {name}", "callback_data": f"del|{fid}"}]
            )

        send_message(chat_id, "⚠ Delete files:", keyboard)

        return

    # DOWNLOAD

    local = f"/tmp/{filename}"

    r = requests.get(url, stream=True)

    downloaded = 0
    next_update = 10

    with open(local, "wb") as f:

        for chunk in r.iter_content(1024*1024):

            if chunk:

                f.write(chunk)
                downloaded += len(chunk)

                percent = int(downloaded*100/size)

                if percent >= next_update:

                    edit_message(
                        chat_id,
                        message_id,
                        f"⬇ Downloading {percent}%"
                    )

                    next_update += 10

    edit_message(chat_id, message_id, "☁ Uploading...")

    upload_url = "https://api.pcloud.com/uploadfile"

    files = {"file": open(local, "rb")}

    data = {
        "auth": PCLOUD_TOKEN,
        "folderid": 0
    }

    requests.post(upload_url, files=files, data=data)

    edit_message(chat_id, message_id, "✅ Upload Complete")

    os.remove(local)


# -----------------------------
# WEBHOOK
# -----------------------------

@app.route("/", methods=["GET"])
def home():
    return "Bot Running"


@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    if "message" in data:

        message = data["message"]

        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]

        if user_id != OWNER_ID:
            return "ok"

        text = message.get("text", "")

        msg = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": "Starting..."}
        ).json()

        message_id = msg["result"]["message_id"]

        download_upload(text, chat_id, message_id)

    elif "callback_query" in data:

        query = data["callback_query"]
        data = query["data"]

        if data.startswith("del|"):
            fileid = data.split("|")[1]
            delete_file(fileid)

    return "ok"
