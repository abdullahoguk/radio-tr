const DATA_URL = "data/stations.json";
const FAV_KEY = "rtr:favs";
const LAST_KEY = "rtr:last";
const TICK = 10; // px per station on the dial
const HLS_SRC = "https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.5.15/hls.min.js";

const $ = (s) => document.querySelector(s);
const el = {
  list: $("#list"), state: $("#state"), search: $("#search"), chips: $("#chips"), groups: $("#groups"),
  countNum: $("#countNum"), countLabel: $("#countLabel"),
  mini: $("#mini"), miniLogo: $("#miniLogo"), miniName: $("#miniName"), miniMeta: $("#miniMeta"),
  miniPlay: $("#miniPlay"), miniOpen: $("#miniOpen"),
  player: $("#player"), playerClose: $("#playerClose"), playerCity: $("#playerCity"),
  playerGroup: $("#playerGroup"), playerNo: $("#playerNo"),
  playerLogo: $("#playerLogo"), bigNum: $("#bigNum"), bigUnit: $("#bigUnit"), bigName: $("#bigName"),
  rulerLabels: $("#rulerLabels"),
  favBtn: $("#favBtn"), shareBtn: $("#shareBtn"), nowLabel: $("#nowLabel"), nowTitle: $("#nowTitle"),
  nowDesc: $("#nowDesc"), nowLink: $("#nowLink"),
  prevBtn: $("#prevBtn"), playBtn: $("#playBtn"), playLabel: $("#playLabel"), nextBtn: $("#nextBtn"),
  toast: $("#toast"), audio: $("#audio"),
};

const ICON_PLAY = '<svg viewBox="0 0 24 24"><path d="M7 4.5v15L19.5 12z"/></svg>';
const ICON_PAUSE = '<svg viewBox="0 0 24 24"><path d="M6.5 4.5h4v15h-4zM13.5 4.5h4v15h-4z"/></svg>';
const ICON_STAR = '<svg viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>';

const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
  },
};

const state = {
  stations: [],
  categories: [],
  catLabel: {},
  view: [],
  query: "",
  cat: null,
  group: null,
  favs: new Set(store.get(FAV_KEY, [])),
  current: null,
  playing: false,
  loading: false,
  hls: null,
};

/* ---------- Data ---------- */

const trLower = (s) => (s || "").toLocaleLowerCase("tr");
const fold = (s) => trLower(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ı/g, "i");

async function load() {
  renderSkeleton();
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    state.categories = data.categories;
    state.catLabel = Object.fromEntries(data.categories.map((c) => [c.id, c.label]));
    state.stations = data.stations.map((s) => ({
      ...s,
      hay: fold([s.name, s.city, s.group, s.freq, ...s.cats.map((c) => state.catLabel[c])].join(" ")),
    }));
    afterLoad();
  } catch {
    showState("Bağlantı yok.", "İstasyon listesi yüklenemedi. İnternet bağlantını kontrol et.", "Tekrar dene", load);
  }
}

function afterLoad() {
  renderChips();
  applyFilter();
  const last = store.get(LAST_KEY, null);
  const s = last && state.stations.find((x) => x.id === last);
  if (s && !state.current) select(s, { autoplay: false });
}

/* ---------- Rendering ---------- */

function padNum(n, width = 3) {
  const s = String(n);
  const zeros = Math.max(0, width - s.length);
  return `<span class="z">${"0".repeat(zeros)}</span>${s}`;
}

function freqHtml(freq) {
  // 97.0 -> 097.0 with the padding zero muted, like a tuner display.
  const [int, dec = "0"] = String(freq).split(".");
  return padNum(int, 3) + "." + dec;
}

function catsOf(s) {
  return s.cats.map((c) => state.catLabel[c]).filter(Boolean).join(" · ");
}

function metaOf(s) {
  const parts = [];
  if (s.city) parts.push(s.city);
  if (s.freq) parts.push(`${s.freq} FM`);
  const cats = catsOf(s);
  if (cats) parts.push(cats);
  return parts.join(" · ") || "Canlı yayın";
}

