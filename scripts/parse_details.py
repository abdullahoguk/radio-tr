"""Merge radyolar.net.tr detail pages (description, genres, website) into the listing JSON."""
import html, json, os, re, sys

listing = json.load(open(sys.argv[1]))
detail_dir = sys.argv[2]

def text(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()

for st in listing:
    path = os.path.join(detail_dir, os.path.basename(st["href"]))
    if not os.path.exists(path):
        continue
    s = open(path, encoding="utf-8").read()
    m = re.search(r'<div class="st-desc">(.*?)</div>', s, re.S)
    st["desc"] = text(m.group(1)) if m else None
    meta = re.search(r'<div class="st-meta">(.*?)</div>', s, re.S)
    st["genres"] = re.findall(r"genre/([a-z0-9-]+)", meta.group(1)) if meta else []
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            d = json.loads(blob)
        except ValueError:
            continue
        if d.get("@type") == "RadioStation":
            same = [u for u in d.get("sameAs", []) if not re.search(r"facebook|instagram|x\.com|twitter|youtube|wikipedia|apple\.com|google\.com|tiktok|t\.me|whatsapp", u)]
            st["website"] = same[0] if same else None
            st["lang"] = None
    lang = re.search(r'Dil</span>\s*<span class="v">([^<]+)<', s)
    st["lang"] = html.unescape(lang.group(1)).strip() if lang else None
json.dump(listing, sys.stdout, ensure_ascii=False, indent=1)
