
import json
import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# PENGATURAN
# =========================

TOKEN = os.getenv("BOT_TOKEN")

FILTER_FILE = "filters.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# =========================
# DATABASE KATA FILTER
# =========================

def load_filters():
    if not os.path.exists(FILTER_FILE):
        return []

    try:
        with open(FILTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_filters(words):
    with open(FILTER_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)


FILTER_WORDS = load_filters()


# =========================
# CEK ADMIN
# =========================

async def is_admin(update: Update):
    if not update.effective_chat or not update.effective_user:
        return False

    try:
        member = await update.effective_chat.get_member(
            update.effective_user.id
        )

        return member.status in ["administrator", "creator"]

    except Exception as e:
        logging.error(e)
        return False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aktif!\n\n"
        "Perintah admin:\n"
        "/tambah kata - menambah kata filter\n"
        "/hapus kata - menghapus kata filter\n"
        "/daftar - melihat daftar kata filter\n\n"
        "Contoh:\n"
        "/tambah kata1\n"
        "/tambah kata2"
    )


# =========================
# TAMBAH KATA
# =========================

async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        await update.message.reply_text(
            "❌ Hanya admin grup yang boleh menambah kata filter."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Gunakan:\n/tambah kata\n\nContoh:\n/tambah kata terlarang"
        )
        return

    word = " ".join(context.args).strip().lower()

    if word in FILTER_WORDS:
        await update.message.reply_text(
            f"⚠️ Kata '{word}' sudah ada di daftar filter."
        )
        return

    FILTER_WORDS.append(word)
    save_filters(FILTER_WORDS)

    await update.message.reply_text(
        f"✅ Kata '{word}' berhasil ditambahkan ke filter."
    )


# =========================
# HAPUS KATA
# =========================

async def hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        await update.message.reply_text(
            "❌ Hanya admin grup yang boleh menghapus kata filter."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Gunakan:\n/hapus kata\n\nContoh:\n/hapus kata terlarang"
        )
        return

    word = " ".join(context.args).strip().lower()

    if word not in FILTER_WORDS:
        await update.message.reply_text(
            f"⚠️ Kata '{word}' tidak ditemukan."
        )
        return

    FILTER_WORDS.remove(word)
    save_filters(FILTER_WORDS)

    await update.message.reply_text(
        f"✅ Kata '{word}' berhasil dihapus dari filter."
    )


# =========================
# DAFTAR FILTER
# =========================

async def daftar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not FILTER_WORDS:
        await update.message.reply_text(
            "📋 Daftar filter masih kosong."
        )
        return

    daftar_kata = "\n".join(
        f"{i + 1}. {word}"
        for i, word in enumerate(FILTER_WORDS)
    )

    await update.message.reply_text(
        "📋 DAFTAR KATA FILTER:\n\n" + daftar_kata
    )


# =========================
# FILTER PESAN
# =========================

async def filter_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()

    # Jangan proses perintah bot
    if text.startswith("/"):
        return

    for word in FILTER_WORDS:

        if word.lower() in text:

            try:
                await update.message.delete()

                logging.info(
                    f"Pesan dihapus karena mengandung: {word}"
                )

            except Exception as e:
                logging.error(
                    f"Gagal menghapus pesan: {e}"
                )

            break


# =========================
# MAIN
# =========================

def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN belum diatur di Environment Variables Render."
        )

    app = Application.builder().token(TOKEN).build()

    # Command
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tambah", tambah))
    app.add_handler(CommandHandler("hapus", hapus))
    app.add_handler(CommandHandler("daftar", daftar))

    # Filter semua pesan teks
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            filter_message
        )
    )

    print("🤖 Bot aktif...")

    app.run_polling()


if __name__ == "__main__":
    main()
