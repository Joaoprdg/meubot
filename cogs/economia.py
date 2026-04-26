"""
UBG Bot - Cog de Economia
Comandos: /saldo, /daily, /transferir, /addcoins
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timedelta
from utils import embed_erro, embed_sucesso, embed_info, fmt_moeda, COR_GOLD, COR_INFO

# ID do dono do bot
DONO_ID = 1054448809515687936


class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # ─────────────────────────────────────────────
    # /saldo
    # ─────────────────────────────────────────────

    @app_commands.command(name="saldo", description="Veja seu saldo atual ou o de outro usuário.")
    @app_commands.describe(usuario="Usuário que você quer consultar (opcional)")
    async def saldo(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        dados = self.db.get_or_create_usuario(alvo.id)

        embed = discord.Embed(
            title=f"💳 Carteira de {alvo.display_name}",
            color=COR_GOLD
        )
        embed.add_field(name="Saldo", value=fmt_moeda(dados["saldo"]), inline=False)
        embed.set_thumbnail(url=alvo.display_avatar.url)
        embed.set_footer(text="Untitled Boxing Game Economy")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /daily
    # ─────────────────────────────────────────────

    @app_commands.command(name="daily", description="Colete sua recompensa diária (1x por dia).")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        dados = self.db.get_or_create_usuario(user_id)

        agora = datetime.utcnow()

        if dados["daily_last"]:
            ultimo = datetime.fromisoformat(dados["daily_last"])
            proximo = ultimo + timedelta(hours=24)
            if agora < proximo:
                restante = proximo - agora
                horas   = int(restante.total_seconds() // 3600)
                minutos = int((restante.total_seconds() % 3600) // 60)
                embed = embed_erro(
                    "Daily ainda não disponível",
                    f"Você já coletou hoje!\n⏳ Disponível em **{horas}h {minutos}m**."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        recompensa = random.randint(600, 1200)
        novo_saldo = self.db.atualizar_saldo(user_id, recompensa)
        self.db.set_daily(user_id, agora.isoformat())

        embed = embed_sucesso(
            "Daily coletado!",
            f"Você recebeu {fmt_moeda(recompensa)} como recompensa diária!\n"
            f"Saldo atual: {fmt_moeda(novo_saldo)}"
        )
        embed.set_footer(text="Volte amanhã para coletar novamente.")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /transferir
    # ─────────────────────────────────────────────

    @app_commands.command(name="transferir", description="Envie coins para outro jogador.")
    @app_commands.describe(
        destinatario="Usuário que vai receber as coins",
        valor="Quantidade de coins a transferir"
    )
    async def transferir(
        self,
        interaction: discord.Interaction,
        destinatario: discord.Member,
        valor: int
    ):
        remetente_id    = interaction.user.id
        destinatario_id = destinatario.id

        if destinatario_id == remetente_id:
            await interaction.response.send_message(
                embed=embed_erro("Transferência inválida", "Você não pode transferir para si mesmo."),
                ephemeral=True
            )
            return

        if destinatario.bot:
            await interaction.response.send_message(
                embed=embed_erro("Transferência inválida", "Você não pode transferir para bots."),
                ephemeral=True
            )
            return

        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "O valor deve ser maior que zero."),
                ephemeral=True
            )
            return

        dados_rem = self.db.get_or_create_usuario(remetente_id)

        if dados_rem["saldo"] < valor:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Saldo insuficiente",
                    f"Você tem {fmt_moeda(dados_rem['saldo'])} e tentou transferir {fmt_moeda(valor)}."
                ),
                ephemeral=True
            )
            return

        self.db.get_or_create_usuario(destinatario_id)
        novo_saldo_rem  = self.db.atualizar_saldo(remetente_id, -valor)
        novo_saldo_dest = self.db.atualizar_saldo(destinatario_id, valor)

        embed = discord.Embed(
            title="💸 Transferência realizada",
            color=COR_INFO
        )
        embed.add_field(
            name="De",
            value=f"{interaction.user.mention}\nNovo saldo: {fmt_moeda(novo_saldo_rem)}",
            inline=True
        )
        embed.add_field(
            name="Para",
            value=f"{destinatario.mention}\nNovo saldo: {fmt_moeda(novo_saldo_dest)}",
            inline=True
        )
        embed.add_field(name="Valor enviado", value=fmt_moeda(valor), inline=False)
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /addcoins (apenas dono)
    # ─────────────────────────────────────────────

    @app_commands.command(name="addcoins", description="Adiciona coins para um usuário.")
    @app_commands.describe(
        usuario="Usuário que vai receber as coins",
        valor="Quantidade de coins a adicionar"
    )
    async def addcoins(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        valor: int
    ):
        if interaction.user.id != DONO_ID:
            await interaction.response.send_message(
                embed=embed_erro("Sem permissão", "Você não pode usar este comando."),
                ephemeral=True
            )
            return

        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "O valor deve ser maior que zero."),
                ephemeral=True
            )
            return

        self.db.get_or_create_usuario(usuario.id)
        novo_saldo = self.db.atualizar_saldo(usuario.id, valor)

        embed = embed_sucesso(
            "Coins adicionadas!",
            f"{fmt_moeda(valor)} adicionadas para {usuario.mention}.\n"
            f"Saldo atual: {fmt_moeda(novo_saldo)}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Economia(bot))
