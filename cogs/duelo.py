"""
UBG Bot - Cog de Duelo
Comando: /duelo
Desafie outro jogador para uma batalha 1v1 apostando coins!
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from utils import embed_erro, embed_sucesso, fmt_moeda, COR_APOSTA, COR_GOLD, COR_ERRO

# Duelos pendentes: {desafiado_id: {dados do duelo}}
duelos_pendentes: dict = {}


class Duelo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # ─────────────────────────────────────────────
    # /duelo
    # ─────────────────────────────────────────────

    @app_commands.command(name="duelo", description="Desafie outro jogador para um duelo 1v1!")
    @app_commands.describe(
        oponente="Jogador que você quer desafiar",
        aposta="Quantidade de coins para apostar"
    )
    async def duelo(
        self,
        interaction: discord.Interaction,
        oponente: discord.Member,
        aposta: int
    ):
        desafiante = interaction.user

        # Validações básicas
        if oponente.id == desafiante.id:
            await interaction.response.send_message(
                embed=embed_erro("Duelo inválido", "Você não pode se desafiar."),
                ephemeral=True
            )
            return

        if oponente.bot:
            await interaction.response.send_message(
                embed=embed_erro("Duelo inválido", "Você não pode desafiar um bot."),
                ephemeral=True
            )
            return

        if aposta <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Aposta inválida", "A aposta deve ser maior que zero."),
                ephemeral=True
            )
            return

        # Verifica saldo do desafiante
        dados_des = self.db.get_or_create_usuario(desafiante.id)
        if dados_des["saldo"] < aposta:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Saldo insuficiente",
                    f"Você tem {fmt_moeda(dados_des['saldo'])} e tentou apostar {fmt_moeda(aposta)}."
                ),
                ephemeral=True
            )
            return

        # Verifica saldo do oponente
        dados_op = self.db.get_or_create_usuario(oponente.id)
        if dados_op["saldo"] < aposta:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Oponente sem saldo",
                    f"{oponente.display_name} não tem coins suficientes para este duelo."
                ),
                ephemeral=True
            )
            return

        # Verifica se já tem duelo pendente
        if oponente.id in duelos_pendentes:
            await interaction.response.send_message(
                embed=embed_erro("Duelo pendente", f"{oponente.display_name} já tem um duelo aguardando resposta."),
                ephemeral=True
            )
            return

        # Registra duelo pendente
        duelos_pendentes[oponente.id] = {
            "desafiante_id": desafiante.id,
            "aposta": aposta
        }

        # Monta embed de desafio com botões
        embed = discord.Embed(
            title="🥊 Desafio de Duelo!",
            description=(
                f"{oponente.mention}, você foi desafiado por {desafiante.mention}!\n\n"
                f"💰 Aposta: **{aposta:,.0f} coins**\n\n"
                f"Você tem **60 segundos** para aceitar ou recusar."
            ),
            color=COR_APOSTA
        )

        view = DueloView(
            bot=self.bot,
            desafiante=desafiante,
            oponente=oponente,
            aposta=aposta,
            db=self.db
        )

        await interaction.response.send_message(
            content=oponente.mention,
            embed=embed,
            view=view
        )

        # Timeout de 60s
        await asyncio.sleep(60)
        if oponente.id in duelos_pendentes:
            duelos_pendentes.pop(oponente.id, None)
            embed_timeout = embed_erro(
                "Duelo expirado",
                f"{oponente.display_name} não respondeu a tempo. O duelo foi cancelado."
            )
            await interaction.edit_original_response(embed=embed_timeout, view=None)


class DueloView(discord.ui.View):
    def __init__(self, bot, desafiante, oponente, aposta, db):
        super().__init__(timeout=60)
        self.bot        = bot
        self.desafiante = desafiante
        self.oponente   = oponente
        self.aposta     = aposta
        self.db         = db

    @discord.ui.button(label="✅ Aceitar", style=discord.ButtonStyle.success)
    async def aceitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.oponente.id:
            await interaction.response.send_message(
                "Apenas o desafiado pode responder.", ephemeral=True
            )
            return

        duelos_pendentes.pop(self.oponente.id, None)
        self.stop()

        # Verifica saldos novamente
        dados_des = self.db.get_usuario(self.desafiante.id)
        dados_op  = self.db.get_usuario(self.oponente.id)

        if dados_des["saldo"] < self.aposta or dados_op["saldo"] < self.aposta:
            await interaction.response.edit_message(
                embed=embed_erro("Duelo cancelado", "Um dos jogadores não tem saldo suficiente."),
                view=None
            )
            return

        # Sorteia vencedor (50/50)
        vencedor = random.choice([self.desafiante, self.oponente])
        perdedor = self.oponente if vencedor == self.desafiante else self.desafiante

        # Transfere coins
        self.db.atualizar_saldo(perdedor.id, -self.aposta)
        self.db.atualizar_saldo(vencedor.id, self.aposta)

        novo_saldo_v = self.db.get_usuario(vencedor.id)["saldo"]
        novo_saldo_p = self.db.get_usuario(perdedor.id)["saldo"]

        # Animação de luta
        fases = [
            "🥊 Os lutadores entram no ringue...",
            "⚡ A luta começa! Golpes sendo trocados...",
            "💥 Um golpe decisivo foi desferido!",
        ]

        embed_luta = discord.Embed(title="🥊 Duelo em andamento...", color=COR_APOSTA)
        embed_luta.description = fases[0]
        await interaction.response.edit_message(embed=embed_luta, view=None)

        for fase in fases[1:]:
            await asyncio.sleep(1.5)
            embed_luta.description = fase
            await interaction.edit_original_response(embed=embed_luta)

        await asyncio.sleep(1.5)

        # Resultado final
        embed_result = discord.Embed(
            title="🏆 Duelo Encerrado!",
            color=COR_GOLD
        )
        embed_result.add_field(
            name="🥇 Vencedor",
            value=f"{vencedor.mention}\n+{fmt_moeda(self.aposta)}\nSaldo: {fmt_moeda(novo_saldo_v)}",
            inline=True
        )
        embed_result.add_field(
            name="💀 Perdedor",
            value=f"{perdedor.mention}\n-{fmt_moeda(self.aposta)}\nSaldo: {fmt_moeda(novo_saldo_p)}",
            inline=True
        )
        embed_result.set_footer(text="Use /duelo para desafiar alguém!")
        await interaction.edit_original_response(embed=embed_result)

    @discord.ui.button(label="❌ Recusar", style=discord.ButtonStyle.danger)
    async def recusar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.oponente.id:
            await interaction.response.send_message(
                "Apenas o desafiado pode responder.", ephemeral=True
            )
            return

        duelos_pendentes.pop(self.oponente.id, None)
        self.stop()

        embed = embed_erro(
            "Duelo recusado",
            f"{self.oponente.display_name} recusou o desafio de {self.desafiante.mention}. 🐔"
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(Duelo(bot))
