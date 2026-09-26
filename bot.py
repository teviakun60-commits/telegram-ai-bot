import os
import json
import threading
import time
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

MODEL_NAME = "gemini-3.8-flash"


# =========================
# PENGATURAN HEMAT KUOTA
# =========================

# Minimal jeda antar request Gemini
GEMINI_COOLDOWN = 3

# Maksimal panjang pesan yang dikirim ke Gemini
MAX_MESSAGE_LENGTH = 500

# Saat terkena 429, jangan terus mencoba
quota_block_until = 0

# Waktu blokir sementara setelah 429
QUOTA_BLOCK_SECONDS = 60

last_gemini_request = 0


# =========================
# FILTER
# =========================

FILTER_FILE = "filters.json"


def load_filters():
    try:
        with open(FILTER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_filters():
    with open(FILTER_FILE, "w", encoding="utf-8") as f:
        json.dump(
            FILTER_WORDS,
            f,
            ensure_ascii=False,
            indent=2
        )


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

        return member.status in [
            "administrator",
            "creator"
        ]

    except Exception:
        return False


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🤖 Halo! Saya bot AI grup.\n\n"
        "Saya bisa menjawab pesan member dan menghapus "
        "pesan yang mengandung kata filter.\n\n"
        "Perintah admin:\n"
        "/tambah kata\n"
        "/hapus kata\n"
        "/daftar"
    )


# =========================
# TAMBAH FILTER
# =========================

async def tambah(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    word = " ".join(
        context.args
    ).lower().strip()

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

async def hapus(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    word = " ".join(
        context.args
    ).lower().strip()

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

async def daftar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not FILTER_WORDS:

        await update.message.reply_text(
            "📋 Belum ada kata filter."
        )

        return

    teks = "📋 DAFTAR FILTER:\n\n"

    for nomor, word in enumerate(
        FILTER_WORDS,
        1
    ):

        teks += f"{nomor}. {word}\n"

    await update.message.reply_text(teks)


# =========================
# CEK APAKAH PERLU AI
# =========================

def should_use_ai(text):

    text = text.strip()

    if not text:
        return False

    # Pesan terlalu panjang tidak perlu diproses
    if len(text) > MAX_MESSAGE_LENGTH:
        return False

    # Pesan yang sangat pendek dan bukan pertanyaan
    # tidak perlu memakai Gemini
    simple_messages = [
        "ok",
        "oke",
        "iya",
        "ya",
        "nggak",
        "ga",
        "gak",
        "wkwk",
        "haha",
        "hehe",
        "lol",
        "👍",
        "😂",
        "🤣",
        "😆",
        "🙏",
        "❤️",
    ]

    if text.lower() in simple_messages:
        return False

    return True


# =========================
# GEMINI
# =========================

async def ask_gemini(text):

    global last_gemini_request
    global quota_block_until

    now = time.time()

    # Kalau kuota sedang diblokir
    if now < quota_block_until:

        print(
            "⏳ Gemini sedang dibatasi karena quota 429."
        )

        return None

    # Batasi frekuensi request
    wait_time = (
        GEMINI_COOLDOWN
        - (now - last_gemini_request)
    )

    if wait_time > 0:

        await __import__("asyncio").sleep(
            wait_time
        )

    prompt = f"""
Kamu adalah teman ngobrol di grup Telegram.

Jawab langsung seperti teman biasa.
Jangan mengatakan bahwa kamu adalah AI, bot,
atau assistant.

Gunakan bahasa Indonesia yang santai,
natural dan singkat.

Jawaban maksimal 2-3 kalimat.
Gunakan emoji secukupnya.

Pesan member:
{text}
"""

    try:

        last_gemini_request = time.time()

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        answer = response.text

        if answer:

            return answer.strip()

        return None

    except Exception as e:

        error_text = str(e)

        print(
            f"Gemini error: {error_text}",
            flush=True
        )

        # =========================
        # JIKA QUOTA 429
        # =========================

        if "429" in error_text or \
           "RESOURCE_EXHAUSTED" in error_text:

            quota_block_until = (
                time.time()
                + QUOTA_BLOCK_SECONDS
            )

            print(
                "⛔ Gemini terkena quota. "
                "Request Gemini dihentikan sementara.",
                flush=True
            )

        return None


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
    # CEK FILTER
    # =====================

    lower_text = text.lower()

    for word in FILTER_WORDS:

        if word.lower() in lower_text:

            try:

                await update.message.delete()

                print(
                    f"🗑️ Pesan dihapus karena filter: {word}",
                    flush=True
                )

            except Exception as e:

                print(
                    f"Gagal menghapus pesan: {e}",
                    flush=True
                )

            return

    # =====================
    # CEK PERLU AI
    # =====================

    if not should_use_ai(text):

        print(
            "ℹ️ Pesan tidak dikirim ke Gemini:",
            text,
            flush=True
        )

        return

    # =====================
    # GEMINI
    # =====================

    answer = await ask_gemini(text)

    if answer:

        try:

            await update.message.reply_text(
                answer
            )

        except Exception as e:

            print(
                f"Gagal mengirim jawaban Telegram: {e}",
                flush=True
            )

    else:

        print(
            "⚠️ Gemini tidak memberikan jawaban.",
            flush=True
        )


# =========================
# SERVER HTTP UNTUK RENDER
# =========================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"Telegram AI Bot is running!"
        )

    def log_message(
        self,
        format,
        *args
    ):

        return


def start_server():

    server = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    print(
        f"🌐 HTTP server berjalan di port {PORT}",
        flush=True
    )

    server.serve_forever()


# =========================
# MAIN
# =========================

def main():

    # =========================
    # HTTP SERVER
    # =========================

    threading.Thread(
        target=start_server,
        daemon=True
    ).start()

    # =========================
    # TELEGRAM
    # =========================

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =========================
    # COMMAND
    # =========================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "tambah",
            tambah
        )
    )

    app.add_handler(
        CommandHandler(
            "hapus",
            hapus
        )
    )

    app.add_handler(
        CommandHandler(
            "daftar",
            daftar
        )
    )

    # =========================
    # PESAN MEMBER
    # =========================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "🤖 Bot AI aktif...",
        flush=True
    )

    app.run_polling()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