function counted(key) {
  const counts = new Map();
  for (const s of state.stations) for (const v of [].concat(s[key] ?? [])) counts.set(v, (counts.get(v) || 0) + 1);
  return counts;
}

function chip(attr, id, label, count, pressed, cls = "") {
  return `<button class="chip ${cls}" ${attr}="${id ?? ""}" aria-pressed="${pressed}">${esc(label)}<sup>${count}</sup></button>`;
}

function renderChips() {
  const cats = counted("cats");
  el.chips.innerHTML = [
    chip("data-cat", null, "Tümü", state.stations.length, state.cat === null),
    chip("data-cat", "fav", "Favoriler", state.favs.size, state.cat === "fav", "chip--fav"),
    ...state.categories.filter((c) => cats.get(c.id)).map((c) => chip("data-cat", c.id, c.label, cats.get(c.id), state.cat === c.id)),
  ].join("");
  const groups = [...counted("group")].filter(([g, n]) => g && n > 2).sort((a, b) => b[1] - a[1]);
  el.groups.innerHTML = `<span class="chips-label">Yayın grubu</span>` +
    groups.map(([g, n]) => chip("data-group", g, g, n, state.group === g, "chip--sm")).join("");
}

function applyFilter() {
  const q = fold(state.query.trim());
  const terms = q.split(/\s+/).filter(Boolean);
  state.view = state.stations.filter((s) => {
    if (state.cat === "fav" && !state.favs.has(s.id)) return false;
    if (state.cat && state.cat !== "fav" && !s.cats.includes(state.cat)) return false;
    if (state.group && s.group !== state.group) return false;
    return terms.every((t) => s.hay.includes(t));
  });
  const label = [state.group, state.cat === "fav" ? "Favoriler" : state.catLabel[state.cat]].filter(Boolean).join(" · ");
  el.countLabel.textContent = label || (q ? "Sonuç" : "Tümü");
  el.countNum.textContent = state.view.length;
  renderList();
}

function renderList() {
  if (!state.view.length) {
    el.list.innerHTML = "";
    if (state.cat === "fav" && !state.favs.size) showState("Henüz favori yok.", "Bir istasyonun yanındaki yıldıza dokunarak ekleyebilirsin.");
    else showState("Sonuç yok.", state.query ? `“${state.query}” için istasyon bulunamadı.` : "Bu filtrelerle eşleşen istasyon yok.");
    return;
  }
  el.state.hidden = true;
  const html = state.view.map((s) => {
    const active = state.current?.id === s.id;
    const fav = state.favs.has(s.id);
    return `<li class="row${active ? " is-active" : ""}" data-id="${s.id}">
      <span class="row-num">${padNum(s.no)}</span>
      <img class="logo" src="${s.logo}" alt="" loading="lazy" decoding="async" width="48" height="48">
      <div class="row-main">
        <div class="row-name">${esc(s.name)}</div>
        <div class="row-meta">${esc(metaOf(s))}</div>
      </div>
      <div class="row-side">
        <span class="eq" aria-hidden="true"><i></i><i></i><i></i></span>
        ${s.group ? `<span class="row-group">${esc(s.group)}</span>` : ""}
        <button class="row-fav" aria-label="Favori" aria-pressed="${fav}">${ICON_STAR}</button>
      </div>
    </li>`;
  }).join("");
  el.list.innerHTML = html;
}

function renderSkeleton() {
  el.list.innerHTML = Array.from({ length: 8 }, () => '<li class="skeleton"></li>').join("");
}

