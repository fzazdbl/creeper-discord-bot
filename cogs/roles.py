"""Gestion centralisée des rôles du serveur."""
from __future__ import annotations

import discord
from discord.ext import commands

from utils import config, logs as audit_logs


class Roles(commands.Cog):
    """Cog chargé de créer et maintenir la hiérarchie des rôles."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _log(self, guild: discord.Guild, message: str) -> None:
        """Envoie le message spécifié dans le salon #logs si présent."""

        await audit_logs.log_to_channel(guild, message)

    async def synchronize_roles(self, guild: discord.Guild) -> list[str]:
        """Crée ou met à jour les rôles définis dans la configuration."""

        report: list[str] = []
        for role_conf in config.get_roles():
            role = discord.utils.get(guild.roles, name=role_conf.name)
            if role is None:
                role = await guild.create_role(
                    name=role_conf.name,
                    permissions=role_conf.permissions,
                    colour=role_conf.colour,
                    mentionable=role_conf.mentionable,
                    hoist=role_conf.hoist,
                    reason="Provisionnement automatique Creeper",
                )
                report.append(f"✅ Rôle créé : {role_conf.name}")
            else:
                await role.edit(
                    permissions=role_conf.permissions,
                    colour=role_conf.colour,
                    mentionable=role_conf.mentionable,
                    hoist=role_conf.hoist,
                    reason="Synchronisation automatique Creeper",
                )
                report.append(f"♻️ Rôle mis à jour : {role_conf.name}")

        await self._reorder_roles(guild)
        await self._log(guild, "🧱 Synchronisation des rôles terminée.")
        return report

    async def _reorder_roles(self, guild: discord.Guild) -> None:
        """Tente de positionner les rôles créés juste sous le rôle du bot."""

        if guild.me is None or guild.me.top_role is None:
            return

        top_position = guild.me.top_role.position - 1
        if top_position <= 0:
            return

        position_map: dict[discord.Role, int] = {}
        current_position = top_position
        for role_conf in config.get_roles():
            role = discord.utils.get(guild.roles, name=role_conf.name)
            if role and role != guild.me.top_role:
                position_map[role] = max(current_position, 1)
                current_position -= 1

        if position_map:
            try:
                await guild.edit_role_positions(positions=position_map)
            except discord.Forbidden:
                await self._log(
                    guild,
                    "⚠️ Impossible d'ajuster la hiérarchie des rôles : permissions insuffisantes.",
                )


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog au bot."""

    await bot.add_cog(Roles(bot))
