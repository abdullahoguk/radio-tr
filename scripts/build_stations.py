"""Build public/data/stations.json from the researched sources.

Inputs (in .cache/, produced during research):
  rn_full.json             radyolar.net.tr listing + detail pages (popularity order)
  karnaval_stations.json   Karnaval's own station catalogue (karnaval.com)
  results.json             stream probe results from check_streams.py
TRT channels come from radyo.trt.net.tr's official player and are listed below.

Categories are assigned here, by rules over name + description and by hand
overrides; the upstream genre tags are not used.
"""
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"

CATEGORIES = [
    ("pop", "Türkçe Pop"),
    ("yabanci", "Yabancı Hit"),
    ("slow", "Slow"),
    ("arabesk", "Arabesk"),
    ("thm", "Türk Halk Müziği"),
    ("tsm", "Türk Sanat Müziği"),
    ("yoresel", "Yöresel"),
    ("rock", "Rock"),
    ("rap", "Rap"),
    ("dans", "Dans"),
    ("caz", "Caz"),
    ("klasik", "Klasik"),
    ("nostalji", "Nostalji"),
    ("haber", "Haber"),
    ("spor", "Spor"),
    ("dini", "Dini"),
]

# Stations broadcasting mainly in Kurdish, or not in Turkish at all.
EXCLUDE = {
    "TRT Kurdî Radyo", "Azadi FM", "Radyo Dengê Kurdî", "Radyo Hêvî", "Radyo Evin",
    "Dost Radyo", "Veng Radyo", "Amed Radyo TV", "Radio AVA", "Power Greece",
    "TRT Müzik",  # TV channel audio, not a radio station
    "Türkiye Polis Radyosu",  # server resets browser connections
}

