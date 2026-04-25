"""
UBG Bot - Cog de Apostas
Comandos: /criar_aposta, /apostar, /fechar_aposta, /apostas_abertas
"""

import discord
from discord import app_commands
from discord.ext import commands
import uuid
from utils import (
    embed_erro, embed_sucesso, embed_info,
    fmt_moeda, is_admin, COR_APOSTA, COR_GOLD, COR_SUCESSO, COR_ERRO
)


def gerar_id_aposta() -> str:
    """Gera um ID curto único para a aposta (6 caracteres hex)."""
    return uuid.uuid4().hex[:6].upper()


class Apostas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # ─────────────────────────────────────────────
    # /criar_aposta  (apenas admin)
    # ─────────────────────────────────────────────

    @app_commands.command(name="criar_aposta", description="[ADMIN] Cria uma nova aposta entre dois lutadores.")
    @app_commands.describe(
        lutador1="Nome do primeiro lutador",
        lutador2="Nome do segundo lutador"
    )
    @is_admin()
    async def criar_aposta(
        self,
        interaction: discord.Interaction,
        lutador1: str,
        lutador2: str
    ):
        # Valida nomes
        lutador1 = lutador1.strip()
        lutador2 = lutador2.strip()

        if not lutador1 or not lutador2:
            await interaction.response.send_message(
                embed=embed_erro("Nomes inválidos", "Os nomes dos lutadores não podem estar vazios."),
                ephemeral=True
            )
            return

        if lutador1.lower() == lutador2.lower():
            await interaction.response.send_message(
                embed=embed_erro("Lutadores iguais", "Os dois lutadores devem ser diferentes."),
                ephemeral=True
            )
            return

        aposta_id = gerar_id_aposta()
        self.db.criar_aposta(aposta_id, lutador1, lutador2, interaction.user.id)

        embed = discord.Embed(
            title="🥊 Nova Aposta Criada!",
            description=(
                f"Use `/apostar` com o **ID da aposta** abaixo para participar.\n\n"
                f"**Escolha seu lutador e quanto quer arriscar!**"
            ),
            color=COR_APOSTA
        )
        embed.add_field(name="ID da Aposta", value=f"`{aposta_id}`", inline=False)
        embed.add_field(name="🔴 Lutador 1", value=lutador1, inline=True)
        embed.add_field(name="🔵 Lutador 2", value=lutador2, inline=True)
        embed.add_field(name="Status", value="🟢 Aberta", inline=False)
        embed.set_footer(text=f"Criada por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /apostar
    # ─────────────────────────────────────────────

    @app_commands.command(name="apostar", description="Aposte em um lutador em uma aposta ativa.")
    @app_commands.describe(
        aposta_id="ID da aposta (use /apostas_abertas para ver os IDs)",
        lutador="Nome exato do lutador em quem você quer apostar",
        valor="Quantidade de coins que você quer apostar"
    )
    async def apostar(
        self,
        interaction: discord.Interaction,
        aposta_id: str,
        lutador: str,
        valor: int
    ):
        user_id   = interaction.user.id
        aposta_id = aposta_id.strip().upper()
        lutador   = lutador.strip()

        # Valida valor
        if valor <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Valor inválido", "O valor apostado deve ser maior que zero."),
                ephemeral=True
            )
            return

        # Busca a aposta
        aposta = self.db.get_aposta(aposta_id)
        if not aposta:
            await interaction.response.send_message(
                embed=embed_erro("Aposta não encontrada", f"Não existe aposta com ID `{aposta_id}`."),
                ephemeral=True
            )
            return

        if aposta["status"] != "aberta":
            await interaction.response.send_message(
                embed=embed_erro("Aposta encerrada", "Esta aposta já foi fechada."),
                ephemeral=True
            )
            return

        # Valida o lutador escolhido
        l1 = aposta["lutador1"]
        l2 = aposta["lutador2"]
        if lutador.lower() not in (l1.lower(), l2.lower()):
            await interaction.response.send_message(
                embed=embed_erro(
                    "Lutador inválido",
                    f"Os lutadores desta aposta são:\n🔴 `{l1}`\n🔵 `{l2}`\n\nEscreva o nome exato."
                ),
                ephemeral=True
            )
            return

        # Normaliza para o nome original
        lutador = l1 if lutador.lower() == l1.lower() else l2

        # Verifica saldo
        dados = self.db.get_or_create_usuario(user_id)
        if dados["saldo"] < valor:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Saldo insuficiente",
                    f"Você tem {fmt_moeda(dados['saldo'])} e tentou apostar {fmt_moeda(valor)}."
                ),
                ephemeral=True
            )
            return

        # Verifica se já apostou
        ja_apostou = self.db.get_palpite_usuario(aposta_id, user_id)
        if ja_apostou:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Já apostou",
                    f"Você já apostou **{fmt_moeda(ja_apostou['valor'])}** em **{ja_apostou['lutador']}** nesta aposta."
                ),
                ephemeral=True
            )
            return

        # Debita saldo e registra palpite
        self.db.atualizar_saldo(user_id, -valor)
        self.db.registrar_palpite(aposta_id, user_id, lutador, valor)
        self.db.incrementar_stat(user_id, "total_apostas")

        embed = embed_sucesso(
            "Aposta registrada!",
            f"Você apostou {fmt_moeda(valor)} em **{lutador}**!\n"
            f"Saldo restante: {fmt_moeda(dados['saldo'] - valor)}"
        )
        embed.add_field(name="ID da Aposta", value=f"`{aposta_id}`", inline=True)
        embed.add_field(name="Seu Lutador", value=lutador, inline=True)
        embed.set_footer(text="Boa sorte! 🥊")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /fechar_aposta  (apenas admin)
    # ─────────────────────────────────────────────

    @app_commands.command(name="fechar_aposta", description="[ADMIN] Fecha uma aposta e distribui os prêmios.")
    @app_commands.describe(
        aposta_id="ID da aposta a ser fechada",
        vencedor="Nome exato do lutador vencedor"
    )
    @is_admin()
    async def fechar_aposta(
        self,
        interaction: discord.Interaction,
        aposta_id: str,
        vencedor: str
    ):
        aposta_id = aposta_id.strip().upper()
        vencedor  = vencedor.strip()

        # Busca a aposta
        aposta = self.db.get_aposta(aposta_id)
        if not aposta:
            await interaction.response.send_message(
                embed=embed_erro("Aposta não encontrada", f"Não existe aposta com ID `{aposta_id}`."),
                ephemeral=True
            )
            return

        if aposta["status"] != "aberta":
            await interaction.response.send_message(
                embed=embed_erro("Aposta já fechada", "Esta aposta já foi encerrada."),
                ephemeral=True
            )
            return

        l1 = aposta["lutador1"]
        l2 = aposta["lutador2"]
        if vencedor.lower() not in (l1.lower(), l2.lower()):
            await interaction.response.send_message(
                embed=embed_erro(
                    "Lutador inválido",
                    f"Os lutadores desta aposta são:\n🔴 `{l1}`\n🔵 `{l2}`"
                ),
                ephemeral=True
            )
            return

        # Normaliza nome
        vencedor = l1 if vencedor.lower() == l1.lower() else l2
        perdedor = l2 if vencedor == l1 else l1

        # Fecha a aposta no banco
        self.db.fechar_aposta(aposta_id, vencedor)

        palpites = self.db.get_palpites_da_aposta(aposta_id)
        if not palpites:
            embed = embed_info("Aposta Encerrada", f"**{vencedor}** venceu, mas ninguém apostou.")
            embed.add_field(name="ID", value=f"`{aposta_id}`", inline=True)
            await interaction.response.send_message(embed=embed)
            return

        # Calcula totais por lado
        total_vencedor = sum(p["valor"] for p in palpites if p["lutador"] == vencedor)
        total_perdedor = sum(p["valor"] for p in palpites if p["lutador"] == perdedor)
        total_pool     = total_vencedor + total_perdedor

        vencedores_info = []
        perdedores_info = []

        for palpite in palpites:
            uid    = palpite["user_id"]
            valor  = palpite["valor"]
            lut    = palpite["lutador"]

            if lut == vencedor:
                # Prêmio proporcional: recupera o apostado + share do pool do perdedor
                if total_vencedor > 0:
                    proporcao = valor / total_vencedor
                    ganho     = valor + (total_perdedor * proporcao)
                else:
                    ganho = valor

                self.db.atualizar_saldo(uid, ganho)
                self.db.incrementar_stat(uid, "vitorias")
                vencedores_info.append((uid, valor, ganho))
            else:
                self.db.incrementar_stat(uid, "derrotas")
                perdedores_info.append((uid, valor))

        # Monta embed de resultado
        embed = discord.Embed(
            title="🏆 Aposta Encerrada!",
            color=COR_GOLD
        )
        embed.add_field(name="ID", value=f"`{aposta_id}`", inline=True)
        embed.add_field(name="Vencedor", value=f"🏆 **{vencedor}**", inline=True)
        embed.add_field(name="Pool Total", value=fmt_moeda(total_pool), inline=True)

        if vencedores_info:
            linhas = []
            for uid, apostado, recebido in vencedores_info:
                membro = interaction.guild.get_member(uid)
                nome   = membro.display_name if membro else f"ID:{uid}"
                lucro  = recebido - apostado
                linhas.append(f"✅ **{nome}** apostou {fmt_moeda(apostado)} → recebeu {fmt_moeda(recebido)} (+{fmt_moeda(lucro)})")
            embed.add_field(
                name=f"Ganhadores ({len(vencedores_info)})",
                value="\n".join(linhas)[:1024],
                inline=False
            )

        if perdedores_info:
            linhas = []
            for uid, apostado in perdedores_info:
                membro = interaction.guild.get_member(uid)
                nome   = membro.display_name if membro else f"ID:{uid}"
                linhas.append(f"❌ **{nome}** perdeu {fmt_moeda(apostado)}")
            embed.add_field(
                name=f"Perdedores ({len(perdedores_info)})",
                value="\n".join(linhas)[:1024],
                inline=False
            )

        embed.set_footer(text=f"Aposta encerrada por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /apostas_abertas
    # ─────────────────────────────────────────────

    @app_commands.command(name="apostas_abertas", description="Lista todas as apostas em andamento.")
    async def apostas_abertas(self, interaction: discord.Interaction):
        apostas = self.db.get_apostas_abertas()

        if not apostas:
            await interaction.response.send_message(
                embed=embed_info("Sem apostas abertas", "Não há nenhuma aposta ativa no momento."),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🥊 Apostas em Andamento",
            description=f"**{len(apostas)}** aposta(s) ativa(s). Use `/apostar` para participar!",
            color=COR_APOSTA
        )

        for aposta in apostas:
            aposta_id = aposta["aposta_id"]
            palpites  = self.db.get_palpites_da_aposta(aposta_id)
            total     = sum(p["valor"] for p in palpites)
            n_apostas = len(palpites)

            embed.add_field(
                name=f"ID: `{aposta_id}`",
                value=(
                    f"🔴 {aposta['lutador1']} **vs** 🔵 {aposta['lutador2']}\n"
                    f"Pool: {fmt_moeda(total)} | Participantes: **{n_apostas}**"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # Tratamento de erros de permissão
    # ─────────────────────────────────────────────

    @criar_aposta.error
    @fechar_aposta.error
    async def erro_permissao(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                embed=embed_erro("Sem permissão", "Apenas **administradores** podem usar este comando."),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Apostas(bot))
