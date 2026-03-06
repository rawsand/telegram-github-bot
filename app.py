import os
import requests
from flask import Flask, request
from pcloud_handler import PcloudHandler
from urllib.parse import urlparse

BOT_TOKEN = os.getenv("BOT_TOKEN")
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)
pcloud = PcloudHandler(PCLOUD_TOKEN)


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, data=data)


def get_filename_from_url(url):
    path = urlparse(url).path
    name = path.split("/")[-1]

    if name == "":
        name = "file.bin"

    return name


def get_file_size(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        size = r.headers.get("content-length")

        if size:
            return int(size)
    except:
        pass

    return None


def format_size(size):
    if size is None:
        return "Unknown"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024


def download_stream(url):
    r = requests.get(url, stream=True)
    return r.raw


@app.route("/", methods=["POST"])
def webhook():

    data = request.json

    if "message" not in data:
        return "ok"

    message = data["message"]

    if "text" not in message:
        return "ok"

    text = message["text"]
    chat_id = message["chat"]["id"]

    if not text.startswith("http"):
        send_message(chat_id, "❌ Send a direct download link.")
        return "ok"

    url = text.strip()

    filename = get_filename_from_url(url)
    filesize = get_file_size(url)

    free_space = pcloud.get_free_space()

    send_message(
        chat_id,
        f"📂 File: {filename}\n"
        f"📦 Size: {format_size(filesize)}\n"
        f"☁ Free pCloud: {format_size(free_space)}"
    )

    if filesize and filesize > free_space:
        send_message(chat_id, "❌ Not enough space in pCloud.")
        return "ok"

    try:

        send_message(chat_id, "⬇ Downloading...")

        file_stream = download_stream(url)

        send_message(chat_id, "⬆ Uploading to pCloud...")

        result = pcloud.upload_file(file_stream, filename)

        if result.get("result") == 0:
            send_message(chat_id, "✅ Upload completed.")
        else:
            send_message(chat_id, f"❌ Upload failed: {result}")

    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")

    return "ok"


@app.route("/", methods=["GET"])
def home():
    return "Bot Running"
