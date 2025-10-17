"""Commandes et protections automatiques pour la modération."""
from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque
from typing import Deque, Dict

import discord
from discord import app_commands
from discord.ext import commands

from utils import config, embeds, logs as audit_logs


class Moderation(commands.Cog):
    """Regroupe les outils de modération et l'anti-abus basique."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._message_buckets: Dict[int, Deque[float]] = defaultdict(deque)
        if config.BLOCKED_DOMAINS:
            domains_pattern = "|".join(re.escape(domain) for domain in config.BLOCKED_DOMAINS)
            self._domain_regex = re.compile(rf"https?://[^\s]*({domains_pattern})", re.IGNORECASE)
        else:
            self._domain_regex = None
        if config.BANNED_WORDS:
            words_pattern = "|".join(re.escape(word) for word in config.BANNED_WORDS)
            self._words_regex = re.compile(rf"\b({words_pattern})\b", re.IGNORECASE)
        else:
            self._words_regex = None

    async def _ensure_muted_role(self, guild: discord.Guild) -> discord.Role | None:
        """Récupère ou crée le rôle muet utilisé par Creeper."""

        muted_role = discord.utils.get(guild.roles, name=config.MUTED_ROLE_NAME)
        if muted_role is None:
            try:
                muted_role = await guild.create_role(
                    name=config.MUTED_ROLE_NAME,
                    reason="Création automatique pour les sanctions",
                    permissions=discord.Permissions(send_messages=False, speak=False),
                )
            except discord.Forbidden:
                return None
            except discord.HTTPException:
                return None

            await self._sync_muted_permissions(guild, muted_role)

        return muted_role

    async def _sync_muted_permissions(self, guild: discord.Guild, role: discord.Role) -> None:
        """Applique les permissions d'interdiction de parler aux salons existants."""

        for channel in guild.channels:
            overwrite = channel.overwrites_for(role)
            updated = False
            if isinstance(channel, discord.TextChannel):
                if overwrite.send_messages is not False:
                    overwrite.send_messages = False
                    updated = True
                if overwrite.add_reactions is not False:
                    overwrite.add_reactions = False
                    updated = True
            elif isinstance(channel, discord.VoiceChannel):
                if overwrite.speak is not False:
                    overwrite.speak = False
                    updated = True
                if overwrite.stream is not False:
                    overwrite.stream = False
                    updated = True

            if updated:
                try:
                    await channel.set_permissions(role, overwrite=overwrite)
                except discord.Forbidden:
                    continue
                except discord.HTTPException:
                    continue

    async def _apply_temporary_mute(
        self,
        member: discord.Member,
        duration_seconds: int,
        *,
        reason: str,
    ) -> None:
        guild = member.guild
        if guild is None:
            return
        role = await self._ensure_muted_role(guild)
        if role is None:
            return
        if role not in member.roles:
            try:
                await member.add_roles(role, reason=reason)
            except discord.Forbidden:
                return
            except discord.HTTPException:
                return

        async def _delayed_unmute() -> None:
            await asyncio.sleep(duration_seconds)
            await self._remove_mute(member, reason="Fin de la sanction automatique")

        asyncio.create_task(_delayed_unmute())

    async def _remove_mute(self, member: discord.Member, *, reason: str) -> None:
        guild = member.guild
        if guild is None:
            return
        role = discord.utils.get(guild.roles, name=config.MUTED_ROLE_NAME)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=reason)
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

    def _record_message(self, author_id: int) -> int:
        now = time.monotonic()
        bucket = self._message_buckets[author_id]
        bucket.append(now)
        while bucket and now - bucket[0] > config.SPAM_INTERVAL_SECONDS:
            bucket.popleft()
        return len(bucket)

    async def _handle_automod(
        self,
        message: discord.Message,
        *,
        reason: str,
        notify: bool = True,
    ) -> None:
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        if notify:
            try:
                await message.channel.send(
                    content=message.author.mention,
                    embed=embeds.warning_embed("Message supprimé", reason),
                    delete_after=10,
                )
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

        if message.guild:
            await audit_logs.log_to_channel(
                message.guild,
                f"🛡️ Message supprimé de {message.author.mention} : {reason}\nContenu : {message.content}",
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        content_lower = message.content.lower()
        if self._words_regex and self._words_regex.search(content_lower):
            await self._handle_automod(message, reason="Langage inapproprié détecté.")
            return

        if self._domain_regex and self._domain_regex.search(content_lower):
            await self._handle_automod(message, reason="Lien potentiellement dangereux bloqué.")
            return

        count = self._record_message(message.author.id)
        if count >= config.SPAM_MESSAGE_LIMIT:
            await self._handle_automod(message, reason="Détection de spam.")
            await self._apply_temporary_mute(
                message.author, 120, reason="Anti-spam automatique Creeper"
            )
            try:
                await message.author.send(
                    "Tu as été temporairement muet 2 minutes pour cause de spam sur le serveur Minecraft BTS SIO."
                )
            except discord.Forbidden:
                pass
            return

    @app_commands.command(name="ban", description="Bannit un membre du serveur.")
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        raison: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        if membre == interaction.user:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Action impossible", "Tu ne peux pas te bannir toi-même."),
                ephemeral=True,
            )
            return

        try:
            await interaction.guild.ban(membre, reason=raison)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Permissions insuffisantes", "Je ne peux pas bannir ce membre."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Erreur", "Impossible de bannir ce membre pour le moment."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=embeds.success_embed(
                "Membre banni",
                f"{membre.mention} a été banni du serveur.",
            ),
            ephemeral=True,
        )
        await audit_logs.log_to_channel(
            interaction.guild,
            f"⛔ {membre.mention} banni par {interaction.user.mention} : {raison or 'Aucune raison fournie'}",
        )

    @app_commands.command(name="kick", description="Expulse un membre du serveur.")
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        raison: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        if membre == interaction.user:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Action impossible", "Tu ne peux pas t'expulser toi-même."),
                ephemeral=True,
            )
            return

        try:
            await interaction.guild.kick(membre, reason=raison)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Permissions insuffisantes", "Je ne peux pas expulser ce membre."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Erreur", "Impossible d'expulser ce membre pour le moment."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=embeds.success_embed(
                "Membre expulsé",
                f"{membre.mention} a été expulsé du serveur.",
            ),
            ephemeral=True,
        )
        await audit_logs.log_to_channel(
            interaction.guild,
            f"👢 {membre.mention} expulsé par {interaction.user.mention} : {raison or 'Aucune raison fournie'}",
        )

    @app_commands.command(name="mute", description="Rend un membre muet sur tout le serveur.")
    @app_commands.describe(duree="Durée en minutes (laisser vide pour indéterminé)")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        duree: app_commands.Range[int, 1, 1440] | None = None,
        raison: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        if membre == interaction.user:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Action impossible", "Tu ne peux pas te rendre muet toi-même."),
                ephemeral=True,
            )
            return

        role = await self._ensure_muted_role(interaction.guild)
        if role is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Rôle introuvable",
                    "Je ne peux pas créer ou récupérer le rôle muet. Vérifie mes permissions.",
                ),
                ephemeral=True,
            )
            return

        try:
            await membre.add_roles(role, reason=raison or "Mute via Creeper")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Permissions insuffisantes", "Je ne peux pas appliquer le rôle muet à ce membre."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Erreur", "Impossible d'ajouter le rôle muet pour le moment."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=embeds.success_embed(
                "Membre muet",
                f"{membre.mention} ne peut plus écrire ou parler." + (
                    f" Durée : {duree} min." if duree else ""
                ),
            ),
            ephemeral=True,
        )

        await audit_logs.log_to_channel(
            interaction.guild,
            f"🔇 {membre.mention} muet par {interaction.user.mention} : {raison or 'Aucune raison fournie'}",
        )

        if duree:
            await self._apply_temporary_mute(
                membre, duree * 60, reason="Mute temporaire programmé via commande"
            )

    @app_commands.command(name="unmute", description="Rend la parole à un membre.")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        await self._remove_mute(membre, reason=f"Demande de {interaction.user}")
        await interaction.response.send_message(
            embed=embeds.success_embed(
                "Membre rétabli",
                f"{membre.mention} peut à nouveau écrire et parler.",
            ),
            ephemeral=True,
        )
        await audit_logs.log_to_channel(
            interaction.guild,
            f"🔈 {membre.mention} a été rétabli par {interaction.user.mention}.",
        )

    @app_commands.command(name="warn", description="Avertit un membre par message privé.")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        raison: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        try:
            await membre.send(
                embed=embeds.build_embed(
                    "Avertissement officiel",
                    f"Tu as reçu un avertissement sur {interaction.guild.name} : {raison}",
                )
            )
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            embed=embeds.success_embed(
                "Avertissement envoyé",
                f"{membre.mention} a été averti en privé.",
            ),
            ephemeral=True,
        )
        await audit_logs.log_to_channel(
            interaction.guild,
            f"⚠️ {membre.mention} averti par {interaction.user.mention} : {raison}",
        )


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog de modération au bot."""

    await bot.add_cog(Moderation(bot))
