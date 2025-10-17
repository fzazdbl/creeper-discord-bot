"""Module de configuration central du bot Creeper."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path

import discord

BOT_NAME: str = "Creeper"
"""Nom public du bot."""

DEFAULT_WELCOME_CHANNEL_NAME: str = "📥-bienvenue"
"""Nom du salon d'accueil destiné aux nouveaux membres (valeur par défaut)."""

DEFAULT_LOG_CHANNEL_NAME: str = "📚-logs"
"""Nom du salon texte recevant les journaux d'actions du bot (valeur par défaut)."""

DEFAULT_MUSIC_VOICE_CHANNEL_NAME: str = "🎶 Écouter de la musique (vocal)"
"""Nom du salon vocal officiel dédié à l'écoute musicale (valeur par défaut)."""

DEFAULT_ROLE_NAME: str = "🧱 Joueur"
"""Nom du rôle attribué par défaut aux nouveaux arrivants humains."""

BOT_ROLE_NAME: str = "🤖 Bot"
"""Nom du rôle attribué automatiquement aux bots rejoignant le serveur."""

MUTED_ROLE_NAME: str = "🔇 Muted"
"""Nom du rôle appliqué lors d'une mise en sourdine par modération."""

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

MINECRAFT_SERVER_IP: str = "play.mc-bts-sio.fr"
"""Adresse IP/hostname du serveur Minecraft."""

MINECRAFT_SERVER_SEED: str = "8123476501298746501"
"""Seed du monde Minecraft à afficher aux joueurs."""

MINECRAFT_SERVER_PORT: int = 25565
"""Port TCP du serveur Minecraft (25565 par défaut)."""

MINECRAFT_MEMES: tuple[str, ...] = (
    "https://i.imgflip.com/4/46e43q.jpg",
    "https://i.imgflip.com/1bij.jpg",
    "https://i.imgflip.com/7o1y2f.jpg",
    "https://i.imgflip.com/3i7p96.jpg",
)
"""Collection de mèmes Minecraft envoyés par la commande /meme."""

BANNED_WORDS: tuple[str, ...] = (
    "con",
    "connard",
    "fdp",
    "merde",
    "salope",
)
"""Liste basique de mots grossiers à supprimer automatiquement."""

BLOCKED_DOMAINS: tuple[str, ...] = (
    "grabify",
    "iplogger",
    "gyazo.in",
    "discordgift.site",
)
"""Domaines suspects entraînant la suppression automatique du message."""

SPAM_MESSAGE_LIMIT: int = 5
"""Nombre de messages autorisés par intervalle avant détection de spam."""

SPAM_INTERVAL_SECONDS: int = 8
"""Fenêtre de temps pour le contrôle anti-spam."""

_STATE_FILE = Path(__file__).with_name("config_state.json")


@dataclass(slots=True)
class ConfigState:
    """Représente l'état de configuration personnalisable du bot."""

    welcome_channel_name: str = DEFAULT_WELCOME_CHANNEL_NAME
    log_channel_name: str = DEFAULT_LOG_CHANNEL_NAME
    music_voice_channel_name: str = DEFAULT_MUSIC_VOICE_CHANNEL_NAME
    welcome_messages_enabled: bool = True
    role_colours: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ConfigState":
        """Construit un état à partir d'un dictionnaire brut."""

        role_colours_raw = payload.get("role_colours", {})
        if not isinstance(role_colours_raw, dict):
            role_colours_raw = {}
        role_colours = {
            str(name): int(value)
            for name, value in role_colours_raw.items()
            if isinstance(name, str) and isinstance(value, int)
        }
        return cls(
            welcome_channel_name=str(
                payload.get("welcome_channel_name", DEFAULT_WELCOME_CHANNEL_NAME)
            ),
            log_channel_name=str(payload.get("log_channel_name", DEFAULT_LOG_CHANNEL_NAME)),
            music_voice_channel_name=str(
                payload.get("music_voice_channel_name", DEFAULT_MUSIC_VOICE_CHANNEL_NAME)
            ),
            welcome_messages_enabled=bool(payload.get("welcome_messages_enabled", True)),
            role_colours=role_colours,
        )

    def to_dict(self) -> dict[str, object]:
        """Sérialise l'état pour une écriture dans un fichier JSON."""

        return {
            "welcome_channel_name": self.welcome_channel_name,
            "log_channel_name": self.log_channel_name,
            "music_voice_channel_name": self.music_voice_channel_name,
            "welcome_messages_enabled": self.welcome_messages_enabled,
            "role_colours": self.role_colours,
        }


def _load_state() -> ConfigState:
    if not _STATE_FILE.exists():
        return ConfigState()
    try:
        payload = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ConfigState()
    return ConfigState.from_dict(payload)


