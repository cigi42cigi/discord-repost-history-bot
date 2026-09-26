"""FeverDream - Discord bot pro prepositlani zprav mezi servery.

Spusteni: python bot.py  (viz docs.md pro plny navod)
"""
from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from core.config import DEV_GUILD_ID, DISCORD_TOKEN
from core.jobs import JobManager
from core.storage import LinkStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("feverdream")

INTENTS = discord.Intents.default()
INTENTS.message_content = True  # nutne pro cteni obsahu/priloh zprav
INTENTS.guilds = True


class FeverDreamBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!feverdream ", intents=INTENTS, help_command=None)
        self.link_storage = LinkStorage()
        self.job_manager = JobManager()

    async def setup_hook(self) -> None:
        for extension in ("cogs.linking", "cogs.repost", "cogs.broadcast"):
            await self.load_extension(extension)

        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Slash prikazy synchronizovany na vyvojovy server %s", DEV_GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Slash prikazy synchronizovany globalne")

    async def on_ready(self) -> None:
        log.info("Prihlasen jako %s (ID: %s)", self.user, self.user.id)
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name="/repost-history | /link-add"
        ))

    async def on_message(self, message: discord.Message) -> None:
        # Nikdy neresit vlastni zpravy nebo zpravy poslane pres nas relay webhook
        # (jinak by hrozila nekonecna smycka mezi propojenymi kanaly).
        if message.author == self.user or message.webhook_id is not None:
            return

        links = self.link_storage.get_targets_for_source(message.channel.id)
        for link in links:
            target = self.get_channel(link.target_channel_id)
            if target is None:
                log.warning("Cilovy kanal %s pro link %s neni dostupny", link.target_channel_id, link.id)
                continue
            from core.forwarder import forward_message, is_forwardable
            if not is_forwardable(message):
                continue
            try:
                await forward_message(message, target)
            except discord.HTTPException as exc:
                log.error("Zive prepositlani zpravy %s selhalo: %s", message.id, exc)

        await self.process_commands(message)


def main() -> None:
    bot = FeverDreamBot()
    asyncio.run(bot.start(DISCORD_TOKEN))


if __name__ == "__main__":
    main()
