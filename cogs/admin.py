"""Commandes d'administration avancées (config & reload)."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import config, embeds, logs as audit_logs


class Administration(commands.Cog):
    """Regroupe les outils de personnalisation et de maintenance du bot."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    config_group = app_commands.Group(
        name="config",
        description="Personnalise Creeper sans modifier le code.",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @config_group.command(name="channels", description="Change les salons utilisés par Creeper")
    @app_commands.describe(
        log_channel="Nouveau nom du salon de logs",
        welcome_channel="Nouveau nom du salon de bienvenue",
        music_channel="Nouveau nom du salon vocal musique",
    )
    async def config_channels(
        self,
        interaction: discord.Interaction,
        log_channel: str | None = None,
        welcome_channel: str | None = None,
        music_channel: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande n'est disponible que dans un serveur."),
                ephemeral=True,
            )
            return

        if not any([log_channel, welcome_channel, music_channel]):
            await interaction.response.send_message(
                embed=embeds.warning_embed("Aucun changement", "Indique au moins un salon à personnaliser."),
                ephemeral=True,
            )
            return

        guild = interaction.guild
        changes: list[str] = []
        warnings: list[str] = []

        if log_channel:
            previous = config.get_log_channel_name()
            config.set_log_channel_name(log_channel)
            target = discord.utils.get(guild.text_channels, name=previous) or discord.utils.get(
                guild.text_channels, name=log_channel
            )
            if target:
                try:
                    await target.edit(name=log_channel, reason=f"Changement demandé par {interaction.user}")
                except discord.Forbidden:
                    warnings.append("Permissions insuffisantes pour renommer le salon de logs.")
                except discord.HTTPException:
                    warnings.append("Erreur Discord lors du renommage du salon de logs.")
            else:
                warnings.append("Salon de logs introuvable. Il sera recréé automatiquement au prochain besoin.")
            changes.append(f"📚 Logs → **{log_channel}**")

        if welcome_channel:
            previous = config.get_welcome_channel_name()
            config.set_welcome_channel_name(welcome_channel)
            target = discord.utils.get(guild.text_channels, name=previous) or discord.utils.get(
                guild.text_channels, name=welcome_channel
            )
            if target:
                try:
                    await target.edit(name=welcome_channel, reason=f"Changement demandé par {interaction.user}")
                except discord.Forbidden:
                    warnings.append("Permissions insuffisantes pour renommer le salon de bienvenue.")
                except discord.HTTPException:
                    warnings.append("Erreur Discord lors du renommage du salon de bienvenue.")
            else:
                warnings.append("Salon de bienvenue introuvable. Pense à le créer manuellement ou relancer /setup.")
            changes.append(f"👋 Bienvenue → **{welcome_channel}**")

        if music_channel:
            previous = config.get_music_voice_channel_name()
            config.set_music_voice_channel_name(music_channel)
            target = discord.utils.get(guild.voice_channels, name=previous) or discord.utils.get(
                guild.voice_channels, name=music_channel
            )
            if target:
                try:
                    await target.edit(name=music_channel, reason=f"Changement demandé par {interaction.user}")
                except discord.Forbidden:
                    warnings.append("Permissions insuffisantes pour renommer le salon vocal musique.")
                except discord.HTTPException:
                    warnings.append("Erreur Discord lors du renommage du salon vocal musique.")
            else:
                warnings.append("Salon vocal musique introuvable. Pense à le créer manuellement ou relancer /setup.")
            changes.append(f"🎶 Musique → **{music_channel}**")

        description_lines = ["**Changements appliqués :**", *changes]
        if warnings:
            description_lines.append("\n**Attention :**")
            description_lines.extend(f"• {warning}" for warning in warnings)

        embed = embeds.success_embed(
            "Configuration mise à jour",
            "\n".join(description_lines),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await audit_logs.log_to_channel(
            guild,
            f"⚙️ Paramètres de salons ajustés par {interaction.user.mention} : {', '.join(changes)}",
        )

    @config_group.command(name="role_couleur", description="Modifie la couleur d'un rôle géré par Creeper")
    @app_commands.describe(
        role="Rôle à personnaliser",
        couleur="Couleur hexadécimale (#RRGGBB)",
        reinitialiser="Réinitialise la couleur par défaut",
    )
    async def config_role_colour(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        couleur: str | None = None,
        reinitialiser: bool = False,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        if role.name not in {r.name for r in config.get_roles()}:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Rôle non géré",
                    "Seuls les rôles provisionnés par Creeper peuvent être modifiés avec cette commande.",
                ),
                ephemeral=True,
            )
            return

        if reinitialiser:
            config.set_role_colour(role.name, None)
            target_colour = config.get_default_role_colour(role.name)
            try:
                await role.edit(colour=target_colour, reason=f"Réinitialisation demandée par {interaction.user}")
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=embeds.warning_embed(
                        "Permissions insuffisantes",
                        "Je ne peux pas modifier ce rôle, vérifie ma position dans la hiérarchie.",
                    ),
                    ephemeral=True,
                )
                return
            await interaction.response.send_message(
                embed=embeds.success_embed("Couleur réinitialisée", f"Le rôle {role.mention} utilise à nouveau sa couleur par défaut."),
                ephemeral=True,
            )
            await audit_logs.log_to_channel(
                interaction.guild,
                f"🎨 Couleur de {role.name} réinitialisée par {interaction.user.mention}.",
            )
            return

        if not couleur:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Couleur manquante", "Indique une couleur hexadécimale ou active la réinitialisation."),
                ephemeral=True,
            )
            return

        hex_value = couleur.strip().lstrip("#")
        if len(hex_value) != 6:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Format invalide", "Utilise un format hexadécimal du type #RRGGBB."),
                ephemeral=True,
            )
            return
        try:
            colour_value = int(hex_value, 16)
        except ValueError:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Format invalide", "Utilise un format hexadécimal du type #RRGGBB."),
                ephemeral=True,
            )
            return

        new_colour = discord.Colour(colour_value)
        try:
            await role.edit(colour=new_colour, reason=f"Personnalisation demandée par {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embeds.warning_embed(
                    "Permissions insuffisantes",
                    "Je ne peux pas modifier ce rôle, vérifie ma position dans la hiérarchie.",
                ),
                ephemeral=True,
            )
            return

        config.set_role_colour(role.name, new_colour)
        await interaction.response.send_message(
            embed=embeds.success_embed("Couleur mise à jour", f"Le rôle {role.mention} utilise désormais la couleur #{hex_value.upper()}."),
            ephemeral=True,
        )
        await audit_logs.log_to_channel(
            interaction.guild,
            f"🎨 Couleur de {role.name} définie sur #{hex_value.upper()} par {interaction.user.mention}.",
        )

    @config_group.command(name="welcome", description="Active ou désactive les messages d'accueil")
    @app_commands.describe(actif="Choisis si le message de bienvenue est envoyé")
    async def config_welcome(self, interaction: discord.Interaction, actif: bool) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        config.set_welcome_messages(actif)
        status = "activés" if actif else "désactivés"
        await interaction.response.send_message(
            embed=embeds.success_embed("Mises à jour", f"Les messages de bienvenue sont désormais {status}."),
            ephemeral=True,
        )
        await audit_logs.log_to_channel(
            interaction.guild,
            f"👋 Messages de bienvenue {status} par {interaction.user.mention}.",
        )

    @app_commands.command(name="reload", description="Recharge un ou plusieurs cogs du bot.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(module="Nom complet du module à recharger (laisser vide pour tout).")
    async def reload(self, interaction: discord.Interaction, module: str | None = None) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=embeds.warning_embed("Serveur requis", "Cette commande doit être utilisée dans un serveur."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        results: list[str] = []
        targets: list[str]
        if module:
            targets = [module]
        else:
            targets = list(self.bot.extensions.keys())

        failures: list[str] = []
        for target in targets:
            try:
                await self.bot.reload_extension(target)
                results.append(f"✅ {target}")
            except commands.ExtensionError as error:
                failures.append(f"⚠️ {target} → {error}")

        description_lines = []
        if results:
            description_lines.append("**Extensions rechargées :**")
            description_lines.extend(f"• {line}" for line in results)
        if failures:
            description_lines.append("\n**Échecs :**")
            description_lines.extend(f"• {line}" for line in failures)
        if not description_lines:
            description_lines.append("Aucune extension correspondante n'a été trouvée.")

        await interaction.followup.send(
            embed=embeds.build_embed("🔄 Rechargement terminé", "\n".join(description_lines)),
            ephemeral=True,
        )
        log_summary = results + failures
        if not log_summary:
            log_summary = ["aucune extension"]
        await audit_logs.log_to_channel(
            interaction.guild,
            f"🔄 Commande /reload exécutée par {interaction.user.mention}: {', '.join(log_summary)}",
        )

    @reload.autocomplete("module")
    async def reload_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=name, value=name)
            for name in self.bot.extensions.keys()
            if current.lower() in name.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    """Ajoute les commandes d'administration au bot."""

    await bot.add_cog(Administration(bot))
