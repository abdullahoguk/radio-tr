"""Probe radio stream URLs and report which ones actually deliver audio.

Usage: python3 check_streams.py candidates.json > results.json
candidates.json: [{"id": "...", "urls": ["https://...", ...]}, ...]

For each URL (http:// URLs are also tried as https://) we check:
  - Icecast/Shoutcast/MP3/AAC: the server answers and starts sending audio bytes.
  - HLS (.m3u8): the playlist is valid and its first segment downloads; we also
    record whether CORS headers allow playback through hls.js in the browser.
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

ORIGIN = "https://radio.abdullahog.uk"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def curl(url, max_time=8, max_bytes=None, body=True):
    """Return (exit_code, headers_text, body_bytes, effective_url)."""
    cmd = ["curl", "-sS", "-L", "--http0.9", "-A", UA, "-H", f"Origin: {ORIGIN}",
           "-m", str(max_time), "-D", "-", "-w", "\n__EFFECTIVE__%{url_effective}"]
    if max_bytes:
        cmd += ["-r", f"0-{max_bytes}"]
    if not body:
        cmd += ["-o", "/dev/null"]
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, timeout=max_time + 5)
    out = p.stdout
    eff = ""
    if b"\n__EFFECTIVE__" in out:
        out, eff = out.rsplit(b"\n__EFFECTIVE__", 1)
        eff = eff.decode(errors="ignore")
    # Split the last header block from the body.
    head, bodyb = b"", out
    parts = re.split(rb"\r?\n\r?\n", out)
    heads = []
    while parts and re.match(rb"^(HTTP/|ICY )", parts[0]):
        heads.append(parts.pop(0))
    head = heads[-1].decode(errors="ignore") if heads else ""
    bodyb = b"\r\n\r\n".join(parts)
    return p.returncode, head, bodyb, eff


def header(head, name):
    m = re.search(rf"^{name}:\s*(.+?)\s*$", head, re.I | re.M)
    return m.group(1) if m else None


def status(head):
    m = re.match(r"^(?:HTTP/[\d.]+|ICY)\s+(\d+)", head)
    return int(m.group(1)) if m else 0


def looks_like_audio(data):
    if len(data) < 2048:
        return False
    if data[:3] == b"ID3" or data[:4] == b"OggS" or data[:4] == b"fLaC":
        return True
    # MPEG audio / ADTS AAC frame sync somewhere in the first chunk.
    for i in range(min(len(data) - 1, 4096)):
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            return True
    return False


def probe_hls(url):
    code, head, body, eff = curl(url, max_time=10)
    text = body.decode(errors="ignore")
    if "#EXTM3U" not in text:
        return None
    cors = header(head, "access-control-allow-origin")
    base = eff or url
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    if not lines:
        return None
    nxt = urljoin(base, lines[0])
    if "#EXT-X-STREAM-INF" in text:
        code2, head2, body2, eff2 = curl(nxt, max_time=10)
        t2 = body2.decode(errors="ignore")
        if "#EXTM3U" not in t2:
            return None
        cors = cors if header(head2, "access-control-allow-origin") else None
        segs = [l.strip() for l in t2.splitlines() if l.strip() and not l.startswith("#")]
        if not segs:
            return None
        seg = urljoin(eff2 or nxt, segs[-1])
    else:
        seg = nxt
    code3, head3, body3, _ = curl(seg, max_time=10, max_bytes=65535)
    if status(head3) not in (200, 206) or len(body3) < 1024:
        return None
    seg_cors = header(head3, "access-control-allow-origin")
    return {"type": "hls", "cors": bool(cors and seg_cors)}


def probe(url):
    try:
        if re.search(r"\.m3u8(\?|$)", url, re.I):
            r = probe_hls(url)
            return r
        code, head, body, eff = curl(url, max_time=7, max_bytes=None)
        st = status(head)
        ctype = (header(head, "content-type") or "").lower()
        if "mpegurl" in ctype or body[:7] == b"#EXTM3U":
            return probe_hls(eff or url)
        if st in (200, 206) and (ctype.startswith("audio") or "ogg" in ctype or looks_like_audio(body)):
            if "text/html" in ctype:
                return None
            return {"type": "icy", "ctype": ctype.split(";")[0] or None, "final": eff or url}
        return None
    except Exception:
        return None


def check(item):
    tried = []
    for url in item["urls"]:
        variants = [url]
        if url.startswith("http://"):
            variants = ["https://" + url[7:], url]
        for v in variants:
            tried.append(v)
            r = probe(v)
            if r:
                r.update({"id": item["id"], "url": v, "ok": True, "https": v.startswith("https://")})
                return r
    return {"id": item["id"], "ok": False, "tried": tried}


if __name__ == "__main__":
    items = json.load(open(sys.argv[1]))
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(check, items))
    json.dump(results, sys.stdout, ensure_ascii=False, indent=1)
