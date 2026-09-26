🇬🇧 [Read this in English](README.md) | 🇨🇿 Čeština

# FeverDream

Discord bot pro přeposílání zpráv (textu, fotek, videí a příloh) z jednoho
Discord serveru na druhý, hromadné rozesílání zpráv a servisní hlášení o
průběhu práce.

Tento bot byl vytvořen za účelem kopy-pastnout celý jeden discord kanál do druhého na jiném serveru.


## Obsah

1. [Volba jazyka a technologií](#1-volba-jazyka-a-technologií)
2. [Architektura](#2-architektura)
3. [Jak bot funguje](#3-jak-bot-funguje)
4. [Příkazy](#4-příkazy)
5. [Instalace a spuštění](#5-instalace-a-spuštění)
6. [Nastavení bota na Discordu](#6-nastavení-bota-na-discordu)
7. [Omezení a poznámky](#7-omezení-a-poznámky)

---

## 1. Volba jazyka a technologií

Jako implementační jazyk byl zvolen **Python 3.11+** s knihovnou **discord.py**.

Důvody:

- Discord.py je nejvyzrálejší a nejlépe zdokumentovaná knihovna pro psaní
  Discord botů – nativně podporuje slash příkazy, webhooky, přílohy,
  rate-limit handling a asynchronní zpracování (asyncio), což je pro bota,
  který má hromadně přeposílat stovky až tisíce zpráv s přílohami, klíčové.
- Python umožňuje rychlý vývoj a snadnou údržbu i pro lidi, kteří nejsou
  odborníci na nízkoúrovňové síťové programování.
- Alternativy (Node.js + discord.js, Java + JDA) jsou srovnatelně schopné,
  ale Python/discord.py má nejjednodušší API právě pro práci s přílohami
  (`Attachment.to_file()`) a webhooky, což tento bot využívá jako klíčovou
  techniku pro zachování jména a avataru původního autora při přeposílání.

## 2. Architektura

```
reposting_bot/
├── bot.py                # vstupní bod, inicializace bota, on_message listener
├── core/
│   ├── config.py         # načtení konfigurace z .env
│   ├── storage.py        # JSON perzistence propojení kanálů (linky)
│   ├── forwarder.py      # logika přeposlání jedné zprávy (webhook, přílohy)
│   └── jobs.py           # sledování běžících reposting úloh (historie)
├── cogs/
│   ├── linking.py        # /link-add, /link-remove, /link-list
│   ├── repost.py         # /repost-history, /repost-status, /repost-stop
│   └── broadcast.py      # /broadcast
├── data/
│   └── links.json        # (vzniká za běhu) uložená propojení kanálů
├── requirements.txt
├── .env.example
├── README.md              # anglická dokumentace (hlavní)
└── README.cs.md           # tato česká dokumentace
```

**Klíčové komponenty:**

- **`core/forwarder.py`** – jádro přeposílání. Pro cílový kanál si najde
  nebo vytvoří webhook nazvaný `FeverDream Relay` a přes něj odešle zprávu
  tak, aby v cílovém kanálu vypadala, jako by ji napsal původní autor
  (stejné jméno a avatar). Přílohy (fotky, videa, soubory) se stáhnou a
  znovu nahrají (`Attachment.to_file()`), takže fungují i poté, co
  originální zpráva zanikne.
- **`core/storage.py`** – trvalé propojení „zdrojový kanál → cílový kanál"
  pro *živé* přeposílání nových zpráv. Ukládá se do `data/links.json`, takže
  propojení přežijí restart bota.
- **`core/jobs.py`** – evidence běžících úloh hromadného přeposlání historie
  kanálu (progress, počet souborů, možnost zrušení).
- **`bot.py`** – naslouchá `on_message`. Pokud zpráva přišla z kanálu, který
  je nastavený jako zdroj nějakého propojení, ihned se přepošle do cílového
  kanálu. Zprávy odeslané přes vlastní relay webhook se ignorují, aby
  nevznikla nekonečná smyčka.

## 3. Jak bot funguje

Bot rozlišuje dva režimy přeposílání:

### a) Živé přeposílání (link)

Administrátor jednou nastaví propojení příkazem `/link-add` mezi zdrojovým
kanálem (na aktuálním serveru) a cílovým kanálem (na libovolném serveru, kde
je bot také členem). Od té chvíle bot automaticky přeposílá **každou novou**
zprávu (text, foto, video, přílohu) ze zdroje do cíle bez dalšího zásahu.

### b) Hromadný přepošt historie (repost-history)

Příkazem `/repost-history` bot projde **celou dosavadní historii** zadaného
kanálu (nebo jen posledních N zpráv, pokud je zadán limit) a postupně ji
přepošle do cílového kanálu ve stejném pořadí, v jakém byla napsána
(od nejstarší po nejnovější). Během běhu bot průběžně upravuje svou
"servisní" zprávu s aktuálním počtem zpracovaných zpráv a přeposlaných
souborů, a po dokončení ji upraví na finální hlášení **"Repost dokončen –
práce je hotova!"** spolu se souhrnem (počet zpráv, počet souborů, doba
běhu). Úlohu lze kdykoliv zastavit příkazem `/repost-stop`.

### c) Hromadné zprávy (broadcast)

Příkazem `/broadcast` lze poslat **stejnou zprávu** (volitelně i s jednou
přílohou) do libovolného počtu kanálů najednou – např. oznámení na více
serverů/kanálů současně. Po dokončení bot pošle servisní shrnutí (kolik
kanálů se podařilo/nepodařilo obeslat).

Mezi jednotlivými odesláními bot čeká krátkou prodlevu (`SEND_DELAY_SECONDS`
v `core/config.py`), aby nenarazil na Discord rate limity při větším počtu
zpráv nebo příloh.

## 4. Příkazy

Všechny příkazy jsou implementované jako **slash příkazy** (`/...`).
Příkazy označené 🔒 vyžadují oprávnění **Manage Guild** (Spravovat server).

| Příkaz | Popis |
|---|---|
| 🔒 `/link-add source:#kanal target_channel_id:ID` | Zapne živé přeposílání nových zpráv ze zdrojového kanálu do cílového (i na jiném serveru). |
| 🔒 `/link-remove source:#kanal` | Zruší živé přeposílání pro daný zdrojový kanál. |
| `/link-list` | Vypíše všechna aktivní propojení pro aktuální server. |
| 🔒 `/repost-history source:#kanal target_channel_id:ID [limit]` | Přepošle historii zpráv (vše, nebo posledních `limit`) do cílového kanálu. Zobrazuje průběžný a finální servisní stav. |
| `/repost-status` | Zobrazí stav (běžící/dokončené) reposting úloh na serveru. |
| 🔒 `/repost-stop job_id:ID` | Zastaví běžící reposting úlohu. |
| 🔒 `/broadcast message:text channel_ids:"id1,id2,..." [attachment]` | Odešle hromadnou zprávu (volitelně s přílohou) do více kanálů najednou. |

**Poznámka k `target_channel_id`:** Discord u parametrů typu "kanál" ve
slash příkazech dovoluje vybrat jen kanál z aktuálního serveru. Protože bot
má přeposílat **mezi servery**, cílový kanál se zadává jako číselné ID
(Developer Mode → pravé tlačítko na kanál → „Copy Channel ID"). Bot musí být
členem cílového serveru s právy `Manage Webhooks` a `Send Messages`.

## 5. Instalace a spuštění

### Požadavky

- Python 3.11 nebo novější
- Účet vývojáře na [Discord Developer Portal](https://discord.com/developers/applications)

### Postup

1. **Vytvoř si aplikaci a bota** na Discord Developer Portálu (viz kapitola
   6 níže) a získej **Bot Token**.

2. **Naklonuj/zkopíruj projekt** a otevři terminál ve složce `reposting_bot`.

3. **Vytvoř virtuální prostředí a nainstaluj závislosti:**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Nastav konfiguraci** – zkopíruj `.env.example` do `.env` a vyplň token:

   ```bash
   copy .env.example .env
   ```

   Otevři `.env` a nastav:

   ```
   DISCORD_TOKEN=tvuj-bot-token
   DEV_GUILD_ID=
   ```

   `DEV_GUILD_ID` je volitelné ID serveru pro okamžitou synchronizaci slash
   příkazů během vývoje (jinak se globální synchronizace může projevit
   se zpožděním až cca hodinu).

5. **Spusť bota:**

   ```bash
   python bot.py
   ```

   V konzoli by se mělo objevit hlášení `Přihlásen jako FeverDream#...`.

6. **Pozvi bota na servery**, kde má přeposílat zprávy (viz kapitola 6) –
   bot musí být členem **obou** serverů (zdrojového i cílového).

## 6. Nastavení bota na Discordu

1. Jdi na <https://discord.com/developers/applications> → **New
   Application** → pojmenuj ji `FeverDream`.
2. V sekci **Bot** klikni na **Reset Token** a token zkopíruj do `.env`
   (`DISCORD_TOKEN`).
3. Ve stejné sekci **Bot** zapni **Privileged Gateway Intents**:
   - `MESSAGE CONTENT INTENT` (nutné pro čtení textu a příloh zpráv).
4. V sekci **OAuth2 → URL Generator** zaškrtni:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Manage Webhooks`, `Read Message
     History`, `View Channels`, `Attach Files`, `Embed Links`
5. Vygenerovaný odkaz otevři v prohlížeči a bota pozvi na **zdrojový i
   cílový server**.
6. Na obou serverech uděl botovi přístup ke kanálům, mezi kterými má
   přeposílat (zkontroluj, že žádné channel-specific přepsání oprávnění
   botovi nezakazuje `View Channel` / `Read Message History`).

## 7. Omezení a poznámky

- Discord má limit velikosti přílohy podle úrovně boostu serveru (běžně
  25 MB, boostnuté servery víc). Pokud se příloha nevejde do cílového
  kanálu, bot text zprávy pošle bez ní a doplní poznámku, že příloha byla
  příliš velká.
- Živé přeposílání i hromadný repost historie posílají zprávy pod jménem a
  avatarem původního autora pomocí webhooku – jde tedy o kopii, ne o pravé
  přeposlání (forward) v discordím slova smyslu, ale vizuálně a obsahově
  odpovídá originálu.
- Propojení kanálů (`/link-add`) se ukládají do `data/links.json` a přežijí
  restart bota. Běžící reposting úlohy (`/repost-history`) se po restartu
  bota neobnovují – je potřeba je spustit znovu.
- Pro velké kanály (tisíce zpráv) může `/repost-history` běžet delší dobu
  kvůli prodlevě mezi zprávami (ochrana proti rate limitům Discordu).