function showState(title, text, action, fn) {
  el.state.hidden = false;
  el.state.innerHTML = `${esc(title)}<small>${esc(text)}</small>${action ? `<button>${esc(action)}</button>` : ""}`;
  if (fn) el.state.querySelector("button").onclick = fn;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function markActive() {
  el.list.querySelectorAll(".row.is-active").forEach((r) => r.classList.remove("is-active"));
  if (state.current) el.list.querySelector(`[data-id="${state.current.id}"]`)?.classList.add("is-active");
}

function renderPlayer() {
  const s = state.current;
  if (!s) return;
  if (el.mini.hidden) { el.mini.hidden = false; el.mini.classList.add("enter"); }
  el.miniLogo.src = s.logo;
  el.miniName.textContent = s.name;
  el.playerLogo.src = s.logo;
  el.playerLogo.alt = `${s.name} logosu`;
  el.bigNum.innerHTML = s.freq ? freqHtml(s.freq) : padNum(s.no);
  el.bigUnit.textContent = s.freq ? "FM" : "No.";
  el.bigName.textContent = catsOf(s);
  el.playerCity.textContent = s.city || "Türkiye";
  el.playerGroup.textContent = s.group || "Bağımsız";
  el.playerNo.textContent = `No. ${String(s.no).padStart(3, "0")}`;
  el.nowDesc.textContent = s.desc || "";
  el.nowDesc.hidden = !s.desc;
  el.nowLink.hidden = !s.website;
  if (s.website) {
    el.nowLink.href = s.website;
    el.nowLink.textContent = s.website.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");
  }
  el.favBtn.setAttribute("aria-pressed", state.favs.has(s.id));
  renderNow();
  renderDial();
}

function renderNow() {
  const s = state.current;
  if (!s) return;
  const status = state.loading ? "Bağlanıyor…" : state.playing ? "Canlı yayın" : "Duraklatıldı";
  el.nowLabel.textContent = status;
  el.nowTitle.textContent = s.name;
  el.miniMeta.textContent = state.loading ? status : metaOf(s);
  el.playLabel.textContent = state.playing || state.loading ? "Duraklat" : "Dinle";
  el.miniPlay.innerHTML = state.playing || state.loading ? ICON_PAUSE : ICON_PLAY;
  document.body.classList.toggle("is-playing", state.playing);
  document.body.classList.toggle("is-loading", state.loading);
}

function renderDial() {
  const s = state.current;
  const ruler = el.player.querySelector(".ruler--big");
  const track = ruler.querySelector(".ruler-track");
  const w = ruler.clientWidth || window.innerWidth;
  const total = state.stations.length || 1;
  track.style.width = `${total * TICK + w}px`;
  const x = w / 2 - (s.no - 1) * TICK;
  track.style.transform = `translateX(${x}px)`;
  el.rulerLabels.style.width = track.style.width;
  el.rulerLabels.style.transform = `translateX(${x}px)`;
  const from = Math.max(0, Math.floor((s.no - 60) / 5) * 5);
  const to = Math.min(total, s.no + 60);
  let html = "";
  for (let i = from; i <= to; i += 5) html += `<span style="left:${i * TICK}px">${i + 1}</span>`;
  el.rulerLabels.innerHTML = html;
}

/* ---------- Playback ---------- */

function select(s, { autoplay = true } = {}) {
  state.current = s;
  store.set(LAST_KEY, s.id);
  markActive();
  renderPlayer();
  if (autoplay) play();
}

async function play() {
  const s = state.current;
  if (!s) return;
  stopStream();
  state.loading = true;
  state.playing = false;
  renderNow();
  updateMediaSession();
  try {
    // Prefer hls.js wherever MSE exists: Chromium's native HLS fails on some Turkish CDNs.
    // Browsers without MSE (older iOS Safari) fall back to native playback.
    const Hls = s.hls ? await loadHls().catch(() => null) : null;
    if (Hls?.isSupported()) {
      state.hls = new Hls({ lowLatencyMode: true });
      state.hls.loadSource(s.stream);
      state.hls.attachMedia(el.audio);
      state.hls.on(Hls.Events.ERROR, (_, d) => { if (d.fatal) onError(); });
    } else {
      el.audio.src = s.stream;
    }
    await el.audio.play();
  } catch (e) {
    if (e?.name === "AbortError") return; // superseded by another station
    onError();
  }
}

function stopStream() {
  if (state.hls) { state.hls.destroy(); state.hls = null; }
  el.audio.pause();
  el.audio.removeAttribute("src");
  el.audio.load();
}

function pause() {
  // Live streams buffer while paused; drop the connection so resuming jumps to live.
  stopStream();
  state.playing = false;
  state.loading = false;
  renderNow();
  updateMediaSession();
}

function toggle() {
  if (!state.current) return;
  state.playing || state.loading ? pause() : play();
}

function step(dir) {
  const list = state.view.length ? state.view : state.stations;
  if (!list.length) return;
  const i = list.findIndex((s) => s.id === state.current?.id);
  const next = list[(i + dir + list.length) % list.length];
  select(next);
  el.list.querySelector(`[data-id="${next.id}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function onError() {
  if (!state.current) return;
  state.loading = false;
  state.playing = false;
  renderNow();
  el.nowLabel.textContent = "Yayın açılamadı";
  toast(`${state.current.name} şu an yayında değil.`);
}

let hlsPromise;
function loadHls() {
  if (window.Hls) return Promise.resolve(window.Hls);
  hlsPromise ||= new Promise((resolve, reject) => {
    const sc = document.createElement("script");
    sc.src = HLS_SRC;
    sc.onload = () => resolve(window.Hls);
    sc.onerror = reject;
    document.head.append(sc);
  });
  return hlsPromise;
}

el.audio.addEventListener("playing", () => { state.loading = false; state.playing = true; renderNow(); updateMediaSession(); });
el.audio.addEventListener("waiting", () => { if (state.playing) { state.loading = true; renderNow(); } });
el.audio.addEventListener("error", () => { if (el.audio.getAttribute("src") && !state.hls) onError(); });

function updateMediaSession() {
  if (!("mediaSession" in navigator) || !state.current) return;
  const s = state.current;
  navigator.mediaSession.metadata = new MediaMetadata({
    title: s.name,
    artist: s.city ? `${s.city} · Radyo Türkiye` : "Radyo Türkiye",
    artwork: [
      { src: s.logo, sizes: "160x160", type: "image/webp" },
      { src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  });
  navigator.mediaSession.playbackState = state.playing ? "playing" : "paused";
}

if ("mediaSession" in navigator) {
  const ms = navigator.mediaSession;
  ms.setActionHandler("play", play);
  ms.setActionHandler("pause", pause);
  ms.setActionHandler("stop", pause);
  ms.setActionHandler("previoustrack", () => step(-1));
  ms.setActionHandler("nexttrack", () => step(1));
}

/* ---------- Favorites / share ---------- */

function toggleFav(id) {
  state.favs.has(id) ? state.favs.delete(id) : state.favs.add(id);
  store.set(FAV_KEY, [...state.favs]);
  const on = state.favs.has(id);
  el.list.querySelector(`[data-id="${id}"] .row-fav`)?.setAttribute("aria-pressed", on);
  if (state.current?.id === id) el.favBtn.setAttribute("aria-pressed", on);
  const favChip = el.chips.querySelector('[data-cat="fav"] sup');
  if (favChip) favChip.textContent = state.favs.size;
  if (state.cat === "fav") applyFilter();
}

async function share() {
  const s = state.current;
  if (!s) return;
  const url = new URL(location.href);
  url.hash = `s=${s.id}`;
  const data = { title: s.name, text: `${s.name} — Radyo Türkiye`, url: url.toString() };
  try {
    if (navigator.share) await navigator.share(data);
    else { await navigator.clipboard.writeText(data.url); toast("Bağlantı kopyalandı."); }
  } catch {}
}

/* ---------- Full player sheet ---------- */

function openPlayer() {
  if (!state.current) return;
  el.player.hidden = false;
  el.player.removeAttribute("data-closing");
  el.player.classList.remove("enter");
  void el.player.offsetWidth;
  el.player.classList.add("enter");
  renderDial();
  history.pushState({ player: true }, "");
  el.playBtn.focus({ preventScroll: true });
}

function closePlayer(fromPop = false) {
  if (el.player.hidden) return;
  el.player.setAttribute("data-closing", "");
  setTimeout(() => { el.player.hidden = true; el.player.removeAttribute("data-closing"); }, 450);
  if (!fromPop && history.state?.player) history.back();
}

window.addEventListener("popstate", () => closePlayer(true));

let toastTimer;
function toast(msg) {
  el.toast.textContent = msg;
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.toast.hidden = true), 2800);
}

/* ---------- Theme ---------- */

const THEME_KEY = "rtr:theme";
const themeEl = $("#theme");
const darkMq = matchMedia("(prefers-color-scheme: dark)");

function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") root.dataset.theme = theme;
  else delete root.dataset.theme;
  themeEl.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.theme === (theme || "auto")));
  // Forced themes override the media-scoped theme-color metas.
  const dark = theme === "dark" || (theme !== "light" && darkMq.matches);
  const color = dark ? "#0b0b0b" : "#ebebe8";
  for (const m of document.querySelectorAll('meta[name="theme-color"]')) m.content = theme === "light" || theme === "dark" ? color : m.id === "themeDark" ? "#0b0b0b" : "#ebebe8";
}

themeEl.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  const theme = b.dataset.theme;
  // Stored raw (not JSON) so the inline script in <head> can read it before paint.
  try { theme === "auto" ? localStorage.removeItem(THEME_KEY) : localStorage.setItem(THEME_KEY, theme); } catch {}
  applyTheme(theme);
});

applyTheme((() => { try { return localStorage.getItem(THEME_KEY); } catch { return null; } })());

/* ---------- Events ---------- */

el.list.addEventListener("click", (e) => {
  const row = e.target.closest(".row");
  if (!row) return;
  const id = row.dataset.id;
  if (e.target.closest(".row-fav")) return toggleFav(id);
  const s = state.stations.find((x) => x.id === id);
  if (!s) return;
  if (state.current?.id === id) return toggle();
  select(s);
});

function onChip(attr, key) {
  return (e) => {
    const c = e.target.closest(".chip");
    if (!c) return;
    const v = c.getAttribute(attr) || null;
    state[key] = state[key] === v ? null : v;
    e.currentTarget.querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", (x.getAttribute(attr) || null) === state[key]));
    applyFilter();
  };
}
el.chips.addEventListener("click", onChip("data-cat", "cat"));
el.groups.addEventListener("click", onChip("data-group", "group"));

let searchTimer;
el.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.query = el.search.value; applyFilter(); }, 80);
});

el.miniPlay.addEventListener("click", toggle);
el.miniOpen.addEventListener("click", openPlayer);
el.playerClose.addEventListener("click", () => closePlayer());
el.playBtn.addEventListener("click", toggle);
el.prevBtn.addEventListener("click", () => step(-1));
el.nextBtn.addEventListener("click", () => step(1));
el.favBtn.addEventListener("click", () => state.current && toggleFav(state.current.id));
el.shareBtn.addEventListener("click", share);
window.addEventListener("resize", () => state.current && !el.player.hidden && renderDial());

document.addEventListener("keydown", (e) => {
  const typing = e.target === el.search;
  if (e.key === "/" && !typing) { e.preventDefault(); el.search.focus(); return; }
  if (e.key === "Escape") { if (typing) { el.search.blur(); } else closePlayer(); return; }
  if (typing) return;
  if (e.key === " " && e.target.tagName !== "BUTTON") { e.preventDefault(); toggle(); }
  if (e.key === "ArrowRight") step(1);
  if (e.key === "ArrowLeft") step(-1);
});

// Deep link: #s=<station id>
function fromHash() {
  const m = location.hash.match(/s=([\w-]+)/);
  if (!m) return;
  const s = state.stations.find((x) => x.id === m[1]);
  if (s) { select(s, { autoplay: false }); history.replaceState(null, "", location.pathname); }
}

/* ---------- Boot ---------- */

load().then(fromHash);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
