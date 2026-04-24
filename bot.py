"""
UBG Discord Bot - Main Entry Point
Untitled Boxing Game Economy & Betting Bot
"""

import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv
from database import Database

# =========================
# FIX RENDER (PORTA FAKE)
# =========================
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

Thread(target=run_server).start()

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("UBG-Bot")

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class UBGBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.db = Database()

    async def setup_hook(self):
        """Carrega todos os cogs (módulos) ao iniciar."""
        cogs = ["cogs.economia", "cogs.apostas", "cogs.ranking", "cogs.perfil"]

        for cog in cogs:
            await self.load_extension(cog)
            log.info(f"Cog carregado: {cog}")

        await self.tree.sync()
        log.info("Slash commands sincronizados com o Discord.")

    async def on_ready(self):
        log.info(f"Bot online como {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="🥊 Untitled Boxing Game"
            )
        )


def main():
    token = os.getenv("DISCORD_TOKEN")

    if not token:
        log.error("DISCORD_TOKEN não encontrado!")
        return

    bot = UBGBot()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()