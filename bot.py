# file: bot.py
import os
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, jsonify
import threading

# --- cấu hình logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Discord bot setup ---
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    logger.error("Missing DISCORD_BOT_TOKEN environment variable!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True  # nếu bạn muốn đọc nội dung, nếu cần
bot = commands.Bot(command_prefix="!", intents=intents)

class RemindCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="remind", description="Đặt nhắc sau [time] giây tới @user")
    @app_commands.describe(time="Số giây tới khi nhắc", user="Người bạn muốn nhắc")
    async def remind(self, interaction: discord.Interaction, time: int, user: discord.User):
        if time < 1:
            await interaction.response.send_message("❌ Thời gian phải lớn hơn 0 giây.", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Nhắc {user.mention} sau {time} giây.", ephemeral=True)
        logger.info(f"Scheduling reminder: user={user} in {time}s requested by {interaction.user}")

        await asyncio.sleep(time)

        try:
            await interaction.followup.send(
                f"{user.mention} ⏰ Đây là lời nhắc của bạn!",
                allowed_mentions=discord.AllowedMentions(users=True)
            )
            logger.info(f"Sent reminder to {user}")
        except Exception as e:
            logger.exception("Failed to send reminder message")

@bot.event
async def on_ready():
    logger.info(f"Bot đã sẵn sàng – đăng nhập như {bot.user} (ID {bot.user.id})")
    try:
        # Sync các lệnh slash (toàn cầu hoặc chỉ guild test)
        await bot.tree.sync()
        logger.info("Synced slash commands.")
    except Exception as e:
        logger.exception("Error syncing commands")

async def main_bot():
    await bot.start(TOKEN)

# --- Flask web server cho health check ---
app = Flask(__name__)

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200

def run_flask():
    # Lấy PORT từ biến môi trường (Render thường cung cấp)
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    logger.info(f"Starting Flask server at http://{host}:{port}/healthz")
    app.run(host=host, port=port)

# --- Kết hợp cả 2: chạy bot + flask song song ---
if __name__ == "__main__":
    # Đăng cog
    bot.add_cog(RemindCog(bot))

    # Chạy flask trong thread riêng
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Chạy bot chính
    try:
        asyncio.run(main_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
