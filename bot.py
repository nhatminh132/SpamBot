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
intents.message_content = True  # cần để bot đọc nội dung tin nhắn
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Định nghĩa lệnh prefix với số lần lặp ---
@bot.command(name="remind", help="Đặt nhắc sau [time] giây tới @user, lặp [count] lần")
async def remind(ctx: commands.Context, time: int, user: discord.User, count: int = 1):
    if time < 1:
        await ctx.send("❌ Thời gian phải lớn hơn 0 giây.")
        return
    if count < 1:
        await ctx.send("❌ Số lần phải lớn hơn hoặc bằng 1.")
        return

    await ctx.send(f"✅ Nhắc {user.mention} mỗi {time} giây, tổng {count} lần.")
    logger.info(f"Scheduling {count} reminders for {user} every {time}s requested by {ctx.author}")

    for i in range(count):
        await asyncio.sleep(time)
        try:
            await ctx.send(f"{user.mention} ⏰ (#{i+1}/{count}) Đây là lời nhắc của bạn!")
            logger.info(f"Sent reminder #{i+1} to {user}")
        except Exception as e:
            logger.exception("Failed to send reminder message")
            break

# --- Sự kiện on_ready ---
@bot.event
async def on_ready():
    logger.info(f"Bot đã sẵn sàng – đăng nhập như {bot.user} (ID {bot.user.id})")
    # bạn có thể thêm thông báo khác tại đây

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
