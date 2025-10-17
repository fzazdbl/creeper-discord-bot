"""Commande d'aide contextuelle /help."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import embeds


class Help(commands.Cog):
    """Fournit une vue d'ensemble des commandes disponibles."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Affiche la liste des commandes de Creeper.")
    async def help(self, interaction: discord.Interaction) -> None:
        """Envoie un embed contenant toutes les commandes et leur description."""

        description = (
            "Voici les commandes disponibles :\n\n"
            "• **/setup** – Configure automatiquement les salons, rôles et journaux.\n"
            "• **/play <recherche ou URL>** – Ajoute une musique YouTube à la file d'attente.\n"
            "• **/skip** – Passe à la musique suivante.\n"
            "• **/pause** – Met la lecture en pause.\n"
            "• **/resume** – Reprend la lecture en cours.\n"
            "• **/stop** – Arrête la musique et vide la file d'attente.\n"
        )

        help_embed = embeds.build_embed(title="📚 Centre d'aide Creeper", description=description)
        await interaction.response.send_message(embed=help_embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog d'aide au bot."""

    await bot.add_cog(Help(bot))
