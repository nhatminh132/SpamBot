# file: bot.py
import os
import asyncio
import logging
import threading

import discord
from discord import app_commands
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
intents.message_content = True  # nếu bạn muốn đọc nội dung tin nhắn
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Cog chứa lệnh slash ---
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

# --- Sự kiện on_ready để sync lệnh slash nhanh ---
@bot.event
async def on_ready():
    logger.info(f"Bot đã sẵn sàng – đăng nhập như {bot.user} (ID {bot.user.id})")
    try:
        TEST_GUILD_ID = 123456789012345678  # ← **Thay bằng ID server của bạn**
        guild = discord.Object(id=TEST_GUILD_ID)
        # Copy global commands to this guild (giúp test nhanh)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        logger.info(f"Synced slash commands to guild {TEST_GUILD_ID}.")
    except Exception as e:
        logger.exception("Error syncing commands")

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
    bot.add_cog(RemindCog(bot))

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        asyncio.run(main_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
