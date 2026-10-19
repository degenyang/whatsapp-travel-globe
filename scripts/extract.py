"""Pull travel-related messages out of exported WhatsApp chats, one file per year.

Usage:
    python scripts/extract.py <chat_txt_dir> <out_dir> [--partner "Chat name"] [--me You] [--date-order dmy|mdy]

Reads every *.txt in <chat_txt_dir>. Understands the common WhatsApp export formats:
  Android  "DD/MM/YYYY, HH:MM - Sender: text"   (also 12-hour "h:mm pm")
  iPhone   "[DD/MM/YYYY, HH:MM:SS] Sender: text"
  US       "M/D/YY, h:mm AM - Sender: text"
Lines that don't start with a date belong to the message above (multi-line messages).
Day/month order is guessed per file (a 13+ in the first or second field decides; day-first
otherwise). Force it with --date-order.

Keeps:
  * your own messages (sender == --me; "You" on Android, your own name on iPhone, repeat
    --me for both) that match a travel keyword
  * every matching message in the --partner chat (the person you travel with)
Writes <out_dir>/yYYYY.txt with lines "YYYY-MM-DD HH:MM [chat] Speaker: text".
Those files are what you hand to your AI agent (see prompts/verify_trips.md).
"""
import argparse, collections, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("chat_dir")
ap.add_argument("out_dir")
ap.add_argument("--partner", default=None, help="chat name (file name before '__') of your travel partner")
ap.add_argument("--me", action="append", help='your sender name; repeat for several (default "You")')
ap.add_argument("--date-order", choices=["dmy", "mdy"], default=None, help="default: guess per file")
a = ap.parse_args()
me = set(a.me or ["You"])

# optional "[", date, ", ", time (optional seconds, optional am/pm), then "] " or " - ", sender, ": ", text
line_re = re.compile(
    r"^\[?(\d{1,2})[./-](\d{1,2})[./-](\d{2,4}),? (\d{1,2}):(\d{2})(?::\d{2})?(?:\s?([AaPp])\.?\s?[Mm]\.?)?(?:\] | - )([^:]+?): (.*)$"
)
# English travel words. Add words in your own language before the closing ")".
travel = re.compile(
    r"(landed|just arrived|arrived (at|in)|touch(ed)? ?down|boarding|at (the )?airport|airport (now|already)|"
    r"\bi'?m in |\bi am in |currently in |\btravell?ing\b|on (a |my )?(trip|holiday|vacation)|holiday|vacation|"
    r"trip\b|fly(ing)? (to|back)|flight (to|back|home|is|delayed)|my flight|back (to|in) [a-z]+|jet ?lag|"
    r"hotel|checked in|check ?in (at|to)|check ?out|ferry|roaming|e-?sim|luggage|passport|airbnb|resort|"
    r"staycation|honeymoon|booked (the )?(flight|ticket|hotel)|plane)",
    re.I,
)
# iPhone exports mark some lines with invisible direction marks; newer phones put a narrow no-break space before AM/PM
INVISIBLE = dict.fromkeys(map(ord, "‎‏﻿"), None)


def messages(path):
    """Yield [d1, d2, year, hour, minute, ampm, sender, text, first_line] per message, continuation lines joined."""
    msg = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            ln = ln.translate(INVISIBLE).replace(" ", " ").replace(" ", " ").rstrip("\r\n")
            m = line_re.match(ln)
            if m:
                if msg:
                    yield msg
                msg = list(m.groups()) + [m.group(8)]
            elif msg and ln.strip():
                msg[7] += " " + ln.strip()
    if msg:
        yield msg


def date_order(msgs):
    if a.date_order:
        return a.date_order
    if any(int(m[0]) > 12 for m in msgs):
        return "dmy"
    if any(int(m[1]) > 12 for m in msgs):
        return "mdy"
    return "dmy"


out = collections.defaultdict(list)
for fn in sorted(os.listdir(a.chat_dir)):
    if not fn.endswith(".txt"):
        continue
    chat = fn.rsplit("__", 1)[0]
    partner = a.partner is not None and chat == a.partner
    msgs = list(messages(os.path.join(a.chat_dir, fn)))
    order = date_order(msgs)
    for d1, d2, yy, hh, mi, ampm, who, txt, first in msgs:
        if not (who in me or partner):
            continue
        if len(first) > 220 or "http" in first:  # skip forwards and links
            continue
        if len(txt) > 300:
            txt = txt[:300] + " …"
        if not travel.search(txt):
            continue
        dd, mm = (d1, d2) if order == "dmy" else (d2, d1)
        if not (1 <= int(mm) <= 12 and 1 <= int(dd) <= 31):
            continue  # this line doesn't fit the file's date order
        yy = yy if len(yy) == 4 else "20" + yy
        h = int(hh)
        if ampm:
            h = h % 12 + (12 if ampm in "Pp" else 0)
        w = "Me" if who in me else "Partner"
        out[yy].append(f"{yy}-{int(mm):02d}-{int(dd):02d} {h:02d}:{mi} [{chat[:20]}] {w}: {txt.strip()}")
os.makedirs(a.out_dir, exist_ok=True)
for y, rows in sorted(out.items()):
    rows.sort()
    with open(os.path.join(a.out_dir, f"y{y}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
    print(y, len(rows))
