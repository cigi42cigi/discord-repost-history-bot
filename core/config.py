"""Nacteni konfigurace bota z prostredi (.env)."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
DEV_GUILD_ID: str | None = os.getenv("DEV_GUILD_ID") or None

# Kolik zprav zpracovat mezi jednotlivymi progress-update hlaskami.
PROGRESS_UPDATE_EVERY = 25

# Pauza mezi odeslanim jednotlivych zprav pri hromadnem reposti/broadcastu,
# aby bot nenarazil na Discord rate limity.
SEND_DELAY_SECONDS = 0.8

# Nazev webhooku, ktery bot pouziva k prepositlani zprav pod puvodnim jmenem autora.
WEBHOOK_NAME = "FeverDream Relay"

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN neni nastaveny. Zkopiruj .env.example do .env a vlož token bota."
    )
