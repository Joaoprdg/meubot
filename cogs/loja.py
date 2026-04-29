"""
UBG Bot - Cog de Loja
Comandos: /loja, /comprar, /adicionar_item, /remover_item
"""

import discord
from discord import app_commands
from discord.ext import commands
from utils import embed_erro, embed_sucesso, embed_info, fmt_moeda, COR_GOLD, COR_INFO, COR_SUCESSO

DONO_ID = 1054448809515687936


class Loja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # ─────────────────────────────────────────────
    # /loja
    # ─────────────────────────────────────────────

    @app_commands.command(name="loja", description="Veja os cargos disponíveis para compra.")
    async def loja(self, interaction: discord.Interaction):
        itens = self.db.get_itens_loja()

        if not itens:
            await interaction.response.send_message(
                embed=embed_info("🛒 Loja vazia", "Nenhum item disponível no momento."),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛒 Loja de Cargos — UBG",
            description="Use `/comprar <id_do_item>` para comprar um cargo.",
            color=COR_GOLD
        )

        for item in itens:
            embed.add_field(
                name=f"🏷️ {item['nome']}  •  ID: `{item['cargo_id']}`",
                value=f"💰 Preço: **{item['preco']:,.0f} coins**\n📝 {item['descricao'] or 'Sem descrição'}",
                inline=False
            )

        embed.set_footer(text="Os cargos são entregues automaticamente após a compra.")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /comprar
    # ─────────────────────────────────────────────

    @app_commands.command(name="comprar", description="Compre um cargo da loja.")
    @app_commands.describe(id_item="ID do item que você quer comprar (veja em /loja)")
    async def comprar(self, interaction: discord.Interaction, id_item: str):
        user_id = interaction.user.id
        id_item = id_item.strip()

        item = self.db.get_item_loja(id_item)
        if not item:
            await interaction.response.send_message(
                embed=embed_erro("Item não encontrado", f"Não existe item com ID `{id_item}` na loja."),
                ephemeral=True
            )
            return

        # Verifica se já tem o cargo
        if self.db.usuario_tem_item(user_id, id_item):
            await interaction.response.send_message(
                embed=embed_erro("Já comprado", f"Você já possui o cargo **{item['nome']}**."),
                ephemeral=True
            )
            return

        # Verifica saldo
        dados = self.db.get_or_create_usuario(user_id)
        if dados["saldo"] < item["preco"]:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Saldo insuficiente",
                    f"Este cargo custa {fmt_moeda(item['preco'])} e você tem {fmt_moeda(dados['saldo'])}."
                ),
                ephemeral=True
            )
            return

        # Busca o cargo no servidor
        cargo_discord = None
        for role in interaction.guild.roles:
            if str(role.id) == id_item or role.name.lower() == item["nome"].lower():
                cargo_discord = role
                break

        if not cargo_discord:
            await interaction.response.send_message(
                embed=embed_erro(
                    "Cargo não encontrado",
                    "O cargo existe na loja mas não foi encontrado no servidor. Avise um admin."
                ),
                ephemeral=True
            )
            return

        # Debita saldo, registra compra e dá o cargo
        self.db.atualizar_saldo(user_id, -item["preco"])
        self.db.registrar_compra(user_id, id_item)

        try:
            await interaction.user.add_roles(cargo_discord, reason="Compra na loja UBG")
        except discord.Forbidden:
            # Reembolsa se não conseguir dar o cargo
            self.db.atualizar_saldo(user_id, item["preco"])
            self.db.remover_compra(user_id, id_item)
            await interaction.response.send_message(
                embed=embed_erro(
                    "Erro ao dar cargo",
                    "O bot não tem permissão para dar este cargo. Avise um admin."
                ),
                ephemeral=True
            )
            return

        novo_saldo = self.db.get_usuario(user_id)["saldo"]
        embed = embed_sucesso(
            "Compra realizada!",
            f"Você comprou o cargo **{item['nome']}** por {fmt_moeda(item['preco'])}!\n"
            f"Saldo restante: {fmt_moeda(novo_saldo)}"
        )
        embed.set_footer(text="O cargo foi adicionado ao seu perfil.")
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /adicionar_item (apenas dono)
    # ─────────────────────────────────────────────

    @app_commands.command(name="adicionar_item", description="[DONO] Adiciona um cargo à loja.")
    @app_commands.describe(
        cargo="O cargo do servidor que será vendido",
        preco="Preço em coins",
        descricao="Descrição do item (opcional)"
    )
    async def adicionar_item(
        self,
        interaction: discord.Interaction,
        cargo: discord.Role,
        preco: int,
        descricao: str = ""
    ):
        if interaction.user.id != DONO_ID:
            await interaction.response.send_message(
                embed=embed_erro("Sem permissão", "Apenas o dono pode usar este comando."),
                ephemeral=True
            )
            return

        if preco <= 0:
            await interaction.response.send_message(
                embed=embed_erro("Preço inválido", "O preço deve ser maior que zero."),
                ephemeral=True
            )
            return

        # Usa o ID do cargo como ID do item
        cargo_id = str(cargo.id)

        if self.db.get_item_loja(cargo_id):
            await interaction.response.send_message(
                embed=embed_erro("Já existe", f"O cargo **{cargo.name}** já está na loja."),
                ephemeral=True
            )
            return

        self.db.adicionar_item_loja(cargo_id, cargo.name, preco, descricao)

        embed = embed_sucesso(
            "Item adicionado!",
            f"O cargo **{cargo.name}** foi adicionado à loja por {fmt_moeda(preco)}.\n"
            f"ID do item: `{cargo_id}`"
        )
        await interaction.response.send_message(embed=embed)

    # ─────────────────────────────────────────────
    # /remover_item (apenas dono)
    # ─────────────────────────────────────────────

    @app_commands.command(name="remover_item", description="[DONO] Remove um item da loja.")
    @app_commands.describe(id_item="ID do item a remover (veja em /loja)")
    async def remover_item(self, interaction: discord.Interaction, id_item: str):
        if interaction.user.id != DONO_ID:
            await interaction.response.send_message(
                embed=embed_erro("Sem permissão", "Apenas o dono pode usar este comando."),
                ephemeral=True
            )
            return

        id_item = id_item.strip()
        item = self.db.get_item_loja(id_item)

        if not item:
            await interaction.response.send_message(
                embed=embed_erro("Item não encontrado", f"Não existe item com ID `{id_item}` na loja."),
                ephemeral=True
            )
            return

        self.db.remover_item_loja(id_item)

        embed = embed_sucesso(
            "Item removido!",
            f"O cargo **{item['nome']}** foi removido da loja."
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Loja(bot))
