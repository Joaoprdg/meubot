"""
UBG Bot - Cog de Ranking
Comandos: /ranking, /registrar_vitoria
"""

import discord
from discord import app_commands
from discord.ext import commands
from .utils import embed_erro, embed_info, fmt_moeda, is_admin, COR_GOLD


# Emojis para as primeiras posições
MEDALHAS = {1: "🥇", 2: "🥈", 3: "🥉"}


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # ─────────────────────────────────────────────
    # /ranking
    # ─────────────────────────────────────────────

    @app_commands.command(name="ranking", description="Veja o ranking dos melhores jogadores do servidor.")
    @app_commands.describe(top="Quantos jogadores exibir (padrão: 10, máx: 25)")
    async def ranking(self, interaction: discord.Interaction, top: int = 10):
        # Clamp entre 1 e 25
        top = max(1, min(top, 25))

        jogadores = self.db.get_ranking(top)

        if not jogadores:
            await interaction.response.send_message(
                embed=embed_info("Ranking vazio", "Nenhum jogador registrado ainda."),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🏆 Ranking UBG — Top Lutadores",
            description="Classificados por vitórias (desempate por saldo)",
            color=COR_GOLD
        )

        linhas = []
        for pos, dados in enumerate(jogadores, start=1):
            user_id = dados["user_id"]
            membro  = interaction.guild.get_member(user_id)
            nome    = membro.display_name if membro else f"Jogador #{user_id}"
            medalha = MEDALHAS.get(pos, f"**#{pos}**")

            v  = dados["vitorias"]
            d  = dados["derrotas"]
            vd = f"{v}V / {d}D"
            taxa = f"{v/(v+d)*100:.0f}%" if (v + d) > 0 else "—"

            linhas.append(
                f"{medalha} **{nome}**\n"
                f"┗ {vd} | Taxa: {taxa} | Saldo: {fmt_moeda(dados['saldo'])}"
            )

        embed.description = "\n\n".join(linhas)
        embed.set_footer(text=f"Exibindo top {len(jogadores)} jogadores")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /registrar_vitoria  (apenas admin)
    # ─────────────────────────────────────────────

    @app_commands.command(
        name="registrar_vitoria",
        description="[ADMIN] Registra uma vitória/derrota manualmente para um jogador."
    )
    @app_commands.describe(
        vencedor="Jogador que ganhou",
        perdedor="Jogador que perdeu"
    )
    @is_admin()
    async def registrar_vitoria(
        self,
        interaction: discord.Interaction,
        vencedor: discord.Member,
        perdedor: discord.Member
    ):
        if vencedor.id == perdedor.id:
            await interaction.response.send_message(
                embed=embed_erro("Jogadores iguais", "O vencedor e o perdedor não podem ser o mesmo."),
                ephemeral=True
            )
            return

        if vencedor.bot or perdedor.bot:
            await interaction.response.send_message(
                embed=embed_erro("Jogador inválido", "Bots não podem participar do ranking."),
                ephemeral=True
            )
            return

        self.db.get_or_create_usuario(vencedor.id)
        self.db.get_or_create_usuario(perdedor.id)

        self.db.incrementar_stat(vencedor.id, "vitorias")
        self.db.incrementar_stat(perdedor.id, "derrotas")

        embed = discord.Embed(
            title="📋 Resultado Registrado",
            color=COR_GOLD
        )
        embed.add_field(name="🏆 Vencedor", value=vencedor.mention, inline=True)
        embed.add_field(name="💀 Perdedor", value=perdedor.mention, inline=True)
        embed.set_footer(text=f"Registrado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @registrar_vitoria.error
    async def erro_permissao(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=embed_erro("Sem permissão", "Apenas **administradores** podem usar este comando."),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Ranking(bot))
