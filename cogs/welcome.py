"""Gestion de l'accueil automatique des membres."""
from __future__ import annotations

import discord
from discord.ext import commands

from utils import config, embeds


class Welcome(commands.Cog):
    """Cog chargé des messages de bienvenue et de l'attribution des rôles par défaut."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _log(self, guild: discord.Guild, message: str) -> None:
        """Envoie un message dans le salon de logs si présent."""

        log_channel = discord.utils.get(guild.text_channels, name=config.LOG_CHANNEL_NAME)
        if log_channel is not None:
            await log_channel.send(message)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Souhaite la bienvenue et applique le rôle adapté."""

        guild = member.guild
        if guild is None:
            return

        role_name = config.BOT_ROLE_NAME if member.bot else config.DEFAULT_ROLE_NAME
        role = discord.utils.get(guild.roles, name=role_name)
        if role is not None:
            try:
                await member.add_roles(role, reason="Arrivée d'un nouveau membre")
            except discord.Forbidden:
                await self._log(guild, "⚠️ Impossible d'attribuer automatiquement le rôle.")

        welcome_channel = discord.utils.get(guild.text_channels, name=config.WELCOME_CHANNEL_NAME)
        if welcome_channel is None:
            return

        general_channel = discord.utils.get(guild.text_channels, name="💬-général")
        rules_channel = discord.utils.get(guild.text_channels, name="📜-règlement")
        welcome_message = config.WELCOME_MESSAGE.format(
            mention=member.mention,
            guild=guild.name,
            rules_channel=rules_channel.mention if rules_channel else "le règlement",
            general_channel=general_channel.mention if general_channel else "le salon principal",
        )

        welcome_embed = embeds.build_embed(
            title="🎉 Nouveau membre !",
            description=welcome_message,
        )
        await welcome_channel.send(embed=welcome_embed)
        await self._log(guild, f"👋 {member.display_name} vient de rejoindre le serveur.")


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog d'accueil au bot."""

    await bot.add_cog(Welcome(bot))
