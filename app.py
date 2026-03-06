import requests
from flask import Flask, request

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
PCLOUD_TOKEN = "YOUR_PCLOUD_API_TOKEN"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
PCLOUD_UPLOAD = "https://api.pcloud.com/uploadfile"

app = Flask(__name__)


def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )


def get_file_path(file_id):
    r = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}")
    return r.json()["result"]["file_path"]


def stream_upload_to_pcloud(file_url, filename):

    telegram_stream = requests.get(file_url, stream=True)

    files = {
        "file": (filename, telegram_stream.raw)
    }

    data = {
        "auth": PCLOUD_TOKEN,
        "folderid": 0
    }

    r = requests.post(PCLOUD_UPLOAD, files=files, data=data)
    return r.json()


@app.route("/webhook", methods=["POST"])
def webhook():

    update = request.json

    if "message" not in update:
        return "ok"

    message = update["message"]
    chat_id = message["chat"]["id"]

    file_id = None
    filename = None

    if "video" in message:
        file_id = message["video"]["file_id"]
        filename = f"{file_id}.mp4"

    elif "document" in message:
        file_id = message["document"]["file_id"]
        filename = message["document"]["file_name"]

    else:
        send_message(chat_id, "Send a video or document.")
        return "ok"

    send_message(chat_id, f"⬆ Uploading\n{filename}")

    file_path = get_file_path(file_id)

    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    result = stream_upload_to_pcloud(file_url, filename)

    if result.get("result") == 0:
        send_message(chat_id, "✅ Uploaded to pCloud root")
    else:
        send_message(chat_id, f"❌ Upload failed\n{result}")

    return "ok"


@app.route("/")
def home():
    return "Bot Running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
