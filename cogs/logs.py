"""Cog chargé de centraliser les journaux d'actions du bot."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import logs as audit_logs


class Logs(commands.Cog):
    """Surveille l'activité du bot pour alimenter le salon #logs."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: app_commands.Command | app_commands.Group | None,
    ) -> None:
        if interaction.guild is None or command is None or interaction.user is None:
            return
        await audit_logs.log_to_channel(
            interaction.guild,
            f"✅ Commande /{command.qualified_name} utilisée par {interaction.user.mention} dans {interaction.channel.mention if interaction.channel else 'un salon inconnu'}.",
        )

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if interaction.guild is None:
            return
        command_name = interaction.command.qualified_name if interaction.command else "?"
        await audit_logs.log_error(
            interaction.guild,
            "Erreur de commande",
            f"/{command_name} a échoué : {error}",
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        guild = member.guild
        if guild is None:
            return

        if before.channel is None and after.channel is not None:
            await audit_logs.log_to_channel(
                guild,
                f"🔊 {member.display_name} a rejoint {after.channel.mention}.",
            )
        elif before.channel is not None and after.channel is None:
            await audit_logs.log_to_channel(
                guild,
                f"🔇 {member.display_name} a quitté {before.channel.mention}.",
            )
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            await audit_logs.log_to_channel(
                guild,
                f"🔁 {member.display_name} est passé de {before.channel.mention} à {after.channel.mention}.",
            )


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog de logs au bot."""

    await bot.add_cog(Logs(bot))
