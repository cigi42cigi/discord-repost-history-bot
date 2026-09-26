🇬🇧 English | 🇨🇿 [Přečíst česky](README.cs.md)

# FeverDream

A Discord bot for reposting messages (text, photos, videos and other
attachments) from one Discord server to another, sending bulk messages, and
reporting its own progress via status messages.

This bot was originaly created for copy pasted whole channel from one dc server to anther.

## Contents

1. [Language & technology choice](#1-language--technology-choice)
2. [Architecture](#2-architecture)
3. [How the bot works](#3-how-the-bot-works)
4. [Commands](#4-commands)
5. [Installation & running the bot](#5-installation--running-the-bot)
6. [Setting up the bot on Discord](#6-setting-up-the-bot-on-discord)
7. [Limitations & notes](#7-limitations--notes)

---

## 1. Language & technology choice

**Python 3.11+** with the **discord.py** library was chosen as the
implementation language.

Reasons:

- discord.py is the most mature and best-documented library for writing
  Discord bots — it natively supports slash commands, webhooks,
  attachments, rate-limit handling and asynchronous processing (asyncio),
  which is essential for a bot that has to bulk-repost hundreds or
  thousands of messages with attachments.
- Python allows for fast development and easy maintenance, even for people
  who aren't experts in low-level network programming.
- Alternatives (Node.js + discord.js, Java + JDA) are comparably capable,
  but Python/discord.py has the simplest API specifically for working with
  attachments (`Attachment.to_file()`) and webhooks, which this bot relies
  on as its core technique for preserving the original author's name and
  avatar when reposting.

## 2. Architecture

```
reposting_bot/
├── bot.py                # entry point, bot initialization, on_message listener
├── core/
│   ├── config.py         # loads configuration from .env
│   ├── storage.py        # JSON persistence for channel links
│   ├── forwarder.py      # logic for forwarding a single message (webhook, attachments)
│   └── jobs.py           # tracking of running repost jobs (history reposting)
├── cogs/
│   ├── linking.py        # /link-add, /link-remove, /link-list
│   ├── repost.py         # /repost-history, /repost-status, /repost-stop
│   └── broadcast.py      # /broadcast
├── data/
│   └── links.json        # (created at runtime) stored channel links
├── requirements.txt
├── .env.example
├── README.md              # this English documentation (main)
└── README.cs.md           # Czech documentation
```

**Key components:**

- **`core/forwarder.py`** — the forwarding core. For the target channel it
  finds or creates a webhook named `FeverDream Relay` and sends the message
  through it so that it appears in the target channel as if it had been
  written by the original author (same name and avatar). Attachments
  (photos, videos, files) are downloaded and re-uploaded
  (`Attachment.to_file()`), so they keep working even after the original
  message is gone.
- **`core/storage.py`** — persistent "source channel → target channel"
  links for *live* forwarding of new messages. Stored in `data/links.json`,
  so links survive a bot restart.
- **`core/jobs.py`** — tracks running bulk history-repost jobs (progress,
  file count, cancellation).
- **`bot.py`** — listens for `on_message`. If a message comes from a
  channel configured as the source of a link, it is immediately forwarded
  to the target channel. Messages sent through the bot's own relay webhook
  are ignored, to avoid an infinite loop.

## 3. How the bot works

The bot distinguishes between two forwarding modes:

### a) Live forwarding (link)

An administrator sets up a link once with `/link-add`, between a source
channel (on the current server) and a target channel (on any server the
bot is also a member of). From that point on, the bot automatically
forwards **every new** message (text, photo, video, attachment) from the
source to the target, with no further action needed.

### b) Bulk history repost (repost-history)

With `/repost-history`, the bot walks through the **entire existing
history** of a given channel (or only the last N messages, if a limit is
given) and reposts it into the target channel in the same order it was
originally written (oldest first). While running, the bot continuously
updates its own "status" message with the current number of processed
messages and forwarded files, and once finished it updates that message
into a final report: **"Repost finished — the job is done!"** along with a
summary (message count, file count, duration). The job can be stopped at
any time with `/repost-stop`.

### c) Bulk messages (broadcast)

With `/broadcast` you can send **the same message** (optionally with one
attachment) to any number of channels at once — e.g. an announcement
posted to multiple servers/channels simultaneously. Once done, the bot
sends a status summary (how many channels succeeded/failed).

Between individual sends, the bot waits a short delay (`SEND_DELAY_SECONDS`
in `core/config.py`) so it doesn't run into Discord rate limits when
sending a large number of messages or attachments.

## 4. Commands

All commands are implemented as **slash commands** (`/...`).
Commands marked with 🔒 require the **Manage Guild** permission.

| Command | Description |
|---|---|
| 🔒 `/link-add source:#channel target_channel_id:ID` | Enables live forwarding of new messages from the source channel to the target channel (even on a different server). |
| 🔒 `/link-remove source:#channel` | Disables live forwarding for the given source channel. |
| `/link-list` | Lists all active links for the current server. |
| 🔒 `/repost-history source:#channel target_channel_id:ID [limit]` | Reposts message history (all, or the last `limit` messages) into the target channel. Shows live and final status updates. |
| `/repost-status` | Shows the status (running/finished) of repost jobs on the server. |
| 🔒 `/repost-stop job_id:ID` | Stops a running repost job. |
| 🔒 `/broadcast message:text channel_ids:"id1,id2,..." [attachment]` | Sends a bulk message (optionally with an attachment) to multiple channels at once. |

**Note on `target_channel_id`:** Discord's "channel"-type slash command
parameters only allow picking a channel from the current server. Since the
bot needs to forward **between servers**, the target channel is given as a
numeric ID instead (Developer Mode → right-click the channel → "Copy
Channel ID"). The bot must be a member of the target server with the
`Manage Webhooks` and `Send Messages` permissions.

## 5. Installation & running the bot

### Requirements

- Python 3.11 or newer
- A developer account on the [Discord Developer
  Portal](https://discord.com/developers/applications)

### Steps

1. **Create an application and a bot** on the Discord Developer Portal
   (see section 6 below) and get its **Bot Token**.

2. **Clone/copy the project** and open a terminal in the `reposting_bot`
   folder.

3. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Set up configuration** — copy `.env.example` to `.env` and fill in the
   token:

   ```bash
   copy .env.example .env
   ```

   Open `.env` and set:

   ```
   DISCORD_TOKEN=your-bot-token
   DEV_GUILD_ID=
   ```

   `DEV_GUILD_ID` is an optional server ID used to sync slash commands
   instantly during development (otherwise a global sync can take up to
   about an hour to propagate).

5. **Run the bot:**

   ```bash
   python bot.py
   ```

   The console should show `Logged in as FeverDream#...`.

6. **Invite the bot** to the servers where it should forward messages (see
   section 6) — the bot must be a member of **both** servers (source and
   target).

## 6. Setting up the bot on Discord

1. Go to <https://discord.com/developers/applications> → **New
   Application** → name it `FeverDream`.
2. In the **Bot** section, click **Reset Token** and copy the token into
   `.env` (`DISCORD_TOKEN`).
3. In the same **Bot** section, enable the **Privileged Gateway Intents**:
   - `MESSAGE CONTENT INTENT` (required to read message text and
     attachments).
4. In **OAuth2 → URL Generator**, check:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Manage Webhooks`, `Read Message
     History`, `View Channels`, `Attach Files`, `Embed Links`
5. Open the generated URL in a browser and invite the bot to **both the
   source and target server**.
6. On both servers, grant the bot access to the channels it needs to
   forward between (double-check that no channel-specific permission
   overwrite denies it `View Channel` / `Read Message History`).

## 7. Limitations & notes

- Discord enforces an attachment size limit depending on the server's
  boost level (typically 25 MB, more for boosted servers). If an
  attachment doesn't fit in the target channel, the bot sends the message
  text without it and adds a note that the attachment was too large.
- Both live forwarding and bulk history repost send messages under the
  original author's name and avatar via a webhook — so it's technically a
  copy, not a true Discord "forward", but it visually and content-wise
  matches the original.
- Channel links (`/link-add`) are stored in `data/links.json` and survive
  a bot restart. Running repost jobs (`/repost-history`) are **not**
  resumed after a restart — they need to be started again.
- For large channels (thousands of messages), `/repost-history` can take a
  while to finish due to the delay between messages (protection against
  Discord rate limits).
