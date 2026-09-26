"""Prikazy pro spravu zivych propojeni kanalu (source -> target)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import FeverDreamBot


class LinkingCog(commands.Cog):
    def __init__(self, bot: "FeverDreamBot") -> None:
        self.bot = bot

    def _resolve_channel(self, channel_id: int) -> discord.TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    @app_commands.command(
        name="link-add",
        description="Zapne zive prepositlani novych zprav ze zdrojoveho kanalu do ciloveho.",
    )
    @app_commands.describe(
        source="Zdrojovy kanal (na tomto serveru), odkud se maji zpravy prepositlat.",
        target_channel_id="ID ciloveho kanalu (muze byt i na jinem serveru, kde je bot clenem).",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def link_add(
        self,
        interaction: discord.Interaction,
        source: discord.TextChannel,
        target_channel_id: str,
    ) -> None:
        try:
            target_id = int(target_channel_id.strip())
        except ValueError:
            await interaction.response.send_message("ID ciloveho kanalu musi byt cislo.", ephemeral=True)
            return

        target = self._resolve_channel(target_id)
        if target is None:
            await interaction.response.send_message(
                "Cilovy kanal nenalezen - bot v nem musi byt clenem serveru a mit pravo Manage Webhooks.",
                ephemeral=True,
            )
            return

        link = await self.bot.link_storage.add_link(
            source_channel_id=source.id,
            target_channel_id=target.id,
            source_guild_id=source.guild.id,
            target_guild_id=target.guild.id,
            created_by=interaction.user.id,
        )
        await interaction.response.send_message(
            f"Propojeni **{link.id}** vytvoreno: {source.mention} ({source.guild.name}) "
            f"-> #{target.name} ({target.guild.name}). Nove zpravy se budou prepositlat automaticky.",
        )

    @app_commands.command(
        name="link-remove",
        description="Vypne zive prepositlani ze zadaneho zdrojoveho kanalu.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def link_remove(self, interaction: discord.Interaction, source: discord.TextChannel) -> None:
        removed = await self.bot.link_storage.remove_link(source.id)
        if removed:
            await interaction.response.send_message(f"Propojeni ze {source.mention} zruseno.")
        else:
            await interaction.response.send_message(
                f"Pro {source.mention} zadne propojeni neexistuje.", ephemeral=True
            )

    @app_commands.command(name="link-list", description="Vypise aktivni propojeni kanalu pro tento server.")
    async def link_list(self, interaction: discord.Interaction) -> None:
        links = self.bot.link_storage.links_for_guild(interaction.guild_id)
        if not links:
            await interaction.response.send_message("Zadna propojeni nejsou aktivni.", ephemeral=True)
            return

        lines = []
        for link in links:
            source = self.bot.get_channel(link.source_channel_id)
            target = self.bot.get_channel(link.target_channel_id)
            source_name = source.mention if source else f"#{link.source_channel_id}"
            target_name = f"#{target.name}" if target else f"#{link.target_channel_id}"
            lines.append(f"`{link.id}` {source_name} -> {target_name}")

        await interaction.response.send_message("**Aktivni propojeni:**\n" + "\n".join(lines))

    @link_add.error
    @link_remove.error
    async def on_permission_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "K tomuto prikazu potrebujes opravneni **Manage Guild**.", ephemeral=True
            )
        else:
            raise error


async def setup(bot: "FeverDreamBot") -> None:
    await bot.add_cog(LinkingCog(bot))