TRT_LOGO = "https://trt-public-static.trt.com.tr/eradyo/public/dm_upload/modul2/"
TRT = [
    # name, stream, logo, categories, description, matching names on radyolar.net.tr
    ("TRT Radyo 1", "https://trt.radyotvonline.net/trt1", "ded6c190-5f9e-4de3-a5e5-868f789df1a5.jpg", ["haber"],
     "Eğitim, kültür, haber. Bilim, sanat, edebiyat, tiyatro, spor, çevre, ekonomi; hayata dair her şey. TRT'nin köklü genel yayın kanalı.",
     ["TRT Radyo 1"]),
    ("TRT FM", "https://trt.radyotvonline.net/trtfm", "e27e1421-5735-40c1-affb-4101dc73a305.jpg", ["pop"],
     "Türkçe pop ağırlıklı müzik yayını, ilginç programlar ve saat başı haberler.", ["TRT FM"]),
    ("TRT Radyo 3", "https://rd-trtradyo3.medya.trt.com.tr/master.m3u8", "79633047-a080-4fed-8ed8-5c33c1348563.jpg", ["klasik", "caz"],
     "Elvis Presley'den Joan Baez'e, Frank Sinatra'dan Çaykovski'ye, Mozart'tan Sarah Vaughan'a; klasik müzik, caz ve dünya müziğinin seçkin örnekleri.",
     ["TRT Radyo 3"]),
    ("TRT Nağme", "https://rd-trtnagme.medya.trt.com.tr/master.m3u8", "9d472dd1-a769-4335-91bf-245c5f037c26.jpg", ["tsm"],
     "TRT arşivinden seçme eserler ve yeni kayıtlar. Korolar, dinleyici istekleri ve canlı yayınlarla Türk sanat müziği.", ["TRT Nağme"]),
    ("TRT Türkü", "https://rd-trtturku.medya.trt.com.tr/master.m3u8", "be1b7390-cd1d-43cd-9f0b-86f50a4db873.jpg", ["thm"],
     "Geleneksel türküler ve halk müziği canlı yayınları. Anadolu'nun zengin müzik mirası.", ["TRT Türkü"]),
    ("TRT Radyo Haber", "https://trt.radyotvonline.net/trthaber", "03a0eb4a-3df8-4bb1-b076-6bb1459a470e.jpg", ["haber"],
     "Haberin radyo frekansı. Haber bültenleri, haber programları, hava ve yol durumu, kültür ve sanat gündemi.", ["TRT Radyo Haber"]),
    ("TRT Memleketim FM", "https://radio-trtmemleketimfm.medya.trt.com.tr/master.m3u8", "10087691-9885-4fe3-bb81-b377dd4f7675.png", ["thm", "tsm"],
     "TRT'nin yurt dışında yaşayan vatandaşlara yönelik kanalı. Türk halk ve sanat müziği ağırlıklı yayın.", ["TRT Memleketim FM"]),
    ("TRT Türkiye'nin Sesi", "https://radio-trttsr.medya.trt.com.tr/master.m3u8", "97b4cc85-0765-4010-8ba4-117e49b2b087.png", ["haber"],
     "TRT'nin uluslararası radyo servisi. Türkiye'yi dünyaya Türkçe ve birçok yabancı dilde anlatan yayınlar.",
     ["TRT TSR Türkiye'nin Sesi Radyosu"]),
    ("TRT Antalya Radyosu", "https://radio-trtantalya.medya.trt.com.tr/master.m3u8", "25b139d5-5acc-4a44-9842-eeeb9af7fb17.png", ["yoresel"],
     "1962'den bugüne Akdeniz'in renkleri, müziği, kültürü ve gelenekleri. Her gün 10.05–13.00 arası bölgesel yayın.", []),
    ("TRT Çukurova Radyosu", "https://radio-trtcukurova.medya.trt.com.tr/master.m3u8", "748d235d-66e8-4bc8-ac2c-2a5825801648.png", ["yoresel"],
     "1968'den bugüne Torosların kokusu, yaşamı ve yöresel değerleri. Her gün 10.05–13.00 arası bölgesel yayın.", ["TRT Çukurova Radyosu"]),
    ("TRT Erzurum Radyosu", "https://radio-trterzurum.medya.trt.com.tr/master.m3u8", "756218af-8e16-4f08-a2d0-a0c84736f091.png", ["yoresel", "thm"],
     "1960'tan bugüne türküleriyle, folkloruyla Doğu Anadolu. Her gün 10.05–13.00 arası bölgesel yayın.", []),
    ("TRT GAP Diyarbakır Radyosu", "https://radio-trtgap.medya.trt.com.tr/master.m3u8", "c379b2ac-878a-4a67-8ee7-8946ea716d17.png", ["yoresel"],
     "TRT'nin Güneydoğu Anadolu bölge radyosu. Diyarbakır'dan bölgesel yayın ve yöresel müzik.", []),
    ("TRT Trabzon Radyosu", "https://radio-trttrabzon.medya.trt.com.tr/master.m3u8", "d8b4e8d9-610f-423c-8209-e0683f07b0ff.png", ["yoresel", "thm"],
     "1968'den bugüne yeşiliyle, mavisiyle, tulumuyla, kemençesiyle Karadeniz. Her gün 10.05–13.00 arası bölgesel yayın.", ["TRT Trabzon Radyosu"]),
]
TRT_CITY = {"TRT Antalya Radyosu": "Antalya", "TRT Çukurova Radyosu": "Adana", "TRT Erzurum Radyosu": "Erzurum",
            "TRT GAP Diyarbakır Radyosu": "Diyarbakır", "TRT Trabzon Radyosu": "Trabzon"}

