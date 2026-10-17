"""Low-memory WhatsApp msgstore.db -> per-chat txt (official Android export format).

Usage: python wa_stream_export.py msgstore.db out_txt [contacts.csv|vcf] [jid1,jid2 filter]

msgstore.db = the DECRYPTED Android database (see README step 1).
Timestamps are written in UTC+WA_TZ_HOURS (env var, default 0 = UTC).
The optional contacts file (Google Contacts CSV or .vcf) turns phone numbers into names.
"""
import sqlite3, sys, os, re, io, csv, datetime
sys.stdout.reconfigure(encoding='utf-8')
db, outdir = sys.argv[1], sys.argv[2]
vcf = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(outdir, exist_ok=True)
TZ = datetime.timezone(datetime.timedelta(hours=float(os.environ.get('WA_TZ_HOURS', '0'))))
# Country codes to try for contacts saved without one, e.g. WA_LOCAL_CC=44 or WA_LOCAL_CC=1,44
LOCAL_CC = [c for c in os.environ.get('WA_LOCAL_CC', '').split(',') if c]
names = {}
def add_num(raw, name):
    num = re.sub(r'\D', '', raw or '')
    if not num or not name: return
    if len(num) == 8 and LOCAL_CC:  # local mobile without country code -> register under each local code, DB jid decides
        for cc in LOCAL_CC: names.setdefault(cc + num, name)
    else:
        if num.startswith('00'): num = num[2:]
        names.setdefault(num, name)
if vcf and vcf.lower().endswith('.csv') and os.path.exists(vcf):
    import csv
    for r in csv.DictReader(io.open(vcf, encoding='utf-8-sig')):
        nm = ' '.join(x for x in (r.get('First Name', ''), r.get('Middle Name', ''), r.get('Last Name', '')) if x).strip() or r.get('Organization Name', '').strip()
        for k, v in r.items():
            if k and k.startswith('Phone') and k.endswith('Value') and v:
                for part in v.split(':::'): add_num(part, nm)
    print('contacts loaded: %d numbers' % len(names))
elif vcf and os.path.exists(vcf):
    cur_name = None
    for line in io.open(vcf, encoding='utf-8', errors='ignore'):
        line = line.strip()
        if line.startswith('FN:'): cur_name = line[3:].strip()
        elif line.startswith('TEL') and cur_name:
            num = re.sub(r'\D', '', line.split(':', 1)[-1])
            if len(num) == 8 and LOCAL_CC: num = LOCAL_CC[0] + num  # local mobile
            if num: names.setdefault(num, cur_name)
        elif line == 'END:VCARD': cur_name = None
MEDIA = {1: 'image', 2: 'audio', 3: 'video', 4: 'contact', 5: 'location', 9: 'document', 13: 'gif', 15: 'deleted', 16: 'live location', 20: 'sticker', 66: 'poll', 82: 'poll'}
con = sqlite3.connect('file:%s?mode=ro' % db.replace(chr(92), '/'), uri=True)
c = con.cursor()
jids = {r[0]: (r[1] or '', r[2] or '') for r in c.execute('select _id, user, server from jid')}
lidmap = {r[0]: r[1] for r in c.execute('select lid_row_id, jid_row_id from jid_map')}  # lid jid -> phone jid
lidname = {r[0]: r[1] for r in c.execute('select lid_row_id, display_name from lid_display_name')}
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None  # optional: only these jid users
def disp(jid_id):
    user, server = jids.get(jid_id, ('', ''))
    if server == 'lid':
        pn = jids.get(lidmap.get(jid_id), ('', ''))[0]
        if pn: return names.get(pn, pn)
        return lidname.get(jid_id, user or '?')
    return names.get(user, user or '?')
def safe(s):
    return re.sub(r'[\/:*?"<>|\r\n]+', '_', s).strip()[:80] or 'chat'
index = []
chats = c.execute('select _id, jid_row_id, subject from chat order by sort_timestamp desc').fetchall()
for i, (cid, jid_id, subject) in enumerate(chats):
    user, server = jids.get(jid_id, ('', ''))
    if server == 'status' or server == 'broadcast': continue
    if ONLY and user not in ONLY: continue
    is_group = server == 'g.us'
    cname = subject or disp(jid_id)
    n = c.execute('select count(*) from message where chat_row_id=?', (cid,)).fetchone()[0]
    if n == 0: continue
    fn = os.path.join(outdir, '%s__%s.txt' % (safe(cname), user or cid))
    first = last = None
    with io.open(fn, 'w', encoding='utf-8', newline='\n') as f:
        q = c.execute('select from_me, sender_jid_row_id, timestamp, message_type, text_data from message where chat_row_id=? and message_type != 7 order by timestamp, _id', (cid,))
        while True:
            rows = q.fetchmany(5000)
            if not rows: break
            for from_me, sjid, ts, mtype, text in rows:
                if not ts: continue
                dt = datetime.datetime.fromtimestamp(ts / 1000, TZ)
                stamp = dt.strftime('%d/%m/%Y, %H:%M')
                if first is None: first = dt
                last = dt
                who = 'You' if from_me else (disp(sjid) if is_group and sjid else cname)
                body = text if text else ('<Media omitted: %s>' % MEDIA.get(mtype, 'type %s' % mtype))
                body = body.replace('\r\n', '\n')
                f.write('%s - %s: %s\n' % (stamp, who, body))
    index.append((cname, user or '', 'group' if is_group else 'chat', n, first.strftime('%Y-%m-%d') if first else '', last.strftime('%Y-%m-%d') if last else '', os.path.basename(fn)))
    if i % 200 == 0: print('%d/%d chats...' % (i, len(chats)), flush=True)
with io.open(os.path.join(outdir, '_index.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['chat', 'jid', 'kind', 'messages', 'first', 'last', 'file'])
    for r in sorted(index, key=lambda r: -r[3]): w.writerow(r)
print('DONE chats=%d files, messages=%d' % (len(index), sum(r[3] for r in index)))
