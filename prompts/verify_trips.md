# Prompt: verify trips from the extracted messages

Give this to your AI agent (Claude Code, Codex, …) after running `scripts/extract.py`.
Split the years across several agents running in parallel, e.g. one per 3 years.
Fill in the `<…>` parts first.

---

You are identifying the real trips I took, from my WhatsApp export. Read-only task.

**Files**
- Pre-filtered travel messages, one per year: `<out_dir>/y<YEAR>.txt`.
  Each line is `YYYY-MM-DD HH:MM [chat name] Speaker: text`, where "Me" = me and "Partner" = the person I travel with.
- The full raw chats are in `<chat_txt_dir>` (format `DD/MM/YYYY, HH:MM - Sender: text`, sender "You" = me).
  To read the context around a date, grep with a date prefix such as `^05/04/2019`. Never print a whole chat file.

**Your years:** `<e.g. 2018, 2019, 2020>`

**Home base:** `<e.g. London until 2023-08, then Sydney>`. A move is a relocation, not a trip. After the move, trips back to the old home DO count.

**Count a trip only when I travelled away from home myself**, either overnight or as a clear day trip abroad. Label day trips as day trips.

**Exclude:**
- plans that never happened
- other people's trips, including my partner travelling alone (list these separately)
- staycations (list these separately)
- jargon that only looks like travel (e.g. crypto "bridge" or "airdrop", news like "X just landed in Y")

**Business trips count.** Mark them as business.

**Verify every candidate** in the raw messages around its date. Look for "landed", "boarding", "I'm in X", "back home", hotel stays.

**Output**
1. A table with these columns:
   - start date
   - end date (approximate is fine)
   - destination(s)
   - with whom (if clear)
   - purpose
   - confidence (high / med / low)
   - one short evidence quote with its date
2. Possible but unconfirmed trips.
3. Partner-only trips.
4. Staycations.

Keep it concise. Then count the rows of your own table. Do not just estimate a total.