# Karnaval mounts → categories (Karnaval's own catalogue has no usable genre field).
KARNAVAL_CATS = {
    "JOY_TURK": ["slow", "pop"], "SUPER_FM": ["pop"], "VIRGIN_RADIO": ["rap", "yabanci"], "METRO_FM": ["yabanci"],
    "JOY_FM": ["yabanci", "slow"], "POP90": ["nostalji", "pop"], "POP_TR": ["pop"], "JOYTURK_AKUSTIK": ["slow", "pop"],
    "ODEA": ["pop", "haber"], "SUPER_YENI": ["pop"], "MYDONOSE_TURK": ["dans", "pop"], "SUPER2": ["pop"],
    "EFKAR": ["arabesk", "slow"], "JOYTURK_ROCK": ["rock"], "RADIO_MYDONOSE": ["dans", "yabanci"],
    "GONUL_TURKULERI": ["thm"], "GHOAT_TR": ["nostalji", "pop"], "RETROTURK": ["nostalji", "pop"], "SOLE": ["yabanci"],
    "YOL_ARKADASIM": ["pop"], "KARADENIZ": ["yoresel", "thm"], "POPBESK": ["pop", "arabesk"], "ROCK_STATION": ["rock"],
    "BORUSAN_KLASIK": ["klasik"], "LITERAL": ["yabanci", "rock"], "SC021_SO1": ["slow"], "MAKAM": ["tsm"],
    "JOY_JAZZ": ["caz"], "BASKA": ["pop", "rock"], "GHOAT_EN": ["nostalji", "yabanci"], "SC002_SO1": ["yabanci"],
    "SC019_SO1": ["dans"], "SC030_SO1": ["slow"], "SC018_SO1": ["rap"], "SC009_SO1": [], "KPOP": ["yabanci"],
}
KARNAVAL_SKIP = {"SC009_SO1"}  # BabyJoy: lullabies, not a radio station people browse for

