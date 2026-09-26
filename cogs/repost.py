"""Prikazy pro hromadny repost historie kanalu + servisni (status) zpravy."""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.config import PROGRESS_UPDATE_EVERY, SEND_DELAY_SECONDS
from core.forwarder import forward_message, is_forwardable
from core.jobs import RepostJob

if TYPE_CHECKING:
    from bot import FeverDreamBot


def _progress_embed(job: RepostJob, *, title: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Zpracovano zprav", value=str(job.processed_messages), inline=True)
    embed.add_field(name="Prepositlano souboru", value=str(job.forwarded_files), inline=True)
    embed.add_field(name="Preskoceno", value=str(job.skipped_messages), inline=True)
    embed.add_field(name="Cas beh", value=f"{job.duration_seconds:.0f} s", inline=True)
    embed.set_footer(text=f"Job ID: {job.id}")
    return embed


class RepostCog(commands.Cog):
    def __init__(self, bot: "FeverDreamBot") -> None:
        self.bot = bot

    def _resolve_channel(self, channel_id: int) -> discord.TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _run_history_job(
        self,
        job: RepostJob,
        source: discord.TextChannel,
        target: discord.TextChannel,
        status_message: discord.Message,
    ) -> None:
        try:
            async for message in source.history(limit=job.limit, oldest_first=True):
                if job.cancel_requested:
                    job.status = "cancelled"
                    break

                if is_forwardable(message):
                    try:
                        job.forwarded_files += await forward_message(message, target)
                    except discord.HTTPException:
                        job.skipped_messages += 1
                else:
                    job.skipped_messages += 1

                job.processed_messages += 1

                if job.processed_messages % PROGRESS_UPDATE_EVERY == 0:
                    try:
                        await status_message.edit(
                            embed=_progress_embed(job, title="⏳ Repost probiha...", color=discord.Color.blurple())
                        )
                    except discord.HTTPException:
                        pass

                await asyncio.sleep(SEND_DELAY_SECONDS)
            else:
                job.status = "done"
        except Exception as exc:  # noqa: BLE001 - chceme zachytit a nahlasit jakoukoliv chybu joby
            job.status = "error"
            job.error_message = str(exc)
        finally:
            job.finished_at = time.time()
            if job.status == "done":
                title, color = "✅ Repost dokoncen - prace je hotova!", discord.Color.green()
            elif job.status == "cancelled":
                title, color = "🛑 Repost zrusen", discord.Color.orange()
            else:
                title, color = f"❌ Repost skoncil chybou: {job.error_message}", discord.Color.red()
            try:
                await status_message.edit(embed=_progress_embed(job, title=title, color=color))
            except discord.HTTPException:
                pass

    @app_commands.command(
        name="repost-history",
        description="Prepošle celou (nebo omezenou) historii zprav ze zdrojoveho kanalu do ciloveho.",
    )
    @app_commands.describe(
        source="Zdrojovy kanal (na tomto serveru), jehoz historii chces prepositlat.",
        target_channel_id="ID ciloveho kanalu (muze byt i na jinem serveru, kde je bot clenem).",
        limit="Kolik nejnovejsich zprav prepositlat. Necháno prazdne = uplne vsechny zpravy z kanalu.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def repost_history(
        self,
        interaction: discord.Interaction,
        source: discord.TextChannel,
        target_channel_id: str,
        limit: app_commands.Range[int, 1, 1_000_000] | None = None,
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

        await interaction.response.defer(thinking=True)

        job = self.bot.job_manager.create(
            guild_id=interaction.guild_id,
            started_by=interaction.user.id,
            source_channel_id=source.id,
            target_channel_id=target.id,
            limit=limit,
        )

        status_message = await interaction.followup.send(
            embed=_progress_embed(job, title="⏳ Repost zahajen...", color=discord.Color.blurple()),
            wait=True,
        )

        job.task = asyncio.create_task(self._run_history_job(job, source, target, status_message))

    @app_commands.command(name="repost-status", description="Zobrazi stav bezicich/nedavnych reposting uloh na tomto serveru.")
    async def repost_status(self, interaction: discord.Interaction) -> None:
        jobs = self.bot.job_manager.all_jobs_for_guild(interaction.guild_id)
        if not jobs:
            await interaction.response.send_message("Zatim tu nebezela zadna reposting uloha.", ephemeral=True)
            return

        lines = []
        for job in jobs[-10:]:
            lines.append(
                f"`{job.id}` [{job.status}] {job.processed_messages} zprav, "
                f"{job.forwarded_files} souboru (zdroj <#{job.source_channel_id}> -> cil <#{job.target_channel_id}>)"
            )
        await interaction.response.send_message("**Reposting ulohy:**\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(name="repost-stop", description="Zastavi bezici reposting ulohu podle jejiho ID.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def repost_stop(self, interaction: discord.Interaction, job_id: str) -> None:
        ok = self.bot.job_manager.request_cancel(job_id)
        if ok:
            await interaction.response.send_message(f"Uloha `{job_id}` bude zastavena po dokonceni aktualni zpravy.")
        else:
            await interaction.response.send_message(f"Uloha `{job_id}` nebezi nebo neexistuje.", ephemeral=True)

    @repost_history.error
    @repost_stop.error
    async def on_permission_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "K tomuto prikazu potrebujes opravneni **Manage Guild**.", ephemeral=True
            )
        else:
            raise error


async def setup(bot: "FeverDreamBot") -> None:
    await bot.add_cog(RepostCog(bot))
