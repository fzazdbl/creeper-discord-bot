"""Générateurs d'embeds uniformes pour le bot Creeper."""
from __future__ import annotations

import datetime

import discord

from . import config


def build_embed(
    title: str,
    description: str,
    *,
    colour: discord.Colour | None = None,
    footer: str | None = None,
) -> discord.Embed:
    """Crée un embed basique cohérent avec l'identité visuelle du bot."""

    embed = discord.Embed(
        title=title,
        description=description,
        colour=colour or config.EMBED_COLOR_PRIMARY,
        timestamp=datetime.datetime.utcnow(),
    )
    embed.set_footer(text=footer or config.BOT_NAME)
    return embed


def success_embed(title: str, description: str) -> discord.Embed:
    """Retourne un embed vert pour indiquer une réussite."""

    return build_embed(title=title, description=description, colour=config.EMBED_COLOR_PRIMARY)


def warning_embed(title: str, description: str) -> discord.Embed:
    """Retourne un embed rouge pour indiquer une erreur ou un avertissement."""

    return build_embed(title=title, description=description, colour=config.EMBED_COLOR_WARNING)


def music_embed(title: str, *, requester: discord.abc.User, url: str, duration: str) -> discord.Embed:
    """Crée un embed spécifique pour l'annonce d'une piste audio."""

    description = (
        f"🎶 **Titre :** [{title}]({url})\n"
        f"⏱️ **Durée :** {duration}\n"
        f"🙋 **Demandé par :** {requester.mention}"
    )
    return build_embed(title="Lecture en cours", description=description)


def queue_embed(queue: list[str]) -> discord.Embed:
    """Formate un embed listant la file d'attente musicale."""

    if not queue:
        description = "La file d'attente est actuellement vide."
    else:
        description = "\n".join(f"`{index + 1}.` {item}" for index, item in enumerate(queue))
    return build_embed(title="File d'attente", description=description)
