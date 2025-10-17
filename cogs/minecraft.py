"""Commandes utilitaires pour l'univers Minecraft."""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from utils import config, embeds, logs as audit_logs


class Minecraft(commands.Cog):
    """Ajoute des commandes dédiées au serveur Minecraft de la classe."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ip", description="Affiche l'adresse du serveur Minecraft.")
    async def ip(self, interaction: discord.Interaction) -> None:
        embed = embeds.build_embed(
            "📡 Adresse du serveur",
            f"Rejoins-nous sur **{config.MINECRAFT_SERVER_IP}** !",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if interaction.guild:
            await audit_logs.log_to_channel(interaction.guild, f"📡 IP demandée par {interaction.user.mention}.")

    @app_commands.command(name="seed", description="Affiche la seed du monde Minecraft.")
    async def seed(self, interaction: discord.Interaction) -> None:
        embed = embeds.build_embed(
            "🌱 Seed du monde",
            f"La seed actuelle est **{config.MINECRAFT_SERVER_SEED}**.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if interaction.guild:
            await audit_logs.log_to_channel(interaction.guild, f"🌱 Seed consultée par {interaction.user.mention}.")

    @app_commands.command(name="event", description="Annonce un événement Minecraft dans un salon")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        salon="Salon dans lequel poster l'annonce",
        titre="Titre de l'événement",
        date="Date ou horaire (ex: Vendredi 20h)",
        description="Description rapide de l'événement",
    )
    async def event(
        self,
        interaction: discord.Interaction,
        salon: discord.TextChannel,
        titre: str,
        date: str,
        description: str,
    ) -> None:
        embed = embeds.build_embed(
            title=f"🗓️ {titre}",
            description=f"📅 **Quand ?** {date}\n\n{description}",
        )
        embed.set_footer(text=f"Annonce créée par {interaction.user.display_name}")
        try:
            await salon.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Permissions insuffisantes",
                    "Je ne peux pas envoyer de message dans ce salon.",
                ),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=embeds.success_embed("Événement publié", f"L'événement a été annoncé dans {salon.mention}."),
            ephemeral=True,
        )
        if interaction.guild:
            await audit_logs.log_to_channel(
                interaction.guild,
                f"📅 Événement '{titre}' annoncé dans {salon.mention} par {interaction.user.mention}.",
            )

    @app_commands.command(name="meme", description="Envoie un meme Minecraft aléatoire.")
    async def meme(self, interaction: discord.Interaction) -> None:
        meme_url = random.choice(config.MINECRAFT_MEMES)
        embed = embeds.build_embed(
            "😂 Meme Minecraft",
            "Profite de ce meme choisi totalement au hasard !",
        )
        embed.set_image(url=meme_url)
        await interaction.response.send_message(embed=embed)
        if interaction.guild:
            await audit_logs.log_to_channel(interaction.guild, f"😂 Meme envoyé pour {interaction.user.mention}.")


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog Minecraft au bot."""

    await bot.add_cog(Minecraft(bot))
