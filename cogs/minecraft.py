"""Commandes utilitaires pour l'univers Minecraft."""
from __future__ import annotations

import asyncio
import random
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
from mcstatus import JavaServer

from utils import config, embeds, logs as audit_logs


class Minecraft(commands.Cog):
    """Ajoute des commandes dédiées au serveur Minecraft de la classe."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._status_lock = asyncio.Lock()
        self._cached_status: tuple[float, Any] | None = None

    async def _query_status(self) -> Any:
        """Récupère les informations du serveur Minecraft avec un cache court."""

        async with self._status_lock:
            now = asyncio.get_running_loop().time()
            if self._cached_status and now - self._cached_status[0] < 30:
                return self._cached_status[1]

            server_address = f"{config.MINECRAFT_SERVER_IP}:{config.MINECRAFT_SERVER_PORT}"
            server = JavaServer.lookup(server_address)
            loop = asyncio.get_running_loop()
            status = await loop.run_in_executor(None, server.status)
            self._cached_status = (now, status)
            return status

    @staticmethod
    def _extract_description(description: Any) -> str:
        """Normalise la description MOTD renvoyée par mcstatus."""

        if description is None:
            return ""
        if isinstance(description, str):
            return description

        clean_attr = getattr(description, "clean", None)
        if isinstance(clean_attr, str):
            return clean_attr

        text_attr = getattr(description, "text", None)
        if isinstance(text_attr, str):
            return text_attr

        extra_attr = getattr(description, "extra", None)
        if isinstance(extra_attr, list):
            parts = [part.get("text", "") for part in extra_attr if isinstance(part, dict)]
            filtered = [part for part in parts if part]
            if filtered:
                return " ".join(filtered)

        if isinstance(description, dict):
            parts = []
            text = description.get("text")
            if isinstance(text, str):
                parts.append(text)
            extra = description.get("extra")
            if isinstance(extra, list):
                parts.extend(part.get("text", "") for part in extra if isinstance(part, dict))
            filtered = [part for part in parts if part]
            if filtered:
                return " ".join(filtered)

        return str(description)

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

    @app_commands.command(name="status", description="Affiche l'état actuel du serveur Minecraft.")
    async def status(self, interaction: discord.Interaction) -> None:
        try:
            status = await self._query_status()
        except Exception as exc:  # pragma: no cover - dépend des services externes
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Serveur injoignable",
                    "Impossible de contacter le serveur Minecraft pour le moment.",
                ),
                ephemeral=True,
            )
            if interaction.guild:
                await audit_logs.log_error(
                    interaction.guild,
                    "Statut Minecraft",
                    f"Échec de la récupération du statut : {exc}",
                )
            return

        description = (
            f"👥 Joueurs en ligne : **{status.players.online}**\n"
            f"🧭 Version : **{status.version.name}**\n"
            f"📶 Latence : **{int(status.latency)} ms**"
        )
        embed = embeds.build_embed("Statut du serveur", description)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if interaction.guild:
            await audit_logs.log_to_channel(
                interaction.guild,
                f"📊 Statut Minecraft consulté par {interaction.user.mention}.",
            )

    @app_commands.command(name="motd", description="Affiche le message du jour du serveur Minecraft.")
    async def motd(self, interaction: discord.Interaction) -> None:
        try:
            status = await self._query_status()
        except Exception:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Serveur injoignable",
                    "Impossible de récupérer le message du jour actuellement.",
                ),
                ephemeral=True,
            )
            return

        motd = self._extract_description(status.description)
        embed = embeds.build_embed("Message du jour", motd or "(vide)")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if interaction.guild:
            await audit_logs.log_to_channel(
                interaction.guild,
                f"📝 MOTD consulté par {interaction.user.mention}.",
            )

    @app_commands.command(name="players", description="Liste les joueurs connectés au serveur Minecraft.")
    async def players(self, interaction: discord.Interaction) -> None:
        try:
            status = await self._query_status()
        except Exception:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Serveur injoignable",
                    "Impossible de lister les joueurs actuellement.",
                ),
                ephemeral=True,
            )
            return

        sample = status.players.sample or []
        if not sample:
            description = "Personne n'est connecté pour l'instant."
        else:
            players_list = "\n".join(f"• {player.name}" for player in sample)
            description = f"Joueurs connectés :\n{players_list}"
        embed = embeds.build_embed("Joueurs connectés", description)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if interaction.guild:
            await audit_logs.log_to_channel(
                interaction.guild,
                f"🧑‍🤝‍🧑 Liste des joueurs consultée par {interaction.user.mention}.",
            )


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog Minecraft au bot."""

    await bot.add_cog(Minecraft(bot))
