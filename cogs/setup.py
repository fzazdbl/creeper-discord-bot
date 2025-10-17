"""Commande de configuration automatique du serveur via /setup."""
from __future__ import annotations

import asyncio
from typing import Iterable

import discord
from discord import app_commands
from discord.ext import commands

from utils import config, embeds, checks


class Setup(commands.Cog):
    """Cog responsable de l'initialisation complète du serveur."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _ensure_category(self, guild: discord.Guild, name: str) -> tuple[discord.CategoryChannel, bool]:
        """Récupère ou crée une catégorie et signale si elle vient d'être créée."""

        category = discord.utils.get(guild.categories, name=name)
        if category is None:
            category = await guild.create_category(name=name, reason="Initialisation Creeper /setup")
            return category, True
        return category, False

    async def _ensure_channel(
        self,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        channel_conf: dict[str, str],
    ) -> tuple[discord.abc.GuildChannel, bool]:
        """Crée un salon texte ou vocal selon la configuration fournie."""

        channel_type = channel_conf["type"]
        channel_name = channel_conf["name"]
        if channel_type == "text":
            existing = discord.utils.get(category.text_channels, name=channel_name)
            if existing:
                return existing, False
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                reason="Initialisation Creeper /setup",
                topic="Salon créé automatiquement par Creeper",
            )
            return channel, True
        if channel_type == "voice":
            existing_voice = discord.utils.get(category.voice_channels, name=channel_name)
            if existing_voice:
                return existing_voice, False
            channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                reason="Initialisation Creeper /setup",
            )
            return channel, True
        raise ValueError(f"Type de canal inconnu: {channel_type}")

    async def _log(self, guild: discord.Guild, message: str) -> None:
        """Envoie un message dans le salon des journaux s'il existe."""

        log_channel = discord.utils.get(guild.text_channels, name=config.LOG_CHANNEL_NAME)
        if log_channel is not None:
            await log_channel.send(message)

    async def _provision_roles(self, guild: discord.Guild) -> list[str]:
        """Délègue la création des rôles au cog dédié s'il est chargé."""

        roles_cog = self.bot.get_cog("Roles")
        if roles_cog is None:
            return ["⚠️ Cog des rôles introuvable."]
        return await roles_cog.synchronize_roles(guild)  # type: ignore[no-any-return]

    @app_commands.command(name="setup", description="Configure l'ensemble du serveur Creeper.")
    @app_commands.default_permissions(manage_guild=True)
    @checks.has_manage_guild()
    async def setup(self, interaction: discord.Interaction) -> None:
        """Commande slash déclenchant la création de toutes les ressources serveur."""

        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Contexte invalide", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild

        created_categories: list[str] = []
        created_channels: list[str] = []

        for category_conf in config.CATEGORIES:
            category, created = await self._ensure_category(guild, category_conf["name"])  # type: ignore[index]
            if created:
                created_categories.append(f"📁 {category.name}")
            channels: Iterable[dict[str, str]] = category_conf["channels"]  # type: ignore[index]
            for channel_conf in channels:
                channel, was_created = await self._ensure_channel(guild, category, channel_conf)
                if was_created:
                    icon = "#️⃣" if channel_conf["type"] == "text" else "🔊"
                    created_channels.append(f"{icon} {channel.name}")
                    await self._initialize_channel(channel)

        role_report = await self._provision_roles(guild)

        embed_description = [config.SETUP_SUMMARY_HEADER, ""]
        if created_categories:
            embed_description.append("**Catégories créées :**")
            embed_description.extend(f"• {category}" for category in created_categories)
            embed_description.append("")
        if created_channels:
            embed_description.append("**Salons créés :**")
            embed_description.extend(f"• {channel}" for channel in created_channels)
            embed_description.append("")
        if role_report:
            embed_description.append("**Rôles :**")
            embed_description.extend(f"• {item}" for item in role_report)

        summary_embed = embeds.success_embed(
            "Configuration terminée",
            "\n".join(embed_description) if embed_description else "Aucune modification nécessaire.",
        )

        await interaction.followup.send(embed=summary_embed, ephemeral=True)
        await self._log(guild, f"✅ Configuration /setup exécutée par {interaction.user.mention}.")

    async def setup_hook(self) -> None:
        """Méthode appelée automatiquement par discord.py lors du chargement du cog."""

        await asyncio.sleep(0)

    async def _initialize_channel(self, channel: discord.abc.GuildChannel) -> None:
        """Ajoute des messages d'accueil par défaut dans certains salons clés."""

        if isinstance(channel, discord.TextChannel):
            if channel.name == config.WELCOME_CHANNEL_NAME:
                await channel.send(
                    embed=embeds.build_embed(
                        title="👋 Bienvenue !",
                        description=(
                            "Ce salon accueillera automatiquement chaque nouveau membre. "
                            "Les messages sont gérés par Creeper pour que tout le monde se sente "
                            "comme chez lui dès son arrivée !"
                        ),
                    )
                )
            elif channel.name == config.LOG_CHANNEL_NAME:
                await channel.send(
                    embed=embeds.build_embed(
                        title="📚 Journaux du bot",
                        description="Toutes les actions importantes de Creeper apparaîtront ici.",
                    )
                )


async def setup(bot: commands.Bot) -> None:
    """Point d'entrée standard pour charger le cog."""

    await bot.add_cog(Setup(bot))