# Hand-checked categories for popular stations where description keywords mislead.
OVERRIDES = {
    "DamarTürk FM": ["arabesk"], "Kral Pop Radyo": ["pop"], "Kral FM": ["arabesk", "pop"],
    "PowerTürk FM": ["pop"], "Radyo 7": ["pop", "haber"], "Baba Radyo": ["tsm", "arabesk"],
    "SlowTürk": ["slow"], "Radyo Seymen": ["thm"], "Alem FM": ["pop", "arabesk"], "Radyo 45'lik": ["nostalji", "pop"],
    "Kalp FM": ["arabesk"], "Kafa Radyo": ["haber"], "Best FM": ["pop"], "Park FM": ["arabesk", "pop"],
    "Aşk FM": ["arabesk", "slow"], "A Haber Radyo": ["haber"], "Radyo Ekin 94.4": ["thm"],
    "Show 90'lar": ["nostalji", "pop"], "Show Radyo": ["pop"], "Power POP": ["yabanci"], "CNN Türk Radyo": ["haber"],
    "Radyo Fenomen Türk": ["pop"], "Radyo Turkuvaz": ["pop"], "Radyo Fenomen": ["yabanci"], "A Spor Radyo": ["spor"],
    "Karadeniz FM": ["yoresel"], "Radyo Alaturka": ["tsm"], "Radyo Viva": ["pop"], "Radyo Banko": ["arabesk", "pop"],
    "Radyospor": ["spor"], "İstanbul FM": ["pop"], "Power FM": ["yabanci"], "Radyo Gol": ["spor"],
    "Habertürk Radyo": ["haber"], "X Radio": ["pop", "rock"], "Radyo Özgür": ["pop"], "Dedemin Radyosu": ["nostalji", "tsm"],
    "Vav Radyo": ["dini"], "Mekke FM": ["dini"], "HAYATMiX": ["arabesk"], "Radyo Pal Nostalji": ["nostalji", "pop"],
    "Radyo Mars": ["pop"], "Pal FM": ["arabesk"], "Radyo BoomBox": ["rap"], "Diyanet Radyo": ["dini"],
    "Star Artı FM": ["arabesk", "pop"], "NTV Radyo": ["haber"], "Pal Station": ["yabanci"], "Pal Doğa": ["thm"],
    "Diyanet Kur'an Radyo": ["dini"], "Radyo Tatlıses": ["arabesk"], "İstanbul FM Slow": ["slow"],
    "Radyo Megasite": ["pop"], "Lalegül FM": ["dini"], "Akra FM": ["dini", "haber"], "Radyo D": ["pop"],
    "24 Radyo": ["haber"], "TGRT FM": ["pop", "haber"], "Radyo Voyage": ["yabanci", "caz"], "Kiss FM": ["yabanci"],
    "Number 1 FM": ["yabanci"], "Lig Radyo": ["spor"], "Semerkand Radyo": ["dini"], "Erkam Radyo": ["dini"],
    "Radyo Fenerbahçe": ["spor"], "Diyanet Risalet Radyo": ["dini"], "Türkiye Polis Radyosu": ["pop", "haber"],
    "FG 93.8": ["dans", "yabanci"], "Radyo Kordelya": ["pop"], "Radyo Akdeniz": ["pop"],
    "Radyo Enerji": ["dans", "yabanci"], "Radio Mydonose": ["dans", "yabanci"], "Joy FM": ["yabanci", "slow"],
    "Power Love": ["slow", "yabanci"], "Radyo Ege": ["pop"], "Radyo Remix": ["pop", "rock"], "AÇS Radyosu": ["klasik", "slow"],
    "Dada Radyo": ["pop", "nostalji"], "Lokum FM": ["pop", "arabesk"], "Biber FM": ["tsm", "arabesk"], "Gözde FM": ["pop"],
    "Radyo Duygusal": ["slow", "arabesk"], "Radyo ODTÜ": ["rock", "yabanci"], "Radyo FM 23": ["pop", "arabesk"],
    "İstanbul FM Nostalji": ["nostalji", "pop"], "Radyo 34": ["pop", "arabesk"], "Kilis Sultan Radyo": ["thm"],
    "Konya FM": ["thm", "dini"], "Radyo Ülkü": ["thm", "tsm"], "Radyo Fenomen 2010'lar": ["nostalji", "yabanci"],
    "Radyo Mavi": ["pop", "arabesk"], "Radio Gramophone": ["nostalji", "tsm"], "Adana FM": ["pop"],
    "Radyo Türk": ["thm", "tsm"], "Lider FM": ["arabesk", "thm"], "Radyo 2000 Osmaniye": ["arabesk", "thm"],
    "Gurbetçi FM": ["thm"], "Can Radyo": ["thm"], "Yön Radyo": ["thm"], "Ostim Radyo": ["thm"],
    "Radyo Türkiyem": ["thm", "tsm"], "Radyo Gül": ["dini"], "Number1 Greek": ["yabanci"], "Radyo Akademi": ["pop"],
    "Radyo Viva - Tv100 Haber": ["haber"], "Damardan Kalbe FM": ["arabesk"], "Radyo Duman": ["arabesk", "pop"], "Radyo 75": ["pop", "slow"], "Radyo Nostaljinin Sesi": ["nostalji"],
}

GROUP_RULES = [
    (r"trkvz-radyolar|Turkuvaz Medya", "Turkuvaz Radyolar"),
    (r"powerapp\.com\.tr|Power Media|Power Group|Power Medya", "Power"),
    (r"radyofenomen|rdfenlive", "Radyo Fenomen"),
    (r"Doğuş Yayın", "Doğuş"),
    (r"/radyo7|Radyo 7\b|radyohome|Radyo ?Home", "Radyo 7"),
    (r"istanbulfm\.com\.tr", "İstanbul FM"),
    (r"Diyanet", "Diyanet"),
    (r"Pal Media|/pal[a-z]+/playlist", "Pal Medya"),
    (r"Number1", "Number1"),
    (r"kiss\.radyotvonline|Kiss Gru", "Kiss"),
    (r"Karnaval", "Karnaval"),
]