_STATE: ConfigState = _load_state()
WELCOME_CHANNEL_NAME: str = _STATE.welcome_channel_name
"""Nom du salon d'accueil actuellement configuré."""

LOG_CHANNEL_NAME: str = _STATE.log_channel_name
"""Nom du salon recevant les journaux actuellement configuré."""

MUSIC_VOICE_CHANNEL_NAME: str = _STATE.music_voice_channel_name
"""Nom du salon vocal musique actuellement configuré."""


def _save_state() -> None:
    """Sauvegarde l'état courant sur disque."""

    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(_STATE.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        # L'échec d'écriture ne doit pas bloquer le bot ; une entrée sera loggée ailleurs.
        pass


@dataclass(slots=True)
class RoleConfiguration:
    """Représente une configuration de rôle à provisionner."""

    name: str
    permissions: discord.Permissions
    colour: discord.Colour
    mentionable: bool
    hoist: bool


_DEFAULT_ROLES: tuple[RoleConfiguration, ...] = (
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
            manage_channels=True,
        ),
        colour=discord.Colour.blurple(),
        mentionable=False,
        hoist=False,
    ),
)
"""Définition complète des rôles à créer avec leurs permissions par défaut."""


def get_roles() -> tuple[RoleConfiguration, ...]:
    """Retourne la configuration des rôles en prenant en compte les personnalisations."""

    roles: list[RoleConfiguration] = []
    for role_conf in _DEFAULT_ROLES:
        override_colour = _STATE.role_colours.get(role_conf.name)
        colour = discord.Colour(override_colour) if override_colour is not None else role_conf.colour
        roles.append(
            RoleConfiguration(
                name=role_conf.name,
                permissions=role_conf.permissions,
                colour=colour,
                mentionable=role_conf.mentionable,
                hoist=role_conf.hoist,
            )
        )
    return tuple(roles)


def get_default_role_colour(role_name: str) -> discord.Colour:
    """Retourne la couleur par défaut d'un rôle connu."""

    for role_conf in _DEFAULT_ROLES:
        if role_conf.name == role_name:
            return role_conf.colour
    return discord.Colour.default()


def get_categories() -> list[dict[str, object]]:
    """Structure officielle des catégories et salons à créer via /setup."""

    return [
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
                {"name": get_log_channel_name(), "type": "text"},
                {"name": get_welcome_channel_name(), "type": "text"},
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
                {"name": get_music_voice_channel_name(), "type": "voice"},
            ],
        },
    ]


def get_log_channel_name() -> str:
    return LOG_CHANNEL_NAME


def get_welcome_channel_name() -> str:
    return WELCOME_CHANNEL_NAME


def get_music_voice_channel_name() -> str:
    return MUSIC_VOICE_CHANNEL_NAME


def are_welcome_messages_enabled() -> bool:
    return _STATE.welcome_messages_enabled


def set_log_channel_name(name: str) -> None:
    global LOG_CHANNEL_NAME, _STATE
    _STATE = replace(_STATE, log_channel_name=name)
    LOG_CHANNEL_NAME = name
    _save_state()


def set_welcome_channel_name(name: str) -> None:
    global WELCOME_CHANNEL_NAME, _STATE
    _STATE = replace(_STATE, welcome_channel_name=name)
    WELCOME_CHANNEL_NAME = name
    _save_state()


def set_music_voice_channel_name(name: str) -> None:
    global MUSIC_VOICE_CHANNEL_NAME, _STATE
    _STATE = replace(_STATE, music_voice_channel_name=name)
    MUSIC_VOICE_CHANNEL_NAME = name
    _save_state()


def set_welcome_messages(enabled: bool) -> None:
    global _STATE
    _STATE = replace(_STATE, welcome_messages_enabled=enabled)
    _save_state()


def set_role_colour(role_name: str, colour: discord.Colour | None) -> None:
    """Définit (ou réinitialise) la couleur personnalisée d'un rôle."""

    global _STATE
    role_colours = dict(_STATE.role_colours)
    if colour is None:
        role_colours.pop(role_name, None)
    else:
        role_colours[role_name] = colour.value
    _STATE = replace(_STATE, role_colours=role_colours)
    _save_state()


def get_role_colour_override(role_name: str) -> discord.Colour | None:
    value = _STATE.role_colours.get(role_name)
    return discord.Colour(value) if value is not None else None


def humanize_duration(duration: int | None) -> str:
    """Convertit une durée en secondes vers un format mm:ss lisible."""

    if not duration:
        return "N/A"
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}h {minutes:02d}min {seconds:02d}s"
    return f"{minutes:d}min {seconds:02d}s"
