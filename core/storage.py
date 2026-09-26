"""Jednoducha JSON perzistence pro propojeni kanalu (linky)."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LINKS_FILE = DATA_DIR / "links.json"


@dataclass
class ChannelLink:
    id: str
    source_channel_id: int
    target_channel_id: int
    source_guild_id: int
    target_guild_id: int
    created_by: int
    created_at: float


class LinkStorage:
    """Drzi seznam propojeni 'zdrojovy kanal -> cilovy kanal' pro zivy repost."""

    def __init__(self, path: Path = LINKS_FILE) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._links: dict[str, ChannelLink] = {}
        self._load()

    def _load(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._links = {}
            return
        raw = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        self._links = {
            link_id: ChannelLink(**data) for link_id, data in raw.items()
        }

    def _save(self) -> None:
        raw = {link_id: asdict(link) for link_id, link in self._links.items()}
        self._path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")

    async def add_link(
        self,
        *,
        source_channel_id: int,
        target_channel_id: int,
        source_guild_id: int,
        target_guild_id: int,
        created_by: int,
    ) -> ChannelLink:
        async with self._lock:
            link = ChannelLink(
                id=uuid.uuid4().hex[:8],
                source_channel_id=source_channel_id,
                target_channel_id=target_channel_id,
                source_guild_id=source_guild_id,
                target_guild_id=target_guild_id,
                created_by=created_by,
                created_at=time.time(),
            )
            self._links[link.id] = link
            self._save()
            return link

    async def remove_link(self, source_channel_id: int) -> bool:
        async with self._lock:
            to_remove = [
                link_id
                for link_id, link in self._links.items()
                if link.source_channel_id == source_channel_id
            ]
            for link_id in to_remove:
                del self._links[link_id]
            if to_remove:
                self._save()
            return bool(to_remove)

    def get_targets_for_source(self, source_channel_id: int) -> list[ChannelLink]:
        return [
            link for link in self._links.values()
            if link.source_channel_id == source_channel_id
        ]

    def all_links(self) -> list[ChannelLink]:
        return list(self._links.values())

    def links_for_guild(self, guild_id: int) -> list[ChannelLink]:
        return [
            link for link in self._links.values()
            if link.source_guild_id == guild_id or link.target_guild_id == guild_id
        ]
