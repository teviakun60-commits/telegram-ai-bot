import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

# Ambil token dari environment variable TELEGRAM_BOT_TOKEN
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN belum diset. "
        "Contoh: export TELEGRAM_BOT_TOKEN='TOKEN_BOT_KAMU'"
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def jawab_pesan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    pesan = update.message.text.strip()

    # Balasan sederhana untuk setiap pesan teks yang diterima bot
    await update.message.reply_text(
        f"🤖 Bot menerima: {pesan}"
    )

def main():
    app = Application.builder().token(TOKEN).build()

    # Menangkap semua pesan teks yang bisa diterima bot
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, jawab_pesan))

    print("🤖 Bot aktif...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
