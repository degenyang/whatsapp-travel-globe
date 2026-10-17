# WhatsApp Travel Globe 🌏

Count every trip you've ever taken using only your WhatsApp history, then see them on an interactive 3D globe.

![demo](demo/demo.gif)

*(Demo data: random cities, not real trips.)*

- **Globe:** a single `globe.html` built on [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) with free [OpenFreeMap](https://openfreemap.org) tiles. No API key, no server, no build step.
- **What it shows:**
  - great-circle flight arcs with animated "planes"
  - a pulsing home base, which can change over time (e.g. after a move)
  - year and overnight/day-trip filters with live stats
  - a ▶ Play mode that replays every trip in order
- **Pipeline:** a few small Python scripts plus a prompt you give to your AI agent to turn 5,000+ chats into a verified trip list.

> **Lazy mode:** give this repo to your AI agent (Claude Code, Codex, …) and say *"do this with my WhatsApp"*.

---

## Quick look

Open `globe.html` in a browser. It loads `data/trips.example.js`, the demo data.

## Make your own

### 1. Get all your chats out of WhatsApp

The in-app *Export Chat* only does one chat at a time and caps the number of messages, so read the phone's database instead.

**Android (no root needed)**
1. WhatsApp → Settings → Chats → Chat backup → turn on **End-to-end encrypted backup** and choose **use a 64-digit encryption key**. Save the key somewhere safe.
2. Run a backup, then copy `Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15` to your PC.
3. Decrypt it to `msgstore.db` with either:
   - [KnugiHK/WhatsApp-Chat-Exporter](https://github.com/KnugiHK/WhatsApp-Chat-Exporter): `pip install "whatsapp-chat-exporter[crypt15]"`
   - [ElDavoo/wa-crypt-tools](https://github.com/ElDavoo/wa-crypt-tools)
4. Write one text file per chat:
   ```bash
   # optional: WA_TZ_HOURS=1 for UTC+1 (default 0 = UTC), WA_LOCAL_CC=44 for contacts saved without a country code
   python scripts/wa_stream_export.py msgstore.db chats/ contacts.csv
   ```
   `contacts.csv` is a Google Contacts export. It's optional and turns phone numbers into names.

**iPhone:** make a local (Finder / Apple Devices) backup and run WhatsApp-Chat-Exporter in iOS mode (`-i`) with `--txt`. Any tool that gives you `DD/MM/YYYY, HH:MM - Sender: text` files works.

### 2. Keyword sweep

```bash
python scripts/extract.py chats/ travel/ --partner "Name of the chat with your travel partner"
```

This keeps only your own messages plus your partner chat, filters them for travel words in English, and writes `travel/yYYYY.txt`. Add words for your language in `extract.py`.

Keywords alone are noisy ("check in", "visa", news about someone else landing). Expect several times more hits than real trips. That's what step 3 is for.

### 3. Let AI agents verify every trip

Give your agent `prompts/verify_trips.md`, filled in with your paths, years and home base. Run several agents in parallel, for example one per 3 years. Each agent:
- reads the yearly files
- checks the raw chat around each date
- returns a table of trips with an evidence quote for each one

**Check the maths yourself.** Agents are good at judging trips and bad at adding up their own tables.

### 4. Put the trips on the globe

Copy `data/trips.example.js` to `data/trips.js` and fill it in:

```js
window.TRIPS = {
  title: "My Travels 2018–2026",
  subtitle: "home ★ London → Sydney (Aug 2023)",
  homes: { LON: "Home until 2023-08", SYD: "Home since 2023-08" },
  places: { LON: ["London", 51.5072, -0.1276], PAR: ["Paris", 48.8566, 2.3522] /* … */ },
  country: { LON: "UK", PAR: "FR" /* … */ },
  trips: [
    // start, end ("" = day trip), from, [stops…], note, "o" overnight | "d" day trip
    ["2019-04-05", "2019-04-08", "LON", ["PAR"], "City break", "o"],
  ],
};
```

`globe.html` uses `data/trips.js` when it exists and falls back to the demo otherwise. `data/trips.js` is git-ignored, so your real trips never get committed.

## Privacy

Your chat database is your whole life.
- Keep it on your own machine.
- Don't upload it to "WhatsApp analyzer" websites.
- Never commit `msgstore.db`, chat exports, contacts or your `trips.js`.

The `.gitignore` here blocks the usual file names, but check `git status` before every push anyway.

## Credits

- [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) (BSD-3-Clause)
- [OpenFreeMap](https://openfreemap.org) tiles, © OpenMapTiles, data © OpenStreetMap contributors
- [WhatsApp-Chat-Exporter](https://github.com/KnugiHK/WhatsApp-Chat-Exporter), [wa-crypt-tools](https://github.com/ElDavoo/wa-crypt-tools)

MIT licensed. See [LICENSE](LICENSE).
