"""Utilitaires centralisés d'écriture dans le salon de logs."""
from __future__ import annotations

from typing import Optional

import discord

from . import config


async def _ensure_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Récupère ou crée le salon des journaux pour un serveur."""

    channel_name = config.get_log_channel_name()
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if channel is not None:
        return channel

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            reason="Création automatique du salon de logs Creeper",
            topic="Journal automatique des actions du bot Creeper.",
        )
    except discord.Forbidden:
        return None
    except discord.HTTPException:
        return None
    return channel


async def log_to_channel(
    guild: discord.Guild,
    message: str | None = None,
    *,
    embed: discord.Embed | None = None,
) -> None:
    """Envoie un message dans le salon de logs en créant le canal si nécessaire."""

    if guild is None or (message is None and embed is None):
        return

    channel = await _ensure_log_channel(guild)
    if channel is None:
        return

    try:
        await channel.send(content=message, embed=embed)
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass


async def log_error(guild: discord.Guild, title: str, description: str) -> None:
    """Envoie un embed d'erreur standard dans le salon de logs."""

    embed = discord.Embed(title=title, description=description, colour=discord.Colour.red())
    await log_to_channel(guild, embed=embed)
