import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai


# =========================
# ENVIRONMENT VARIABLES
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN belum diatur di Render.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY belum diatur di Render.")


# =========================
# GEMINI AI
# =========================

client = genai.Client(api_key=GEMINI_API_KEY)


# =========================
# FILTER
# =========================

FILTER_FILE = "filters.json"


def load_filters():
    try:
        with open(FILTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_filters():
    with open(FILTER_FILE, "w", encoding="utf-8") as f:
        json.dump(FILTER_WORDS, f, ensure_ascii=False, indent=2)


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

    except:
        return False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Halo! Saya bot AI grup.\n\n"
        "Saya bisa menjawab pesan member dan menghapus pesan "
        "yang mengandung kata filter.\n\n"
        "Perintah admin:\n"
        "/tambah kata\n"
        "/hapus kata\n"
        "/daftar"
    )


# =========================
# TAMBAH FILTER
# =========================

async def tambah(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        await update.message.reply_text(
            "❌ Perintah ini hanya untuk admin."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Contoh:\n/tambah kata terlarang"
        )
        return

    word = " ".join(context.args).lower().strip()

    if word in FILTER_WORDS:
        await update.message.reply_text(
            "⚠️ Kata tersebut sudah ada."
        )
        return

    FILTER_WORDS.append(word)
    save_filters()

    await update.message.reply_text(
        f"✅ Filter ditambahkan:\n{word}"
    )


# =========================
# HAPUS FILTER
# =========================

async def hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update):
        await update.message.reply_text(
            "❌ Perintah ini hanya untuk admin."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Contoh:\n/hapus kata terlarang"
        )
        return

    word = " ".join(context.args).lower().strip()

    if word not in FILTER_WORDS:
        await update.message.reply_text(
            "⚠️ Kata tersebut tidak ada."
        )
        return

    FILTER_WORDS.remove(word)
    save_filters()

    await update.message.reply_text(
        f"✅ Filter dihapus:\n{word}"
    )


# =========================
# DAFTAR FILTER
# =========================

async def daftar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not FILTER_WORDS:
        await update.message.reply_text(
            "📋 Belum ada kata filter."
        )
        return

    teks = "📋 DAFTAR FILTER:\n\n"

    for nomor, word in enumerate(FILTER_WORDS, 1):
        teks += f"{nomor}. {word}\n"

    await update.message.reply_text(teks)


# =========================
# PROSES PESAN MEMBER
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    text = update.message.text.strip()

    # Jangan proses command
    if text.startswith("/"):
        return

    # =====================
    # CEK KATA FILTER
    # =====================

    lower_text = text.lower()

    for word in FILTER_WORDS:

        if word.lower() in lower_text:

            try:
                await update.message.delete()

                print(
                    f"🗑️ Pesan dihapus karena filter: {word}"
                )

            except Exception as e:

                print(
                    f"Gagal menghapus pesan: {e}"
                )

            return


    # =====================
    # JAWAB DENGAN AI
    # =====================

    try:

        prompt = f"""
Kamu adalah teman ngobrol di grup Telegram.

Jawab langsung seperti teman biasa.
Jangan mengatakan bahwa kamu adalah AI, bot, atau assistant.
Jangan mengawali jawaban dengan "Saya AI" atau "Sebagai AI".
Gunakan bahasa Indonesia yang santai, natural, dan singkat.
Sesuaikan jawaban dengan pertanyaan member.
Boleh menggunakan emoji secukupnya.

Contoh:
Pertanyaan: Aku ganteng ga ya?
Jawaban: Ya, kamu ganteng 😎

Pertanyaan: Aku jelek gak?
Jawaban: Nggak lah, kamu keren 😎

Pertanyaan: Hai
Jawaban: Hai juga 👋

Pesan member:
{text}
"""

        response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)

        answer = response.text

        if answer:
            await update.message.reply_text(answer)

    except Exception as e:
        print(f"Gemini error: {e}", flush=True)
        await update.message.reply_text("⚠️ Maaf, AI sedang tidak dapat menjawab.")
        


# =========================
# SERVER HTTP UNTUK RENDER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        self.wfile.write(
            b"Telegram AI Bot is running!"
        )

    def log_message(self, format, *args):
        return


def start_server():

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(f"🌐 HTTP server berjalan di port {PORT}")

    server.serve_forever()


# =========================
# MAIN
# =========================

def main():

    # Jalankan HTTP server
    threading.Thread(
        target=start_server,
        daemon=True
    ).start()

    # Telegram
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("tambah", tambah)
    )

    app.add_handler(
        CommandHandler("hapus", hapus)
    )

    app.add_handler(
        CommandHandler("daftar", daftar)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("🤖 Bot AI aktif...")

    app.run_polling()


if __name__ == "__main__":
    main()
