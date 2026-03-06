import os
import re
import requests
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")

app = Flask(__name__)

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


def get_pcloud_space():

    url = "https://api.pcloud.com/userinfo"
    params = {"auth": PCLOUD_TOKEN}

    r = requests.get(url, params=params).json()

    quota = r["quota"]
    used = r["usedquota"]

    free = quota - used

    return free


def format_size(size):

    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024


def list_files():

    url = "https://api.pcloud.com/listfolder"
    params = {
        "auth": PCLOUD_TOKEN,
        "folderid": 0
    }

    r = requests.get(url, params=params).json()

    files = []

    if "metadata" in r:
        for f in r["metadata"]["contents"]:
            if not f["isfolder"]:
                files.append((f["name"], f["fileid"]))

    return files


def delete_file(fileid):

    url = "https://api.pcloud.com/deletefile"

    params = {
        "auth": PCLOUD_TOKEN,
        "fileid": fileid
    }

    requests.get(url, params=params)


# -----------------------------
# DOWNLOAD + UPLOAD
# -----------------------------

async def download_upload(url, update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    filename = get_filename(url)

    r = requests.head(url)
    size = int(r.headers.get("content-length", 0))

    free_space = get_pcloud_space()

    msg = await context.bot.send_message(
        chat_id,
        f"📄 File: {filename}\n"
        f"📦 Size: {format_size(size)}\n"
        f"💾 Free Disk: {format_size(free_space)}"
    )

    if free_space < size:

        files = list_files()

        if not files:
            await msg.reply_text("❌ Disk Full and no files to delete")
            return

        keyboard = []

        for name, fid in files[:10]:
            keyboard.append([InlineKeyboardButton(f"Delete {name}", callback_data=f"del|{fid}")])

        await msg.reply_text(
            "⚠ Disk Full. Delete files:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # START DOWNLOAD

    r = requests.get(url, stream=True)

    local = f"/tmp/{filename}"

    downloaded = 0
    next_update = 10

    with open(local, "wb") as f:

        for chunk in r.iter_content(1024 * 1024):

            if chunk:
                f.write(chunk)
                downloaded += len(chunk)

                percent = int(downloaded * 100 / size)

                if percent >= next_update:

                    await msg.edit_text(
                        f"⬇ Downloading...\n{percent}%"
                    )

                    next_update += 10

    await msg.edit_text("☁ Uploading to pCloud...")

    upload_url = "https://api.pcloud.com/uploadfile"

    files = {
        "file": open(local, "rb")
    }

    data = {
        "auth": PCLOUD_TOKEN,
        "folderid": 0
    }

    requests.post(upload_url, files=files, data=data)

    await msg.edit_text("✅ Upload Complete")

    os.remove(local)


# -----------------------------
# TELEGRAM HANDLERS
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a download link.")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        return

    url = update.message.text

    await download_upload(url, update, context)


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data.split("|")

    if data[0] == "del":

        delete_file(data[1])

        await query.edit_message_text("🗑 File Deleted")


# -----------------------------
# BOT START
# -----------------------------

application = ApplicationBuilder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
application.add_handler(CallbackQueryHandler(delete_callback))


@app.route("/")
def home():
    return "Bot Running"


def run_bot():
    application.run_polling()


import threading
threading.Thread(target=run_bot).start()
