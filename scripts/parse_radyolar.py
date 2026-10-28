"""Parse station cards from radyolar.net.tr listing pages into JSON."""
import glob, html, json, re, sys

out = []
for f in sorted(glob.glob(sys.argv[1] + "/p*.html"), key=lambda p: int(re.search(r"p(\d+)", p).group(1))):
    s = open(f, encoding="utf-8").read()
    for m in re.finditer(r'<div class="scard-art"(.*?)aria-label', s, re.S):
        attrs = dict((k, html.unescape(v)) for k, v in re.findall(r'data-([a-z-]+)="([^"]*)"', m.group(1)))
        meta = attrs.get("meta", "")
        city, freq = None, None
        for part in [p.strip() for p in meta.split("·")]:
            fm = re.match(r"([\d.,]+)\s*FM", part)
            if fm: freq = fm.group(1).replace(",", ".")
            elif part: city = part
        out.append({"rank": len(out) + 1, "name": attrs.get("title"), "stream": attrs.get("stream-url"),
                    "logo": attrs.get("logo"), "city": city, "freq": freq, "href": attrs.get("href")})
json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
