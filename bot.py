# file: bot.py
import os
import asyncio
import logging
import threading

import discord
from discord.ext import commands
from flask import Flask, jsonify

# --- cấu hình logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Discord bot setup ---
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    logger.error("Missing DISCORD_BOT_TOKEN environment variable!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True  # vì chúng ta sẽ xử lý lệnh dựa trên nội dung tin nhắn
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Định nghĩa lệnh prefix ---
@bot.command(name="remind", help="Đặt nhắc sau [time] giây tới @user")
async def remind(ctx: commands.Context, time: int, user: discord.User):
    if time < 1:
        await ctx.send("❌ Thời gian phải lớn hơn 0 giây.")
        return

    await ctx.send(f"✅ Nhắc {user.mention} sau {time} giây.")
    logger.info(f"Scheduling reminder: user={user} in {time}s requested by {ctx.author}")

    await asyncio.sleep(time)

    try:
        await ctx.send(f"{user.mention} ⏰ Đây là lời nhắc của bạn!")
        logger.info(f"Sent reminder to {user}")
    except Exception as e:
        logger.exception("Failed to send reminder message")

# --- Sự kiện on_ready ---
@bot.event
async def on_ready():
    logger.info(f"Bot đã sẵn sàng – đăng nhập như {bot.user} (ID {bot.user.id})")

# --- Hàm chính để khởi chạy bot ---
async def main_bot():
    await bot.start(TOKEN)

# --- Flask web server cho health check ---
app = Flask(__name__)

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    logger.info(f"Starting Flask server at http://{host}:{port}/healthz")
    app.run(host=host, port=port)

# --- Kết hợp cả 2: chạy bot + flask song song ---
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        asyncio.run(main_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
