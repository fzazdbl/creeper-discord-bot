"""Module de configuration central du bot Creeper."""
from __future__ import annotations

from dataclasses import dataclass

import discord

BOT_NAME: str = "Creeper"
"""Nom public du bot."""

WELCOME_CHANNEL_NAME: str = "📥-bienvenue"
"""Nom du salon d'accueil destiné aux nouveaux membres."""

LOG_CHANNEL_NAME: str = "📚-logs"
"""Nom du salon texte recevant les journaux d'actions du bot."""

DEFAULT_ROLE_NAME: str = "🧱 Joueur"
"""Nom du rôle attribué par défaut aux nouveaux arrivants humains."""

BOT_ROLE_NAME: str = "🤖 Bot"
"""Nom du rôle attribué automatiquement aux bots rejoignant le serveur."""

MUSIC_VOICE_CHANNEL_NAME: str = "🎶 Écouter de la musique (vocal)"
"""Nom du salon vocal officiel dédié à l'écoute musicale."""

EMBED_COLOR_PRIMARY: discord.Colour = discord.Colour(0x57F287)
"""Couleur principale des embeds informatifs."""

EMBED_COLOR_WARNING: discord.Colour = discord.Colour(0xED4245)
"""Couleur utilisée pour les messages d'avertissement."""

WELCOME_MESSAGE: str = (
    "Bienvenue {mention} sur **{guild}** !\n\n"
    "➡️ Pense à consulter {rules_channel} pour découvrir le règlement.\n"
    "➡️ Présente-toi et échange avec la classe dans {general_channel}.\n"
    "Nous sommes ravis de t'accueillir parmi les explorateurs BTS SIO !"
)
"""Message d'accueil envoyé lorsqu'un membre rejoint le serveur."""

SETUP_SUMMARY_HEADER: str = (
    "La configuration du serveur Minecraft BTS SIO est terminée."
)
"""Texte introductif récapitulatif de la commande /setup."""

CATEGORIES: list[dict[str, object]] = [
    {
        "name": "💬 Discussions",
        "channels": [
            {"name": "💬-général", "type": "text"},
            {"name": "🤔-questions", "type": "text"},
            {"name": "📊-sondages", "type": "text"},
        ],
    },
    {
        "name": "📜 Annonces & Infos",
        "channels": [
            {"name": "📢-annonces", "type": "text"},
            {"name": "📜-règlement", "type": "text"},
            {"name": LOG_CHANNEL_NAME, "type": "text"},
            {"name": WELCOME_CHANNEL_NAME, "type": "text"},
        ],
    },
    {
        "name": "🛠️ Support & Aide",
        "channels": [
            {"name": "🛠️-aide", "type": "text"},
            {"name": "❓-faq", "type": "text"},
        ],
    },
    {
        "name": "🧱 Screenshots & Builds",
        "channels": [
            {"name": "🧱-screenshots", "type": "text"},
            {"name": "🎨-créations", "type": "text"},
        ],
    },
    {
        "name": "🎮 Équipe & Builders",
        "channels": [
            {"name": "👥-équipe", "type": "text"},
            {"name": "📌-projets", "type": "text"},
        ],
    },
    {
        "name": "🔊 Vocaux",
        "channels": [
            {"name": "🔊 Discussion", "type": "voice"},
            {"name": "🗣️ Réunion", "type": "voice"},
        ],
    },
    {
        "name": "🎧 Musique",
        "channels": [
            {"name": MUSIC_VOICE_CHANNEL_NAME, "type": "voice"},
        ],
    },
]
"""Structure officielle des catégories et salons à créer via /setup."""

@dataclass(slots=True)
class RoleConfiguration:
    """Représente une configuration de rôle à provisionner."""

    name: str
    permissions: discord.Permissions
    colour: discord.Colour
    mentionable: bool
    hoist: bool


ROLES: tuple[RoleConfiguration, ...] = (
    RoleConfiguration(
        name="👑 Admin",
        permissions=discord.Permissions(administrator=True),
        colour=discord.Colour.gold(),
        mentionable=False,
        hoist=True,
    ),
    RoleConfiguration(
        name="🔧 Modérateur",
        permissions=discord.Permissions(
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            mute_members=True,
            move_members=True,
            view_audit_log=True,
        ),
        colour=discord.Colour.orange(),
        mentionable=True,
        hoist=True,
    ),
    RoleConfiguration(
        name=DEFAULT_ROLE_NAME,
        permissions=discord.Permissions(
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            connect=True,
            speak=True,
        ),
        colour=discord.Colour.green(),
        mentionable=True,
        hoist=False,
    ),
    RoleConfiguration(
        name=BOT_ROLE_NAME,
        permissions=discord.Permissions(
            send_messages=True,
            embed_links=True,
            read_messages=True,
            read_message_history=True,
            connect=True,
            speak=True,
            use_application_commands=True,
            manage_messages=True,
        ),
        colour=discord.Colour.blurple(),
        mentionable=False,
        hoist=False,
    ),
)
"""Définition complète des rôles à créer avec leurs permissions."""


def humanize_duration(duration: int | None) -> str:
    """Convertit une durée en secondes vers un format mm:ss lisible."""

    if not duration:
        return "N/A"
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}h {minutes:02d}min {seconds:02d}s"
    return f"{minutes:d}min {seconds:02d}s"
