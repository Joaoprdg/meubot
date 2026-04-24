"""
UBG Bot - Cog de Perfil
Comando: /perfil
"""

import discord
from discord import app_commands
from discord.ext import commands
from .utils import fmt_moeda, COR_INFO


class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name="perfil", description="Veja seu perfil completo ou o de outro jogador.")
    @app_commands.describe(usuario="Jogador que você quer ver (opcional)")
    async def perfil(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo  = usuario or interaction.user
        dados = self.db.get_or_create_usuario(alvo.id)

        v = dados["vitorias"]
        d = dados["derrotas"]
        t = dados["total_apostas"]

        taxa_vitoria = f"{v/(v+d)*100:.1f}%" if (v + d) > 0 else "—"

        # Determina rank de título baseado em vitórias
        titulo = _titulo(v)

        embed = discord.Embed(
            title=f"👤 Perfil de {alvo.display_name}",
            description=f"*{titulo}*",
            color=COR_INFO
        )
        embed.set_thumbnail(url=alvo.display_avatar.url)

        embed.add_field(name="💰 Saldo",         value=fmt_moeda(dados["saldo"]),  inline=True)
        embed.add_field(name="🥊 Apostas Feitas", value=str(t),                     inline=True)
        embed.add_field(name="\u200b",            value="\u200b",                    inline=True)  # espaçador

        embed.add_field(name="🏆 Vitórias",    value=str(v),       inline=True)
        embed.add_field(name="💀 Derrotas",    value=str(d),       inline=True)
        embed.add_field(name="📊 Taxa W/L",    value=taxa_vitoria, inline=True)

        embed.set_footer(text="Untitled Boxing Game • UBG Economy Bot")
        await interaction.response.send_message(embed=embed)


def _titulo(vitorias: int) -> str:
    """Retorna um título/rank baseado no número de vitórias."""
    if vitorias == 0:  return "🥋 Novato do Ringue"
    if vitorias < 5:   return "🤜 Lutador Iniciante"
    if vitorias < 15:  return "⚡ Lutador Amador"
    if vitorias < 30:  return "🔥 Lutador Experiente"
    if vitorias < 50:  return "💥 Contendor Perigoso"
    if vitorias < 100: return "🏅 Profissional"
    return "👑 Lenda do Ringue"


async def setup(bot):
    await bot.add_cog(Perfil(bot))
