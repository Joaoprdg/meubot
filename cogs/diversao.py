"""
UBG Bot - Cog de Diversão
Comandos: /coinflip, /slots, /roubar, /trabalhar, /depositar, /sacar, /banco
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta
from utils import embed_erro, embed_sucesso, embed_info, fmt_moeda, COR_GOLD, COR_APOSTA, COR_ERRO, COR_SUCESSO, COR_INFO

# Cooldowns em memória
_cooldowns: dict = {}

def check_cooldown(user_id: int, acao: str, segundos: int) -> int | None:
    """Retorna segundos restantes ou None se liberado."""
    key = f"{user_id}:{acao}"
    agora = datetime.utcnow()
    if key in _cooldowns:
        restante = (_cooldowns[key] + timedelta(seconds=segundos)) - agora
        if restante.total_seconds() > 0:
            return int(restante.total_seconds())
    _cooldowns[key] = agora
    return None


class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # ─────────────────────────────────────────────
    # /coinflip
    # ─────────────────────────────────────────────

    @app_commands.command(name="coinflip", description="Aposte coins em cara ou coroa!")
    @app_commands.describe(escolha="Sua escolha: cara ou coroa", valor="Quantidade de coins para apostar")
    @app_commands.choices(escolha=[
        app_commands.Choice(name="🪙 Cara", value="cara"),
        app_commands.Choice(name="🔵 Coroa", value="coroa"),
    ])
    async def coinflip(self, interaction: discord.Interaction, escolha: str, valor: int):
        user_id = interaction.user.id

        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "A aposta deve ser maior que zero."), ephemeral=True)
            return

        dados = self.db.get_or_create_usuario(user_id)
        if dados["saldo"] < valor:
            await interaction.response.send_message(
                embed=embed_erro("Saldo insuficiente",
                    f"Você tem {fmt_moeda(dados['saldo'])} e tentou apostar {fmt_moeda(valor)}."), ephemeral=True)
            return

        resultado = random.choice(["cara", "coroa"])
        ganhou    = escolha == resultado
        emoji_res = "🪙" if resultado == "cara" else "🔵"

        if ganhou:
            novo  = self.db.atualizar_saldo(user_id, valor)
            embed = discord.Embed(
                title="🎉 Você ganhou!",
                description=f"A moeda caiu em **{emoji_res} {resultado.capitalize()}**!\nGanho: {fmt_moeda(valor)}\nSaldo: {fmt_moeda(novo)}",
                color=COR_SUCESSO)
        else:
            novo  = self.db.atualizar_saldo(user_id, -valor)
            embed = discord.Embed(
                title="😢 Você perdeu!",
                description=f"A moeda caiu em **{emoji_res} {resultado.capitalize()}**!\nPerdeu: {fmt_moeda(valor)}\nSaldo: {fmt_moeda(novo)}",
                color=COR_ERRO)

        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /slots
    # ─────────────────────────────────────────────

    SIMBOLOS = ["🥊", "⚡", "🔥", "💀", "👑", "💎"]
    MULTIPLICADORES = {"💎": 10, "👑": 5, "🥊": 3, "🔥": 2, "⚡": 1.5, "💀": 0}

    @app_commands.command(name="slots", description="Tente a sorte na máquina caça-níquel!")
    @app_commands.describe(valor="Quantidade de coins para apostar")
    async def slots(self, interaction: discord.Interaction, valor: int):
        user_id = interaction.user.id

        cd = check_cooldown(user_id, "slots", 10)
        if cd:
            await interaction.response.send_message(
                embed=embed_erro("Calma aí!", f"Aguarde **{cd}s** para jogar novamente."), ephemeral=True)
            return

        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "A aposta deve ser maior que zero."), ephemeral=True)
            return

        dados = self.db.get_or_create_usuario(user_id)
        if dados["saldo"] < valor:
            await interaction.response.send_message(
                embed=embed_erro("Saldo insuficiente",
                    f"Você tem {fmt_moeda(dados['saldo'])} e tentou apostar {fmt_moeda(valor)}."), ephemeral=True)
            return

        embed_spin = discord.Embed(title="🎰 Caça-Níquel UBG", description="🔄 | 🔄 | 🔄\n\n*Girando...*", color=COR_APOSTA)
        await interaction.response.send_message(embed=embed_spin)
        await asyncio.sleep(1.5)

        s1, s2, s3 = random.choices(self.SIMBOLOS, k=3)
        linha = f"{s1} | {s2} | {s3}"

        if s1 == s2 == s3:
            mult  = self.MULTIPLICADORES.get(s1, 2)
            ganho = int(valor * mult)
            novo  = self.db.atualizar_saldo(user_id, ganho)
            titulo = "🎉 JACKPOT!" if mult >= 5 else "🎉 Você ganhou!"
            desc  = f"{linha}\n\nTrês {s1} seguidos! Multiplicador: **{mult}x**\nGanho: {fmt_moeda(ganho)}\nSaldo: {fmt_moeda(novo)}"
            cor   = COR_GOLD
        elif s1 == s2 or s2 == s3 or s1 == s3:
            ganho = int(valor * 0.5)
            novo  = self.db.atualizar_saldo(user_id, ganho)
            titulo = "😊 Quase lá!"
            desc  = f"{linha}\n\nDois iguais! Você recuperou metade.\nGanho: {fmt_moeda(ganho)}\nSaldo: {fmt_moeda(novo)}"
            cor   = COR_APOSTA
        else:
            novo  = self.db.atualizar_saldo(user_id, -valor)
            titulo = "😢 Sem sorte!"
            desc  = f"{linha}\n\nNenhum símbolo igual. Você perdeu {fmt_moeda(valor)}.\nSaldo: {fmt_moeda(novo)}"
            cor   = COR_ERRO

        embed_res = discord.Embed(title=titulo, description=desc, color=cor)
        embed_res.set_footer(text="Use /slots novamente em 10 segundos.")
        await interaction.edit_original_response(embed=embed_res)

    # ─────────────────────────────────────────────
    # /roubar — cooldown aumentado para 1h
    # ─────────────────────────────────────────────

    @app_commands.command(name="roubar", description="Tente roubar coins de outro jogador! (cooldown: 1h)")
    @app_commands.describe(alvo="Jogador que você quer tentar roubar")
    async def roubar(self, interaction: discord.Interaction, alvo: discord.Member):
        user_id = interaction.user.id
        alvo_id = alvo.id

        if alvo_id == user_id:
            await interaction.response.send_message(
                embed=embed_erro("Inválido", "Você não pode roubar a si mesmo."), ephemeral=True)
            return

        if alvo.bot:
            await interaction.response.send_message(
                embed=embed_erro("Inválido", "Você não pode roubar um bot."), ephemeral=True)
            return

        cd = check_cooldown(user_id, "roubar", 3600)  # 1 hora
        if cd:
            horas   = cd // 3600
            minutos = (cd % 3600) // 60
            await interaction.response.send_message(
                embed=embed_erro("Cooldown", f"Aguarde **{horas}h {minutos}m** para tentar roubar novamente."),
                ephemeral=True)
            return

        dados_ladrão = self.db.get_or_create_usuario(user_id)
        dados_alvo   = self.db.get_or_create_usuario(alvo_id)

        # Só rouba da carteira, banco é protegido
        if dados_alvo["saldo"] < 100:
            await interaction.response.send_message(
                embed=embed_erro("Alvo pobre",
                    f"{alvo.display_name} não tem coins suficientes na carteira para roubar.\n"
                    f"💡 Coins no banco são protegidas!"),
                ephemeral=True)
            return

        sucesso = random.random() < 0.40  # 40% de chance

        if sucesso:
            pct   = random.uniform(0.10, 0.30)
            valor = int(dados_alvo["saldo"] * pct)
            valor = max(50, valor)

            self.db.atualizar_saldo(alvo_id, -valor)
            novo  = self.db.atualizar_saldo(user_id, valor)

            frases = [
                f"Você se aproveitou da distração de {alvo.display_name} e levou",
                f"Missão cumprida! Você roubou",
                f"Silêncio total... você escapou com",
            ]
            embed = discord.Embed(
                title="🦹 Roubo bem-sucedido!",
                description=(
                    f"{random.choice(frases)} {fmt_moeda(valor)} de {alvo.mention}!\n"
                    f"*(Coins no banco são protegidas 🏦)*\n"
                    f"Seu saldo: {fmt_moeda(novo)}"
                ),
                color=COR_SUCESSO)
        else:
            multa = int(dados_ladrão["saldo"] * 0.10)
            multa = max(50, min(multa, int(dados_ladrão["saldo"])))

            novo  = self.db.atualizar_saldo(user_id, -multa)
            self.db.atualizar_saldo(alvo_id, multa)

            frases = [
                f"{alvo.display_name} te pegou em flagrante!",
                f"A guarda te viu! Você foi multado.",
                f"Plano furado! {alvo.display_name} reagiu.",
            ]
            embed = discord.Embed(
                title="🚨 Roubo fracassado!",
                description=(
                    f"{random.choice(frases)}\n"
                    f"Você pagou {fmt_moeda(multa)} de multa para {alvo.mention}.\n"
                    f"Seu saldo: {fmt_moeda(novo)}"
                ),
                color=COR_ERRO)

        embed.set_footer(text="Cooldown: 1 hora")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /trabalhar
    # ─────────────────────────────────────────────

    EMPREGOS = [
        ("🥊 Sparring Partner",          100, 250),
        ("🎙️ Comentarista",               150, 300),
        ("🧹 Limpador do Ginásio",        80,  200),
        ("📸 Fotógrafo de Lutas",         120, 280),
        ("🩺 Médico do Ringue",           200, 400),
        ("🎽 Vendedor de Gear",           100, 350),
        ("🏋️ Personal Trainer",           150, 350),
        ("📦 Carregador de Equipamentos", 80,  220),
    ]

    @app_commands.command(name="trabalhar", description="Trabalhe para ganhar coins! (cooldown: 1h)")
    async def trabalhar(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        cd = check_cooldown(user_id, "trabalhar", 3600)
        if cd:
            horas   = cd // 3600
            minutos = (cd % 3600) // 60
            await interaction.response.send_message(
                embed=embed_erro("Você está cansado!", f"Descanse um pouco. Disponível em **{horas}h {minutos}m**."),
                ephemeral=True)
            return

        emprego, minimo, maximo = random.choice(self.EMPREGOS)
        ganho = random.randint(minimo, maximo)
        novo  = self.db.atualizar_saldo(interaction.user.id, ganho)

        embed = discord.Embed(
            title=f"{emprego}",
            description=f"Você trabalhou duro e ganhou {fmt_moeda(ganho)}!\nSaldo atual: {fmt_moeda(novo)}",
            color=COR_GOLD)
        embed.set_footer(text="Você pode trabalhar novamente em 1 hora.")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /banco — ver saldo do banco
    # ─────────────────────────────────────────────

    @app_commands.command(name="banco", description="Veja seu saldo no banco (protegido de roubos).")
    async def banco(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        dados   = self.db.get_or_create_usuario(user_id)
        banco   = self.db.get_saldo_banco(user_id)

        embed = discord.Embed(title="🏦 Seu Banco UBG", color=COR_INFO)
        embed.add_field(name="💰 Carteira", value=fmt_moeda(dados["saldo"]), inline=True)
        embed.add_field(name="🏦 Banco",    value=fmt_moeda(banco),          inline=True)
        embed.add_field(name="💎 Total",    value=fmt_moeda(dados["saldo"] + banco), inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="Coins no banco são protegidas de roubos.")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /depositar — deposita na carteira → banco
    # ─────────────────────────────────────────────

    @app_commands.command(name="depositar", description="Deposite coins no banco para protegê-las de roubos.")
    @app_commands.describe(valor="Quantidade de coins a depositar (ou 'tudo')")
    async def depositar(self, interaction: discord.Interaction, valor: int):
        user_id = interaction.user.id
        dados   = self.db.get_or_create_usuario(user_id)

        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "O valor deve ser maior que zero."), ephemeral=True)
            return

        if dados["saldo"] < valor:
            await interaction.response.send_message(
                embed=embed_erro("Saldo insuficiente",
                    f"Você tem {fmt_moeda(dados['saldo'])} na carteira."), ephemeral=True)
            return

        carteira, banco = self.db.depositar_banco(user_id, valor)

        embed = embed_sucesso(
            "Depósito realizado!",
            f"Você depositou {fmt_moeda(valor)} no banco.\n\n"
            f"💰 Carteira: {fmt_moeda(carteira)}\n"
            f"🏦 Banco: {fmt_moeda(banco)}"
        )
        embed.set_footer(text="Coins no banco são protegidas de roubos.")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /sacar — retira do banco → carteira
    # ─────────────────────────────────────────────

    @app_commands.command(name="sacar", description="Saque coins do banco para sua carteira.")
    @app_commands.describe(valor="Quantidade de coins a sacar")
    async def sacar(self, interaction: discord.Interaction, valor: int):
        user_id = interaction.user.id
        banco   = self.db.get_saldo_banco(user_id)

        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "O valor deve ser maior que zero."), ephemeral=True)
            return

        if banco < valor:
            await interaction.response.send_message(
                embed=embed_erro("Saldo insuficiente",
                    f"Você tem {fmt_moeda(banco)} no banco."), ephemeral=True)
            return

        carteira, novo_banco = self.db.sacar_banco(user_id, valor)

        embed = embed_sucesso(
            "Saque realizado!",
            f"Você sacou {fmt_moeda(valor)} do banco.\n\n"
            f"💰 Carteira: {fmt_moeda(carteira)}\n"
            f"🏦 Banco: {fmt_moeda(novo_banco)}"
        )
        embed.set_footer(text="Cuidado! Coins na carteira podem ser roubadas.")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Diversao(bot))
