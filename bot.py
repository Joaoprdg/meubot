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

load_dotenv()  # Carrega variáveis do arquivo .env automaticamente

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("UBG-Bot")

# Configuração de intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class UBGBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",  # prefix legacy (não usado com slash)
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

        # Sincroniza os slash commands com o Discord
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
        log.error("DISCORD_TOKEN não encontrado! Defina a variável de ambiente.")
        return

    bot = UBGBot()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
