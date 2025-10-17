"""Cog complet de gestion musicale basé sur YouTube."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

from utils import config, embeds, logs as audit_logs

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": False,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


def _has_manage_messages(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    return bool(permissions and permissions.manage_messages)


@dataclass(slots=True)
class Track:
    """Représente une piste dans la file d'attente."""

    title: str
    stream_url: Optional[str]
    webpage_url: str
    duration: Optional[int]
    requester: discord.abc.User

    @property
    def display(self) -> str:
        """Retourne un texte humainement lisible pour la file d'attente."""

        return f"{self.title} ({config.humanize_duration(self.duration)})"


@dataclass(slots=True)
class GuildMusicState:
    """Stocke l'état musical propre à un serveur."""

    queue: Deque[Track]
    now_playing: Optional[Track] = None
    text_channel: Optional[discord.TextChannel] = None


class Music(commands.Cog):
    """Implémente les commandes de lecture musicale."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._states: dict[int, GuildMusicState] = {}

    def _get_state(self, guild: discord.Guild) -> GuildMusicState:
        """Retourne l'état courant d'un serveur, en le créant au besoin."""

        state = self._states.get(guild.id)
        if state is None:
            state = GuildMusicState(queue=deque())
            self._states[guild.id] = state
        return state

    async def _log(self, guild: discord.Guild, message: str) -> None:
        await audit_logs.log_to_channel(guild, message)

    async def _search_tracks(self, query: str, requester: discord.abc.User) -> list[Track]:
        """Interroge YouTube via yt_dlp pour obtenir une ou plusieurs pistes."""

        loop = asyncio.get_running_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        except yt_dlp.utils.DownloadError as error:  # type: ignore[attr-defined]
            raise app_commands.AppCommandError(
                "Impossible de contacter YouTube pour cette requête. Merci de réessayer plus tard."
            ) from error
        except Exception as error:  # noqa: BLE001
            raise app_commands.AppCommandError(
                "Une erreur inconnue est survenue lors de la récupération des informations YouTube."
            ) from error

        entries = data.get("entries") if isinstance(data, dict) else None
        if entries:
            tracks = [self._entry_to_track(entry, requester) for entry in entries if entry]
            return [track for track in tracks if track is not None]
        track = self._entry_to_track(data, requester)
        return [track] if track else []

    def _entry_to_track(self, entry: dict, requester: discord.abc.User) -> Optional[Track]:
        """Transforme une entrée yt_dlp en objet Track."""

        if not entry:
            return None
        stream_url = entry.get("url")
        webpage_url = entry.get("webpage_url") or entry.get("url") or ""
        if not (stream_url or webpage_url):
            return None
        return Track(
            title=entry.get("title") or "Titre inconnu",
            stream_url=stream_url,
            webpage_url=webpage_url,
            duration=entry.get("duration"),
            requester=requester,
        )

    async def _connect(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        """Fait rejoindre le salon vocal du membre s'il n'y est pas déjà."""

        if interaction.guild is None or interaction.user is None:
            return None
        voice_state = getattr(interaction.user, "voice", None)
        if voice_state is None or voice_state.channel is None:
            return None

        try:
            if interaction.guild.voice_client:
                if interaction.guild.voice_client.channel != voice_state.channel:
                    await interaction.guild.voice_client.move_to(voice_state.channel)
                return interaction.guild.voice_client

            return await voice_state.channel.connect()
        except discord.Forbidden:
            raise app_commands.AppCommandError(
                "Je n'ai pas les permissions nécessaires pour rejoindre ce salon vocal."
            ) from None
        except discord.ClientException as error:
            raise app_commands.AppCommandError(
                "Impossible de rejoindre le salon vocal pour le moment."
            ) from error

    async def _start_playback(self, guild: discord.Guild) -> None:
        """Démarre la lecture si aucune piste n'est en cours."""

        voice_client = guild.voice_client
        state = self._get_state(guild)
        if voice_client is None or voice_client.is_playing() or voice_client.is_paused():
            return

        if not state.queue:
            state.now_playing = None
            await self._notify(state, guild, "✅ File d'attente terminée.")
            await self._log(guild, "✅ La file de lecture est terminée.")
            return

        track = state.queue.popleft()
        state.now_playing = track
        stream_url = await self._ensure_stream_url(track)
        if stream_url is None:
            await self._notify(state, guild, f"⚠️ Impossible de lire {track.title}.")
            await self._log(guild, f"⚠️ Lecture échouée pour {track.title} : URL introuvable.")
            await self._start_playback(guild)
            return
        audio_source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        voice_client.play(
            audio_source,
            after=lambda error: self.bot.loop.call_soon_threadsafe(self._after_song, guild.id, error),
        )
        await self._notify(
            state,
            guild,
            embed=embeds.music_embed(
                track.title,
                requester=track.requester,
                url=track.webpage_url or track.stream_url,
                duration=config.humanize_duration(track.duration),
            ),
        )
        await self._log(
            guild,
            f"🎶 Lecture démarrée : **{track.title}** demandée par {track.requester.mention}",
        )

    def _after_song(self, guild_id: int, error: Exception | None) -> None:
        """Callback exécuté à la fin d'une piste pour lancer la suivante."""

        if error:
            self.bot.loop.create_task(self._handle_error(guild_id, error))
            return
        self.bot.loop.create_task(self._resume_queue(guild_id))

    async def _handle_error(self, guild_id: int, error: Exception) -> None:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        state = self._states.get(guild.id)
        if state:
            await self._notify(state, guild, f"⚠️ Erreur pendant la lecture : {error}")
        await audit_logs.log_error(guild, "Erreur musicale", str(error))
        await self._resume_queue(guild_id)

    async def _resume_queue(self, guild_id: int) -> None:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        await self._start_playback(guild)

    async def _notify(
        self,
        state: GuildMusicState,
        guild: discord.Guild,
        message: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
    ) -> None:
        """Envoie un message dans le dernier salon texte utilisé ou dans les logs."""

        channel: Optional[discord.TextChannel] = state.text_channel
        if channel is None:
            channel = discord.utils.get(guild.text_channels, name=config.get_log_channel_name())
        if channel is None:
            return
        try:
            if embed:
                await channel.send(embed=embed)
            elif message:
                await channel.send(message)
        except discord.Forbidden:
            await self._log(guild, "⚠️ Impossible d'envoyer un message dans le salon de notification.")
        except discord.HTTPException:
            await self._log(guild, "⚠️ Envoi de message échoué (erreur Discord).")

    def _user_can_control(self, interaction: discord.Interaction) -> bool:
        """Vérifie que l'utilisateur partage le salon vocal du bot."""

        if interaction.guild is None:
            return False
        voice_state = getattr(interaction.user, "voice", None)
        user_channel = voice_state.channel if voice_state else None
        bot_channel = interaction.guild.voice_client.channel if interaction.guild.voice_client else None
        return user_channel is not None and bot_channel is not None and user_channel == bot_channel

    def _check_control_permissions(self, interaction: discord.Interaction) -> bool:
        if not _has_manage_messages(interaction):
            return False
        return self._user_can_control(interaction)

    @app_commands.command(name="play", description="Lit une musique ou une playlist YouTube.")
    async def play(self, interaction: discord.Interaction, recherche: str) -> None:
        """Ajoute la requête à la file d'attente et lance la lecture."""

        if not recherche or not recherche.strip():
            await interaction.response.send_message(
                embed=embeds.warning_embed("Requête manquante", "Indique un lien ou un mot-clé pour /play."),
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        voice_state = getattr(interaction.user, "voice", None)
        if voice_state is None or voice_state.channel is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Salon vocal requis", "Rejoins un salon vocal avant d'utiliser /play."),
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        try:
            voice_client = await self._connect(interaction)
        except app_commands.AppCommandError as error:
            await interaction.followup.send(embed=embeds.warning_embed("Connexion impossible", str(error)), ephemeral=True)
            return

        if voice_client is None:
            await interaction.followup.send(
                embed=embeds.warning_embed("Connexion impossible", "Je n'ai pas réussi à rejoindre ton salon vocal."),
                ephemeral=True,
            )
            return

        try:
            tracks = await self._search_tracks(recherche, interaction.user)
        except app_commands.AppCommandError as error:
            await interaction.followup.send(embed=embeds.warning_embed("Erreur", str(error)), ephemeral=True)
            await self._log(interaction.guild, f"⚠️ Recherche YouTube échouée : {error}")
            return

        if not tracks:
            await interaction.followup.send(
                embed=embeds.warning_embed("Aucun résultat", "Je n'ai trouvé aucune piste correspondante."),
                ephemeral=True,
            )
            return

        state = self._get_state(interaction.guild)
        state.queue.extend(tracks)
        if isinstance(interaction.channel, discord.TextChannel):
            state.text_channel = interaction.channel

        if len(tracks) > 1:
            description = (
                f"{len(tracks)} pistes ajoutées à la file d'attente.\n"
                f"Prochaine lecture : **{tracks[0].title}**"
            )
        else:
            description = f"**{tracks[0].title}** a été ajoutée à la file d'attente."

        await interaction.followup.send(embed=embeds.build_embed("🎵 File mise à jour", description))
        await self._log(
            interaction.guild,
            f"➕ {interaction.user.mention} a ajouté {len(tracks)} piste(s) à la file de lecture.",
        )
        await self._start_playback(interaction.guild)

    @app_commands.command(name="skip", description="Passe à la musique suivante.")
    @app_commands.default_permissions(manage_messages=True)
    async def skip(self, interaction: discord.Interaction) -> None:
        """Passe immédiatement à la piste suivante."""

        if interaction.guild is None or interaction.guild.voice_client is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Aucune lecture", "Je ne suis connecté à aucun salon vocal."),
                ephemeral=True,
            )
            return

        if not self._check_control_permissions(interaction):
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Accès refusé",
                    "Tu dois disposer de la permission 'Gérer les messages' et être dans mon salon vocal.",
                ),
                ephemeral=True,
            )
            return

        interaction.guild.voice_client.stop()
        await self._log(interaction.guild, f"⏭️ Lecture avancée par {interaction.user.mention}.")
        await interaction.response.send_message("⏭️ Lecture avancée.", ephemeral=True)

    @app_commands.command(name="stop", description="Arrête la musique et vide la file d'attente.")
    @app_commands.default_permissions(manage_messages=True)
    async def stop(self, interaction: discord.Interaction) -> None:
        """Arrête toute lecture et quitte le salon vocal."""

        guild = interaction.guild
        voice_client = guild.voice_client if guild else None
        if guild is None or voice_client is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Aucune lecture", "Aucune musique n'est en cours."),
                ephemeral=True,
            )
            return

        if not self._check_control_permissions(interaction):
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Accès refusé",
                    "Tu dois disposer de la permission 'Gérer les messages' et être dans mon salon vocal.",
                ),
                ephemeral=True,
            )
            return

        state = self._get_state(guild)
        state.queue.clear()
        state.now_playing = None
        voice_client.stop()
        try:
            await voice_client.disconnect()
        except discord.HTTPException:
            await self._log(guild, "⚠️ Impossible de me déconnecter du salon vocal.")
        self._states.pop(guild.id, None)
        await self._log(guild, f"🛑 Arrêt complet demandé par {interaction.user.mention}.")
        await interaction.response.send_message("🛑 Lecture interrompue et file vidée.", ephemeral=True)

    @app_commands.command(name="pause", description="Met la musique en pause.")
    @app_commands.default_permissions(manage_messages=True)
    async def pause(self, interaction: discord.Interaction) -> None:
        """Met en pause la lecture actuelle."""

        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client is None or not voice_client.is_playing():
            await interaction.response.send_message(
                embed=embeds.warning_embed("Aucune lecture", "Aucune musique n'est en cours."),
                ephemeral=True,
            )
            return

        if not self._check_control_permissions(interaction):
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Accès refusé",
                    "Tu dois disposer de la permission 'Gérer les messages' et être dans mon salon vocal.",
                ),
                ephemeral=True,
            )
            return

        voice_client.pause()
        await self._log(interaction.guild, f"⏸️ Lecture mise en pause par {interaction.user.mention}.")
        await interaction.response.send_message("⏸️ Lecture mise en pause.", ephemeral=True)

    @app_commands.command(name="resume", description="Relance la musique en pause.")
    @app_commands.default_permissions(manage_messages=True)
    async def resume(self, interaction: discord.Interaction) -> None:
        """Relance la lecture après une pause."""

        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client is None or not voice_client.is_paused():
            await interaction.response.send_message(
                embed=embeds.warning_embed("Aucune pause", "La musique n'est pas en pause."),
                ephemeral=True,
            )
            return

        if not self._check_control_permissions(interaction):
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Accès refusé",
                    "Tu dois disposer de la permission 'Gérer les messages' et être dans mon salon vocal.",
                ),
                ephemeral=True,
            )
            return

        voice_client.resume()
        await self._log(interaction.guild, f"▶️ Lecture relancée par {interaction.user.mention}.")
        await interaction.response.send_message("▶️ Lecture relancée.", ephemeral=True)

    async def _ensure_stream_url(self, track: Track) -> Optional[str]:
        """Garantit la présence d'une URL de flux valide pour la lecture."""

        if track.stream_url and "youtube.com/watch" not in track.stream_url:
            return track.stream_url

        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(None, lambda: ytdl.extract_info(track.webpage_url, download=False))
        except yt_dlp.utils.DownloadError:  # type: ignore[attr-defined]
            return None
        except Exception:  # noqa: BLE001
            return None

        if isinstance(info, dict) and info.get("entries"):
            info = next((entry for entry in info["entries"] if entry), None)
        if not isinstance(info, dict):
            return None

        track.stream_url = info.get("url")
        track.duration = track.duration or info.get("duration")
        return track.stream_url


async def setup(bot: commands.Bot) -> None:
    """Ajoute le cog musical au bot."""

    await bot.add_cog(Music(bot))
