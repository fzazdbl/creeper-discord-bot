"""Gestion de l'accueil automatique des membres."""
from __future__ import annotations

import discord
from discord.ext import commands

from utils import config, embeds, logs as audit_logs


class Welcome(commands.Cog):
    """Cog chargé des messages de bienvenue et de l'attribution des rôles par défaut."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _assign_role(self, member: discord.Member) -> None:
        """Assigne le rôle adapté au membre qui rejoint."""

        guild = member.guild
        role_name = config.BOT_ROLE_NAME if member.bot else config.DEFAULT_ROLE_NAME
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            return
        try:
            await member.add_roles(role, reason="Arrivée d'un nouveau membre")
        except discord.Forbidden:
            await audit_logs.log_to_channel(guild, "⚠️ Impossible d'attribuer automatiquement le rôle.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Souhaite la bienvenue et applique le rôle adapté."""

        guild = member.guild
        await self._assign_role(member)
        await audit_logs.log_to_channel(guild, f"👋 {member.display_name} vient de rejoindre le serveur.")

        if not config.are_welcome_messages_enabled():
            return

        welcome_channel = discord.utils.get(guild.text_channels, name=config.get_welcome_channel_name())
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

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Consigne le départ d'un membre."""

        guild = member.guild
        await audit_logs.log_to_channel(guild, f"👋 {member.display_name} a quitté le serveur.")


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog d'accueil au bot."""

    await bot.add_cog(Welcome(bot))
