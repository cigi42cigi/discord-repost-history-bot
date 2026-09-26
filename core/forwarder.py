"""Logika pro prepositlani jedne zpravy vcetne priloh (foto/video) pres webhook."""
from __future__ import annotations

import logging

import discord

from core.config import WEBHOOK_NAME

log = logging.getLogger("feverdream.forwarder")

# discord.py cache webhooku podle ID kanalu, aby se nemusel poporade
# dotazovat API pri kazde prepositlane zprave.
_webhook_cache: dict[int, discord.Webhook] = {}


async def get_or_create_webhook(channel: discord.TextChannel) -> discord.Webhook:
    cached = _webhook_cache.get(channel.id)
    if cached is not None:
        return cached

    webhooks = await channel.webhooks()
    webhook = discord.utils.get(webhooks, name=WEBHOOK_NAME)
    if webhook is None:
        webhook = await channel.create_webhook(name=WEBHOOK_NAME)

    _webhook_cache[channel.id] = webhook
    return webhook


def is_forwardable(message: discord.Message) -> bool:
    """Zprava se ma prepositlat, pokud ma text, embed nebo prilohu."""
    return bool(message.content or message.embeds or message.attachments)


async def forward_message(message: discord.Message, target_channel: discord.TextChannel) -> int:
    """Prepošle jednu zpravu (text, foto, video, embed) do ciloveho kanalu.

    Vraci pocet uspesne prepositlanych priloh (souboru).
    """
    webhook = await get_or_create_webhook(target_channel)

    files = []
    for attachment in message.attachments:
        try:
            files.append(await attachment.to_file())
        except discord.HTTPException:
            log.warning("Nepodarilo se stahnout prilohu %s ze zpravy %s", attachment.filename, message.id)

    try:
        await webhook.send(
            content=message.content or None,
            username=message.author.display_name[:80] or "FeverDream",
            avatar_url=message.author.display_avatar.url,
            embeds=message.embeds,
            files=files,
            allowed_mentions=discord.AllowedMentions.none(),
            thread=target_channel if isinstance(target_channel, discord.Thread) else discord.utils.MISSING,
        )
    except discord.HTTPException as exc:
        # Nejcastejsi pripad: prilohy jsou moc velke pro cilovy server (limit velikosti souboru).
        # Zkusime to poslat aspon bez priloh, aby se neztratil text zpravy.
        log.warning("Odeslani se souborem selhalo (%s), zkousim bez priloh", exc)
        if files:
            await webhook.send(
                content=(message.content or "") + "\n*(prilohy se nepodarilo prepositlat - jsou prilis velke)*",
                username=message.author.display_name[:80] or "FeverDream",
                avatar_url=message.author.display_avatar.url,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            raise

    return len(files)
