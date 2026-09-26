"""Sledovani bezicich uloh (repost historie kanalu) pro /repost-status a /repost-stop."""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class RepostJob:
    id: str
    guild_id: int
    started_by: int
    source_channel_id: int
    target_channel_id: int
    limit: int | None
    status: str = "running"  # running | done | cancelled | error
    processed_messages: int = 0
    forwarded_files: int = 0
    skipped_messages: int = 0
    error_message: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    cancel_requested: bool = False
    task: "asyncio.Task | None" = field(default=None, repr=False, compare=False)

    @property
    def duration_seconds(self) -> float:
        end = self.finished_at or time.time()
        return end - self.started_at


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, RepostJob] = {}

    def create(
        self,
        *,
        guild_id: int,
        started_by: int,
        source_channel_id: int,
        target_channel_id: int,
        limit: int | None,
    ) -> RepostJob:
        job = RepostJob(
            id=uuid.uuid4().hex[:6],
            guild_id=guild_id,
            started_by=started_by,
            source_channel_id=source_channel_id,
            target_channel_id=target_channel_id,
            limit=limit,
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> RepostJob | None:
        return self._jobs.get(job_id)

    def request_cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.status != "running":
            return False
        job.cancel_requested = True
        return True

    def running_jobs_for_guild(self, guild_id: int) -> list[RepostJob]:
        return [
            job for job in self._jobs.values()
            if job.guild_id == guild_id and job.status == "running"
        ]

    def all_jobs_for_guild(self, guild_id: int) -> list[RepostJob]:
        return [job for job in self._jobs.values() if job.guild_id == guild_id]