KEYWORDS = [
    ("dini", r"(dinî|dini içerikli radyo|islami|ilahi|kur'?an|tasavvuf|diyanet|kuran meali|mevlid|manevi)"),
    ("haber", r"(haber radyosu|haber kanalı|24 saat haber|haber ağırlıklı|haber-yorum)"),
    ("spor", r"\b(spor radyosu|spor yayın|futbol|maç)"),
    ("tsm", r"(türk sanat müziği|sanat müziği|klasik türk müziği|fasıl|alaturka|tsm\b)"),
    ("thm", r"(türk halk müziği|türkü|halk müziği|thm\b|bozlak|uzun hava)"),
    ("arabesk", r"(arabesk|fantezi|damar)"),
    ("yoresel", r"(karadeniz|kemençe|horon|ege havaları|ankara havaları|roman havaları|yöresel|oyun havaları)"),
    ("slow", r"(slow|romantik|akustik|duygusal)"),
    ("rock", r"\brock\b|metal"),
    ("rap", r"\b(rap|hip[- ]?hop|r&b)\b"),
    ("dans", r"\b(dans|dance|elektronik|electronic|house|edm|remix|club)\b"),
    ("caz", r"\b(caz|jazz|blues)\b"),
    ("klasik", r"(klasik müzik|klasik batı|classical|senfoni|opera)"),
    ("nostalji", r"(nostalji|90'lar|80'ler|70'ler|45'lik|retro|eski şarkı|plak)"),
    ("yabanci", r"(yabancı|foreign|international|dünya hitleri|global hit|top 40)"),
    ("pop", r"(türkçe pop|pop müzik|\bpop\b|hit)"),
]


def slugify(s):
    s = s.replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def fold(s):
    return slugify(s).replace("-", "")


def classify(name, desc):
    """Categories ordered by where they first show up: in the name, then in the description."""
    if name in OVERRIDES:
        return OVERRIDES[name]
    name_l, desc_l = name.lower(), (desc or "").lower()
    hits = []
    for cat, rx in KEYWORDS:
        m_name = re.search(rx, name_l, re.I)
        m_desc = re.search(rx, desc_l, re.I)
        if m_name or m_desc:
            hits.append((0 if m_name else 1, m_desc.start() if m_desc else 0, cat))
    ordered = [c for *_, c in sorted(hits)]
    if "pop" in ordered and len(ordered) > 2:
        ordered.remove("pop")
    return ordered[:2] or ["pop"]


def group_of(name, desc, stream):
    hay = f"{name} {desc or ''} {stream}"
    for rx, g in GROUP_RULES:
        if re.search(rx, hay):
            return g
    return None


def stw_mount(url):
    """StreamTheWorld mount name from a stream URL (JOY_TURK128AAC.aac -> JOY_TURK)."""
    if "streamtheworld" not in (url or ""):
        return None
    tok = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    return re.sub(r"(\.aac|\.aa|\.a)$", "", tok).removesuffix("_SC").removesuffix("AAC").removesuffix("AA").removesuffix("A").removesuffix("128").removesuffix("12").removesuffix("1")


