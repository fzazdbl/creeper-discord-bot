"""Point d'entrée principal du bot Creeper."""
from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils import config

COGS = [
    "cogs.roles",
    "cogs.setup",
    "cogs.music",
    "cogs.welcome",
    "cogs.help",
    "cogs.logs",
    "cogs.admin",
    "cogs.moderation",
    "cogs.minecraft",
]


class CreeperBot(commands.Bot):
    """Bot personnalisé gérant automatiquement le chargement des cogs."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        intents.voice_states = True
        intents.message_content = True
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            activity=discord.Game(name="Minecraft BTS SIO"),
        )
        self.synced = False

    async def setup_hook(self) -> None:
        """Charge les cogs et synchronise les commandes slash au démarrage."""

        for extension in COGS:
            await self.load_extension(extension)
        await self.tree.sync()
        self.synced = True

    async def on_ready(self) -> None:  # type: ignore[override]
        """Affiche un message confirmant la connexion du bot."""

        logging.info("✅ %s est connecté et prêt.", self.user)


async def main() -> None:
    """Initialise les dépendances et démarre le bot."""

    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise RuntimeError("Le token Discord est introuvable. Définis la variable DISCORD_TOKEN.")

    bot = CreeperBot()
    async with bot:
        logging.info("Démarrage de %s...", config.BOT_NAME)
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Arrêt manuel demandé. À bientôt !")
