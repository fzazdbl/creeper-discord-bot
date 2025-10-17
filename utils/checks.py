"""Outils de vérification de permissions pour les commandes d'application."""
from __future__ import annotations

import discord
from discord import app_commands


def has_manage_guild() -> app_commands.Check:
    """Restreint l'exécution d'une commande aux responsables du serveur."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans un serveur.")
        permissions = interaction.user.guild_permissions  # type: ignore[assignment]
        if not permissions.manage_guild:
            raise app_commands.CheckFailure(
                "Seuls les membres possédant la permission 'Gérer le serveur' peuvent utiliser cette commande."
            )
        return True

    return app_commands.check(predicate)


def ensure_voice_connection(interaction: discord.Interaction) -> discord.VoiceClient | None:
    """Retourne la connexion vocale du serveur si elle existe."""

    if interaction.guild is None:
        return None
    return interaction.guild.voice_client
