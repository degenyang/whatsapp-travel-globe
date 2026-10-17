"""Pull travel-related messages out of exported WhatsApp chats, one file per year.

Usage:
    python scripts/extract.py <chat_txt_dir> <out_dir> [--partner "Chat name"] [--me You]

Reads every *.txt in <chat_txt_dir> (official WhatsApp export format,
"DD/MM/YYYY, HH:MM - Sender: text"). Keeps:
  * your own messages (sender == --me, "You" in Android exports) that match a travel keyword
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
ap.add_argument("--me", default="You")
a = ap.parse_args()

line_re = re.compile(r"^(\d{2})/(\d{2})/(\d{4}), (\d{2}:\d{2}) - ([^:]+?): (.*)$")
# English travel words. Add words in your own language before the closing ")".
travel = re.compile(
    r"(landed|just arrived|arrived (at|in)|touch(ed)? ?down|boarding|at (the )?airport|airport (now|already)|"
    r"\bi'?m in |\bi am in |currently in |\btravell?ing\b|on (a |my )?(trip|holiday|vacation)|holiday|vacation|"
    r"trip\b|fly(ing)? (to|back)|flight (to|back|home|is|delayed)|my flight|back (to|in) [a-z]+|jet ?lag|"
    r"hotel|checked in|check ?in (at|to)|check ?out|ferry|roaming|e-?sim|luggage|passport|airbnb|resort|"
    r"staycation|honeymoon|booked (the )?(flight|ticket|hotel)|plane)",
    re.I,
)
out = collections.defaultdict(list)
for fn in sorted(os.listdir(a.chat_dir)):
    if not fn.endswith(".txt"):
        continue
    chat = fn.rsplit("__", 1)[0]
    partner = a.partner is not None and chat == a.partner
    with open(os.path.join(a.chat_dir, fn), encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = line_re.match(ln)
            if not m:
                continue
            dd, mm, yy, hm, who, txt = m.groups()
            if not (who == a.me or partner):
                continue
            if len(txt) > 220 or "http" in txt:  # skip forwards and links
                continue
            if travel.search(txt):
                w = "Me" if who == a.me else "Partner"
                out[yy].append(f"{yy}-{mm}-{dd} {hm} [{chat[:20]}] {w}: {txt.strip()}")
os.makedirs(a.out_dir, exist_ok=True)
for y, rows in sorted(out.items()):
    rows.sort()
    with open(os.path.join(a.out_dir, f"y{y}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
    print(y, len(rows))