def short(desc, limit=320):
    if not desc:
        return None
    desc = re.sub(r"\s+", " ", desc).strip()
    if len(desc) <= limit:
        return desc
    cut = desc[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "))
    return cut[: end + 1] if end > 120 else cut.rsplit(" ", 1)[0] + "…"


def main():
    rn = json.load(open(CACHE / "rn_full.json"))
    kv = json.load(open(CACHE / "karnaval_stations.json"))
    results = {r["id"]: r for r in json.load(open(CACHE / "results.json"))}
    rn_by_name = {s["name"]: s for s in rn}

    stations, seen, logo_sources = [], set(), {}

    def add(st):
        key = fold(st["name"])
        if key in seen:
            return
        seen.add(key)
        stations.append(st)

    # 1. TRT — official streams and logos.
    for name, stream, logo, cats, desc, aliases in TRT:
        match = next((rn_by_name[a] for a in aliases if a in rn_by_name), None)
        freq = match and match.get("freq")
        add({
            "name": name, "stream": stream, "hls": stream.endswith(".m3u8"),
            "logo_src": TRT_LOGO + logo, "cats": cats, "desc": desc, "group": "TRT",
            "city": TRT_CITY.get(name) or (match and match.get("city") if match and match.get("city") and "FM" not in match["city"] else "Ankara"),
            "freq": freq, "website": "https://radyo.trt.net.tr", "rank": match["rank"] if match else 400,
        })
    for a in [a for t in TRT for a in t[5]] + ["TRT Kurdî Radyo", "TRT Müzik"]:
        seen.add(fold(a))

    # 2. Karnaval — official catalogue, StreamTheWorld streams.
    rn_by_fold = {fold(s["name"]): s for s in rn}
    rn_by_mount = {stw_mount(s["stream"]): s for s in rn if stw_mount(s["stream"])}
    for st in kv.values():
        mount = st["mount"]
        if mount in KARNAVAL_SKIP:
            continue
        res = results.get("kv:" + mount)
        if not res or not res["ok"]:
            continue
        match = rn_by_mount.get(mount) or rn_by_fold.get(fold(st["name"]))
        freqs = st.get("frequencies") or {}
        f34 = freqs.get("city_34") or next(iter(freqs.values()), None) if freqs else None
        desc = (match and match.get("desc")) or st.get("slogan") or st.get("short_description")
        add({
            "name": st["name"], "stream": res["url"], "hls": False,
            "logo_src": st.get("android_default_logo") or st.get("mono_logo"),
            "cats": KARNAVAL_CATS.get(mount, ["pop"]), "desc": desc, "slogan": st.get("slogan") or None,
            "group": "Karnaval", "city": "İstanbul", "freq": f34["frequency"] if f34 else None,
            "website": "https://karnaval.com/" + (st.get("sanitized_url") or ""),
            "rank": match["rank"] if match else 300 + int(st.get("sort_order") or 0),
        })
        if match:
            seen.add(fold(match["name"]))

    # 3. Everything else from radyolar.net.tr, in popularity order.
    for s in rn:
        if s["name"] in EXCLUDE or (s.get("lang") and s["lang"] not in ("Türkçe", "English")):
            continue
        res = results.get("rn:%d" % s["rank"])
        if not res or not res["ok"] or not res["https"]:
            continue
        city = s.get("city")
        if city and re.search(r"\bFM\b", city):
            city = None
        add({
            "name": s["name"], "stream": res["url"], "hls": res["type"] == "hls",
            "logo_src": s.get("logo"), "cats": classify(s["name"], s.get("desc")), "desc": s.get("desc"),
            "group": group_of(s["name"], s.get("desc"), s["stream"]), "city": city, "freq": s.get("freq"),
            "website": s.get("website"), "rank": s["rank"],
        })

    stations.sort(key=lambda s: s["rank"])
    used = set()
    out = []
    for i, s in enumerate(stations, 1):
        sid = slugify(s["name"])
        while sid in used:
            sid += "-2"
        used.add(sid)
        out.append({k: v for k, v in {
            "id": sid, "no": i, "name": s["name"], "cats": s["cats"], "city": s["city"], "freq": s["freq"],
            "group": s["group"], "desc": short(s["desc"]), "stream": s["stream"], "hls": s["hls"] or None,
            "website": s.get("website"), "logo": f"logos/{sid}.webp",
        }.items() if v is not None})
        logo_sources[sid] = s["logo_src"]

    data = {
        "updated": date.today().isoformat(),
        "categories": [{"id": c, "label": l} for c, l in CATEGORIES],
        "stations": out,
    }
    (ROOT / "public/data").mkdir(parents=True, exist_ok=True)
    with open(ROOT / "public/data/stations.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    with open(CACHE / "logo_sources.json", "w") as f:
        json.dump(logo_sources, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} stations written", file=sys.stderr)


if __name__ == "__main__":
    main()
