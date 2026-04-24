"""
UBG Bot - Utilitários compartilhados
Funções e constantes reutilizáveis entre os cogs.
"""

import discord
from discord import app_commands
from typing import Optional


# ─────────────────────────────────────────────
# Cores padrão dos embeds
# ─────────────────────────────────────────────
COR_SUCESSO  = 0x2ECC71   # verde
COR_ERRO     = 0xE74C3C   # vermelho
COR_INFO     = 0x3498DB   # azul
COR_AVISO    = 0xF39C12   # laranja
COR_GOLD     = 0xF1C40F   # dourado
COR_APOSTA   = 0x9B59B6   # roxo


# ─────────────────────────────────────────────
# Builders de Embed
# ─────────────────────────────────────────────

def embed_erro(titulo: str, descricao: str) -> discord.Embed:
    return discord.Embed(title=f"❌ {titulo}", description=descricao, color=COR_ERRO)

def embed_sucesso(titulo: str, descricao: str) -> discord.Embed:
    return discord.Embed(title=f"✅ {titulo}", description=descricao, color=COR_SUCESSO)

def embed_info(titulo: str, descricao: str = "") -> discord.Embed:
    return discord.Embed(title=titulo, description=descricao, color=COR_INFO)


# ─────────────────────────────────────────────
# Formatação de moeda
# ─────────────────────────────────────────────

def fmt_moeda(valor: float) -> str:
    """Formata um valor numérico como moeda do bot."""
    return f"💰 **{valor:,.0f}** coins"


# ─────────────────────────────────────────────
# Verificação de permissão de admin
# ─────────────────────────────────────────────

def is_admin():
    """Check de permissão para comandos de administrador."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.CheckFailure("Apenas administradores podem usar este comando.")
    return app_commands.check(predicate)
